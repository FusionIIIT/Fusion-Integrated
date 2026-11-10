"""
Pure Python Domain Rules for PSM (Purchase and Stores Management).
No Django imports allowed.
"""

from decimal import Decimal
from typing import Any, Union


def validate_indent_completeness(indent_data: dict[str, Any]) -> None:
    """Validate completeness of an indent (BR-PSM-001 / AFR-PSM-002, AFR-PSM-003).

    Required fields: item_details, quantity, estimated_cost, justification.
    Raises ValueError if any field is missing or invalid.
    """
    if not isinstance(indent_data, dict):
        raise ValueError("Indent data must be a dictionary.")

    required_fields = ["item_details", "quantity", "estimated_cost", "justification"]
    missing = [f for f in required_fields if f not in indent_data or indent_data[f] is None]
    if missing:
        raise ValueError(f"Missing required indent fields: {', '.join(missing)}")

    # Check non-empty string for item_details & justification
    item_details = str(indent_data.get("item_details", "")).strip()
    if not item_details:
        raise ValueError("Field 'item_details' must be a non-empty string.")

    justification = str(indent_data.get("justification", "")).strip()
    if not justification:
        raise ValueError("Field 'justification' must be a non-empty string.")

    # Check quantity
    try:
        qty = int(indent_data["quantity"])
        if qty <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("Field 'quantity' must be a positive integer greater than zero.")

    # Check estimated_cost
    try:
        cost = Decimal(str(indent_data["estimated_cost"]))
        if cost <= Decimal("0.00"):
            raise ValueError()
    except Exception:
        raise ValueError("Field 'estimated_cost' must be a positive number greater than zero.")


def is_possible_duplicate(new_indent: dict[str, Any], existing_indents: list[dict[str, Any]]) -> bool:
    """Check item matching and cost closeness against active indents (BR-PSM-015 / AFR-PSM-004).

    An active indent is one that is in a pending or non-terminal state
    (e.g., SUBMITTED, STOCK_CHECKED, DEPT_REVIEWED, HEAD_RECOMMENDED, AWAITING_FINAL_APPROVAL).
    If same normalized item_details and estimated_cost within 5% tolerance, returns True.
    """
    if not existing_indents:
        return False

    new_item = str(new_indent.get("item_details", "")).strip().lower()
    try:
        new_cost = float(new_indent.get("estimated_cost", 0))
    except (ValueError, TypeError):
        return False

    active_statuses = {
        "SUBMITTED",
        "STOCK_CHECKED",
        "DEPT_REVIEWED",
        "HEAD_RECOMMENDED",
        "AWAITING_FINAL_APPROVAL",
    }

    for ex in existing_indents:
        # Check status if provided; if no status provided, assume active
        ex_status = str(ex.get("status", "SUBMITTED")).strip().upper()
        if ex_status not in active_statuses:
            continue

        ex_item = str(ex.get("item_details", "")).strip().lower()
        if new_item != ex_item:
            continue

        try:
            ex_cost = float(ex.get("estimated_cost", 0))
        except (ValueError, TypeError):
            continue

        # Check closeness within 5% tolerance or exact match
        if ex_cost == 0 and new_cost == 0:
            return True
        if ex_cost > 0:
            diff_ratio = abs(new_cost - ex_cost) / ex_cost
            if diff_ratio <= 0.05:
                return True

    return False


def determine_procurement_routing(requested_qty: int, available_stock: int) -> str:
    """Determine procurement routing based on available stock (BR-PSM-003 / AFR-PSM-013, 030).

    Returns 'INTERNAL_ISSUE' if stock is fully available, else 'EXTERNAL_PROCUREMENT'.
    """
    if requested_qty <= 0:
        raise ValueError("Requested quantity must be positive.")
    if available_stock >= requested_qty:
        return "INTERNAL_ISSUE"
    return "EXTERNAL_PROCUREMENT"


def determine_procurement_method(
    estimated_cost: Union[float, Decimal, int],
    tender_threshold: Union[float, Decimal, int] = 100000.0,
) -> str:
    """Determine procurement method based on estimated cost threshold (BR-PSM-008 / AFR-PSM-031).

    Returns 'DIRECT' if cost < tender_threshold, else 'TENDER'.
    """
    cost = float(estimated_cost)
    threshold = float(tender_threshold)
    if cost >= threshold:
        return "TENDER"
    return "DIRECT"


def validate_rejection_justification(decision: str, justification: str) -> None:
    """Mandates non-empty justification string when decision is REJECT (BR-PSM-005 / AFR-PSM-026)."""
    norm_decision = str(decision).strip().upper()
    if norm_decision in ["REJECT", "REJECTED"]:
        if not justification or not str(justification).strip():
            raise ValueError("A non-empty justification is mandatory when rejecting an indent.")
