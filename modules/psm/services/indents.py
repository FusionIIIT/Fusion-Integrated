# Indent lifecycle services and single transition choke point (PSM-UC-001, 005, 023, 024).
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.psm.domain import indent_rules as ir
from modules.psm.domain import state_machine as sm
from modules.psm.models import Indent, IndentTransition, IndentVersion, StockItem, StockReservation
from modules.psm.selectors import scoping
from modules.psm.services.common import (
    audit_record,
    enqueue_notification,
    next_number,
    policy_to_spec,
    require_active_policy,
    translate_errors,
)


def _indent_snapshot(indent: Indent) -> dict:
    return {
        "department": indent.department,
        "item_id": indent.item_id,
        "item_description": indent.item_description,
        "quantity": indent.quantity,
        "estimated_cost": str(indent.estimated_cost),
        "justification": indent.justification,
        "priority": indent.priority,
        "status": indent.status,
    }


def _check_duplicate(indent: Indent, window_days: int, now) -> int | None:
    recent = (
        Indent.objects.filter(
            department__iexact=indent.department,
            submitted_at__isnull=False,
        )
        .exclude(status__in=(sm.WITHDRAWN, sm.REJECTED))
        .order_by("-submitted_at")[:100]
    )
    refs = [
        ir.ExistingIndentRef(
            indent_id=r.pk,
            department=r.department,
            item_description=r.item_description,
            quantity=r.quantity,
            submitted_at=r.submitted_at,
        )
        for r in recent
    ]
    return ir.find_potential_duplicate(
        department=indent.department,
        item_description=indent.item_description,
        quantity=indent.quantity,
        now=now,
        window_days=window_days,
        candidates=refs,
        exclude_indent_id=indent.pk,
    )


def transition_indent(
    *,
    indent: Indent,
    to_status: str,
    actor,
    actor_lane: str,
    reason: str = "",
    action: str = "indent.transition",
    extra_updates: dict | None = None,
) -> Indent:
    """Single transactional choke point for every indent state change."""
    with translate_errors():
        sm.resolve("indent", indent.status, to_status, actor_lane)
    frm = indent.status
    now = timezone.now()
    indent.status = to_status
    indent.current_stage_since = now
    indent.sla_reminded_at = None
    indent.sla_escalated_at = None
    update_fields = [
        "status",
        "current_stage_since",
        "sla_reminded_at",
        "sla_escalated_at",
        "updated_at",
    ]
    for k, v in (extra_updates or {}).items():
        setattr(indent, k, v)
        if k not in update_fields:
            update_fields.append(k)
    indent.save(update_fields=update_fields)
    IndentTransition.objects.create(
        indent=indent,
        from_status=frm,
        to_status=to_status,
        actor_user_id=getattr(actor, "user_id", None) if actor else None,
        actor_role=scoping.active_role_of(actor) if actor else "system",
        reason=reason[:500],
    )
    audit_record(
        actor=actor,
        action=action,
        target_type="indent",
        target_id=indent.pk,
        from_state=frm,
        to_state=to_status,
        details={"reason": reason} if reason else {},
    )
    return indent


@transaction.atomic
def create_indent(
    *,
    actor,
    department: str,
    item_description: str,
    quantity: int,
    estimated_cost: Decimal,
    justification: str,
    item_id: int | None = None,
    submit: bool = True,
) -> Indent:
    """Create and optionally submit a purchase indent (PSM-UC-001, BR-PSM-001, 015)."""
    policy = require_active_policy()
    spec = policy_to_spec(policy)
    with translate_errors():
        ir.validate_indent_completeness(
            ir.IndentInput(
                item_description=item_description,
                quantity=quantity,
                estimated_cost=estimated_cost,
                justification=justification,
                department=department,
            )
        )
    item = StockItem.objects.filter(pk=item_id, is_active=True).first() if item_id else None
    if item_id is not None and item is None:
        raise NotFoundError("Selected stock item was not found.")
    now = timezone.now()
    indent = Indent.objects.create(
        user_id=actor.user_id,
        department=department.strip(),
        item=item,
        item_description=item_description.strip(),
        quantity=quantity,
        estimated_cost=estimated_cost,
        justification=justification.strip(),
        status=sm.DRAFT,
        version=1,
        policy=policy,
    )
    if submit:
        dup_id = _check_duplicate(indent, spec.duplicate_window_days, now)
        transition_indent(
            indent=indent,
            to_status=sm.SUBMITTED,
            actor=actor,
            actor_lane=sm.EMPLOYEE,
            action="indent.submitted",
            reason="Submitted by requestor",
            extra_updates={
                "indent_number": next_number("IND"),
                "submitted_at": now,
                "is_duplicate_flagged": dup_id is not None,
                "duplicate_of_indent_id": dup_id,
            },
        )
        IndentVersion.objects.create(
            indent=indent, version=1, snapshot=_indent_snapshot(indent), actor_user_id=actor.user_id
        )
        enqueue_notification(
            topic="indent.submitted",
            dedupe_key=f"indent.submitted:{indent.pk}:v1",
            recipient_user_id=actor.user_id,
            subject=f"Indent {indent.indent_number} submitted",
            body=f"Indent for {indent.item_description} (qty {indent.quantity}) submitted.",
            payload={"indent_id": indent.pk, "duplicate_flagged": indent.is_duplicate_flagged},
        )
    return indent


