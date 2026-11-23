def stock_after(current: int, change: int) -> int:
    result = current + change
    if change == 0:
        raise ValueError("Enter a non-zero stock adjustment.")
    if result < 0:
        raise ValueError("The adjustment would make stock negative; enter a smaller deduction.")
    return result


def is_low_stock(quantity: int, reorder_threshold: int) -> bool:
    return quantity < reorder_threshold
