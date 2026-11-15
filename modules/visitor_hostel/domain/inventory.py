"""Inventory quantity rules (BR-VH-041)."""
from __future__ import annotations

KINDS = ("linen", "utensils", "consumable", "other")


class NegativeStock(Exception):
    def __init__(self, quantity: int, delta: int):
        super().__init__(
            f"Only {quantity} in stock; cannot remove {-delta}. Record what is "
            f"actually on hand instead.")
        self.quantity, self.delta = quantity, delta


def apply_delta(quantity: int, delta: int) -> int:
    after = quantity + delta
    if after < 0:
        raise NegativeStock(quantity, delta)
    return after


def is_below_threshold(quantity: int, threshold: int) -> bool:
    """Strictly below; at the threshold is not an alert (UC-VH-025 alt flow 1)."""
    return quantity < threshold
