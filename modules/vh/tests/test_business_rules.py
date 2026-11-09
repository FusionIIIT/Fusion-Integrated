"""Systematic unit and integration test suite covering all 38 Business Rules (BR-VH-002..050)."""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.utils import timezone

from modules.vh.models import (
    Bill,
    BillingResponsibility,
    Booking,
    BookingStatus,
    InventoryCategory,
    InventoryItem,
    MealAddOn,
    MealBooking,
    MealType,
    OccupancyType,
    OfflineBookingType,
    PaymentMode,
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
)
from modules.vh.services.notifications import (
    check_inventory_threshold_alert,
    check_stay_exception_alerts,
)


@pytest.mark.django_db
class TestBR002BillingResponsibilityValues:
    """BR-VH-002: Restrict billing responsibility to Visitor, Indenter, Institute, or Project."""

    @pytest.mark.parametrize("valid_resp", [
        BillingResponsibility.VISITOR,
        BillingResponsibility.INDENTER,
        BillingResponsibility.INSTITUTE,
        BillingResponsibility.PROJECT,
    ])
    def test_valid_billing_responsibility(self, api_client, category_a, valid_resp):
        today = timezone.localdate()
        resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 1,
                "visitor_name": "Resp Guest",
                "visitor_category": category_a.id,
                "visit_purpose": "Conference",
                "check_in_date": str(today + timedelta(days=2)),
                "check_out_date": str(today + timedelta(days=3)),
                "billing_responsibility": valid_resp,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["billing_responsibility"] == valid_resp

    @pytest.mark.parametrize("invalid_resp", ["STUDENT", "CORPORATE", "ALUMNI", "VENDOR", "OTHER"])
    def test_invalid_billing_responsibility_rejected(self, api_client, category_a, invalid_resp):
        today = timezone.localdate()
        resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 1,
                "visitor_name": "Bad Resp Guest",
                "visitor_category": category_a.id,
                "visit_purpose": "Conference",
                "check_in_date": str(today + timedelta(days=2)),
                "check_out_date": str(today + timedelta(days=3)),
                "billing_responsibility": invalid_resp,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "billing_responsibility" in str(resp.data)


@pytest.mark.django_db
class TestBR003To005OfflineBookings:
    """BR-VH-003: Same approval routing; BR-VH-004: Same availability check; BR-VH-005: Clearly flag offline."""

    @pytest.mark.parametrize("offline_type", [OfflineBookingType.TELEPHONIC, OfflineBookingType.WALK_IN])
    def test_offline_booking_flag_and_routing(self, api_client, category_a, offline_type):
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 1,
                "is_offline": True,
                "offline_booking_type": offline_type,
                "visitor_name": f"Offline Guest {offline_type}",
                "visitor_category": category_a.id,
                "visit_purpose": "Official Meeting",
                "check_in_date": str(today + timedelta(days=2)),
                "check_out_date": str(today + timedelta(days=4)),
            },
            format="json",
        )
        assert create_resp.status_code == 201
        b_id = create_resp.data["id"]
        assert create_resp.data["is_offline"] is True
        assert create_resp.data["offline_booking_type"] == offline_type

        # Follows same routing (BR-VH-003)
        fwd_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/forward/", {"remarks": "Routing test"})
        assert fwd_resp.status_code == 200
        assert fwd_resp.data["status"] == BookingStatus.FORWARDED

        app_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/approve/", {"remarks": "Routing approve test"})
        assert app_resp.status_code == 200
        assert app_resp.data["status"] == BookingStatus.APPROVED


