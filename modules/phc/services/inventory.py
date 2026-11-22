"""PHC services: inventory management and procurement.

PHC-UC-09, PHC-UC-10, PHC-UC-14, PHC-UC-16.
AFR-PHC-024 … AFR-PHC-031.
PHC-BR-07, PHC-BR-10, PHC-BR-11.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.phc.domain.state_machine import (
    InvalidRequisitionTransition,
    RequisitionState,
    advance_requisition,
)
from modules.phc.models import (
    InventoryAudit,
    InventoryItem,
    ProcurementRequisition,
    RequisitionLineItem,
)
from modules.phc.services import notifications

log = logging.getLogger("fusion.phc.inventory")


# ---------------------------------------------------------------------------
# Inventory stock control  (AFR-PHC-024, AFR-PHC-025, AFR-PHC-026)
# ---------------------------------------------------------------------------


def adjust_stock(
    *,
    item: InventoryItem,
    delta: Decimal,
    actor_user_id: int,
    notes: str = "",
) -> InventoryItem:
    """Add (delta > 0) or deduct (delta < 0) stock.

    Writes an immutable InventoryAudit row (PHC-BR-09).
    Fires low-stock notification if the new level is below threshold (PHC-BR-07).
    """
    if delta == 0:
        raise BadRequestError("Stock delta must be non-zero.")

    new_qty = item.stock_quantity + delta
    if new_qty < 0:
        raise ConflictError(
            f"Deduction of {abs(delta)} {item.unit} would bring stock negative "
            f"(current: {item.stock_quantity} {item.unit}).",
            code="insufficient_stock",
        )

    with transaction.atomic():
        before = item.stock_quantity
        item.stock_quantity = new_qty
        item.save(update_fields=["stock_quantity", "updated_at"])
        InventoryAudit.objects.create(
            item=item,
            delta=delta,
            quantity_before=before,
            quantity_after=new_qty,
            actor_user_id=actor_user_id,
            notes=notes,
        )

    log.info(
        "phc.inventory.adjusted item=%s delta=%s new_qty=%s by=%s",
        item.pk,
        delta,
        new_qty,
        actor_user_id,
    )

    # PHC-BR-07: alert if strictly below threshold
    if item.is_low_stock:
        notifications.notify_low_stock(item=item, actor_user_id=actor_user_id)

    return item


# ---------------------------------------------------------------------------
# Procurement requisitions  (AFR-PHC-027 … AFR-PHC-031)
# ---------------------------------------------------------------------------


def create_requisition(
    *,
    title: str,
    justification: str = "",
    line_items: list[dict],  # [{"item_name": str, "quantity": Decimal, "unit": str}]
    actor_user_id: int,
) -> ProcurementRequisition:
    """PHC-UC-10: PHC Staff submits a procurement requisition (AFR-PHC-027).

    Sets status = pending_approval (PHC-BR-10) and routes to Approving Authority.
    """
    if not line_items:
        raise BadRequestError("A requisition must contain at least one line item.")

    with transaction.atomic():
        req = ProcurementRequisition.objects.create(
            title=title,
            justification=justification,
            status=RequisitionState.PENDING_APPROVAL,
            submitted_by_user_id=actor_user_id,
        )
        RequisitionLineItem.objects.bulk_create(
            [
                RequisitionLineItem(
                    requisition=req,
                    item_name=li["item_name"],
                    quantity=Decimal(str(li["quantity"])),
                    unit=li.get("unit", ""),
                    notes=li.get("notes", ""),
                )
                for li in line_items
            ]
        )
    log.info("phc.requisition.created req=%s by=%s", req.pk, actor_user_id)
    return req


def _advance_requisition(
    *,
    req: ProcurementRequisition,
    to_status: str,
    actor_role: str,
    actor_user_id: int,
    notes: str = "",
) -> ProcurementRequisition:
    try:
        advance_requisition(req.status, to_status, actor_role)
    except InvalidRequisitionTransition as exc:
        raise ConflictError(str(exc), code="invalid_requisition_transition") from exc

    with transaction.atomic():
        req.status = to_status
        req.decided_by_user_id = actor_user_id
        req.decision_notes = notes
        req.decided_at = timezone.now()
        req.save(
            update_fields=[
                "status",
                "decided_by_user_id",
                "decision_notes",
                "decided_at",
                "updated_at",
            ]
        )
    return req


def decide_requisition(
    *,
    req: ProcurementRequisition,
    actor_user_id: int,
    approve: bool,
    notes: str = "",
) -> ProcurementRequisition:
    """PHC-UC-16: Approving Authority approves or rejects a requisition.

    PHC-BR-10, PHC-BR-11.
    """
    to_status = RequisitionState.APPROVED if approve else RequisitionState.REJECTED
    req = _advance_requisition(
        req=req,
        to_status=to_status,
        actor_role="approving_authority",
        actor_user_id=actor_user_id,
        notes=notes,
    )
    # PHC-BR-11: notify originating PHC Staff
    notifications.notify_requisition_decided(
        requisition=req,
        new_status=to_status,
        actor_user_id=actor_user_id,
    )
    log.info("phc.requisition.decided req=%s status=%s by=%s", req.pk, to_status, actor_user_id)
    return req


def mark_fulfilled(
    *,
    req: ProcurementRequisition,
    actor_user_id: int,
) -> ProcurementRequisition:
    """PHC-UC-14: PHC Staff marks an approved requisition as Fulfilled.

    AFR-PHC-031. Does NOT automatically update inventory (removed from scope -
    per UC-14 notes: stock changes remain a separate PHC Staff action).
    """
    req = _advance_requisition(
        req=req,
        to_status=RequisitionState.FULFILLED,
        actor_role="phc_staff",
        actor_user_id=actor_user_id,
        notes="Marked fulfilled after delivery.",
    )
    with transaction.atomic():
        req.fulfilled_at = timezone.now()
        req.save(update_fields=["fulfilled_at", "updated_at"])
    log.info("phc.requisition.fulfilled req=%s by=%s", req.pk, actor_user_id)
    return req
