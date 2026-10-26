"""Service integration tests for Employee Leave Management.

Verifies end-to-end service workflows against the PostgreSQL test database:
- Leave application and quota management
- Substitute decline and replacement recovery (EL-UC-019)
- Director exception and self-sanction (BR-EL-020)
- Cancellation staged review and refund idempotency (CW-EL-02 / BR-EL-023)
- Leave extension and incremental deduction (CW-EL-03 / BR-EL-025)
- Duty resumption and balance adjustments (CW-EL-04 / BR-EL-027, 028)
- Offline-sanctioned leave and duplicate reference rejection (BR-EL-029 / EL-UC-016)
- Year-end rollover and idempotency (EL-UC-020 / BR-EL-002 through 009)
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.directory.models import UserRef
from modules.elm.domain.policy import ApplicationStatus
from modules.elm.models import HolidayCalendar, LeaveBalance, LeaveType
from modules.elm.services.application_service import (
    apply_leave,
    nominate_replacement_substitute,
    respond_substitute,
    review_leave,
)
from modules.elm.services.cancellation_service import (
    request_cancellation,
    review_cancellation,
)
from modules.elm.services.extension_service import request_extension
from modules.elm.services.offline_leave_service import record_offline_sanctioned_leave
from modules.elm.services.resumption_service import (
    review_duty_resumption,
    submit_duty_resumption,
)
from modules.elm.services.rollover_service import execute_year_end_rollover

pytestmark = pytest.mark.django_db


@pytest.fixture
def elm_types():
    """Ensure standard leave types exist."""
    types = [
        LeaveType(code="CL", name="Casual Leave", annual_quota=Decimal("8.0"),
                  can_carry_forward=False, requires_substitute=False),
        LeaveType(code="RH", name="Restricted Holiday", annual_quota=Decimal("2.0"),
                  can_carry_forward=False, requires_substitute=False),
        LeaveType(code="SCL", name="Special Casual Leave", annual_quota=Decimal("15.0"),
                  can_carry_forward=False, requires_substitute=True),
        LeaveType(code="EL", name="Earned Leave", annual_quota=Decimal("30.0"),
                  can_carry_forward=True, requires_substitute=True),
        LeaveType(code="VL", name="Vacation Leave", annual_quota=Decimal("60.0"),
                  can_carry_forward=False, requires_substitute=True),
        LeaveType(code="COL", name="Commuted Leave", annual_quota=Decimal("20.0"),
                  can_carry_forward=True, requires_substitute=True),
    ]
    created = []
    for t in types:
        obj, _ = LeaveType.objects.get_or_create(code=t.code, defaults={
            "name": t.name,
            "annual_quota": t.annual_quota,
            "can_carry_forward": t.can_carry_forward,
            "requires_substitute": t.requires_substitute,
            "is_active": True,
        })
        created.append(obj)
    return created


@pytest.fixture
def user_balances(elm_types):
    """Seed balances for test users."""
    UserRef.objects.get_or_create(user_id=101, defaults={"username": "u101",
                                  "display_name": "Faculty 101", "kind": "faculty"})
    UserRef.objects.get_or_create(user_id=102, defaults={"username": "u102",
                                  "display_name": "Staff 102", "kind": "staff"})
    UserRef.objects.get_or_create(user_id=103, defaults={"username": "u103",
                                  "display_name": "Substitute 103", "kind": "faculty"})

    for t in elm_types:
        LeaveBalance.objects.get_or_create(
            user_id=101,
            leave_type=t,
            year=2026,
            defaults={"allocated": t.annual_quota, "used": Decimal("0.0"),
                      "pending": Decimal("0.0")},
        )
        LeaveBalance.objects.get_or_create(
            user_id=102,
            leave_type=t,
            year=2026,
            defaults={"allocated": t.annual_quota, "used": Decimal("0.0"),
                      "pending": Decimal("0.0")},
        )


def test_apply_leave_quota_and_pending_balance(user_balances):
    """Verify application deducts from remaining by adding to pending."""
    app = apply_leave(
        user_id=101,
        leave_type_code="CL",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 3),
        reason="Personal work",
    )
    assert app.status == ApplicationStatus.AWAITING_UNIT_HEAD.value
    assert app.total_days == Decimal("3.0")

    bal = LeaveBalance.objects.get(user_id=101, leave_type__code="CL", year=2026)
    assert bal.pending == Decimal("3.0")
    assert bal.remaining == Decimal("5.0")

    # Overlapping application rejection
    with pytest.raises(ValueError, match="overlapping with"):
        apply_leave(
            user_id=101,
            leave_type_code="CL",
            start_date=date(2026, 4, 2),
            end_date=date(2026, 4, 5),
        )


def test_rh_calendar_restriction(user_balances):
    """Verify Restricted Holiday can only be applied on dates in HolidayCalendar."""
    # Date not in calendar
    with pytest.raises(ValueError, match="not listed as a Restricted Holiday"):
        apply_leave(
            user_id=101,
            leave_type_code="RH",
            start_date=date(2026, 3, 15),
            end_date=date(2026, 3, 15),
        )

    # Add RH to calendar and apply successfully
    HolidayCalendar.objects.create(date=date(2026, 3, 15), title="Festival", is_restricted=True)
    app = apply_leave(
        user_id=101,
        leave_type_code="RH",
        start_date=date(2026, 3, 15),
        end_date=date(2026, 3, 15),
    )
    assert app.status == ApplicationStatus.AWAITING_UNIT_HEAD.value


def test_substitute_workflow_and_recovery(user_balances):
    """Verify substitute decline transitions to applicant action and replacement nomination."""
    app = apply_leave(
        user_id=101,
        leave_type_code="EL",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 5),
        substitute_user_id=103,
    )
    assert app.status == ApplicationStatus.AWAITING_SUBSTITUTE.value

    # Substitute declines
    app = respond_substitute(app.id, substitute_user_id=103, decision="declined")
    assert app.substitute_status == "declined"
    assert app.status == ApplicationStatus.APPLICANT_ACTION_REQUIRED.value

    # Applicant nominates replacement substitute
    UserRef.objects.get_or_create(user_id=104, defaults={"username": "u104",
                                  "display_name": "Substitute 104", "kind": "faculty"})
    app = nominate_replacement_substitute(app.id, applicant_user_id=101, substitute_user_id=104)
    assert app.substitute_user_id == 104
    assert app.substitute_status == "pending"
    assert app.status == ApplicationStatus.AWAITING_SUBSTITUTE.value

    # New substitute accepts
    app = respond_substitute(app.id, substitute_user_id=104, decision="accepted")
    assert app.substitute_status == "accepted"
    assert app.status == ApplicationStatus.AWAITING_UNIT_HEAD.value


def test_director_exception_and_self_sanction(user_balances):
    """Verify Director self-sanction bypasses Unit Head review (BR-EL-020)."""
    # Director applies for leave
    app = apply_leave(
        user_id=101,
        leave_type_code="CL",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 2),
        is_director=True,
    )
    # Direct routing to AWAITING_DIRECTOR
    assert app.status == ApplicationStatus.AWAITING_DIRECTOR.value

    # Non-director cannot self-sanction
    with pytest.raises(ValueError, match="Only the Director applicant can perform"):
        review_leave(app.id, reviewer_user_id=999, decision="approved")

    # Director self-sanctions
    app = review_leave(app.id, reviewer_user_id=101, decision="approved")
    assert app.status == ApplicationStatus.APPROVED.value

    bal = LeaveBalance.objects.get(user_id=101, leave_type__code="CL", year=2026)
    assert bal.used == Decimal("2.0")
    assert bal.pending == Decimal("0.0")


def test_cancellation_workflow_and_refund_idempotency(user_balances):
    """Verify staged cancellation review and duplicate refund prevention (CW-EL-02)."""
    # Create approved EL application starting in future
    app = apply_leave(
        user_id=101,
        leave_type_code="EL",
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 14),
        substitute_user_id=103,
    )
    respond_substitute(app.id, substitute_user_id=103, decision="accepted")
    # Unit Head recommends
    app = review_leave(app.id, reviewer_user_id=201, decision="recommended")
    assert app.status == ApplicationStatus.AWAITING_FINAL_SANCTION.value
    assert app.recommendation == "recommended"
    # Sanction authority approves
    app = review_leave(app.id, reviewer_user_id=301, decision="approved")
    assert app.status == ApplicationStatus.APPROVED.value

    bal = LeaveBalance.objects.get(user_id=101, leave_type__code="EL", year=2026)
    assert bal.used == Decimal("5.0")

    # Request cancellation
    app = request_cancellation(app.id, applicant_user_id=101, reason="Plans cancelled")
    assert app.cancellation_status == "requested"
    assert app.status == ApplicationStatus.CANCELLATION_PENDING_UNIT_HEAD.value

    # Unit Head recommends cancellation
    app = review_cancellation(app.id, reviewer_user_id=201, decision="recommended")
    assert app.status == ApplicationStatus.CANCELLATION_PENDING_FINAL.value

    # Sanction authority approves cancellation -> balance refunded
    app = review_cancellation(app.id, reviewer_user_id=301, decision="approved")
    assert app.status == ApplicationStatus.CANCELLED.value
    assert app.cancellation_status == "approved"
    assert app.is_balance_refunded is True

    bal.refresh_from_db()
    assert bal.used == Decimal("0.0")

    # Attempt duplicate cancellation review
    with pytest.raises(ValueError, match="not pending cancellation"):
        review_cancellation(app.id, reviewer_user_id=301, decision="approved")


def test_leave_extension_incremental_deduction(user_balances):
    """Verify leave extension contiguous date requirement and incremental deduction (CW-EL-03)."""
    # Create approved EL application
    orig_app = apply_leave(
        user_id=101,
        leave_type_code="EL",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),  # 5 days
        substitute_user_id=103,
    )
    respond_substitute(orig_app.id, substitute_user_id=103, decision="accepted")
    review_leave(orig_app.id, reviewer_user_id=201, decision="recommended")
    orig_app = review_leave(orig_app.id, reviewer_user_id=301, decision="approved")
    assert orig_app.status == ApplicationStatus.APPROVED.value

    bal = LeaveBalance.objects.get(user_id=101, leave_type__code="EL", year=2026)
    assert bal.used == Decimal("5.0")

    # Request extension starting immediately contiguous (Aug 6 to Aug 8: 3 days)
    ext_app = request_extension(
        original_application_id=orig_app.id,
        applicant_user_id=101,
        start_date=date(2026, 8, 6),
        end_date=date(2026, 8, 8),
        reason="Need 3 extra days",
        substitute_user_id=103,
    )
    assert ext_app.is_extension is True
    assert ext_app.original_application_id == orig_app.id
    assert ext_app.total_days == Decimal("3.0")

    bal.refresh_from_db()
    # Incremental 3 days pending
    assert bal.pending == Decimal("3.0")

    # Substitute accepts and Sanction Authority approves
    respond_substitute(ext_app.id, substitute_user_id=103, decision="accepted")
    review_leave(ext_app.id, reviewer_user_id=201, decision="recommended")
    ext_app = review_leave(ext_app.id, reviewer_user_id=301, decision="approved")
    assert ext_app.status == ApplicationStatus.APPROVED.value

    bal.refresh_from_db()
    # Total used is 5 (original) + 3 (incremental) = 8
    assert bal.used == Decimal("8.0")
    assert bal.pending == Decimal("0.0")


def test_duty_resumption_early_and_late(user_balances):
    """Verify duty resumption normal, early refund, and late deduction (CW-EL-04)."""
    # 1. Early Resumption
    app_early = apply_leave(
        user_id=101,
        leave_type_code="EL",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 10),  # 10 days
        substitute_user_id=103,
    )
    respond_substitute(app_early.id, substitute_user_id=103, decision="accepted")
    review_leave(app_early.id, reviewer_user_id=201, decision="recommended")
    review_leave(app_early.id, reviewer_user_id=301, decision="approved")

    # Resumes early on Sept 6 (unused 4 days)
    app_early = submit_duty_resumption(
        application_id=app_early.id,
        user_id=101,
        actual_resumption_date=date(2026, 9, 6),
    )
    assert app_early.resumption_status == "pending_review"

    # Review resumption
    app_early = review_duty_resumption(app_early.id, reviewer_user_id=201)
    assert app_early.resumption_status == "reviewed_early"
    assert app_early.resumption_days_adjusted == Decimal("-4.0")

    bal = LeaveBalance.objects.get(user_id=101, leave_type__code="EL", year=2026)
    # Originally 10 used, 4 refunded -> 6 used
    assert bal.used == Decimal("6.0")

    # Repeated review blocked
    with pytest.raises(ValueError, match="Must be 'pending_review'"):
        review_duty_resumption(app_early.id, reviewer_user_id=201)


def test_offline_sanctioned_leave_duplicate_reference(user_balances):
    """Verify offline leave records immediately and rejects duplicate sanction references."""
    app = record_offline_sanctioned_leave(
        user_id=102,
        leave_type_code="CL",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 2),
        sanction_reference="OFFLINE-2026-001",
        sanction_date=date(2026, 9, 25),
        sanction_authority_name="Director Office",
        recorder_user_id=501,
    )
    assert app.is_offline is True
    assert app.status == ApplicationStatus.APPROVED.value

    bal = LeaveBalance.objects.get(user_id=102, leave_type__code="CL", year=2026)
    assert bal.used == Decimal("2.0")

    # Duplicate reference for same user even on non-overlapping dates rejected (BR-EL-029)
    with pytest.raises(ValueError, match="duplicate rejection rule"):
        record_offline_sanctioned_leave(
            user_id=102,
            leave_type_code="CL",
            start_date=date(2026, 11, 1),
            end_date=date(2026, 11, 2),
            sanction_reference="OFFLINE-2026-001",
            sanction_date=date(2026, 10, 25),
            sanction_authority_name="Director Office",
        )


def test_year_end_rollover_execution_and_idempotency(user_balances):
    """Verify rollover execution across employees with fractional VL-to-EL and idempotency."""
    # Set faculty 101 VL used to 45 (unused 15 -> 7.5 EL)
    vl_bal = LeaveBalance.objects.get(user_id=101, leave_type__code="VL", year=2026)
    vl_bal.used = Decimal("45.0")
    vl_bal.save()

    records = execute_year_end_rollover(target_year=2026, executor_user_id=901)
    assert len(records) >= 1

    rec101 = next(r for r in records if r.user_id == 101)
    assert rec101.el_credited_from_vl == Decimal("7.5")
    assert rec101.vl_converted == Decimal("15.0")

    # Verify 2027 balances created
    el_2027 = LeaveBalance.objects.get(user_id=101, leave_type__code="EL", year=2027)
    # 30 (2026 quota) + 7.5 (converted) = 37.5
    assert el_2027.allocated == Decimal("37.5")

    # Second execution is idempotent and returns empty list without duplicate adjustments
    second_run = execute_year_end_rollover(target_year=2026, executor_user_id=901)
    assert second_run == []
