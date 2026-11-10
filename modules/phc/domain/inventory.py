from enum import Enum

class RequisitionState(Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FULFILLED = "FULFILLED"

def is_valid_stock_adjustment(inventory_item, delta):
    new_quantity = inventory_item.quantity + delta
    return new_quantity >= 0 and new_quantity < inventory_item.reorder_threshold

def validate_requisition_lines(lines):
    if not lines:
        raise ValueError("A requisition must have at least one line")
    for line in lines:
        if line.quantity <= 0:
            raise ValueError("All line quantities must be positive")

def can_transition(current_state, new_state):
    if current_state == RequisitionState.PENDING_APPROVAL and new_state in [RequisitionState.APPROVED, RequisitionState.REJECTED]:
        return True
    elif current_state == RequisitionState.APPROVED and new_state == RequisitionState.FULFILLED:
        return True
    return False
