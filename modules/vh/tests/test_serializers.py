"""Unit tests for VH module serializers and validation logic."""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.vh.api.serializers import (
    BillSerializer,
    BookingModificationSerializer,
    BookingSerializer,
    InventoryItemSerializer,
    InventoryReplenishmentSerializer,
    MealBookingSerializer,
    RoomSerializer,
    TariffSerializer,
    VHAlertSerializer,
    VHNotificationLogSerializer,
    VHMSUserRoleSerializer,
    VisitorCategorySerializer,
)
from modules.vh.models import (
    Bill,
    BillingResponsibility,
    Booking,
    BookingStatus,
    InventoryItem,
    MealAddOn,
    MealType,
    OccupancyType,
    OfflineBookingType,
    Room,
    RoomStatus,
    RoomType,
    VHMSUserRoleType,
)


@pytest.mark.django_db
class TestVisitorCategorySerializer:
    def test_valid_serialization(self, category_a):
        ser = VisitorCategorySerializer(category_a)
        assert ser.data["code"] == "A"
        assert ser.data["name"] == category_a.name

    @pytest.mark.parametrize("invalid_code", ["X", "1", "A+", "INVALID"])
    def test_invalid_category_code_validation(self, invalid_code):
        ser = VisitorCategorySerializer(data={"code": invalid_code, "name": "Test"})
        assert ser.is_valid() is False
        assert "code" in ser.errors


@pytest.mark.django_db
class TestRoomSerializer:
    @pytest.mark.parametrize("r_type", [RoomType.SUITE, RoomType.NON_SUITE])
    @pytest.mark.parametrize("occ", [OccupancyType.SINGLE, OccupancyType.DOUBLE])
    def test_valid_room_serialization(self, r_type, occ):
        ser = RoomSerializer(data={
            "room_number": f"RM-{r_type[:2]}-{occ[:2]}",
            "room_type": r_type,
            "occupancy_type": occ,
            "floor": 1,
            "status": RoomStatus.AVAILABLE,
        })
        assert ser.is_valid(), ser.errors

    @pytest.mark.parametrize("bad_status", ["UNKNOWN", "VACANT", "DIRTY"])
    def test_invalid_room_status_choice(self, bad_status):
        ser = RoomSerializer(data={
            "room_number": "RM-BAD",
            "status": bad_status,
        })
        assert ser.is_valid() is False
        assert "status" in ser.errors


@pytest.mark.django_db
class TestMealBookingSerializerValidation:
    @pytest.mark.parametrize("status_val,should_succeed", [
        (BookingStatus.PENDING, False),
        (BookingStatus.FORWARDED, False),
        (BookingStatus.APPROVED, False),
        (BookingStatus.REJECTED, False),
        (BookingStatus.ROOM_ALLOTTED, False),
        (BookingStatus.CHECKED_IN, True),
        (BookingStatus.CHECKED_OUT, False),
        (BookingStatus.CANCELLATION_REQUESTED, False),
        (BookingStatus.CANCELLED, False),
    ])
    def test_meal_booking_status_validation_br_vh_025(self, category_a, status_val, should_succeed):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Meal Val Guest",
            visitor_category=category_a,
            visit_purpose="Meal Val",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=status_val,
        )
        ser = MealBookingSerializer(data={
            "booking": b.id,
            "date": str(today + timedelta(days=1)),
            "meal_type": MealType.LUNCH,
            "add_on": MealAddOn.NONE,
            "number_of_persons": 1,
        })
        if should_succeed:
            assert ser.is_valid(), ser.errors
        else:
            assert ser.is_valid() is False
            assert "booking" in ser.errors
            assert "BR-VH-025" in str(ser.errors["booking"])

    @pytest.mark.parametrize("date_offset,should_succeed", [
        (-1, False),  # before check-in
        (0, True),    # on check-in
        (1, True),    # during stay
        (2, True),    # on check-out
        (3, False),   # after check-out
        (10, False),  # way after check-out
    ])
    def test_meal_booking_date_duration_validation_br_vh_031(self, category_a, date_offset, should_succeed):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Meal Duration Guest",
            visitor_category=category_a,
            visit_purpose="Duration Val",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.CHECKED_IN,
        )
        ser = MealBookingSerializer(data={
            "booking": b.id,
            "date": str(today + timedelta(days=date_offset)),
            "meal_type": MealType.DINNER,
            "add_on": MealAddOn.TEA,
            "number_of_persons": 1,
        })
        if should_succeed:
            assert ser.is_valid(), ser.errors
        else:
            assert ser.is_valid() is False
            assert "date" in ser.errors
            assert "BR-VH-031" in str(ser.errors["date"])


