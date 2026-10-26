"""Tests for Employee Leave Management models."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError

from modules.leave.models import (
    CadreLeaveQuota,
    Holiday,
    HolidayCalendar,
    LeaveBalance,
    LeaveLedgerEntry,
    LeaveRequest,
    LeaveType,
    ResumptionRecord,
    SubstituteNomination,
    WorkflowTransition,
)


@pytest.mark.django_db
def test_leave_type_and_cadre_quota_creation():
    cl = LeaveType.objects.create(
        code="CL",
        name="Casual Leave",
        allows_half_day=True,
        lapses_at_year_end=True,
    )
    quota = CadreLeaveQuota.objects.create(
        cadre="faculty",
        leave_type=cl,
        annual_quota=Decimal("8.0"),
    )
    assert cl.code == "CL"
    assert quota.annual_quota == Decimal("8.0")
    assert str(quota) == "faculty: CL = 8.0"


@pytest.mark.django_db
def test_holiday_calendar_and_holiday():
    cal = HolidayCalendar.objects.create(year=2026, title="Holidays 2026", is_published=True)
    h1 = Holiday.objects.create(
        calendar=cal,
        date=date(2026, 1, 26),
        name="Republic Day",
        is_restricted=False,
    )
    rh = Holiday.objects.create(
        calendar=cal,
        date=date(2026, 3, 20),
        name="Nowruz",
        is_restricted=True,
    )
    assert cal.holidays.count() == 2
    assert not h1.is_restricted
    assert rh.is_restricted


@pytest.mark.django_db
def test_leave_balance_and_ledger_entry():
    el = LeaveType.objects.create(code="EL", name="Earned Leave", carries_forward=True)
    bal = LeaveBalance.objects.create(
        user_id=101,
        leave_type=el,
        year=2026,
        credited_days=Decimal("30.0"),
        available_days=Decimal("30.0"),
    )
    assert bal.available_days == Decimal("30.0")

    # Record debit ledger entry
    entry = LeaveLedgerEntry.objects.create(
        balance=bal,
        entry_type="debit",
        amount=Decimal("5.0"),
        balance_after=Decimal("25.0"),
        reference_type="leave_request",
        reference_id=1,
        performed_by_user_id=101,
    )
    assert entry.balance.available_days == Decimal("30.0")
    assert entry.balance_after == Decimal("25.0")
    assert bal.ledger_entries.count() == 1


@pytest.mark.django_db
def test_leave_balance_unique_constraint():
    cl = LeaveType.objects.create(code="CL_UNIQ", name="Casual Leave")
    LeaveBalance.objects.create(
        user_id=101,
        leave_type=cl,
        year=2026,
        credited_days=Decimal("8.0"),
        available_days=Decimal("8.0"),
    )
    with pytest.raises(IntegrityError):
        LeaveBalance.objects.create(
            user_id=101,
            leave_type=cl,
            year=2026,
            credited_days=Decimal("8.0"),
            available_days=Decimal("8.0"),
        )


@pytest.mark.django_db
def test_leave_balance_negative_check_constraint():
    el = LeaveType.objects.create(code="EL_CHECK", name="Earned Leave")
    with pytest.raises(IntegrityError):
        LeaveBalance.objects.create(
            user_id=102,
            leave_type=el,
            year=2026,
            credited_days=Decimal("10.0"),
            available_days=Decimal("-1.0"),  # Violates check constraint
        )


@pytest.mark.django_db
def test_leave_request_lifecycle_models():
    cl = LeaveType.objects.create(code="CL", name="Casual Leave", allows_half_day=True)
    req = LeaveRequest.objects.create(
        application_number="LEAVE-2026-0001",
        user_id=1001,
        cadre="faculty",
        leave_type=cl,
        start_date=date(2026, 10, 15),
        end_date=date(2026, 10, 15),
        is_half_day=True,
        half_day_period="first_half",
        requested_days=Decimal("0.5"),
        reason="Family personal engagement",
        status="awaiting_substitute",
    )
    assert req.application_number == "LEAVE-2026-0001"
    assert req.is_half_day
    assert req.requested_days == Decimal("0.5")

    # Substitute nomination
    sub = SubstituteNomination.objects.create(
        request=req,
        substitute_user_id=1002,
        status="pending",
    )
    assert req.substitutes.count() == 1
    assert sub.status == "pending"

    # Workflow transition
    tr = WorkflowTransition.objects.create(
        request=req,
        from_state="draft",
        to_state="awaiting_substitute",
        action="submit",
        actor_user_id=1001,
        actor_role="faculty",
        remarks="Submitted with substitute nomination",
    )
    assert req.transitions.count() == 1
    assert tr.to_state == "awaiting_substitute"


@pytest.mark.django_db
def test_resumption_record_relationship():
    el = LeaveType.objects.create(code="EL", name="Earned Leave", allows_extension=True)
    req = LeaveRequest.objects.create(
        application_number="LEAVE-2026-0002",
        user_id=1005,
        cadre="staff",
        leave_type=el,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 10),
        requested_days=Decimal("10.0"),
        reason="Annual rest",
        status="approved",
    )
    res = ResumptionRecord.objects.create(
        request=req,
        expected_date=date(2026, 10, 11),
        actual_resumption_date=date(2026, 10, 13),
        nature="late",
        difference_days=Decimal("2.0"),
        remarks="Train delayed",
    )
    assert req.resumption == res
    assert res.nature == "late"
    assert res.difference_days == Decimal("2.0")


@pytest.mark.django_db
def test_approved_model_corrections_fields():
    # 1. requires_medical_certificate on LeaveType (BR-EL-009)
    col = LeaveType.objects.create(
        code="COL",
        name="Commuted Leave",
        requires_medical_certificate=True,
    )
    assert col.requires_medical_certificate is True

    # 2. station_destination, cancellation, extension, recommendation, and department
    req = LeaveRequest.objects.create(
        application_number="LEAVE-2026-CORR-01",
        user_id=1010,
        cadre="faculty",
        department="Computer Science & Engineering",
        leave_type=col,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 5),
        requested_days=Decimal("5.0"),
        reason="Medical treatment",
        is_station_leave=True,
        station_destination="New Delhi",
        unit_head_recommendation="recommended",
        unit_head_remarks="Covered by substitute, recommended",
        cancellation_reason="Treatment rescheduled",
        extension_end_date=date(2026, 11, 8),
        extension_days=Decimal("3.0"),
        extension_reason="Doctor advised extended rest",
    )
    assert req.department == "Computer Science & Engineering"
    assert req.station_destination == "New Delhi"
    assert req.unit_head_recommendation == "recommended"
    assert req.extension_days == Decimal("3.0")
    assert req.cancellation_reason == "Treatment rescheduled"


@pytest.mark.django_db
def test_department_scoping_and_hod_isolation():
    # Two requests from different departments awaiting HOD review
    cl = LeaveType.objects.create(code="CL_DEPT", name="Casual Leave")
    req_cse = LeaveRequest.objects.create(
        application_number="LEAVE-CSE-01",
        user_id=2001,
        cadre="faculty",
        department="Computer Science & Engineering",
        leave_type=cl,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        requested_days=Decimal("2.0"),
        reason="Personal",
        status="awaiting_unit_head",
        current_handler_role="HOD",
    )
    req_me = LeaveRequest.objects.create(
        application_number="LEAVE-ME-01",
        user_id=2002,
        cadre="faculty",
        department="Mechanical Engineering",
        leave_type=cl,
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 11),
        requested_days=Decimal("2.0"),
        reason="Personal",
        status="awaiting_unit_head",
        current_handler_role="HOD",
    )

    # When querying for HOD CSE (department="Computer Science & Engineering")
    cse_requests = LeaveRequest.objects.filter(
        status="awaiting_unit_head",
        current_handler_role="HOD",
        department="Computer Science & Engineering",
    )
    assert cse_requests.count() == 1
    assert cse_requests.first().id == req_cse.id

    # HOD ME cannot see CSE requests
    me_requests = LeaveRequest.objects.filter(
        status="awaiting_unit_head",
        current_handler_role="HOD",
        department="Mechanical Engineering",
    )
    assert me_requests.count() == 1
    assert me_requests.first().id == req_me.id
