import pytest
from django.db import DatabaseError, transaction

from core.api.exceptions import ConflictError
from modules.phc.models import (
    InventoryItem,
    InventoryMovement,
    LowStockAlert,
    PHCAuditEvent,
)
from modules.phc.services.inventory import adjust_stock

pytestmark = pytest.mark.django_db


# PHC-BR-07; PHC-UC-09; CFR-PHC-006; AFR-PHC-024; AFR-PHC-025; AFR-PHC-026.
def test_phc_br_07_uc_09_stock_ledger_and_strict_low_stock_alert():
    item = InventoryItem.objects.create(name="Bandage", unit="units",
                                        reorder_threshold=5)
    _, initial, _ = adjust_stock(item_id=item.pk, quantity_delta=10,
                                 reason="Received", actor_user_id=2001)
    _, reduced, _ = adjust_stock(item_id=item.pk, quantity_delta=-6,
                                 reason="Dispensed", actor_user_id=2001)
    assert initial == 10
    assert reduced == 4
    assert InventoryMovement.objects.filter(item=item).count() == 2
    assert LowStockAlert.objects.filter(item=item).count() == 1
    assert PHCAuditEvent.objects.filter(object_type="inventory_item",
                                        object_id=item.pk).count() == 2
    with pytest.raises(ConflictError):
        adjust_stock(item_id=item.pk, quantity_delta=-5,
                     reason="Too much", actor_user_id=2001)
    assert InventoryMovement.objects.filter(item=item).count() == 2


# PHC-BR-09; CFR-PHC-012; AFR-PHC-037.
def test_phc_br_09_audit_and_stock_movement_rows_are_database_immutable():
    event = PHCAuditEvent.objects.create(actor_user_id=10, action="test.action",
        object_type="test", object_id=1)
    item = InventoryItem.objects.create(name="Gloves", unit="pair",
                                        reorder_threshold=2)
    movement = InventoryMovement.objects.create(item=item, quantity_delta=1,
        reason="Received", actor_user_id=10)
    with pytest.raises(DatabaseError), transaction.atomic():
        PHCAuditEvent.objects.filter(pk=event.pk).update(action="changed")
    with pytest.raises(DatabaseError), transaction.atomic():
        InventoryMovement.objects.filter(pk=movement.pk).delete()


def test_phc_br_07_uc_09_inventory_api_creates_items_adjusts_stock_and_lists_alerts(
        stub_iam):
    from rest_framework.test import APIClient

    from conftest import make_session

    stub_iam(make_session(user_id=2001, kind="staff", modules=("phc",),
        permissions=("phc.inventory.view", "phc.inventory.create",
                    "phc.inventory.update"), roles=("Compounder",),
        active_role="Compounder"))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token phc-inventory")
    created = client.post("/api/v1/phc/inventory", {
        "name": "Gauze", "reorder_threshold": 4,
    }, format="json")
    assert created.status_code == 201
    duplicate = client.post("/api/v1/phc/inventory", {
        "name": "Gauze", "reorder_threshold": 4,
    }, format="json")
    assert duplicate.status_code == 409
    item_id = created.json()["id"]
    stocked = client.post(f"/api/v1/phc/inventory/{item_id}/movements", {
        "quantity_delta": 8, "reason": "Delivery",
    }, format="json")
    assert stocked.status_code == 201
    depleted = client.post(f"/api/v1/phc/inventory/{item_id}/movements", {
        "quantity_delta": -5, "reason": "Dispensed",
    }, format="json")
    assert depleted.status_code == 201
    assert depleted.json()["quantity_after"] == 3
    assert client.get("/api/v1/phc/inventory").json()["results"][0]["unit"] == "units"
    alerts = client.get("/api/v1/phc/inventory/low-stock-alerts")
    assert alerts.status_code == 200
    assert alerts.json()["results"][0]["quantity_after"] == 3
    invalid = client.post(f"/api/v1/phc/inventory/{item_id}/movements", {
        "quantity_delta": 0,
    }, format="json")
    assert invalid.status_code == 400
