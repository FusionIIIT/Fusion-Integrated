"""Unit and domain service tests for Employee Leave Management (ELM)."""
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from modules.leave.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveType,
)
from modules.leave.services import (
    calculate_leave_days,
    get_or_create_balance,
    nominate_replacement_substitute,
    request_approved_leave_cancellation,
    respond_to_substitute_request,
    review_by_sanctioning_authority,
    review_by_unit_head,
    review_cancellation_request,
    review_resumption_submission,
    submit_leave_application,
    submit_resumption_of_duty,
    validate_application_rules,
    withdraw_leave_application,
)


@pytest.fixture
def leave_types(db):
    cl = LeaveType.objects.create(
        code="CL",
        name="Casual Leave",
        max_days_per_year=Decimal("8.0"),
        requires_substitute=True,
        is_continuous_counting=False,
    )
    rh = LeaveType.objects.create(
        code="RH",
        name="Restricted Holiday",
        max_days_per_year=Decimal("2.0"),
        requires_substitute=True,
        is_continuous_counting=False,
    )
    el = LeaveType.objects.create(
        code="EL",
        name="Earned Leave",
        max_days_per_year=Decimal("30.0"),
        requires_substitute=True,
        is_continuous_counting=True,
        can_carry_forward=True,
    )
    return {"CL": cl, "RH": rh, "EL": el}


@pytest.mark.django_db
def test_calculate_leave_days_continuous_vs_working(leave_types):
    el = leave_types["EL"]
    cl = leave_types["CL"]
    start = date(2026, 11, 2)
    end = date(2026, 11, 8)
    assert calculate_leave_days(el, start, end) == Decimal("7.0")
    assert calculate_leave_days(cl, start, end) == Decimal("5.0")
    assert calculate_leave_days(cl, start, start, is_half_day=True) == Decimal("0.5")


@pytest.mark.django_db
def test_validate_application_rules_insufficient_balance(leave_types):
    cl = leave_types["CL"]
    balance = get_or_create_balance("emp1", cl, 2026)
    balance.consumed = Decimal("8.0")
    balance.save()

    with pytest.raises(ValidationError) as exc:
        validate_application_rules(
            applicant_id="emp1",
            leave_type=cl,
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 3),
        )
    assert "Insufficient leave balance" in str(exc.value)


@pytest.mark.django_db
def test_validate_application_rules_overlap_detected(leave_types):
    cl = leave_types["CL"]
    app = submit_leave_application(
        applicant_id="emp1",
        leave_type=cl,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        reason="Initial application",
    )
    assert app.id is not None

    with pytest.raises(ValidationError) as exc:
        validate_application_rules(
            applicant_id="emp1",
            leave_type=cl,
            start_date=date(2026, 11, 3),
            end_date=date(2026, 11, 5),
        )
    assert "Overlaps with active leave application" in str(exc.value)


@pytest.mark.django_db
def test_substitute_workflow_and_replacement(leave_types):
    cl = leave_types["CL"]
    app = submit_leave_application(
        applicant_id="emp1",
        leave_type=cl,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Personal work",
        substitute_id="sub1",
    )
    assert app.status == LeaveApplication.STATUS_AWAITING_SUBSTITUTE
    assert app.substitute_status == LeaveApplication.SUB_STATUS_PENDING

    app = respond_to_substitute_request(
        application=app,
        substitute_id="sub1",
        action="decline",
        remarks="Busy with lectures",
    )
    assert app.status == LeaveApplication.STATUS_SUBSTITUTE_DECLINED
    assert app.substitute_status == LeaveApplication.SUB_STATUS_DECLINED

    app = nominate_replacement_substitute(
        application=app,
        applicant_id="emp1",
        new_substitute_id="sub2",
        remarks="Nominated replacement",
    )
    assert app.status == LeaveApplication.STATUS_AWAITING_SUBSTITUTE
    assert app.substitute_id == "sub2"

    app = respond_to_substitute_request(
        application=app,
        substitute_id="sub2",
        action="accept",
        remarks="Consented",
    )
    assert app.status == LeaveApplication.STATUS_AWAITING_UNIT_HEAD
    assert app.substitute_status == LeaveApplication.SUB_STATUS_ACCEPTED