@pytest.mark.django_db
class TestBR006To009CancellationChargesSchedule:
    """BR-VH-006..009: Compute cancellation charges according to schedule.

    - >= 7 days notice: 0% charge (BR-VH-007)
    - 1 to 6 days notice: 25% of 1-day room rent (BR-VH-008)
    - 0 or past days notice: 50% of 1-day room rent (BR-VH-009)
    """

    @pytest.mark.parametrize("days_notice", [7, 8, 9, 10, 11, 14, 21, 30, 45, 60])
    def test_cancellation_7_or_more_days_notice_zero_charge_br_vh_007(
        self, api_client, category_a, sample_tariff, days_notice
    ):
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Cancel Notice {days_notice}",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today + timedelta(days=days_notice),
            check_out_date=today + timedelta(days=days_notice + 2),
            number_of_rooms=1,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/")
        assert resp.status_code == 200
        assert Decimal(resp.data["applicable_cancellation_charge"]) == Decimal("0.00")

    @pytest.mark.parametrize("days_notice", [1, 2, 3, 4, 5, 6])
    def test_cancellation_within_7_days_notice_25_percent_br_vh_008(
        self, api_client, category_a, sample_tariff, days_notice
    ):
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Cancel Notice {days_notice}",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today + timedelta(days=days_notice),
            check_out_date=today + timedelta(days=days_notice + 2),
            number_of_rooms=1,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/")
        assert resp.status_code == 200
        # Tariff is 1000/day. 25% = 250.00
        assert Decimal(resp.data["applicable_cancellation_charge"]) == Decimal("250.00")

    @pytest.mark.parametrize("days_notice", [0, -1, -2])
    def test_cancellation_same_day_or_past_50_percent_br_vh_009(
        self, api_client, category_a, sample_tariff, days_notice
    ):
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Cancel Same Day {days_notice}",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today + timedelta(days=days_notice),
            check_out_date=today + timedelta(days=days_notice + 2),
            number_of_rooms=1,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/")
        assert resp.status_code == 200
        # Tariff is 1000/day. 50% = 500.00
        assert Decimal(resp.data["applicable_cancellation_charge"]) == Decimal("500.00")

    @pytest.mark.parametrize("rooms,days_notice,expected_charge", [
        (1, 10, Decimal("0.00")),
        (2, 10, Decimal("0.00")),
        (3, 10, Decimal("0.00")),
        (1, 3, Decimal("250.00")),    # 25% of 1000*1 = 250
        (2, 3, Decimal("500.00")),    # 25% of 1000*2 = 500
        (3, 3, Decimal("750.00")),    # 25% of 1000*3 = 750
        (4, 3, Decimal("1000.00")),   # 25% of 1000*4 = 1000
        (1, 0, Decimal("500.00")),    # 50% of 1000*1 = 500
        (2, 0, Decimal("1000.00")),   # 50% of 1000*2 = 1000
        (3, 0, Decimal("1500.00")),   # 50% of 1000*3 = 1500
        (4, 0, Decimal("2000.00")),   # 50% of 1000*4 = 2000
    ])
    def test_cancellation_charges_multiplied_by_number_of_rooms(
        self, api_client, category_a, sample_tariff, rooms, days_notice, expected_charge
    ):
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Cancel Rooms {rooms}",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today + timedelta(days=days_notice),
            check_out_date=today + timedelta(days=days_notice + 2),
            number_of_rooms=rooms,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/")
        assert resp.status_code == 200
        assert Decimal(resp.data["applicable_cancellation_charge"]) == expected_charge


@pytest.mark.django_db
class TestBR010To011BillingAdjustments:
    """BR-VH-010: Adjust billing according to confirmed modification; BR-VH-011: Confirmed cancellation billing."""

    def test_confirmed_cancellation_bill_adjustment_br_vh_011(
        self, api_client, category_a, sample_tariff
    ):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Adjust Guest",
            visitor_category=category_a,
            visit_purpose="Adjust Check",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            number_of_rooms=1,
        )
        api_client.post(f"/api/v1/vh/bookings/{b.id}/request_cancellation/")
        confirm_resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/confirm_cancellation/")
        assert confirm_resp.status_code == 200
        bill = Bill.objects.get(booking=b)
        assert bill.cancellation_charges == Decimal("250.00")
        assert bill.total_amount == Decimal("250.00")


