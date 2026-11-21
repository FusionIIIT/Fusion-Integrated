"""Audited HR workflow decisions by the currently assigned authority.

Only a verified IAM active designation may act. Every decision snapshots one
state transition and notification in the same database transaction.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.hreis.domain import leave, routing, workflow
from modules.hreis.models import (
    ApprovalRouteStep,
    AuditEvent,
    EmployeeServiceRecord,
    HRRequest,
    HRRequestTransition,
    LeaveLedgerEntry,
    Notification,
    OutboxEvent,
)
from modules.hreis.services.authz import require
from modules.hreis.services.requests import _key, _route

_ADMIN = frozenset({"hradmin"})
_AUTHORITY = routing.AUTHORITY_DESIGNATIONS


def _append(actor, row, move, key, *, reason="", step_after=None):
    step_before = row.route_step
    row.state = move.target
    row.route_step = step_before if step_after is None else step_after
    row.version += 1
    row.save(update_fields=["state", "route_step", "version", "updated_at"])
    HRRequestTransition.objects.create(
        request=row,
        source=move.source,
        event=move.event,
        target=move.target,
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        specification=move.specification,
        step_before=step_before,
        step_after=row.route_step,
        idempotency_key=key,
        reason=reason,
    )
    AuditEvent.objects.create(
        event_key=f"request:{key}",
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        subject_user_id=row.user_id,
        action=f"{row.family}_{move.event}",
        resource_kind="hr_request",
        resource_id=row.pk,
        data={
            "from": move.source,
            "to": move.target,
            "step_before": step_before,
            "step_after": row.route_step,
            "specification": move.specification,
        },
    )
    Notification.objects.create(
        event_key=f"notification:{key}",
        recipient_user_id=row.user_id,
        request=row,
        title=f"{row.family.upper()} request: {move.event}",
        message=f"Your request is now {move.target.replace('_', ' ')}.",
    )
    OutboxEvent.objects.create(
        event_key=f"outbox:{key}",
        event_type="hreis.notification",
        payload={
            "request_id": row.pk,
            "subject_user_id": row.user_id,
            "family": row.family,
            "state": row.state,
            "event": move.event,
        },
    )
    return row


@transaction.atomic
def verify_claim(
    actor,
    *,
    request_id: int,
    document_review_reference: str,
    eligibility_basis: str,
    idempotency_key: str,
) -> HRRequest:
    require(actor, "hreis.claim.review", allowed_roles=_ADMIN)
    key = _key(idempotency_key)
    row = (
        HRRequest.objects.select_for_update()
        .filter(
            pk=request_id,
            family__in=("ltc", "cpda"),
            state=workflow.AWAITING_HR_VERIFICATION,
        )
        .first()
    )
    if row is None:
        raise NotFoundError(
            "No pending HR-verification claim was found.", code="claim_not_pending_verification"
        )
    if row.user_id == actor.user_id:
        raise NotFoundError(
            "No claim is assigned to you for independent review.", code="claim_not_assigned"
        )
    if (
        not isinstance(document_review_reference, str)
        or not document_review_reference.strip()
        or not isinstance(eligibility_basis, str)
        or not eligibility_basis.strip()
    ):
        raise BadRequestError(
            "Record the evidence and eligibility basis of HR review.",
            code="missing_review_evidence",
        )
    employee = EmployeeServiceRecord.objects.filter(user_id=row.user_id).first()
    if employee is None:
        raise ConflictError("Employee service record is missing.", code="employee_record_missing")
    from modules.directory.contracts import get_users

    user = get_users([row.user_id]).get(row.user_id)
    if user is None or user.kind not in {"faculty", "staff"}:
        raise ConflictError(
            "Employee category cannot be independently verified.",
            code="employee_identity_unavailable",
        )
    if row.policy_version_id is None:
        raise ConflictError("Claim has no frozen institutional policy.", code="policy_unavailable")
    route = _route(row.family, user.kind, employee.department, row.policy_version)
    guards = {
        "documents_verified": True,
        "eligibility_verified": True,
        "route_configured": True,
        "verification_passed": True,
    }
    move = workflow.resolve(
        row.family,
        row.state,
        "verify",
        workflow.HR_ADMINISTRATOR,
        guard_results=guards,
    )
    row.claim.hr_verified_by_user_id = actor.user_id
    row.claim.save(update_fields=["hr_verified_by_user_id"])
    for position, designation in enumerate(route.authorities):
        ApprovalRouteStep.objects.create(
            request=row,
            position=position,
            designation=designation,
            policy_version_label=route.version,
        )
    return _append(
        actor,
        row,
        move,
        key,
        reason=f"Manual HR attestation; documents: {document_review_reference}; "
        f"eligibility: {eligibility_basis}",
    )


def _route_snapshot(row) -> routing.ApprovalRoute:
    steps = list(ApprovalRouteStep.objects.filter(request=row).order_by("position"))
    if not steps or [s.position for s in steps] != list(range(len(steps))):
        raise ConflictError(
            "The frozen approval route is unavailable.", code="route_snapshot_missing"
        )
    return routing.ApprovalRoute(
        family=row.family,
        employee_kind="faculty",
        department="frozen",
        version=steps[0].policy_version_label,
        authorities=tuple(s.designation for s in steps),
    )


@transaction.atomic
def decide_request(
    actor, *, request_id: int, event: str, reason: str, idempotency_key: str
) -> HRRequest:
    if event not in {"approve", "reject", "forward"}:
        raise BadRequestError("Choose approve, reject or forward.", code="invalid_decision")
    # This endpoint supports leave/LTC/CPDA. Annual appraisal has a distinct
    # finalization and reviewer-assignment procedure.
    row = (
        HRRequest.objects.select_for_update()
        .filter(
            pk=request_id,
            family__in=("leave", "ltc", "cpda"),
            state=workflow.PENDING_AUTHORITY,
        )
        .first()
    )
    if row is None:
        raise NotFoundError("No pending approval request was found.", code="request_not_pending")
    if row.user_id == getattr(actor, "user_id", None):
        raise NotFoundError(
            "No request is assigned to your current role.", code="request_not_assigned"
        )
    permission = "hreis.leave.approve" if row.family == "leave" else "hreis.claim.approve"
    require(actor, permission, allowed_roles=_AUTHORITY)
    key = _key(idempotency_key)
    route = _route_snapshot(row)
    try:
        routing.require_current_authority(route, row.route_step, actor.active_role)
    except routing.RouteError as exc:
        raise NotFoundError(
            "No request is assigned to your current role.", code="request_not_assigned"
        ) from exc
    if event == "reject" and (not isinstance(reason, str) or not reason.strip()):
        raise BadRequestError("Give the rejection reason.", code="rejection_reason_missing")
    if event == "approve" and row.route_step != len(route.authorities) - 1:
        raise ConflictError("Forward to the next assigned authority first.", code="route_not_final")
    if event == "forward" and row.route_step == len(route.authorities) - 1:
        raise ConflictError("There is no later approval authority.", code="route_complete")
    guards = {
        "current_authority": True,
        "balance_valid": True,
        "next_authority_exists": event == "forward",
    }
    if event == "approve" and row.family == "leave":
        # Serialize all leave approvals for this employee through one stable row,
        # so two concurrent approvals cannot both spend the same opening balance.
        EmployeeServiceRecord.objects.select_for_update().get(user_id=row.user_id)
        total = leave.ledger_balance(
            LeaveLedgerEntry.objects.filter(
                user_id=row.user_id,
                leave_type=row.subtype,
            ).values_list("quantity", flat=True)
        )
        try:
            duration = Decimal(row.payload["duration"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ConflictError(
                "The frozen leave duration is invalid.", code="invalid_leave_duration"
            ) from exc
        if not duration.is_finite() or duration <= 0 or total < duration:
            raise ConflictError(
                "The employee does not have enough leave balance.", code="insufficient_balance"
            )
    move = workflow.resolve(
        row.family,
        row.state,
        event,
        workflow.AUTHORITY,
        guard_results=guards,
    )
    if event == "approve" and row.family == "leave":
        LeaveLedgerEntry.objects.create(
            user_id=row.user_id,
            leave_type=row.subtype,
            quantity=-duration,
            request=row,
            policy_version=row.policy_version,
            event_key=f"leave-approved:{key}",
            actor_user_id=actor.user_id,
        )
    next_step = row.route_step + 1 if event == "forward" else None
    return _append(actor, row, move, key, reason=reason.strip(), step_after=next_step)
