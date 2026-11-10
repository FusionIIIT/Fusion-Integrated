"""VH inventory, threshold alerts and replenishment (UC-VH-014, 015, 025)."""
from __future__ import annotations

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.visitor_hostel.domain import duty
from modules.visitor_hostel.domain import inventory as rules
from modules.visitor_hostel.domain import permissions as perms
from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import (
    InventoryAdjustment,
    InventoryAlert,
    InventoryItem,
    ReplenishmentRequirement,
)
from modules.visitor_hostel.selectors import duty as duty_selectors
from modules.visitor_hostel.services import authz, notifications

log = logging.getLogger("fusion.visitor_hostel.inventory")


def _evaluate(item: InventoryItem) -> InventoryAlert | None:
    """UC-VH-025, run in the same transaction as every quantity or threshold change."""
    open_alert = InventoryAlert.objects.filter(item=item, resolved_at__isnull=True).first()
    if not rules.is_below_threshold(item.quantity, item.min_threshold):
        if open_alert:
            open_alert.resolved_at = timezone.now()
            open_alert.save(update_fields=["resolved_at"])
        return None
    if open_alert:
        return open_alert
    alert = InventoryAlert.objects.create(item=item, quantity_at_alert=item.quantity,
                                          threshold_at_alert=item.min_threshold)
    notifications.enqueue(
        topic="inventory.below_threshold", dedupe_key=f"vh:inventory:{alert.pk}",
        recipient_user_id=duty_selectors.current_holder_id(duty.CARETAKER),
        subject=f"VH inventory low: {item.name}",
        body=(f"{item.name} is at {item.quantity} {item.unit}, below its minimum "
              f"of {item.min_threshold}."),
        payload={"item_id": item.pk, "alert_id": alert.pk})
    log.info("visitor_hostel.inventory.below_threshold item=%s qty=%s min=%s",
             item.pk, item.quantity, item.min_threshold)
    return alert


@transaction.atomic
def create_item(*, actor, name: str, kind: str, unit: str = "pcs", quantity: int = 0,
                min_threshold: int = 0) -> InventoryItem:
    authz.require_operator(actor, sm.CARETAKER, perms.INVENTORY_MANAGE)
    if kind not in rules.KINDS:
        raise BadRequestError(f"Kind must be one of {', '.join(rules.KINDS)}.",
                              code="invalid_kind")
    if quantity < 0 or min_threshold < 0:
        raise BadRequestError("Quantities cannot be negative.", code="negative_quantity")
    try:
        with transaction.atomic():
            item = InventoryItem.objects.create(name=name.strip(), kind=kind, unit=unit,
                                                quantity=quantity,
                                                min_threshold=min_threshold)
    except IntegrityError as exc:
        raise ConflictError("An item with that name already exists.",
                            code="duplicate_item") from exc
    InventoryAdjustment.objects.create(item=item, delta=quantity, quantity_after=quantity,
                                       reason="opening stock", actor_user_id=actor.user_id)
    _evaluate(item)
    return item


def _locked(item_id: int) -> InventoryItem:
    item = InventoryItem.objects.select_for_update().filter(pk=item_id).first()
    if item is None:
        raise NotFoundError("No such inventory item.")
    return item


@transaction.atomic
def adjust(*, item_id: int, actor, delta: int, reason: str) -> InventoryItem:
    """Every change is a ledger row, so usage is reportable (AFR-VH-085)."""
    authz.require_operator(actor, sm.CARETAKER, perms.INVENTORY_MANAGE)
    if delta == 0:
        raise BadRequestError("An adjustment must change the quantity.", code="zero_delta")
    if not reason.strip():
        raise BadRequestError("Say why the quantity changed.", code="reason_required")
    item = _locked(item_id)
    try:
        item.quantity = rules.apply_delta(item.quantity, delta)
    except rules.NegativeStock as exc:
        raise ConflictError(str(exc), code="negative_stock") from exc
    item.save(update_fields=["quantity", "updated_at"])
    InventoryAdjustment.objects.create(item=item, delta=delta, quantity_after=item.quantity,
                                       reason=reason[:200], actor_user_id=actor.user_id)
    _evaluate(item)
    return item


@transaction.atomic
def set_threshold(*, item_id: int, actor, min_threshold: int) -> InventoryItem:
    authz.require_operator(actor, sm.CARETAKER, perms.INVENTORY_MANAGE)
    if min_threshold < 0:
        raise BadRequestError("A threshold cannot be negative.", code="negative_quantity")
    item = _locked(item_id)
    item.min_threshold = min_threshold
    item.save(update_fields=["min_threshold", "updated_at"])
    _evaluate(item)
    return item


@transaction.atomic
def raise_replenishment(*, actor, item_id: int, quantity_required: int,
                        note: str = "") -> ReplenishmentRequirement:
    """Records a requirement for the VH In-Charge. Procurement is out of scope."""
    authz.require_operator(actor, sm.CARETAKER, perms.REPLENISHMENT_CREATE)
    if quantity_required < 1:
        raise BadRequestError("Ask for at least one.", code="invalid_quantity")
    item = _locked(item_id)
    return ReplenishmentRequirement.objects.create(
        item=item, quantity_required=quantity_required, note=note[:300],
        raised_by_user_id=actor.user_id)


@transaction.atomic
def approve_replenishment(*, requirement_id: int, actor) -> ReplenishmentRequirement:
    """UC-VH-015. The spec states no rejection outcome, so there is none."""
    authz.require_operator(actor, sm.INCHARGE, perms.REPLENISHMENT_APPROVE)
    req = (ReplenishmentRequirement.objects.select_for_update()
           .filter(pk=requirement_id).first())
    if req is None:
        raise NotFoundError("No such replenishment requirement.")
    if req.raised_by_user_id == actor.user_id:
        raise PermissionDeniedError("You raised this requirement; it needs another "
                                    "officer's approval.", code="self_decision")
    if req.status != "pending":
        raise ConflictError("This requirement is already approved.",
                            code="already_approved")
    req.status = "approved"
    req.approved_by_user_id = actor.user_id
    req.approved_at = timezone.now()
    req.save(update_fields=["status", "approved_by_user_id", "approved_at", "updated_at"])
    return req