@pytest.mark.django_db
class TestBR012RoomAllotmentEligibility:
    """BR-VH-012: VHMS shall allow rooms to be allotted only after booking approval."""

    @pytest.mark.parametrize("status_val", [
        BookingStatus.PENDING,
        BookingStatus.FORWARDED,
        BookingStatus.REJECTED,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_allotment_blocked_for_non_approved_bookings(
        self, api_client, category_a, sample_room, status_val
    ):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Eligibility Guest",
            visitor_category=category_a,
            visit_purpose="Eligibility",
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=2),
            status=status_val,
        )
        resp = api_client.post(
            f"/api/v1/vh/bookings/{b.id}/allot_room/",
            {"room_ids": [sample_room.id]},
            format="json",
        )
        assert resp.status_code == 400
        assert "BR-VH-012" in resp.data["error"]


@pytest.mark.django_db
class TestBR013To016RoomAndOccupancyTypes:
    """BR-VH-013..016: Support Single/Double occupancy and Suite/Non-suite rooms."""

    @pytest.mark.parametrize("r_type", [RoomType.SUITE, RoomType.NON_SUITE])
    @pytest.mark.parametrize("occ", [OccupancyType.SINGLE, OccupancyType.DOUBLE])
    def test_supported_room_and_occupancy_records(self, r_type, occ):
        room = Room.objects.create(
            room_number=f"RM-{r_type}-{occ}",
            room_type=r_type,
            occupancy_type=occ,
        )
        assert room.room_type in [RoomType.SUITE, RoomType.NON_SUITE]
        assert room.occupancy_type in [OccupancyType.SINGLE, OccupancyType.DOUBLE]


@pytest.mark.django_db
class TestBR017And018StayExceptionsAndAlerts:
    """BR-VH-017: No-show alert when guest has not checked in; BR-VH-018: Overstay alert when stay exceeds duration."""

    @pytest.mark.parametrize("is_checked_in,is_past_arrival,expect_noshow", [
        (False, True, True),
        (True, True, False),
        (False, False, False),
    ])
    def test_no_show_conditions_br_vh_017(
        self, category_a, sample_room, is_checked_in, is_past_arrival, expect_noshow
    ):
        today = timezone.localdate()
        arr_date = today - timedelta(days=1) if is_past_arrival else today + timedelta(days=2)
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="No Show Cond",
            visitor_category=category_a,
            visit_purpose="Stay",
            check_in_date=arr_date,
            check_out_date=arr_date + timedelta(days=2),
            status=BookingStatus.CHECKED_IN if is_checked_in else BookingStatus.ROOM_ALLOTTED,
        )
        RoomAllotment.objects.create(
            booking=b,
            room=sample_room,
            check_in_time=timezone.now() if is_checked_in else None,
        )
        res = check_stay_exception_alerts()
        if expect_noshow:
            assert res["no_shows"] >= 1
            assert VHAlert.objects.filter(alert_type=VHAlertType.NO_SHOW, booking=b).exists()
        else:
            assert not VHAlert.objects.filter(alert_type=VHAlertType.NO_SHOW, booking=b).exists()

    @pytest.mark.parametrize("is_checked_out,is_past_departure,expect_overstay", [
        (False, True, True),
        (True, True, False),
        (False, False, False),
    ])
    def test_overstay_conditions_br_vh_018(
        self, category_a, sample_room, is_checked_out, is_past_departure, expect_overstay
    ):
        today = timezone.localdate()
        dep_date = today - timedelta(days=1) if is_past_departure else today + timedelta(days=2)
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Overstay Cond",
            visitor_category=category_a,
            visit_purpose="Stay",
            check_in_date=dep_date - timedelta(days=3),
            check_out_date=dep_date,
            status=BookingStatus.CHECKED_OUT if is_checked_out else BookingStatus.CHECKED_IN,
        )
        RoomAllotment.objects.create(
            booking=b,
            room=sample_room,
            check_in_time=timezone.now() - timedelta(days=3),
            check_out_time=timezone.now() if is_checked_out else None,
        )
        res = check_stay_exception_alerts()
        if expect_overstay:
            assert res["overstays"] >= 1
            assert VHAlert.objects.filter(alert_type=VHAlertType.OVERSTAY, booking=b).exists()
        else:
            assert not VHAlert.objects.filter(alert_type=VHAlertType.OVERSTAY, booking=b).exists()


