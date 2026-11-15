"""Unit tests for VH module cross-boundary contracts (ops/checks/contracts_are_plural.py compliant)."""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.utils import timezone

from modules.vh import contracts
from modules.vh.models import (
    Bill,
    Booking,
    BookingStatus,
    Room,
    RoomStatus,
    RoomType,
    VHMSUserRole,
    VHMSUserRoleType,
)


@pytest.mark.django_db
class TestGetBookingsForUsersContract:
    def test_empty_sequence(self):
        assert contracts.get_bookings_for_users([]) == []

    def test_non_existent_users(self):
        assert contracts.get_bookings_for_users([9999, 8888]) == []

    @pytest.mark.parametrize("booking_count", [1, 2, 5])
    def test_single_user_multiple_bookings(self, category_a, booking_count):
        today = timezone.localdate()
        for i in range(booking_count):
            Booking.objects.create(
                indenter_id=100,
                visitor_name=f"Guest {i}",
                visitor_category=category_a,
                visit_purpose="Meeting",
                check_in_date=today,
                check_out_date=today + timedelta(days=1),
            )
        res = contracts.get_bookings_for_users([100])
        assert len(res) == booking_count
        assert all(b["indenter_id"] == 100 for b in res)

    def test_multiple_users_bookings(self, category_a):
        today = timezone.localdate()
        b1 = Booking.objects.create(
            indenter_id=10,
            visitor_name="Guest A",
            visitor_category=category_a,
            visit_purpose="Exam",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        b2 = Booking.objects.create(
            indenter_id=20,
            visitor_name="Guest B",
            visitor_category=category_a,
            visit_purpose="Workshop",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
        )
        res = contracts.get_bookings_for_users([10, 20])
        assert len(res) == 2
        uids = {b["indenter_id"] for b in res}
        assert uids == {10, 20}

    def test_contract_keys_structure(self, category_a):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=5,
            visitor_name="Structure Check",
            visitor_category=category_a,
            visit_purpose="Audit",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        item = contracts.get_bookings_for_users([5])[0]
        for key in ["id", "booking_reference", "indenter_id", "visitor_name", "status", "check_in_date", "check_out_date"]:
            assert key in item


@pytest.mark.django_db
class TestGetRoomsByIdsContract:
    def test_empty_sequence(self):
        assert contracts.get_rooms_by_ids([]) == []

    def test_non_existent_rooms(self):
        assert contracts.get_rooms_by_ids([9999, 8888]) == []

    @pytest.mark.parametrize("room_nums", [
        ["101"],
        ["101", "102"],
        ["101", "102", "201"],
    ])
    def test_rooms_retrieval(self, room_nums):
        r_ids = []
        for num in room_nums:
            r, _ = Room.objects.get_or_create(room_number=num, defaults={"status": RoomStatus.AVAILABLE})
            r_ids.append(r.id)
        res = contracts.get_rooms_by_ids(r_ids)
        assert len(res) == len(room_nums)
        returned_nums = {r["room_number"] for r in res}
        assert returned_nums == set(room_nums)

    def test_contract_room_keys(self, sample_room):
        item = contracts.get_rooms_by_ids([sample_room.id])[0]
        for key in ["id", "room_number", "room_type", "occupancy_type", "status"]:
            assert key in item


@pytest.mark.django_db
class TestGetBillsForBookingsContract:
    def test_empty_sequence(self):
        assert contracts.get_bills_for_bookings([]) == []

    def test_non_existent_booking(self):
        assert contracts.get_bills_for_bookings([9999]) == []

    @pytest.mark.parametrize("is_settled,is_finalized", [
        (False, False),
        (True, True),
        (False, True),
    ])
    def test_bill_states(self, category_a, is_settled, is_finalized):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bill Guest",
            visitor_category=category_a,
            visit_purpose="Bill Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        bill = Bill.objects.create(
            booking=b,
            total_amount=Decimal("1500.00"),
            is_settled=is_settled,
            is_finalized=is_finalized,
        )
        res = contracts.get_bills_for_bookings([b.id])
        assert len(res) == 1
        assert res[0]["total_amount"] == "1500.00"
        assert res[0]["is_settled"] is is_settled
        assert res[0]["is_finalized"] is is_finalized


@pytest.mark.django_db
class TestGetActiveOperationalRolesContract:
    def test_empty_sequence(self):
        assert contracts.get_active_operational_roles([]) == []

    def test_inactive_roles_excluded(self):
        VHMSUserRole.objects.create(
            role_type=VHMSUserRoleType.CARETAKER,
            user_id=11,
            is_active=False,
        )
        assert contracts.get_active_operational_roles([VHMSUserRoleType.CARETAKER]) == []

    @pytest.mark.parametrize("requested_roles,expected_count", [
        ([VHMSUserRoleType.CARETAKER], 1),
        ([VHMSUserRoleType.IN_CHARGE], 1),
        ([VHMSUserRoleType.CARETAKER, VHMSUserRoleType.IN_CHARGE], 2),
    ])
    def test_active_roles_retrieval(self, requested_roles, expected_count):
        VHMSUserRole.objects.create(role_type=VHMSUserRoleType.CARETAKER, user_id=101, is_active=True)
        VHMSUserRole.objects.create(role_type=VHMSUserRoleType.IN_CHARGE, user_id=202, is_active=True)
        res = contracts.get_active_operational_roles(requested_roles)
        assert len(res) == expected_count


@pytest.mark.django_db
class TestGetPendingBookingCountsContract:
    def test_empty_sequence(self):
        assert contracts.get_pending_booking_counts_for_users([]) == []

    @pytest.mark.parametrize("pending_c,approved_c", [
        (0, 0),
        (1, 2),
        (3, 1),
        (5, 0),
    ])
    def test_pending_booking_counts(self, category_a, pending_c, approved_c):
        today = timezone.localdate()
        uid = 50 + pending_c * 10 + approved_c
        for i in range(pending_c):
            Booking.objects.create(
                indenter_id=uid,
                visitor_name=f"P-{i}",
                visitor_category=category_a,
                visit_purpose="P",
                check_in_date=today,
                check_out_date=today + timedelta(days=1),
                status=BookingStatus.PENDING,
            )
        for i in range(approved_c):
            Booking.objects.create(
                indenter_id=uid,
                visitor_name=f"A-{i}",
                visitor_category=category_a,
                visit_purpose="A",
                check_in_date=today,
                check_out_date=today + timedelta(days=1),
                status=BookingStatus.APPROVED,
            )
        res = contracts.get_pending_booking_counts_for_users([uid])
        assert len(res) == 1
        assert res[0]["user_id"] == uid
        assert res[0]["pending_count"] == pending_c

