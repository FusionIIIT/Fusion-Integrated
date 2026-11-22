"""Inventory and stock services (CFR-DEPT-004, CFR-DEPT-005, BW-DEPT-01)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from modules.dept.domain.exceptions import AvailabilityError
from modules.dept.domain.stock import transition_stock_request, validate_stock_request_creation
from modules.dept.models.department import Department
from modules.dept.models.inventory import InventoryItem, StockTransaction
from modules.dept.models.stock_requests import StockRequest


@transaction.atomic
def create_inventory_item(
    department_code: str,
    item_code: str,
    name: str,
    category: str,
    initial_quantity: int,
    unit: str,
    actor_principal: Any,
) -> InventoryItem:
    if initial_quantity < 0:
        raise ValidationError("Initial quantity cannot be negative.")

    dept, _ = Department.objects.get_or_create(
        code=department_code,
        defaults={"name": f"Department of {department_code}"},
    )

    item = InventoryItem.objects.create(
        department=dept,
        item_code=item_code.strip(),
        name=name.strip(),
        category=category.upper().strip(),
        quantity=initial_quantity,
        unit=unit.strip(),
    )

    if initial_quantity > 0:
        user_id = str(getattr(actor_principal, "user_id", getattr(actor_principal, "id", "admin")))
        StockTransaction.objects.create(
            inventory_item=item,
            transaction_type="INSERTION",
            quantity_delta=initial_quantity,
            balance_after=initial_quantity,
            performed_by_id=user_id,
            notes="Initial stock creation",
        )

    return item


@transaction.atomic
def add_stock_to_item(
    item_id: str,
    quantity: int,
    actor_principal: Any,
    notes: str = "",
) -> InventoryItem:
    if quantity <= 0:
        raise ValidationError("Stock addition quantity must be positive.")

    item = InventoryItem.objects.select_for_update().get(id=item_id)
    new_quantity = item.quantity + quantity
    item.quantity = new_quantity
    item.save(update_fields=["quantity", "updated_at"])

    user_id = str(getattr(actor_principal, "user_id", getattr(actor_principal, "id", "admin")))
    StockTransaction.objects.create(
        inventory_item=item,
        transaction_type="INSERTION",
        quantity_delta=quantity,
        balance_after=new_quantity,
        performed_by_id=user_id,
        notes=notes,
    )

    return item


@transaction.atomic
def submit_stock_request(
    department_code: str,
    inventory_item_id: str,
    requested_quantity: int,
    purpose: str,
    faculty_principal: Any,
) -> StockRequest:
    item = InventoryItem.objects.select_for_update().get(id=inventory_item_id)
    validate_stock_request_creation(requested_quantity, item.quantity)

    dept = Department.objects.get(code=department_code)
    user_id = str(
        getattr(faculty_principal, "user_id", getattr(faculty_principal, "id", "faculty"))
    )

    return StockRequest.objects.create(
        department=dept,
        inventory_item=item,
        requested_by_id=user_id,
        requested_quantity=requested_quantity,
        purpose=purpose.strip(),
        status="SUBMITTED",
    )


@transaction.atomic
def decide_stock_request(
    stock_request_id: str,
    decision: str,
    hod_principal: Any,
    remarks: str = "",
) -> StockRequest:
    from django.utils import timezone

    sr = StockRequest.objects.select_for_update().get(id=stock_request_id)
    event = decision.upper().strip()  # "APPROVE" or "REJECT"

    next_status = transition_stock_request(
        current_state=sr.status,
        event=event,
        acting_role="HOD",
        requested_quantity=sr.requested_quantity,
        available_quantity=sr.inventory_item.quantity,
    )

    user_id = str(getattr(hod_principal, "user_id", getattr(hod_principal, "id", "hod")))
    sr.status = next_status
    sr.hod_decision_by_id = user_id
    sr.hod_decision_at = timezone.now()
    sr.hod_remarks = remarks
    sr.save()
    return sr


@transaction.atomic
def issue_stock_request(
    stock_request_id: str,
    dept_admin_principal: Any,
    notes: str = "",
) -> StockRequest:
    from django.utils import timezone

    sr = StockRequest.objects.select_for_update().get(id=stock_request_id)
    item = InventoryItem.objects.select_for_update().get(id=sr.inventory_item_id)

    next_status = transition_stock_request(
        current_state=sr.status,
        event="ISSUE",
        acting_role="DEPT_ADMIN",
        requested_quantity=sr.requested_quantity,
        available_quantity=item.quantity,
    )

    if item.quantity < sr.requested_quantity:
        raise AvailabilityError("Insufficient stock in inventory for issuance.")

    new_balance = item.quantity - sr.requested_quantity
    item.quantity = new_balance
    item.save(update_fields=["quantity", "updated_at"])

    user_id = str(
        getattr(dept_admin_principal, "user_id", getattr(dept_admin_principal, "id", "admin"))
    )

    StockTransaction.objects.create(
        inventory_item=item,
        transaction_type="ISSUANCE",
        quantity_delta=-sr.requested_quantity,
        balance_after=new_balance,
        performed_by_id=user_id,
        related_request_id=sr.id,
        notes=notes or f"Issued for stock request {sr.id}",
    )

    sr.status = next_status
    sr.issued_by_id = user_id
    sr.issued_at = timezone.now()
    sr.save()

    return sr
