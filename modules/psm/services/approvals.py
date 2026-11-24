# Indent approvals and SLA reminder/escalation sweep (PSM-UC-011, 012, 016).
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm.domain import approval_policy as ap
from modules.psm.domain import state_machine as sm
from modules.psm.models import Indent, InternalIssue, StockReservation
from modules.psm.selectors import scoping
from modules.psm.services.common import (
    enqueue_notification,
    policy_to_spec,
    require_active_policy,
    translate_errors,
)
from modules.psm.services.indents import transition_indent


def _reject_by_dept_admin(actor, indent: Indent, reason: str) -> Indent:
    """Release active reservations and reject an indent at Department Admin review."""
    with translate_errors():
        cleaned = ap.ensure_rejection_reason(reason)
    StockReservation.objects.filter(indent_id=indent.pk, status="active").update(
        status="released", released_at=timezone.now()
    )
    transition_indent(
        indent=indent,
        to_status=sm.REJECTED,
        actor=actor,
        actor_lane=sm.DEPT_ADMIN,
        action="indent.rejected",
        reason=cleaned,
        extra_updates={
            "rejection_reason": cleaned,
            "priority": indent.priority,
            "duplicate_reviewed": True,
        },
    )
    enqueue_notification(
        topic="indent.rejected",
        dedupe_key=f"indent.rejected:{indent.pk}:dept",
        recipient_user_id=indent.user_id,
        subject=f"Indent {indent.indent_number} rejected",
        body=f"Your indent was rejected by Department Admin. Reason: {cleaned}",
        payload={"indent_id": indent.pk},
    )
    return indent


def _approve_by_dept_admin(actor, indent: Indent, reason: str) -> None:
    """Approve an indent for either internal stock issue or HOD recommendation."""
    if indent.status == sm.STOCK_RESERVED:
        res = StockReservation.objects.filter(indent_id=indent.pk, status="active").first()
        if res is None:
            raise ConflictError(
                "No active stock reservation exists for this indent; re-run stock check.",
                code="reservation_missing",
            )
        transition_indent(
            indent=indent,
            to_status=sm.INTERNAL_APPROVED,
            actor=actor,
            actor_lane=sm.DEPT_ADMIN,
            action="indent.internal_approved",
            reason=reason or "Approved for internal stock issue",
            extra_updates={"priority": indent.priority, "duplicate_reviewed": True},
        )
        InternalIssue.objects.get_or_create(
            indent=indent,
            defaults={"location": res.location, "reservation": res, "status": "approved"},
        )
        return
    transition_indent(
        indent=indent,
        to_status=sm.DEPARTMENT_REVIEWED,
        actor=actor,
        actor_lane=sm.DEPT_ADMIN,
        action="indent.department_reviewed",
        reason=reason or "Reviewed by Department Admin",
        extra_updates={"priority": indent.priority, "duplicate_reviewed": True},
    )


@transaction.atomic
def dept_admin_review(
    *,
    actor,
    indent_id: int,
    decision: str,
    priority: str | None = None,
    reason: str = "",
) -> Indent:
    """Department Admin reviews indent, records priority, and approves or rejects (PSM-UC-011)."""
    indent = scoping.indents_for(actor).select_for_update(of=("self",)).filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    with translate_errors():
        ap.ensure_not_self_approval(indent.user_id, actor.user_id)
    if priority is not None:
        if priority not in ap.VALID_PRIORITIES:
            raise DomainError(
                "Select a valid priority: normal, high, or critical.", code="invalid_priority"
            )
        indent.priority = priority
    if decision == "reject":
        return _reject_by_dept_admin(actor, indent, reason)
    if decision != "approve":
        raise DomainError(
            "Choose either 'approve' or 'reject' for Department Admin review.",
            code="invalid_decision",
        )
    _approve_by_dept_admin(actor, indent, reason)
    enqueue_notification(
        topic="indent.reviewed",
        dedupe_key=f"indent.reviewed:{indent.pk}:{indent.status}",
        recipient_user_id=indent.user_id,
        subject=f"Indent {indent.indent_number} updated to {indent.status}",
        body=f"Department Admin reviewed your indent (priority: {indent.priority}).",
        payload={"indent_id": indent.pk, "status": indent.status},
    )
    return indent


def _apply_hod_decision(actor, indent: Indent, decision: str, reason: str) -> None:
    """Apply HOD recommend, request_changes, or reject transition."""
    if decision == "recommend":
        transition_indent(
            indent=indent,
            to_status=sm.HOD_RECOMMENDED,
            actor=actor,
            actor_lane=sm.DEPT_HEAD,
            action="indent.hod_recommended",
            reason=reason or "Recommended by Department Head",
        )
        return
    if decision in ("request_changes", "reject"):
        with translate_errors():
            cleaned = ap.ensure_rejection_reason(reason)
        to_status = sm.CHANGES_REQUESTED if decision == "request_changes" else sm.REJECTED
        extra = {"rejection_reason": cleaned} if decision == "reject" else None
        transition_indent(
            indent=indent,
            to_status=to_status,
            actor=actor,
            actor_lane=sm.DEPT_HEAD,
            action=f"indent.{decision}",
            reason=cleaned,
            extra_updates=extra,
        )
        return
    raise DomainError(
        "Choose 'recommend', 'request_changes', or 'reject'.", code="invalid_decision"
    )


