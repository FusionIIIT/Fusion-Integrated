"""Tests for Employee Leave Management selectors."""

from datetime import date
from decimal import Decimal

import pytest

from modules.leave.models import (
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    SubstituteNomination,
)
from modules.leave.selectors import (
    get_approvals_queue,
    get_pending_substitute_requests,
    get_user_balances,
    get_user_requests,
)


@pytest.fixture
def leave_types(db):
    cl = LeaveType.objects.create(code="CL", name="Casual Leave", allows_half_day=True)
    el = LeaveType.objects.create(code="EL", name="Earned Leave", allows_extension=True)
    rh = LeaveType.objects.create(code="RH", name="Restricted Holiday")
    return {"CL": cl, "EL": el, "RH": rh}


@pytest.mark.django_db
def test_get_user_balances_isolation_and_filters(leave_types):
    # Balances for user 101
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["CL"],
        year=2026,
        credited_days=Decimal("8.0"),
        available_days=Decimal("6.0"),
    )
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["RH"],
        year=2026,
        credited_days=Decimal("2.0"),
        available_days=Decimal("2.0"),
    )
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=leave_types["CL"],
        year=2025,
        credited_days=Decimal("8.0"),
        available_days=Decimal("0.0"),
    )

    # Balance for user 102 (should never be seen by 101)
    LeaveBalance.objects.create(
        user_id=102,
        leave_type=leave_types["CL"],
        year=2026,
        credited_days=Decimal("8.0"),
        available_days=Decimal("8.0"),
    )

    # 1. Fetch user 101 without year filter -> returns 3 balances for 101, ordered by code
    bals_101 = get_user_balances(101)
    assert bals_101.count() == 3
    assert {b.user_id for b in bals_101} == {101}
    assert [b.leave_type.code for b in bals_101] == ["CL", "CL", "RH"]

    # 2. Fetch with year filter
    bals_101_2026 = get_user_balances(101, year=2026)
    assert bals_101_2026.count() == 2
    assert all(b.year == 2026 for b in bals_101_2026)

    # 3. User with no balances -> empty queryset
    assert get_user_balances(999).count() == 0

    # 4. None user_id -> empty queryset
    assert get_user_balances(None).count() == 0


@pytest.mark.django_db
def test_get_user_requests_isolation_and_filters(leave_types):
    # Requests for user 201
    LeaveRequest.objects.create(
        application_number="LEAVE-2026-01",
        user_id=201,
        cadre="faculty",
        leave_type=leave_types["CL"],
        start_date=date(2026, 3, 10),
        end_date=date(2026, 3, 11),
        requested_days=Decimal("2.0"),
        reason="Personal work",
        status="approved",
    )
    req2 = LeaveRequest.objects.create(
        application_number="LEAVE-2026-02",
        user_id=201,
        cadre="faculty",
        leave_type=leave_types["RH"],
        start_date=date(2026, 4, 15),
        end_date=date(2026, 4, 15),
        requested_days=Decimal("1.0"),
        reason="Festival",
        status="draft",
    )

    # Request for user 202 (cross-user isolation)
    LeaveRequest.objects.create(
        application_number="LEAVE-2026-03",
        user_id=202,
        cadre="staff",
        leave_type=leave_types["EL"],
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 5),
        requested_days=Decimal("5.0"),
        reason="Vacation",
        status="approved",
    )

    # 1. User isolation: only 201's requests returned
    qs_201 = get_user_requests(201)
    assert qs_201.count() == 2
    assert {r.application_number for r in qs_201} == {"LEAVE-2026-01", "LEAVE-2026-02"}

    # 2. Filter by status
    qs_draft = get_user_requests(201, status="draft")
    assert qs_draft.count() == 1
    assert qs_draft.first().id == req2.id

    # 3. Filter by date range
    qs_dates = get_user_requests(201, start_date=date(2026, 4, 1), end_date=date(2026, 4, 30))
    assert qs_dates.count() == 1
    assert qs_dates.first().id == req2.id

    # 4. Unknown user and None
    assert get_user_requests(999).count() == 0
    assert get_user_requests(None).count() == 0


