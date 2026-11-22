"""Inventory and stock selectors (CFR-DEPT-004, CFR-DEPT-006)."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from modules.dept.models.inventory import InventoryItem, StockTransaction
from modules.dept.models.stock_requests import StockRequest


def list_inventory_items(
    department_code: str,
    category: str | None = None,
) -> QuerySet[InventoryItem]:
    qs = InventoryItem.objects.filter(department_id=department_code)
    if category:
        qs = qs.filter(category=category.upper())
    return qs.order_by("name")


def list_stock_transactions(item_id: str) -> QuerySet[StockTransaction]:
    return StockTransaction.objects.filter(inventory_item_id=item_id).order_by("-created_at")


def list_stock_requests_for_principal(
    department_code: str,
    principal: Any,
    mine_only: bool = False,
    status: str | None = None,
) -> QuerySet[StockRequest]:
    qs = StockRequest.objects.filter(department_id=department_code)

    roles = set(getattr(principal, "roles", []))
    is_admin_or_hod = bool(roles.intersection({"HOD", "Dept_Admin"})) or getattr(
        principal, "is_staff", False
    )

    if mine_only or not is_admin_or_hod:
        user_id = str(getattr(principal, "user_id", getattr(principal, "id", "")))
        qs = qs.filter(requested_by_id=user_id)

    if status:
        qs = qs.filter(status=status.upper())

    return qs.order_by("-created_at")
