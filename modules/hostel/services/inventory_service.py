"""Hostel inventory and staff services (CFR-HM-028, HM-UC-028, 029, 039, BR-HM-027)."""

from __future__ import annotations

from datetime import date

from django.db import transaction

from modules.hostel.domain.constants import InventoryCategory, StaffRole, StaffShift
from modules.hostel.domain.errors import ValidationError
from modules.hostel.models import Hostel, HostelInventory, HostelStaff


@transaction.atomic
def record_inventory_item(
    hostel_id: int,
    item_name: str,
    category: str = InventoryCategory.FURNITURE.value,
    quantity_total: int = 0,
    quantity_functional: int = 0,
    quantity_damaged: int = 0,
    location: str = "",
    last_inspected_at: date | None = None,
    remarks: str = "",
) -> HostelInventory:
    """CFR-HM-028, HM-UC-028, BR-HM-027: Caretaker maintains inventory records."""
    if not item_name or not item_name.strip():
        raise ValidationError("Item name is required")
    if quantity_total < 0:
        raise ValidationError("Quantity cannot be negative")

    hostel = Hostel.objects.get(id=hostel_id)

    return HostelInventory.objects.create(
        hostel=hostel,
        item_name=item_name.strip(),
        category=category,
        quantity_total=quantity_total,
        quantity_functional=quantity_functional,
        quantity_damaged=quantity_damaged,
        location=location.strip(),
        last_inspected_at=last_inspected_at,
        remarks=remarks.strip(),
    )


@transaction.atomic
def record_staff_member(
    hostel_id: int,
    name: str,
    role: str = StaffRole.CLEANER.value,
    phone_number: str = "",
    shift: str = StaffShift.MORNING.value,
    is_active: bool = True,
) -> HostelStaff:
    """CFR-HM-028, HM-UC-029: Maintain operational staff member and shift."""
    if not name or not name.strip():
        raise ValidationError("Staff name is required")

    hostel = Hostel.objects.get(id=hostel_id)

    return HostelStaff.objects.create(
        hostel=hostel,
        name=name.strip(),
        role=role,
        phone_number=phone_number.strip(),
        shift=shift,
        is_active=is_active,
    )