@transaction.atomic
def modify_indent(*, actor, indent_id: int, **changes) -> Indent:
    """Modify an own pending indent and create a new version (PSM-UC-023, BW-PSM-07)."""
    policy = require_active_policy()
    spec = policy_to_spec(policy)
    indent = Indent.objects.select_for_update().filter(pk=indent_id, user_id=actor.user_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    with translate_errors():
        ir.ensure_state_permissible(indent.status, spec.modifiable_states, "modify")
    for key in ("department", "item_description", "quantity", "estimated_cost", "justification"):
        if key in changes:
            val = changes[key]
            setattr(indent, key, val.strip() if isinstance(val, str) else val)
    if "item_id" in changes:
        item_id = changes["item_id"]
        item = StockItem.objects.filter(pk=item_id, is_active=True).first() if item_id else None
        if item_id is not None and item is None:
            raise NotFoundError("Selected stock item was not found.")
        indent.item = item
    with translate_errors():
        ir.validate_indent_completeness(
            ir.IndentInput(
                item_description=indent.item_description,
                quantity=indent.quantity,
                estimated_cost=indent.estimated_cost,
                justification=indent.justification,
                department=indent.department,
            )
        )
    now = timezone.now()
    dup_id = _check_duplicate(indent, spec.duplicate_window_days, now)
    next_ver = indent.version + 1
    extra = {
        "version": next_ver,
        "is_duplicate_flagged": dup_id is not None,
        "duplicate_of_indent_id": dup_id,
        "duplicate_reviewed": False,
        "department": indent.department,
        "item": indent.item,
        "item_description": indent.item_description,
        "quantity": indent.quantity,
        "estimated_cost": indent.estimated_cost,
        "justification": indent.justification,
    }
    if not indent.indent_number:
        extra["indent_number"] = next_number("IND")
        extra["submitted_at"] = now
    transition_indent(
        indent=indent,
        to_status=sm.SUBMITTED,
        actor=actor,
        actor_lane=sm.EMPLOYEE,
        action="indent.modified",
        reason=f"Modified to version {next_ver}",
        extra_updates=extra,
    )
    IndentVersion.objects.create(
        indent=indent,
        version=next_ver,
        snapshot=_indent_snapshot(indent),
        actor_user_id=actor.user_id,
    )
    return indent


@transaction.atomic
def withdraw_indent(*, actor, indent_id: int, reason: str = "") -> Indent:
    """Withdraw or cancel an own indent when policy permits (PSM-UC-005, BR-PSM-007)."""
    policy = require_active_policy()
    spec = policy_to_spec(policy)
    indent = Indent.objects.select_for_update().filter(pk=indent_id, user_id=actor.user_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    with translate_errors():
        ir.ensure_state_permissible(indent.status, spec.withdrawable_states, "withdraw")
    StockReservation.objects.filter(indent_id=indent.pk, status="active").update(
        status="released", released_at=timezone.now()
    )
    transition_indent(
        indent=indent,
        to_status=sm.WITHDRAWN,
        actor=actor,
        actor_lane=sm.EMPLOYEE,
        action="indent.withdrawn",
        reason=reason.strip() or "Withdrawn by requestor",
    )
    enqueue_notification(
        topic="indent.withdrawn",
        dedupe_key=f"indent.withdrawn:{indent.pk}",
        recipient_user_id=actor.user_id,
        subject=f"Indent {indent.indent_number or indent.pk} withdrawn",
        body="Your purchase indent has been withdrawn.",
        payload={"indent_id": indent.pk},
    )
    return indent


@transaction.atomic
def repeat_as_draft(*, actor, indent_id: int) -> Indent:
    """Create a new editable draft copied from a visible prior indent (PSM-UC-024, AFR-PSM-011)."""
    source = scoping.indents_for(actor).filter(pk=indent_id).first()
    if source is None:
        raise NotFoundError("Source indent not found.")
    policy = require_active_policy()
    draft = Indent.objects.create(
        user_id=actor.user_id,
        department=source.department,
        item=source.item,
        item_description=source.item_description,
        quantity=source.quantity,
        estimated_cost=source.estimated_cost,
        justification=source.justification,
        status=sm.DRAFT,
        version=1,
        repeated_from_indent_id=source.pk,
        policy=policy,
    )
    audit_record(
        actor=actor,
        action="indent.repeated",
        target_type="indent",
        target_id=draft.pk,
        to_state=sm.DRAFT,
        details={"source_indent_id": source.pk},
    )
    return draft
