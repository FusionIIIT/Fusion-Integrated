from django.db import transaction
from django.db.models import F

from modules.psm.domain.validators import ValidationError
from modules.psm.models.indent import Indent, IndentStatus
from modules.psm.models.inventory import StockItem, StockLedger, StockTransactionType


@transaction.atomic
def reserve_stock(
    stock_item_id: int, quantity: int, user_id: int, reference_id: str = ""
) -> StockItem:
    """Reserves stock for an indent or internal order, ensuring quantity <= available."""
    if quantity <= 0:
        raise ValidationError("Reservation quantity must be strictly positive.")

    stock = StockItem.objects.select_for_update().get(pk=stock_item_id)
    available = stock.quantity_on_hand - stock.quantity_reserved
    if quantity > available:
        raise ValidationError(
            f"Cannot reserve {quantity} units. Only {available} units available in stock."
        )

    stock.quantity_reserved = F("quantity_reserved") + quantity
    stock.save(update_fields=["quantity_reserved", "updated_at"])
    stock.refresh_from_db()

    StockLedger.objects.create(
        stock_item=stock,
        transaction_type=StockTransactionType.RESERVATION_LOCK,
        quantity=quantity,
        balance_after=stock.quantity_on_hand - stock.quantity_reserved,
        reference_id=reference_id,
        recorded_by_user_id=user_id,
        remarks=f"Stock reservation for reference {reference_id}",
    )
    return stock


@transaction.atomic
def fulfill_internal_stock(indent_id: int, user_id: int) -> Indent:
    """Enforces BW-PSM-01: Fulfills indent directly from central stores stock."""
    indent = Indent.objects.select_for_update().get(pk=indent_id)
    if indent.status != IndentStatus.APPROVED:
        raise ValidationError(
            f"Cannot fulfill indent with status '{indent.status}'. Must be APPROVED."
        )

    for item in indent.items.all():
        stock, _ = StockItem.objects.select_for_update().get_or_create(item_master=item.item_master)
        if stock.quantity_on_hand < item.quantity_requested:
            raise ValidationError(
                f"Insufficient stock for {item.item_master.name}. "
                f"Requested: {item.quantity_requested}, "
                f"Available on hand: {stock.quantity_on_hand}."
            )
        stock.quantity_on_hand = F("quantity_on_hand") - item.quantity_requested
        stock.save(update_fields=["quantity_on_hand", "updated_at"])
        stock.refresh_from_db()

        StockLedger.objects.create(
            stock_item=stock,
            transaction_type=StockTransactionType.INTERNAL_ISSUE,
            quantity=-item.quantity_requested,
            balance_after=stock.quantity_on_hand,
            reference_id=indent.indent_number,
            recorded_by_user_id=user_id,
            remarks=f"Internal fulfillment of indent {indent.indent_number}",
        )

    indent.status = IndentStatus.FULFILLED
    indent.save(update_fields=["status", "updated_at"])
    return indent


@transaction.atomic
def credit_stock_from_grn(grn_item, user_id: int) -> StockItem:
    """Credits accepted items from GRN into the stock inventory."""
    stock, _ = StockItem.objects.select_for_update().get_or_create(
        item_master=grn_item.po_line_item.item_master
    )
    stock.quantity_on_hand = F("quantity_on_hand") + grn_item.quantity_accepted
    stock.save(update_fields=["quantity_on_hand", "updated_at"])
    stock.refresh_from_db()

    StockLedger.objects.create(
        stock_item=stock,
        transaction_type=StockTransactionType.RECEIPT_CREDIT,
        quantity=grn_item.quantity_accepted,
        balance_after=stock.quantity_on_hand,
        reference_id=grn_item.grn.grn_number,
        recorded_by_user_id=user_id,
        remarks=f"Received via GRN {grn_item.grn.grn_number}",
    )
    return stock
