"""
Pure Python 3-Way Match Verification (BR-PSM-017, BR-PSM-018 / AFR-PSM-056).
Strictly NO Django imports.
"""

from decimal import Decimal
from typing import Any, Union


def perform_three_way_match(
    po_amount: Union[float, Decimal, int],
    grn_accepted_qty: int,
    unit_price: Union[float, Decimal, int],
    invoice_amount: Union[float, Decimal, int],
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Perform three-way match consistency check between:
    1. Purchase Order total amount (po_amount)
    2. Goods Receipt Note accepted quantity evaluated at unit price (grn_accepted_qty * unit_price)
    3. Vendor Invoice total amount (invoice_amount)

    Returns:
        {
            "status": "VERIFIED" | "MISMATCH_HOLD",
            "po_amount": float,
            "delivered_value": float,
            "invoice_amount": float,
            "discrepancies": list[str]
        }
    """
    po = float(po_amount)
    qty = int(grn_accepted_qty)
    price = float(unit_price)
    inv = float(invoice_amount)

    delivered_val = round(qty * price, 2)
    discrepancies: list[str] = []

    if qty < 0:
        discrepancies.append(f"Invalid GRN accepted quantity: {qty}")

    # Check 1: Invoice vs Delivered Value
    if abs(inv - delivered_val) > tolerance:
        discrepancies.append(
            f"Invoice amount ({inv:.2f}) does not match delivered goods value ({delivered_val:.2f})."
        )

    # Check 2: Invoice vs PO Amount (cannot exceed PO amount)
    if inv - po > tolerance:
        discrepancies.append(
            f"Invoice amount ({inv:.2f}) exceeds Purchase Order ceiling ({po:.2f})."
        )

    # Check 3: Delivered value vs PO Amount
    if delivered_val - po > tolerance:
        discrepancies.append(
            f"Delivered value ({delivered_val:.2f}) exceeds Purchase Order amount ({po:.2f})."
        )

    status = "VERIFIED" if not discrepancies else "MISMATCH_HOLD"

    return {
        "status": status,
        "is_matched": status == "VERIFIED",
        "po_amount": po,
        "delivered_value": delivered_val,
        "invoice_amount": inv,
        "discrepancies": discrepancies,
    }
