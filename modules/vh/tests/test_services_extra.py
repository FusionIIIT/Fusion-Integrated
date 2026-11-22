# Unit tests covering service layer edge cases, inventory mutations, and alerts
from datetime import date, timedelta
from decimal import Decimal

import pytest

from conftest import make_principal
from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.vh.models.alerts import StayAlert
from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem
from modules.vh.services import alerts as alert_services
from modules.vh.services import billing as billing_services
from modules.vh.services import booking_lifecycle as booking_services
from modules.vh.services import inventory as inventory_services
from modules.vh.services import roles as role_services

pytestmark = pytest.mark.django_db


def test_inventory_services_crud_and_thresholds():
    principal = make_principal(user_id=201, permissions=("vh.inventory.manage",))

    # Save new item
    item = inventory_services.save_inventory_item(
        {
            "item_name": "Bath Mat",
            "category": "linen",
            "current_quantity": 12,
            "minimum_threshold": 10,
            "unit": "pieces",
        },
        principal,
    )
    assert item.id is not None
    assert item.is_threshold_alert is False

    # Update item
    item_updated = inventory_services.save_inventory_item(
        {
            "id": item.id,
            "item_name": "Bath Mat Deluxe",
            "category": "linen",
            "current_quantity": 8,
            "minimum_threshold": 10,
            "unit": "pieces",
        },
        principal,
    )
    assert item_updated.item_name == "Bath Mat Deluxe"
    assert item_updated.is_threshold_alert is True

    # Stock update
    inventory_services.update_inventory_stock(item.id, 5, principal)
    item.refresh_from_db()
    assert item.current_quantity == 13
    assert item.is_threshold_alert is False

    # Negative stock refused
    with pytest.raises(BadRequestError):
        inventory_services.update_inventory_stock(item.id, -20, principal)

    # Missing name refused
    with pytest.raises(BadRequestError):
        inventory_services.save_inventory_item({"item_name": ""}, principal)

    # Not found
    with pytest.raises(NotFoundError):
        inventory_services.update_inventory_stock(99999, 1, principal)


def test_evaluate_all_inventory_thresholds():
    InventoryItem.objects.create(
        item_name="Soap Bar",
        category="toiletries",
        current_quantity=2,
        minimum_threshold=10,
        is_threshold_alert=False,
    )
    count = inventory_services.evaluate_all_inventory_thresholds()
    assert count >= 1


def test_booking_modification_service():
    indenter = make_principal(user_id=101, permissions=("vh.booking.create",))
    other_indenter = make_principal(user_id=102, permissions=("vh.booking.create",))

    b = Booking.objects.create(
        booking_reference="VH-MOD-1",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=10),
        departure_date=date.today() + timedelta(days=12),
        status="pending",
    )

    # Non-owner cannot modify
    with pytest.raises(PermissionDeniedError):
        booking_services.request_booking_modification(
            b.id, {"visit_purpose": "Changed"}, other_indenter
        )

    # Owner can modify pending booking
    mod = booking_services.request_booking_modification(
        b.id,
        {"visit_purpose": "Updated purpose", "visitor_category": "B", "number_of_rooms": 2},
        indenter,
    )
    assert mod.visit_purpose == "Updated purpose"
    assert mod.visitor_category == "B"
    assert mod.number_of_rooms == 2


def test_booking_service_validation_errors():
    principal = make_principal(user_id=101, permissions=("vh.booking.create",))

    # Invalid dates (departure before arrival)
    with pytest.raises(BadRequestError):
        booking_services.create_online_booking(
            {
                "arrival_date": str(date.today() + timedelta(days=5)),
                "departure_date": str(date.today() + timedelta(days=2)),
            },
            principal,
        )

    # Missing dates
    with pytest.raises(BadRequestError):
        booking_services.create_online_booking({}, principal)

    # Offline booking invalid source
    with pytest.raises(BadRequestError):
        booking_services.create_offline_booking({"booking_source": "invalid_source"}, principal)


def test_stay_alerts_evaluation():
    principal = make_principal(user_id=201, permissions=("vh.role.reassign",))
    with pytest.raises(BadRequestError):
        role_services.reassign_operational_role("invalid_role", 123, None, None, principal)

    # Test no-show alert generation
    b1 = Booking.objects.create(
        booking_reference="VH-ALT-NOSHOW",
        indenter_id=101,
        arrival_date=date.today() - timedelta(days=2),
        departure_date=date.today() + timedelta(days=2),
        status="room_allotted",
    )
    no_shows = alert_services.evaluate_no_shows()
    assert no_shows >= 1
    assert StayAlert.objects.filter(booking=b1, alert_type="no_show").exists()

    # Test overstay alert generation
    b2 = Booking.objects.create(
        booking_reference="VH-ALT-OVERSTAY",
        indenter_id=101,
        arrival_date=date.today() - timedelta(days=5),
        departure_date=date.today() - timedelta(days=1),
        status="checked_in",
    )
    overstays = alert_services.evaluate_overstays()
    assert overstays >= 1
    assert StayAlert.objects.filter(booking=b2, alert_type="overstay").exists()


def test_billing_services_errors():
    principal = make_principal(user_id=201, permissions=("vh.bill.settle",))

    with pytest.raises(NotFoundError):
        billing_services.generate_bill(99999, principal)

    with pytest.raises(NotFoundError):
        billing_services.record_offline_settlement(99999, Decimal("100.00"), "RCP-1", "", principal)

    b = Booking.objects.create(
        booking_reference="VH-BILL-ERR",
        indenter_id=101,
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_out",
    )
    bill = Bill.objects.create(
        booking=b, bill_number="BILL-ERR-1", total_amount=Decimal("500.00"), status="generated"
    )

    with pytest.raises(BadRequestError):
        billing_services.record_offline_settlement(bill.id, Decimal("0.00"), "RCP-1", "", principal)
