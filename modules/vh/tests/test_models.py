"""Unit tests for Visitors Hostel (VH) models and constraints."""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from modules.vh.models import (
    Bill,
    BillingResponsibility,
    Booking,
    BookingModification,
    BookingStatus,
    InventoryCategory,
    InventoryItem,
    InventoryReplenishment,
    MealAddOn,
    MealBooking,
    MealType,
    ModificationStatus,
    OccupancyType,
    OfflineBookingType,
    PaymentMode,
    ReplenishmentStatus,
    Room,
    RoomAllotment,
    RoomStatus,
    RoomType,
    Tariff,
    VHAlert,
    VHAlertType,
    VHNotificationEventType,
    VHNotificationLog,
    VisitorCategory,
    VHMSUserRole,
    VHMSUserRoleType,
    generate_booking_reference,
)


@pytest.mark.django_db
class TestVisitorCategoryModel:
    @pytest.mark.parametrize("code,name", [
        (VisitorCategory.CATEGORY_A, "Category A - Institute Guests / Official"),
        (VisitorCategory.CATEGORY_B, "Category B - Invited Academic / Research Visitors"),
        (VisitorCategory.CATEGORY_C, "Category C - Students / Alumni Guests"),
        (VisitorCategory.CATEGORY_D, "Category D - Others / Personal"),
    ])
    def test_visitor_category_creation_and_str(self, code, name):
        cat = VisitorCategory.objects.create(code=code, name=name)
        assert cat.code == code
        assert str(cat) == f"{code} - {name}"

    def test_duplicate_category_code_raises_integrity_error(self, category_a):
        with pytest.raises(IntegrityError):
            VisitorCategory.objects.create(code=category_a.code, name="Duplicate")


@pytest.mark.django_db
class TestRoomModel:
    @pytest.mark.parametrize("r_type", [RoomType.SUITE, RoomType.NON_SUITE])
    @pytest.mark.parametrize("occ", [OccupancyType.SINGLE, OccupancyType.DOUBLE])
    @pytest.mark.parametrize("st", [RoomStatus.AVAILABLE, RoomStatus.OCCUPIED, RoomStatus.MAINTENANCE])
    def test_room_type_occupancy_and_status_combinations(self, r_type, occ, st):
        num = f"R-{r_type[:2]}-{occ[:1]}-{st[:2]}"
        room = Room.objects.create(
            room_number=num,
            room_type=r_type,
            occupancy_type=occ,
            status=st,
        )
        assert room.room_type == r_type
        assert room.occupancy_type == occ
        assert room.status == st
        assert str(room) == f"Room {num} ({room.get_room_type_display()}, {st})"

    def test_room_number_unique(self, sample_room):
        with pytest.raises(IntegrityError):
            Room.objects.create(room_number=sample_room.room_number)


@pytest.mark.django_db
class TestTariffModel:
    def test_tariff_creation_and_str(self, category_a):
        tariff = Tariff.objects.create(
            category=category_a,
            room_type=RoomType.SUITE,
            occupancy_type=OccupancyType.DOUBLE,
            rate_per_day=Decimal("1500.00"),
            effective_from=timezone.localdate(),
        )
        assert tariff.rate_per_day == Decimal("1500.00")
        assert "Tariff A SUITE/DOUBLE: 1500.00/day" in str(tariff)

    def test_tariff_unique_together_constraint(self, category_a):
        today = timezone.localdate()
        Tariff.objects.create(
            category=category_a,
            room_type=RoomType.NON_SUITE,
            occupancy_type=OccupancyType.SINGLE,
            rate_per_day=Decimal("500.00"),
            effective_from=today,
        )
        with pytest.raises(IntegrityError):
            Tariff.objects.create(
                category=category_a,
                room_type=RoomType.NON_SUITE,
                occupancy_type=OccupancyType.SINGLE,
                rate_per_day=Decimal("600.00"),
                effective_from=today,
            )


