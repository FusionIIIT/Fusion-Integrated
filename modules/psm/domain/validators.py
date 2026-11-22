"""Domain validation logic for PSM business rules."""

from collections.abc import Sequence
from decimal import Decimal
from typing import Any


class VendorStatus:
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"
    BLACKLISTED = "BLACKLISTED"


class ValidationError(Exception):
    pass


def validate_indent_completeness(
    title: str,
    purpose: str,
    items: Sequence[dict],
) -> None:
    """Enforces BR-PSM-001: Indent completeness."""
    if not title or not title.strip():
        raise ValidationError("Indent title cannot be empty.")
    if not purpose or not purpose.strip():
        raise ValidationError("Indent purpose/justification cannot be empty.")
    if not items or len(items) == 0:
        raise ValidationError("An indent must contain at least one item line.")

    for idx, item in enumerate(items, 1):
        qty = item.get("quantity_requested")
        if qty is None or int(qty) <= 0:
            raise ValidationError(f"Item line {idx} must have a positive quantity requested.")
        unit_cost = item.get("estimated_unit_cost")
        if unit_cost is None or Decimal(str(unit_cost)) < 0:
            raise ValidationError(f"Item line {idx} cannot have a negative unit cost.")


def validate_rejection_reason(reason: str) -> None:
    """Enforces BR-PSM-005: Rejection justification is mandatory."""
    if not reason or not reason.strip():
        raise ValidationError("Rejection justification cannot be empty.")


def validate_vendor_verified_for_po(vendor: Any, vendor_name: str = "") -> None:
    """Enforces BR-PSM-012: Vendor master verification gate."""
    status = getattr(vendor, "status", vendor)
    name = getattr(vendor, "name", vendor_name) or str(vendor)
    if status != VendorStatus.VERIFIED:
        raise ValidationError(
            f"Cannot issue Purchase Order to vendor '{name}' with status '{status}'. "
            "Only VERIFIED vendors may receive Purchase Orders."
        )
