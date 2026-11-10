from enum import Enum

class RequisitionState(Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FULFILLED = "FULFILLED"

def validate_stock_adjustment(current_quantity: int, delta: int) -> None:
    new_quantity = current_quantity + delta
    if new_quantity < 0:
        raise ValueError("Invalid stock adjustment")

def is_low_stock(quantity: int, threshold: int) -> bool:
    return quantity < threshold

def can_transition(current_state: RequisitionState, new_state: RequisitionState) -> bool:
    if current_state == RequisitionState.PENDING_APPROVAL and new_state in [RequisitionState.APPROVED, RequisitionState.REJECTED]:
        return True
    elif current_state == RequisitionState.APPROVED and new_state == RequisitionState.FULFILLED:
        return True
    return False
