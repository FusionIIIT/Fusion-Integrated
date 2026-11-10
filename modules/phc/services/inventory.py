from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, BadRequestError
from modules.phc.models import InventoryItem, StockAdjustment, AuditEvent, Notification, Requisition, RequisitionLine
from modules.phc.domain.inventory import validate_stock_adjustment, is_low_stock, can_transition, RequisitionState

@transaction.atomic
def adjust_stock(item_id: int, delta: int, reason: str, actor_user_id: int) -> InventoryItem:
    inventory_item = InventoryItem.objects.get(id=item_id)
    
    validate_stock_adjustment(inventory_item.quantity, delta)
    
    inventory_item.quantity += delta
    inventory_item.save()
    
    StockAdjustment.objects.create(
        inventory_item=inventory_item,
        delta=delta,
        reason=reason,
        adjusted_by_user_id=actor_user_id
    )
    
    record_audit("InventoryItem", item_id, "adjust_stock", actor_user_id, from_status=str(inventory_item.quantity - delta), to_status=str(inventory_item.quantity))
    
    if is_low_stock(inventory_item.quantity, inventory_item.reorder_threshold):
        notify(actor_user_id, "low_stock_alert", f"Low stock alert for {inventory_item.name}")
    
    return inventory_item

@transaction.atomic
def create_requisition(requested_by_user_id: int, lines: list[dict]) -> Requisition:
    if not lines:
        raise BadRequestError("A requisition must have at least one line")
    for line in lines:
        if line["quantity"] <= 0:
            raise BadRequestError("All line quantities must be positive")
    
    requisition = Requisition.objects.create(
        requested_by_user_id=requested_by_user_id,
        status=RequisitionState.PENDING_APPROVAL
    )
    
    for line in lines:
        RequisitionLine.objects.create(
            requisition=requisition,
            inventory_item=line["inventory_item"],
            quantity=line["quantity"]
        )
    
    record_audit("Requisition", requisition.id, "create_requisition", actor_user_id)
    
    return requisition

@transaction.atomic
def decide_requisition(req_id: int, decision: str, actor_user_id: int) -> Requisition:
    try:
        requisition = Requisition.objects.get(id=req_id)
    except Requisition.DoesNotExist:
        raise NotFound("Requisition not found")
    
    if not can_transition(requisition.status, RequisitionState[decision]):
        raise BadRequestError("Invalid transition")
    
    requisition.decided_by_user_id = actor_user_id
    requisition.decided_at = timezone.now()
    requisition.status = RequisitionState[decision]
    
    requisition.save()
    
    record_audit("Requisition", req_id, "decide_requisition", actor_user_id, from_status=requisition.status.value, to_status=decision)
    
    if decision == RequisitionState.APPROVED.value:
        notify(requisition.requested_by_user_id, "requisition_approved", f"Your requisition for {requisition.lines.count()} items has been approved.")
    elif decision == RequisitionState.REJECTED.value:
        notify(requisition.requested_by_user_id, "requisition_rejected", f"Your requisition for {requisition.lines.count()} items has been rejected.")
    
    return requisition

@transaction.atomic
def fulfil_requisition(req_id: int, actor_user_id: int) -> Requisition:
    try:
        requisition = Requisition.objects.get(id=req_id)
    except Requisition.DoesNotExist:
        raise NotFound("Requisition not found")
    
    if requisition.status != RequisitionState.APPROVED.value:
        raise BadRequestError("Requisition must be approved to be fulfilled")
    
    requisition.status = RequisitionState.FULFILLED
    requisition.save()
    
    record_audit("Requisition", req_id, "fulfill_requisition", actor_user_id, from_status=RequisitionState.APPROVED.value, to_status=RequisitionState.FULFILLED.value)
    
    return requisition
