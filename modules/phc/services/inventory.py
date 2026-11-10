from django.db import transaction
from modules.phc.models import InventoryItem, StockAdjustment, AuditEvent, Notification, Requisition, RequisitionLine
from modules.phc.domain.inventory import is_valid_stock_adjustment, validate_requisition_lines, can_transition

@transaction.atomic
def adjust_stock(inventory_item, delta, reason, actor_user_id):
    if not is_valid_stock_adjustment(inventory_item, delta):
        raise ValueError("Invalid stock adjustment")
    
    inventory_item.quantity += delta
    inventory_item.save()
    
    StockAdjustment.objects.create(
        inventory_item=inventory_item,
        delta=delta,
        reason=reason,
        adjusted_by_user_id=actor_user_id
    )
    
    record_audit("InventoryItem", inventory_item.id, "adjust_stock", actor_user_id, from_status=str(inventory_item.quantity - delta), to_status=str(inventory_item.quantity))
    
    if inventory_item.quantity < inventory_item.reorder_threshold:
        notify(actor_user_id, "low_stock_alert", f"Low stock alert for {inventory_item.name}")

@transaction.atomic
def create_requisition(lines, actor_user_id):
    validate_requisition_lines(lines)
    
    requisition = Requisition.objects.create(
        requested_by_user_id=actor_user_id,
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
def decide_requisition(requisition_id, decision, actor_user_id):
    requisition = Requisition.objects.get(id=requisition_id)
    
    if not can_transition(requisition.status, decision):
        raise ValueError("Invalid transition")
    
    requisition.decided_by_user_id = actor_user_id
    requisition.decided_at = timezone.now()
    requisition.status = decision
    
    requisition.save()
    
    record_audit("Requisition", requisition.id, "decide_requisition", actor_user_id, from_status=requisition.status.value, to_status=decision)
    
    if decision == RequisitionState.APPROVED:
        notify(requisition.requested_by_user_id, "requisition_approved", f"Your requisition for {requisition.lines.count()} items has been approved.")
    elif decision == RequisitionState.REJECTED:
        notify(requisition.requested_by_user_id, "requisition_rejected", f"Your requisition for {requisition.lines.count()} items has been rejected.")

@transaction.atomic
def fulfill_requisition(requisition_id, actor_user_id):
    requisition = Requisition.objects.get(id=requisition_id)
    
    if requisition.status != RequisitionState.APPROVED:
        raise ValueError("Requisition must be approved to be fulfilled")
    
    requisition.status = RequisitionState.FULFILLED
    requisition.save()
    
    record_audit("Requisition", requisition.id, "fulfill_requisition", actor_user_id, from_status=RequisitionState.APPROVED.value, to_status=RequisitionState.FULFILLED.value)