@pytest.mark.django_db
def test_get_pending_substitute_requests(leave_types):
    req_awaiting = LeaveRequest.objects.create(
        application_number="LEAVE-SUB-01",
        user_id=301,
        cadre="faculty",
        leave_type=leave_types["CL"],
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
        requested_days=Decimal("2.0"),
        reason="Conference",
        status="awaiting_substitute",
    )
    req_approved = LeaveRequest.objects.create(
        application_number="LEAVE-SUB-02",
        user_id=301,
        cadre="faculty",
        leave_type=leave_types["CL"],
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 2),
        requested_days=Decimal("2.0"),
        reason="Past trip",
        status="approved",
    )

    # Nomination 1: Sub is 401, status pending, req is awaiting_substitute -> ACTIVE
    sub1 = SubstituteNomination.objects.create(
        request=req_awaiting,
        substitute_user_id=401,
        status="pending",
    )
    # Nomination 2: Sub is 401, but already accepted -> NOT PENDING
    SubstituteNomination.objects.create(
        request=req_awaiting,
        substitute_user_id=401,
        status="accepted",
    )
    # Nomination 3: Sub is 401, but request is already approved -> NOT WAITING
    SubstituteNomination.objects.create(
        request=req_approved,
        substitute_user_id=401,
        status="pending",
    )
    # Nomination 4: For another substitute 402 -> ISOLATION
    SubstituteNomination.objects.create(
        request=req_awaiting,
        substitute_user_id=402,
        status="pending",
    )

    # Query for 401: only sub1 should be returned
    pending_401 = get_pending_substitute_requests(401)
    assert pending_401.count() == 1
    assert pending_401.first().id == sub1.id

    # Query for 402: only sub4
    pending_402 = get_pending_substitute_requests(402)
    assert pending_402.count() == 1

    # Query for non-substitute / None: empty
    assert get_pending_substitute_requests(999).count() == 0
    assert get_pending_substitute_requests(None).count() == 0


@pytest.mark.django_db
def test_get_approvals_queue_and_isolation(leave_types):
    # Request awaiting HOD
    req_hod = LeaveRequest.objects.create(
        application_number="LEAVE-APP-01",
        user_id=501,
        cadre="faculty",
        leave_type=leave_types["CL"],
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
        requested_days=Decimal("2.0"),
        reason="Family event",
        status="awaiting_unit_head",
        current_handler_role="HOD",
    )

    # Request awaiting Sanctioning Authority (Dean)
    req_dean = LeaveRequest.objects.create(
        application_number="LEAVE-APP-02",
        user_id=502,
        cadre="faculty",
        leave_type=leave_types["EL"],
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 20),
        requested_days=Decimal("11.0"),
        reason="Research leave",
        status="awaiting_sanction",
        current_handler_role="Dean Academic",
        current_handler_user_id=601,
    )

    # Request already approved (NOT in pending approval states)
    LeaveRequest.objects.create(
        application_number="LEAVE-APP-03",
        user_id=503,
        cadre="staff",
        leave_type=leave_types["CL"],
        start_date=date(2026, 8, 5),
        end_date=date(2026, 8, 6),
        requested_days=Decimal("2.0"),
        reason="Health check",
        status="approved",
        current_handler_role="HOD",
    )

    # 1. HOD role queue: sees req_hod, does not see req_dean or already approved
    hod_queue = get_approvals_queue(approver_role="HOD")
    assert hod_queue.count() == 1
    assert hod_queue.first().id == req_hod.id

    # 2. Dean user 601 queue: sees req_dean
    dean_queue = get_approvals_queue(approver_user_id=601, approver_role="Dean Academic")
    assert dean_queue.count() == 1
    assert dean_queue.first().id == req_dean.id

    # 3. Anti-self-approval rule: if HOD user 501 views HOD queue, their own request (req_hod) is excluded
    hod_self_queue = get_approvals_queue(approver_user_id=501, approver_role="HOD")
    assert hod_self_queue.count() == 0

    # 4. Empty arguments -> returns empty queryset
    assert get_approvals_queue().count() == 0
