"""Inventory management and procurement requisition services (CFR-PHC-006, CFR-PHC-007)."""
from typing import Sequence
from django.utils import timezone

from modules.phc.domain.entities import RequisitionStatus, StockThresholdEvaluation
from modules.phc.domain.errors import InsufficientStockError
from modules.phc.domain.state_machine import RequisitionStateMachine
from modules.phc.models.inventory import (
    InventoryItem,
    InventoryStockAdjustment,
    ProcurementRequisition,
    RequisitionItem,
)
from modules.phc.services.audit import record_audit_event
from modules.phc.services.notifications import notify_user


def create_or_update_item(
    item_code: str,
    name: str,
    category: str = "Medicine",
    reorder_threshold: int = 10,
    unit: str = "units",
    description: str = "",
    item_id: int | None = None,
) -> InventoryItem:
    if item_id:
        item = InventoryItem.objects.get(id=item_id)
        item.item_code = item_code.strip()
        item.name = name.strip()
        item.category = category.strip()
        item.reorder_threshold = reorder_threshold
        item.unit = unit.strip()
        item.description = description.strip()
        item.save()
        return item

    return InventoryItem.objects.create(
        item_code=item_code.strip(),
        name=name.strip(),
        category=category.strip(),
        reorder_threshold=reorder_threshold,
        unit=unit.strip(),
        description=description.strip(),
    )


def adjust_stock(
    item_id: int,
    adjustment_type: str,
    quantity: int,
    reason: str,
    actor_user_id: int,
    actor_username: str,
) -> InventoryItem:
    """Adds to or deducts from inventory stock (AFR-PHC-024, 025, 026; BR-PHC-07, BR-PHC-09)."""
    item = InventoryItem.objects.get(id=item_id)
    prev_stock = item.stock_level

    if adjustment_type == "ADD":
        item.stock_level += quantity
    elif adjustment_type == "DEDUCT":
        if item.stock_level < quantity:
            raise InsufficientStockError(
                f"Cannot deduct {quantity} {item.unit}. Current available stock is only {item.stock_level} {item.unit}."
            )
        item.stock_level -= quantity
    else:
        raise ValueError(f"Unknown adjustment type '{adjustment_type}'.")

    item.save()

    # Log adjustment
    InventoryStockAdjustment.objects.create(
        item=item,
        adjustment_type=adjustment_type,
        quantity=quantity,
        previous_stock=prev_stock,
        new_stock=item.stock_level,
        reason=reason.strip(),
        adjusted_by_user_id=actor_user_id,
    )

    # BR-09: Immutable audit trail for inventory level change
    record_audit_event(
        target_type="INVENTORY_LEVEL",
        target_id=item.item_code,
        action=f"STOCK_{adjustment_type}",
        details={
            "quantity": quantity,
            "previous_stock": prev_stock,
            "new_stock": item.stock_level,
            "reason": reason,
        },
        actor_user_id=actor_user_id,
        actor_username=actor_username,
    )

    # BR-07: Low-stock warning trigger (AFR-PHC-025, 026)
    threshold_eval = StockThresholdEvaluation(
        item_code=item.item_code,
        current_stock=item.stock_level,
        reorder_threshold=item.reorder_threshold,
    )
    if threshold_eval.is_low_stock:
        notify_user(
            recipient_user_id=actor_user_id,
            notification_type="LOW_STOCK",
            title=f"Low Stock Warning: {item.name}",
            message=(
                f"Current stock of {item.name} ({item.item_code}) is {item.stock_level} {item.unit}, "
                f"which is below its reorder threshold of {item.reorder_threshold} {item.unit}. "
                f"Please raise a procurement requisition."
            ),
        )

    return item


def submit_procurement_requisition(
    originator_user_id: int,
    originator_username: str,
    justification: str,
    items_data: Sequence[dict],
) -> ProcurementRequisition:
    """Creates and submits a procurement requisition (AFR-PHC-027, 028; UC-PHC-10; CW-PHC-02)."""
    today = timezone.now().date()
    req_count = ProcurementRequisition.objects.count() + 1
    req_number = f"REQ-{today.year}-{req_count:04d}"

    requisition = ProcurementRequisition.objects.create(
        requisition_number=req_number,
        originator_user_id=originator_user_id,
        status=RequisitionStatus.PENDING_APPROVAL.value,
        justification=justification.strip(),
    )

    for entry in items_data:
        item = InventoryItem.objects.get(id=entry["item_id"])
        RequisitionItem.objects.create(
            requisition=requisition,
            item=item,
            quantity_requested=int(entry["quantity"]),
        )

    return requisition


def decide_procurement_requisition(
    requisition_id: int,
    approve: bool,
    actor_user_id: int,
    actor_username: str,
    remarks: str = "",
) -> ProcurementRequisition:
    """Approving Authority decision on procurement requisition (AFR-PHC-029, 030; UC-PHC-16; BR-PHC-10, 11)."""
    requisition = ProcurementRequisition.objects.get(id=requisition_id)
    new_status = RequisitionStateMachine.transition_decision(requisition.status, approve=approve)

    requisition.status = new_status.value
    requisition.approver_user_id = actor_user_id
    requisition.decision_at = timezone.now()
    requisition.decision_remarks = remarks.strip()
    requisition.save()

    # PHC-BR-11 / AFR-PHC-030: Notify originating PHC Staff member
    status_str = "Approved" if approve else "Rejected"
    notify_user(
        recipient_user_id=requisition.originator_user_id,
        notification_type="REQUISITION_DECISION",
        title=f"Requisition {requisition.requisition_number} {status_str}",
        message=f"Your procurement requisition {requisition.requisition_number} has been {status_str} by the Approving Authority. Remarks: {remarks or 'None'}.",
    )

    return requisition


def fulfill_procurement_requisition(
    requisition_id: int,
    actor_user_id: int,
    actor_username: str,
) -> ProcurementRequisition:
    """PHC Staff marks delivered approved requisition as Fulfilled (AFR-PHC-031; UC-PHC-14; BR-PHC-10)."""
    requisition = ProcurementRequisition.objects.get(id=requisition_id)
    new_status = RequisitionStateMachine.transition_fulfill(requisition.status)

    requisition.status = new_status.value
    requisition.fulfilled_at = timezone.now()
    requisition.fulfilled_by_user_id = actor_user_id
    requisition.save()

    return requisition
