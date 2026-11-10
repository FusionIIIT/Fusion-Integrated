"""
Stock Management Services (PSM Module).
Handles stock reservation, internal issue, and inter-departmental transfers.
"""

import uuid
from typing import Any
from django.db import transaction
from core.api.exceptions import BadRequestError as ValidationError, NotFoundError

from modules.psm.models import StockItem, StockTransfer, Indent
from modules.psm.selectors.stock import get_allocable_stock


@transaction.atomic
def reserve_stock(*, stock_item_id: Any, quantity: int) -> StockItem:
    """Reserve stock for an upcoming internal issue.

    Increases reserved_stock if allocable stock is sufficient.
    """
    if quantity <= 0:
        raise ValidationError("Reservation quantity must be a positive integer.")

    item = StockItem.objects.select_for_update().filter(id=int(stock_item_id)).first()
    if not item:
        raise NotFoundError("Stock item not found.")

    allocable = (item.central_stock + item.department_stock) - item.reserved_stock
    if allocable < quantity:
        raise ValidationError(
            f"Insufficient allocable stock ({allocable}) for requested reservation of {quantity} units."
        )

    item.reserved_stock += quantity
    item.save()
    return item


@transaction.atomic
def issue_internal_stock(*, indent_id: Any, stock_item_id: Any = None) -> Indent:
    """Issue stock internally fulfilling an approved indent (AFR-PSM-013).

    Deducts quantity from central/department stock and releases reservation.
    """
    indent = Indent.objects.select_for_update().filter(id=indent_id).first() or \
             Indent.objects.select_for_update().filter(indent_id=str(indent_id)).first()
    if not indent:
        raise NotFoundError("Indent not found.")

    if stock_item_id:
        stock_item = StockItem.objects.select_for_update().filter(id=int(stock_item_id)).first()
        if stock_item:
            # Deduct from central stock first, then department stock
            qty_needed = indent.quantity
            if stock_item.central_stock >= qty_needed:
                stock_item.central_stock -= qty_needed
            else:
                rem = qty_needed - stock_item.central_stock
                stock_item.central_stock = 0
                stock_item.department_stock = max(0, stock_item.department_stock - rem)

            if stock_item.reserved_stock >= qty_needed:
                stock_item.reserved_stock -= qty_needed
            else:
                stock_item.reserved_stock = 0
            stock_item.save()

    indent.status = "APPROVED"
    indent.save()
    return indent


@transaction.atomic
def initiate_stock_transfer(
    *,
    source_dept: str,
    dest_dept: str,
    stock_item_id: Any,
    quantity: int,
) -> StockTransfer:
    """Initiate a stock transfer between departments."""
    if quantity <= 0:
        raise ValidationError("Transfer quantity must be greater than zero.")

    if source_dept.strip().lower() == dest_dept.strip().lower():
        raise ValidationError("Source and destination departments cannot be identical.")

    item = StockItem.objects.filter(id=int(stock_item_id)).first()
    if not item:
        raise NotFoundError("Stock item not found.")

    allocable = get_allocable_stock(stock_item_id)
    if allocable < quantity:
        raise ValidationError(
            f"Cannot transfer {quantity} units. Only {allocable} allocable units available."
        )

    transfer_id = f"TRF-{uuid.uuid4().hex[:8].upper()}"

    transfer = StockTransfer.objects.create(
        transfer_id=transfer_id,
        source_department=source_dept.strip(),
        destination_department=dest_dept.strip(),
        stock_item=item,
        quantity=int(quantity),
        status="REQUESTED",
    )
    return transfer
