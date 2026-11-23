"""Procurement requisitions (PHC-UC-10, PHC-UC-14, PHC-UC-16) through one choke point."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.phc.domain.state_machine import (
    REQUISITION_TRANSITIONS,
    IllegalTransition,
    RequisitionStatus,
    resolve,
)
from modules.phc.models import InventoryItem, Requisition, RequisitionLine
from modules.phc.selectors import scoping
from modules.phc.services import trail

STATUS_LABELS = dict(RequisitionStatus.CHOICES)


@transaction.atomic
def submit(*, actor, purpose: str, lines: list[dict]) -> Requisition:
    # PHC-UC-10: created straight into Pending Approval, routed to the Approving Authority.
    if not lines:
        raise BadRequestError("Add at least one item and quantity.", code="no_lines")
    item_ids = [line["item_id"] for line in lines]
    if len(set(item_ids)) != len(item_ids):
        raise BadRequestError("List each item once, with its total quantity.",
                              code="duplicate_line")
    if any(Decimal(line["quantity"]) <= 0 for line in lines):
        raise BadRequestError("Every quantity must be more than zero.", code="bad_quantity")
    known = set(InventoryItem.objects.filter(pk__in=item_ids).values_list("pk", flat=True))
    if known != set(item_ids):
        raise BadRequestError("One of the items is not in the PHC inventory.",
                              code="unknown_item")
    requisition = Requisition.objects.create(originator_user_id=actor.user_id, purpose=purpose)
    RequisitionLine.objects.bulk_create(
        RequisitionLine(requisition=requisition, item_id=line["item_id"],
                        quantity=line["quantity"]) for line in lines)
    return requisition


@transaction.atomic
def transition(*, actor, requisition_id: int, event: str, note: str = "") -> Requisition:
    requisition = Requisition.objects.select_for_update().filter(pk=requisition_id).first()
    if requisition is None or not scoping.requisitions_for(actor).filter(
            pk=requisition_id).exists():
        raise NotFoundError("That requisition does not exist.")
    if requisition.status in RequisitionStatus.TERMINAL:
        raise ConflictError(
            f"This requisition is already {STATUS_LABELS[requisition.status].lower()}.",
            code="requisition_closed")
    try:
        move = resolve(REQUISITION_TRANSITIONS, requisition.status, event, actor.permissions)
    except IllegalTransition as exc:
        raise ConflictError(
            f"This requisition is {STATUS_LABELS[requisition.status].lower()}, so it cannot "
            f"be {'fulfilled' if event == 'fulfill' else event + 'd'} now.",
            code="illegal_transition") from exc
    now = timezone.now()
    fields = ["status", "updated_at"]
    if event in ("approve", "reject"):
        if requisition.originator_user_id == actor.user_id:
            raise ConflictError("You cannot decide a requisition you raised.",
                                code="own_requisition")
        requisition.decided_by_user_id = actor.user_id
        requisition.decision_note = note
        requisition.decided_at = now
        fields += ["decided_by_user_id", "decision_note", "decided_at"]
    else:
        requisition.fulfilled_by_user_id = actor.user_id
        requisition.fulfilled_at = now
        fields += ["fulfilled_by_user_id", "fulfilled_at"]
    requisition.status = move.target
    requisition.save(update_fields=fields)
    if event in ("approve", "reject"):
        # PHC-BR-11
        trail.notify(recipient_user_id=requisition.originator_user_id,
                     kind="requisition_decision",
                     message=f"Your requisition #{requisition.pk} was "
                             f"{STATUS_LABELS[move.target].lower()}.",
                     resource_type="requisition", resource_id=requisition.pk)
    return requisition