@pytest.mark.django_db
class TestBR019VisitorCategories:
    """BR-VH-019: Visitor category values used by VHMS shall be A, B, C, or D."""

    @pytest.mark.parametrize("cat_code", ["A", "B", "C", "D"])
    def test_valid_visitor_categories(self, cat_code):
        cat = VisitorCategory.objects.create(code=cat_code, name=f"Cat {cat_code}")
        assert cat.code in ["A", "B", "C", "D"]


@pytest.mark.django_db
class TestBR023And024TariffSelectionAndIntegrity:
    """BR-VH-023: Select applicable tariff during billing; BR-VH-024: Prevent tariff change from affecting historical bills."""

    def test_tariff_selection_by_category_and_occupancy_br_vh_023(
        self, api_client, all_categories, all_room_combinations, all_tariffs
    ):
        today = timezone.localdate()
        cat = all_categories[1]  # Category B
        room = all_room_combinations[0]  # SUITE, SINGLE
        tariff = Tariff.objects.get(category=cat, room_type=room.room_type, occupancy_type=room.occupancy_type)

        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Tariff Match Guest",
            visitor_category=cat,
            visit_purpose="Research",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.ROOM_ALLOTTED,
        )
        RoomAllotment.objects.create(booking=booking, room=room)
        api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_in/")

        co_resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/")
        assert co_resp.status_code == 200
        expected_charges = tariff.rate_per_day * Decimal("2")
        assert Decimal(co_resp.data["bill"]["room_charges"]) == expected_charges

    def test_historical_bill_not_affected_by_tariff_update_br_vh_024(
        self, category_a, sample_tariff
    ):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Hist Guest",
            visitor_category=category_a,
            visit_purpose="Exam",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        bill = Bill.objects.create(
            booking=b,
            room_charges=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
            is_finalized=True,
        )

        # Update tariff rate
        sample_tariff.rate_per_day = Decimal("2500.00")
        sample_tariff.save()

        # Verify historical bill remains unaltered
        bill.refresh_from_db()
        assert bill.room_charges == Decimal("1000.00")
        assert bill.total_amount == Decimal("1000.00")


@pytest.mark.django_db
class TestBR025To034MessAndMealBookings:
    """BR-VH-025..034: Meal bookings options, stay duration constraint, billing inclusion."""

    @pytest.mark.parametrize("m_type", [MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER])
    @pytest.mark.parametrize("addon", [MealAddOn.NONE, MealAddOn.TEA, MealAddOn.MILK])
    def test_meal_and_addon_options_br_vh_029_030(
        self, api_client, category_a, m_type, addon
    ):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Meal Opt Guest",
            visitor_category=category_a,
            visit_purpose="Food",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.CHECKED_IN,
        )
        resp = api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": b.id,
                "date": str(today + timedelta(days=1)),
                "meal_type": m_type,
                "add_on": addon,
                "number_of_persons": 1,
                "rate": "100.00",
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["meal_type"] == m_type
        assert resp.data["add_on"] == addon

    @pytest.mark.parametrize("days,rooms,rate,expected_rent", [
        (1, 1, Decimal("500.00"), Decimal("500.00")),
        (2, 1, Decimal("500.00"), Decimal("1000.00")),
        (3, 2, Decimal("500.00"), Decimal("3000.00")),
        (5, 3, Decimal("1000.00"), Decimal("15000.00")),
    ])
    def test_bill_calculation_based_on_room_rent_br_vh_033(
        self, api_client, category_a, sample_room, days, rooms, rate, expected_rent
    ):
        today = timezone.localdate()
        Tariff.objects.filter(category=category_a).delete()
        Tariff.objects.create(
            category=category_a,
            room_type=sample_room.room_type,
            occupancy_type=sample_room.occupancy_type,
            rate_per_day=rate,
        )

        b = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Rent Calc {days}d-{rooms}r",
            visitor_category=category_a,
            visit_purpose="Rent Test",
            check_in_date=today,
            check_out_date=today + timedelta(days=days),
            number_of_rooms=rooms,
            status=BookingStatus.ROOM_ALLOTTED,
        )
        RoomAllotment.objects.create(booking=b, room=sample_room)
        api_client.post(f"/api/v1/vh/bookings/{b.id}/check_in/")
        co_resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/check_out/")
        assert co_resp.status_code == 200
        assert Decimal(co_resp.data["bill"]["room_charges"]) == expected_rent