@pytest.mark.django_db
def test_unit_head_approval_and_balance_deduction(leave_types):
    cl = leave_types["CL"]
    app = submit_leave_application(
        applicant_id="emp1",
        leave_type=cl,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Family function",
    )
    assert app.status == LeaveApplication.STATUS_AWAITING_UNIT_HEAD

    app = review_by_unit_head(
        application=app,
        unit_head_id="hod1",
        action="approve",
        remarks="Sanctioned",
    )
    assert app.status == LeaveApplication.STATUS_APPROVED
    bal = LeaveBalance.objects.get(employee_id="emp1", leave_type=cl, year=2026)
    assert bal.consumed == Decimal("2.0")
    assert bal.available == Decimal("6.0")


@pytest.mark.django_db
def test_higher_sanction_recommendation_and_approval(leave_types):
    el = leave_types["EL"]
    app = submit_leave_application(
        applicant_id="emp1",
        leave_type=el,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 6),
        reason="Conference travel",
    )
    assert app.status == LeaveApplication.STATUS_AWAITING_UNIT_HEAD

    app = review_by_unit_head(
        application=app,
        unit_head_id="hod1",
        action="recommend",
        recommendation="RECOMMENDED",
        remarks="Good to travel",
    )
    assert app.status == LeaveApplication.STATUS_AWAITING_SANCTION
    assert app.unit_head_recommendation == "RECOMMENDED"

    app = review_by_sanctioning_authority(
        application=app,
        authority_id="dean1",
        action="approve",
        remarks="Approved by Dean",
    )
    assert app.status == LeaveApplication.STATUS_APPROVED
    bal = LeaveBalance.objects.get(employee_id="emp1", leave_type=el, year=2026)
    assert bal.consumed == Decimal("5.0")


@pytest.mark.django_db
def test_withdraw_pending_application(leave_types):
    cl = leave_types["CL"]
    app = submit_leave_application(
        applicant_id="emp1",
        leave_type=cl,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Trip",
    )
    app = withdraw_leave_application(app, applicant_id="emp1", remarks="Cancelled trip")
    assert app.status == LeaveApplication.STATUS_WITHDRAWN


@pytest.mark.django_db
def test_cancellation_and_balance_restoration(leave_types):
    cl = leave_types["CL"]
    app = submit_leave_application(
        applicant_id="emp1",
        leave_type=cl,
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        reason="December leave",
    )
    app = review_by_unit_head(app, "hod1", "approve")
    bal = LeaveBalance.objects.get(employee_id="emp1", leave_type=cl, year=2026)
    assert bal.consumed == Decimal("2.0")

    app = request_approved_leave_cancellation(app, "emp1", "Event postponed")
    assert app.status == LeaveApplication.STATUS_CANCELLATION_REQUESTED

    app = review_cancellation_request(app, "hod1", "approve")
    assert app.status == LeaveApplication.STATUS_CANCELLED
    bal.refresh_from_db()
    assert bal.consumed == Decimal("0.0")


@pytest.mark.django_db
def test_resumption_early_return_reconciliation(leave_types):
    el = leave_types["EL"]
    app = submit_leave_application(
        applicant_id="emp1",
        leave_type=el,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 6),
        reason="Personal",
    )
    app.status = LeaveApplication.STATUS_APPROVED
    app.leave_days = Decimal("5.0")
    app.save()
    bal = get_or_create_balance("emp1", el, 2026)
    bal.consumed = Decimal("5.0")
    bal.save()

    app = submit_resumption_of_duty(app, "emp1", date(2026, 11, 5), "Returned 2 days early")
    assert app.resumption_status == LeaveApplication.RESUMPTION_PENDING

    app = review_resumption_submission(app, "dean1", "approve")
    assert app.resumption_status == LeaveApplication.RESUMPTION_APPROVED
    assert app.leave_days == Decimal("3.0")
    bal.refresh_from_db()
    assert bal.consumed == Decimal("3.0")