@transaction.atomic
def hod_recommend(*, actor, indent_id: int, decision: str, reason: str = "") -> Indent:
    """Department Head recommends onward, requests changes, or rejects (PSM-UC-016)."""
    indent = scoping.indents_for(actor).select_for_update(of=("self",)).filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    with translate_errors():
        ap.ensure_not_self_approval(indent.user_id, actor.user_id)
    _apply_hod_decision(actor, indent, decision, reason)
    enqueue_notification(
        topic=f"indent.{decision}",
        dedupe_key=f"indent.hod:{indent.pk}:{indent.version}:{decision}",
        recipient_user_id=indent.user_id,
        subject=f"Department Head decision on {indent.indent_number}",
        body=f"Department Head recorded '{decision}' on your indent.",
        payload={"indent_id": indent.pk, "status": indent.status},
    )
    return indent


@transaction.atomic
def final_decision(*, actor, indent_id: int, decision: str, reason: str = "") -> Indent:
    """Director/Registrar approves or rejects a high-value indent (PSM-UC-012)."""
    indent = scoping.indents_for(actor).select_for_update(of=("self",)).filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    with translate_errors():
        ap.ensure_not_self_approval(indent.user_id, actor.user_id)
    if decision == "approve":
        transition_indent(
            indent=indent,
            to_status=sm.PROCUREMENT_AUTHORIZED,
            actor=actor,
            actor_lane=sm.FINAL_AUTHORITY,
            action="indent.final_approved",
            reason=reason or "Approved by final authority",
        )
    elif decision == "reject":
        with translate_errors():
            cleaned = ap.ensure_rejection_reason(reason)
        transition_indent(
            indent=indent,
            to_status=sm.REJECTED,
            actor=actor,
            actor_lane=sm.FINAL_AUTHORITY,
            action="indent.rejected",
            reason=cleaned,
            extra_updates={"rejection_reason": cleaned},
        )
    else:
        raise DomainError(
            "Choose 'approve' or 'reject' for final authority review.", code="invalid_decision"
        )
    enqueue_notification(
        topic=f"indent.final_{decision}",
        dedupe_key=f"indent.final:{indent.pk}:{decision}",
        recipient_user_id=indent.user_id,
        subject=f"Final approval decision on {indent.indent_number}",
        body=f"Final authority recorded '{decision}' for your indent.",
        payload={"indent_id": indent.pk, "status": indent.status},
    )
    return indent


def _evaluate_one_sla(pk: int, now, spec: ap.PolicySpec) -> tuple[int, int]:
    """Evaluate SLA thresholds for a single locked indent and enqueue notifications."""
    with transaction.atomic():
        indent = Indent.objects.select_for_update().get(pk=pk)
        if indent.status not in sm.INDENT_PENDING_APPROVAL or indent.current_stage_since is None:
            return 0, 0
        verdict = ap.evaluate_sla(
            stage_since=indent.current_stage_since,
            now=now,
            priority=indent.priority,
            policy=spec,
            already_reminded=indent.sla_reminded_at is not None,
            already_escalated=indent.sla_escalated_at is not None,
        )
        stage_iso = indent.current_stage_since.isoformat()
        payload = {"indent_id": indent.pk, "status": indent.status, "priority": indent.priority}
        if verdict.needs_escalation:
            indent.sla_escalated_at = now
            indent.save(update_fields=["sla_escalated_at", "updated_at"])
            enqueue_notification(
                topic="indent.sla_escalation",
                dedupe_key=f"sla.esc:{indent.pk}:{indent.status}:{stage_iso}",
                recipient_user_id=indent.user_id,
                subject=f"SLA escalation: {indent.indent_number} pending in {indent.status}",
                body=f"Indent {indent.indent_number} exceeded escalation SLA.",
                payload=payload,
            )
            return 0, 1
        if verdict.needs_reminder:
            indent.sla_reminded_at = now
            indent.save(update_fields=["sla_reminded_at", "updated_at"])
            enqueue_notification(
                topic="indent.sla_reminder",
                dedupe_key=f"sla.rem:{indent.pk}:{indent.status}:{stage_iso}",
                recipient_user_id=indent.user_id,
                subject=f"SLA reminder: {indent.indent_number} awaiting action",
                body=f"Indent {indent.indent_number} is pending in {indent.status}.",
                payload=payload,
            )
            return 1, 0
    return 0, 0


def sweep_slas(*, now=None) -> dict[str, int]:
    """Emit idempotent SLA reminders and escalations (BR-PSM-014, AFR-PSM-085)."""
    policy = require_active_policy()
    spec = policy_to_spec(policy)
    now = now or timezone.now()
    reminded = escalated = 0
    pending_ids = list(
        Indent.objects.filter(
            status__in=sm.INDENT_PENDING_APPROVAL, current_stage_since__isnull=False
        ).values_list("pk", flat=True)
    )
    for pk in pending_ids:
        rem, esc = _evaluate_one_sla(pk, now, spec)
        reminded += rem
        escalated += esc
    return {"reminded": reminded, "escalated": escalated}
