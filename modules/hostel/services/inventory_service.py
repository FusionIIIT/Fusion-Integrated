"""Hostel operational inventory and staff coordination services (3.9, CFR-HM-027, CFR-HM-028, BR-HM-027)."""

from django.db import transaction
from ..domain.constants import InventoryCategory, InventoryCondition, ShiftType, StaffRole
from ..domain.errors import HostelDomainError
from ..models import Hostel, HostelInventoryItem, InventoryAuditLog, StaffAssignment


@transaction.atomic
def create_or_update_inventory_item(
    user_id: int,
    hostel_id: int,
    item_name: str,
    category: str = InventoryCategory.FURNITURE.value,
    total_quantity: int = 1,
    in_use_quantity: int = 0,
    condition: str = InventoryCondition.GOOD.value,
    location: str = "Hostel Store",
    item_id: int | None = None,
) -> HostelInventoryItem:
    """Caretaker creates or updates inventory item with audit log (HM-UC-028, BR-HM-027)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")

    available_qty = max(0, total_quantity - in_use_quantity)

    if item_id:
        item = HostelInventoryItem.objects.select_for_update().filter(id=item_id, hostel=hostel).first()
        if not item:
            raise HostelDomainError(f"Inventory item {item_id} not found.")

        old_state = f"Qty: {item.total_quantity}, In-use: {item.in_use_quantity}, Cond: {item.condition}"
        item.item_name = item_name.strip()
        item.category = category
        item.total_quantity = total_quantity
        item.in_use_quantity = in_use_quantity
        item.available_quantity = available_qty
        item.condition = condition
        item.location = location.strip()
        item.last_updated_by_user_id = user_id
        item.save()

        new_state = f"Qty: {total_quantity}, In-use: {in_use_quantity}, Cond: {condition}"
        InventoryAuditLog.objects.create(
            item=item,
            action="updated",
            details=f"From [{old_state}] to [{new_state}]",
            performed_by_user_id=user_id,
        )
        return item
    else:
        item = HostelInventoryItem.objects.create(
            hostel=hostel,
            item_name=item_name.strip(),
            category=category,
            total_quantity=total_quantity,
            in_use_quantity=in_use_quantity,
            available_quantity=available_qty,
            condition=condition,
            location=location.strip(),
            last_updated_by_user_id=user_id,
        )
        InventoryAuditLog.objects.create(
            item=item,
            action="created",
            details=f"Initial record created: Qty {total_quantity}, Condition {condition}",
            performed_by_user_id=user_id,
        )
        return item


@transaction.atomic
def create_or_update_staff_assignment(
    user_id: int,
    hostel_id: int,
    staff_name: str,
    role_designation: str = StaffRole.ATTENDANT.value,
    shift: str = ShiftType.GENERAL.value,
    contact_number: str = "",
    duty_location: str = "",
    is_active: bool = True,
    assignment_id: int | None = None,
) -> StaffAssignment:
    """Maintain staff coordination info (HM-UC-029)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")

    if assignment_id:
        assignment = StaffAssignment.objects.filter(id=assignment_id, hostel=hostel).first()
        if not assignment:
            raise HostelDomainError(f"Staff assignment {assignment_id} not found.")
        assignment.staff_name = staff_name.strip()
        assignment.role_designation = role_designation
        assignment.shift = shift
        assignment.contact_number = contact_number.strip()
        assignment.duty_location = duty_location.strip()
        assignment.is_active = is_active
        assignment.save()
        return assignment
    else:
        return StaffAssignment.objects.create(
            hostel=hostel,
            staff_name=staff_name.strip(),
            role_designation=role_designation,
            shift=shift,
            contact_number=contact_number.strip(),
            duty_location=duty_location.strip(),
            is_active=is_active,
            assigned_by_user_id=user_id,
        )