@pytest.mark.django_db
class TestBillSerializerImmutability:
    @pytest.mark.parametrize("field_name,new_val", [
        ("room_charges", Decimal("2000.00")),
        ("meal_charges", Decimal("500.00")),
        ("cancellation_charges", Decimal("300.00")),
        ("total_amount", Decimal("2500.00")),
        ("is_finalized", False),
    ])
    def test_finalized_bill_field_mutation_blocked(self, category_a, field_name, new_val):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Imm Guest",
            visitor_category=category_a,
            visit_purpose="Imm",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        bill = Bill.objects.create(
            booking=b,
            room_charges=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
            is_finalized=True,
        )
        ser = BillSerializer(instance=bill, data={field_name: new_val}, partial=True)
        assert ser.is_valid() is False
        assert "BR-VH-037" in str(ser.errors)

    def test_unfinalized_bill_mutation_allowed(self, category_a):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Unfin Guest",
            visitor_category=category_a,
            visit_purpose="Unfin",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        bill = Bill.objects.create(
            booking=b,
            room_charges=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            is_finalized=False,
        )
        ser = BillSerializer(instance=bill, data={"room_charges": Decimal("800.00"), "total_amount": Decimal("800.00")}, partial=True)
        assert ser.is_valid(), ser.errors


@pytest.mark.django_db
class TestBookingModificationSerializerValidation:
    @pytest.mark.parametrize("st,allowed", [
        (BookingStatus.PENDING, True),
        (BookingStatus.FORWARDED, True),
        (BookingStatus.APPROVED, True),
        (BookingStatus.ROOM_ALLOTTED, True),
        (BookingStatus.CHECKED_IN, False),
        (BookingStatus.CHECKED_OUT, False),
        (BookingStatus.CANCELLED, False),
    ])
    def test_modification_allowed_pre_arrival_only(self, category_a, st, allowed):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Mod Val Guest",
            visitor_category=category_a,
            visit_purpose="Mod Val",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            status=st,
        )
        ser = BookingModificationSerializer(data={
            "booking": b.id,
            "new_number_of_rooms": 2,
            "reason": "Need extra room",
        })
        if allowed:
            assert ser.is_valid(), ser.errors
        else:
            assert ser.is_valid() is False
            assert "booking" in ser.errors


@pytest.mark.django_db
class TestBookingSerializerValidation:
    @pytest.mark.parametrize("in_offset,out_offset,is_valid", [
        (1, 3, True),
        (2, 2, True),   # same day allowed
        (4, 2, False),  # check_out before check_in
        (10, 5, False), # check_out before check_in
    ])
    def test_date_range_validation(self, category_a, in_offset, out_offset, is_valid):
        today = timezone.localdate()
        ser = BookingSerializer(data={
            "indenter_id": 1,
            "visitor_name": "Date Range Guest",
            "visitor_category": category_a.id,
            "visit_purpose": "Testing",
            "check_in_date": str(today + timedelta(days=in_offset)),
            "check_out_date": str(today + timedelta(days=out_offset)),
            "number_of_rooms": 1,
            "billing_responsibility": BillingResponsibility.VISITOR,
        })
        if is_valid:
            assert ser.is_valid(), ser.errors
        else:
            assert ser.is_valid() is False
            assert "check_out_date" in ser.errors

    def test_read_only_fields_ignored_on_create(self, category_a):
        today = timezone.localdate()
        ser = BookingSerializer(data={
            "indenter_id": 1,
            "visitor_name": "RO Guest",
            "visitor_category": category_a.id,
            "visit_purpose": "Testing RO",
            "check_in_date": str(today),
            "check_out_date": str(today + timedelta(days=1)),
            "status": BookingStatus.APPROVED,  # attacker trying to inject approved
            "booking_reference": "CUSTOM-REF-123",
        })
        assert ser.is_valid(), ser.errors
        instance = ser.save()
        assert instance.status == BookingStatus.PENDING  # read-only, default stays PENDING
        assert instance.booking_reference != "CUSTOM-REF-123"  # read-only generated


@pytest.mark.django_db
class TestOtherSerializers:
    def test_inventory_item_serializer(self):
        ser = InventoryItemSerializer(data={
            "name": "Bedsheets Extra",
            "category": "LINEN",
            "current_quantity": 25,
            "minimum_threshold": 10,
        })
        assert ser.is_valid(), ser.errors
        inst = ser.save()
        assert ser.data["is_below_threshold"] is False

    def test_user_role_serializer(self):
        ser = VHMSUserRoleSerializer(data={
            "role_type": VHMSUserRoleType.CARETAKER,
            "user_id": 77,
            "start_date": str(timezone.localdate()),
            "is_active": True,
        })
        assert ser.is_valid(), ser.errors

    def test_vh_alert_serializer(self):
        ser = VHAlertSerializer(data={
            "alert_type": "NO_SHOW",
            "message": "Alert message",
        })
        assert ser.is_valid(), ser.errors

    def test_notification_log_serializer(self):
        ser = VHNotificationLogSerializer(data={
            "event_type": "BOOKING_SUBMITTED",
            "recipient_email": "guest@test.com",
            "subject": "Test Subj",
            "body": "Test Body",
        })
        assert ser.is_valid(), ser.errors

