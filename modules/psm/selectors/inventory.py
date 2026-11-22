from modules.psm.models.inventory import StockItem


def get_stock_availability(item_master_id: int) -> tuple[int, int, int]:
    """Returns (on_hand, reserved, available) for an item master."""
    stock = StockItem.objects.filter(item_master_id=item_master_id).first()
    if not stock:
        return 0, 0, 0
    return stock.quantity_on_hand, stock.quantity_reserved, stock.available_quantity