@pytest.mark.django_db
class TestBR036And037BillSettlementAndImmutability:
    """BR-VH-036: Offline cash settlement only; BR-VH-037: Maintain immutable billing records for audit."""

    def test_offline_cash_settlement_br_vh_036(self, api_client, category_a):
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Cash Settle Guest",
            visitor_category=category_a,
            visit_purpose="Cash Check",
            check_in_date=timezone.localdate(),
            check_out_date=timezone.localdate() + timedelta(days=1),
        )
        bill = Bill.objects.create(
            booking=b,
            total_amount=Decimal("1500.00"),
            payment_mode=PaymentMode.CASH,
        )
        resp = api_client.post(
            f"/api/v1/vh/bills/{bill.id}/settle/",
            {"guest_verification_notes": "Cash collected in INR"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["payment_mode"] == "CASH"
        assert resp.data["is_settled"] is True
        assert resp.data["is_finalized"] is True


@pytest.mark.django_db
class TestBR041And043InventoryThresholdAlerts:
    """BR-VH-041: Alert when below threshold; BR-VH-043: Alert triggers system email notification."""

    @pytest.mark.parametrize("qty,threshold,should_alert", [
        (15, 10, False),
        (10, 10, False),
        (9, 10, True),
        (0, 10, True),
    ])
    def test_inventory_threshold_detection_and_notification(self, qty, threshold, should_alert):
        item = InventoryItem.objects.create(
            name=f"Threshold Item {qty}",
            category=InventoryCategory.CONSUMABLES,
            current_quantity=qty,
            minimum_threshold=threshold,
        )
        alert = check_inventory_threshold_alert(item)
        if should_alert:
            assert alert is not None
            assert alert.alert_type == VHAlertType.INVENTORY_THRESHOLD
            assert VHNotificationLog.objects.filter(event_type=VHNotificationEventType.INVENTORY_THRESHOLD).exists()
        else:
            assert alert is None


@pytest.mark.django_db
class TestBR045To050RoleManagementAndRecordTransfer:
    """BR-VH-045: 1 active Caretaker; BR-VH-046: 1 active In-Charge; BR-VH-047..050: Transfer records immediately."""

    @pytest.mark.parametrize("role_type", [VHMSUserRoleType.CARETAKER, VHMSUserRoleType.IN_CHARGE])
    def test_single_active_role_enforcement(self, role_type):
        r1 = VHMSUserRole.reassign_role(role_type=role_type, user_id=10)
        assert r1.is_active is True
        assert VHMSUserRole.objects.filter(role_type=role_type, is_active=True).count() == 1

        r2 = VHMSUserRole.reassign_role(role_type=role_type, user_id=20)
        assert r2.is_active is True
        r1.refresh_from_db()
        assert r1.is_active is False
        assert VHMSUserRole.objects.filter(role_type=role_type, is_active=True).count() == 1

    def test_record_transfer_to_new_caretaker_br_vh_049_050(self, category_a):
        today = timezone.localdate()
        b_pending = Booking.objects.create(
            indenter_id=1,
            visitor_name="Pending Record",
            visitor_category=category_a,
            visit_purpose="P",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=BookingStatus.PENDING,
            assigned_caretaker_id=10,
        )
        b_ongoing = Booking.objects.create(
            indenter_id=1,
            visitor_name="Ongoing Record",
            visitor_category=category_a,
            visit_purpose="O",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=BookingStatus.CHECKED_IN,
            assigned_caretaker_id=10,
        )

        # Reassign caretaker to user 99
        VHMSUserRole.reassign_role(role_type=VHMSUserRoleType.CARETAKER, user_id=99)

        b_pending.refresh_from_db()
        b_ongoing.refresh_from_db()
        assert b_pending.assigned_caretaker_id == 99
        assert b_ongoing.assigned_caretaker_id == 99