@pytest.mark.django_db
class TestBookingModel:
    def test_generate_booking_reference_format(self):
        ref = generate_booking_reference()
        assert ref.startswith("VH-")
        parts = ref.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # 6 hex chars

    @pytest.mark.parametrize("billing_resp", [
        BillingResponsibility.VISITOR,
        BillingResponsibility.INDENTER,
        BillingResponsibility.INSTITUTE,
        BillingResponsibility.PROJECT,
    ])
    def test_booking_billing_responsibility_choices(self, category_a, billing_resp):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Guest",
            visitor_category=category_a,
            visit_purpose="Official",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            billing_responsibility=billing_resp,
        )
        assert b.billing_responsibility == billing_resp
        assert b.booking_reference.startswith("VH-")

    @pytest.mark.parametrize("status_val", [
        BookingStatus.PENDING,
        BookingStatus.FORWARDED,
        BookingStatus.APPROVED,
        BookingStatus.REJECTED,
        BookingStatus.ROOM_ALLOTTED,
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_booking_status_string_representation(self, category_a, status_val):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Status Guest",
            visitor_category=category_a,
            visit_purpose="Testing",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=status_val,
        )
        assert str(b) == f"{b.booking_reference} - Status Guest ({status_val})"

    @pytest.mark.parametrize("off_type", [OfflineBookingType.TELEPHONIC, OfflineBookingType.WALK_IN])
    def test_offline_booking_fields(self, category_a, off_type):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            is_offline=True,
            offline_booking_type=off_type,
            visitor_name="Offline Guest",
            visitor_category=category_a,
            visit_purpose="Walkin",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        assert b.is_offline is True
        assert b.offline_booking_type == off_type


@pytest.mark.django_db
class TestRoomAllotmentModel:
    def test_room_allotment_fields_and_str(self, category_a, sample_room):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Allot Guest",
            visitor_category=category_a,
            visit_purpose="Exam",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=BookingStatus.APPROVED,
        )
        allot = RoomAllotment.objects.create(booking=b, room=sample_room)
        assert allot.is_no_show is False
        assert allot.is_overstay is False
        assert str(allot) == f"Allotment {sample_room.room_number} for {b.booking_reference}"


@pytest.mark.django_db
class TestMealBookingModel:
    @pytest.mark.parametrize("m_type", [
        MealType.BREAKFAST,
        MealType.LUNCH,
        MealType.DINNER,
        MealType.FULL_DAY,
    ])
    @pytest.mark.parametrize("addon", [
        MealAddOn.NONE,
        MealAddOn.TEA,
        MealAddOn.MILK,
    ])
    def test_meal_booking_creation_and_str(self, category_a, m_type, addon):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Diner",
            visitor_category=category_a,
            visit_purpose="Food Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.CHECKED_IN,
        )
        mb = MealBooking.objects.create(
            booking=b,
            date=today,
            meal_type=m_type,
            add_on=addon,
            number_of_persons=1,
            rate=Decimal("120.00"),
            total_amount=Decimal("120.00"),
        )
        assert mb.meal_type == m_type
        assert mb.add_on == addon
        assert str(mb) == f"Meal for {b.booking_reference}: {m_type} on {today}"


@pytest.mark.django_db
class TestBillModel:
    def test_bill_creation_and_str(self, category_a):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Billed",
            visitor_category=category_a,
            visit_purpose="Bill Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        bill = Bill.objects.create(
            booking=b,
            room_charges=Decimal("1000.00"),
            meal_charges=Decimal("200.00"),
            cancellation_charges=Decimal("0.00"),
            total_amount=Decimal("1200.00"),
            payment_mode=PaymentMode.CASH,
            is_settled=True,
            is_finalized=True,
        )
        assert "settled=True, finalized=True" in str(bill)

    def test_finalized_bill_clean_raises_validation_error_on_unfinalize(self, category_a):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Billed 2",
            visitor_category=category_a,
            visit_purpose="Imm Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        bill = Bill.objects.create(
            booking=b,
            total_amount=Decimal("500.00"),
            is_finalized=True,
        )
        bill.is_finalized = False
        with pytest.raises(ValidationError):
            bill.clean()

    def test_finalized_bill_save_raises_validation_error_on_amount_change(self, category_a):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Billed 3",
            visitor_category=category_a,
            visit_purpose="Imm Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        bill = Bill.objects.create(
            booking=b,
            room_charges=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            is_finalized=True,
        )
        bill.room_charges = Decimal("800.00")
        with pytest.raises(ValidationError):
            bill.save()


