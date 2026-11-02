from django.db import transaction
from typing import List
from modules.visitor_hostel.models import InventoryItem, InventoryReplenishment
from modules.visitor_hostel.domain.inventory_policy import is_threshold_breached, validate_replenishment_request

def check_low_stock_items() -> List[InventoryItem]:
    items = [item for item in InventoryItem.objects.all() if is_threshold_breached(item.quantity, item.threshold)]
    return items

@transaction.atomic
def request_replenishment(item_code: str, quantity: int, requested_by: str, remarks: str = "") -> InventoryReplenishment:
    validate_replenishment_request(quantity)
    item = InventoryItem.objects.get(item_code=item_code)
    return InventoryReplenishment.objects.create(item=item, quantity=quantity, requested_by=requested_by, remarks=remarks, status='Requested')

@transaction.atomic
def approve_replenishment(replenishment_id: int, approved_by: str) -> InventoryReplenishment:
    req = InventoryReplenishment.objects.get(id=replenishment_id)
    req.status = 'Approved'
    req.approved_by = approved_by
    req.item.quantity += req.quantity
    req.item.save()
    req.save()
    return req
