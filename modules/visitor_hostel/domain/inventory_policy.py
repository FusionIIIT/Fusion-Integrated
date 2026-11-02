def is_threshold_breached(current_quantity: int, threshold_level: int) -> bool:
    return current_quantity < threshold_level

def validate_replenishment_request(requested_quantity: int) -> bool:
    if requested_quantity <= 0:
        raise ValueError("Requested quantity must be greater than 0")
    return True