@pytest.mark.django_db
class TestInventoryModels:
    @pytest.mark.parametrize("cat_choice", [
        InventoryCategory.LINEN,
        InventoryCategory.UTENSILS,
        InventoryCategory.CONSUMABLES,
        InventoryCategory.OTHERS,
    ])
    def test_inventory_categories_and_str(self, cat_choice):
        item = InventoryItem.objects.create(
            name=f"Item {cat_choice}",
            category=cat_choice,
            current_quantity=15,
            minimum_threshold=10,
        )
        assert item.category == cat_choice
        assert str(item) == f"Item {cat_choice} (Qty: 15, Min: 10)"

    @pytest.mark.parametrize("qty,thresh,expected_below", [
        (15, 10, False),
        (10, 10, False),
        (9, 10, True),
        (0, 5, True),
    ])
    def test_inventory_below_threshold_property(self, qty, thresh, expected_below):
        item = InventoryItem.objects.create(
            name=f"Stock-{qty}-{thresh}",
            current_quantity=qty,
            minimum_threshold=thresh,
        )
        assert item.is_below_threshold is expected_below

    @pytest.mark.parametrize("rep_status", [
        ReplenishmentStatus.PENDING,
        ReplenishmentStatus.APPROVED,
        ReplenishmentStatus.REJECTED,
    ])
    def test_inventory_replenishment_str(self, rep_status):
        item = InventoryItem.objects.create(name=f"Item Rep {rep_status}", current_quantity=2)
        rep = InventoryReplenishment.objects.create(
            item=item,
            quantity_requested=20,
            requested_by_user_id=1,
            status=rep_status,
        )
        assert str(rep) == f"Replenish {item.name} x 20 ({rep_status})"


@pytest.mark.django_db
class TestVHMSUserRoleModel:
    @pytest.mark.parametrize("r_type", [VHMSUserRoleType.CARETAKER, VHMSUserRoleType.IN_CHARGE])
    def test_role_creation_and_str(self, r_type):
        role = VHMSUserRole.objects.create(
            role_type=r_type,
            user_id=401,
            is_active=True,
        )
        assert str(role) == f"{role.get_role_type_display()} - User 401 (active=True)"

    def test_get_active_caretaker_and_incharge(self):
        assert VHMSUserRole.get_active_caretaker() is None
        assert VHMSUserRole.get_active_incharge() is None

        c = VHMSUserRole.objects.create(role_type=VHMSUserRoleType.CARETAKER, user_id=11, is_active=True)
        i = VHMSUserRole.objects.create(role_type=VHMSUserRoleType.IN_CHARGE, user_id=12, is_active=True)

        assert VHMSUserRole.get_active_caretaker().id == c.id
        assert VHMSUserRole.get_active_incharge().id == i.id


@pytest.mark.django_db
class TestBookingModificationModel:
    @pytest.mark.parametrize("m_status", [
        ModificationStatus.PENDING,
        ModificationStatus.CONFIRMED,
        ModificationStatus.REJECTED,
    ])
    def test_modification_status_and_str(self, category_a, m_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Mod Model Guest",
            visitor_category=category_a,
            visit_purpose="Mod Model Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
        )
        mod = BookingModification.objects.create(
            booking=b,
            requested_by_user_id=1,
            reason="Date adjustment",
            status=m_status,
        )
        assert str(mod) == f"Modification for {b.booking_reference} ({m_status})"


@pytest.mark.django_db
class TestVHAlertAndNotificationModels:
    @pytest.mark.parametrize("alt_type", [
        VHAlertType.NO_SHOW,
        VHAlertType.OVERSTAY,
        VHAlertType.INVENTORY_THRESHOLD,
        VHAlertType.STAY_REMINDER,
    ])
    def test_alert_types_and_str(self, alt_type):
        alert = VHAlert.objects.create(
            alert_type=alt_type,
            message=f"Test message for {alt_type}",
        )
        assert str(alert).startswith(f"Alert [{alt_type}]:")

    @pytest.mark.parametrize("evt_type", [
        VHNotificationEventType.BOOKING_SUBMITTED,
        VHNotificationEventType.BOOKING_FORWARDED,
        VHNotificationEventType.BOOKING_APPROVED,
        VHNotificationEventType.BOOKING_REJECTED,
        VHNotificationEventType.CANCELLATION_REQUESTED,
        VHNotificationEventType.BOOKING_CANCELLED,
        VHNotificationEventType.MODIFICATION_REQUESTED,
        VHNotificationEventType.MODIFICATION_CONFIRMED,
        VHNotificationEventType.INVENTORY_THRESHOLD,
    ])
    def test_notification_event_types_and_str(self, evt_type):
        log = VHNotificationLog.objects.create(
            event_type=evt_type,
            recipient_email="test@example.com",
            subject="Subj",
            body="Body",
        )
        assert str(log) == f"Notification [{evt_type}] to test@example.com"

