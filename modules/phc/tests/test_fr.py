"""FR strategy: verify observable functional requirements and service outputs."""

from decimal import Decimal

import pytest

from modules.phc.domain.reimbursement import (
    ReimbursementValidationError,
    check_employee_eligibility,
    check_submission_window,
)
from modules.phc.domain.state_machine import (
    InvalidClaimTransition,
    advance_claim,
)
from modules.phc.domain.state_machine import (
    ReimbursementState as RS,
)
from modules.phc.models import InventoryItem


def test_employee_and_staff_are_eligible_but_student_is_not():
    check_employee_eligibility("faculty")
    check_employee_eligibility("staff")
    with pytest.raises(ReimbursementValidationError):
        check_employee_eligibility("student")


def test_claim_window_accepts_boundary_and_rejects_expired_or_future_date():
    import datetime as dt

    expense = dt.date(2026, 1, 1)
    check_submission_window(expense, dt.date(2026, 3, 2), 60)
    with pytest.raises(ReimbursementValidationError):
        check_submission_window(expense, dt.date(2026, 3, 3), 60)
    with pytest.raises(ReimbursementValidationError):
        check_submission_window(dt.date(2026, 1, 2), expense, 60)


def test_claim_transitions_require_forward_order_and_correct_actor():
    advance_claim(RS.PENDING_PHC_REVIEW, RS.PENDING_ACCOUNTS, "phc_staff")
    with pytest.raises(InvalidClaimTransition):
        advance_claim(RS.PENDING_PHC_REVIEW, RS.REJECTED, "phc_staff")
    with pytest.raises(InvalidClaimTransition):
        advance_claim(RS.PENDING_ACCOUNTS, RS.PENDING_SANCTION, "phc_staff")


@pytest.mark.django_db
def test_inventory_low_stock_is_strictly_below_threshold():
    item = InventoryItem.objects.create(
        name="Gauze", stock_quantity=Decimal("4"), reorder_threshold=Decimal("5")
    )
    assert item.is_low_stock
    item.stock_quantity = Decimal("5")
    assert not item.is_low_stock


# The cases below exercise separate requirement boundaries.  pytest reports
# each parameter as an individual test case (with its scenario ID).


@pytest.mark.parametrize("kind", ["faculty", "staff"], ids=["faculty", "staff"])
def test_fr_employee_categories_are_eligible(kind):
    check_employee_eligibility(kind)


@pytest.mark.parametrize(
    "kind", ["student", "visitor", "alumni", "", "unknown"],
    ids=["student", "visitor", "alumni", "blank", "unrecognized"],
)
def test_fr_non_employee_categories_are_not_eligible(kind):
    with pytest.raises(ReimbursementValidationError):
        check_employee_eligibility(kind)


@pytest.mark.parametrize(
    ("expense_offset", "submit_offset", "window", "accepted"),
    [
        (0, 0, 90, True),
        (-90, 0, 90, True),
        (-89, 0, 90, True),
        (-91, 0, 90, False),
        (1, 0, 90, False),
        (-365, 0, 0, True),
    ],
    ids=["same-day", "last-allowed-day", "inside-window", "one-day-expired", "future-expense", "unlimited-window"],
)
def test_fr_submission_window_boundaries(expense_offset, submit_offset, window, accepted):
    import datetime as dt

    today = dt.date(2026, 11, 22)
    args = (today + dt.timedelta(days=expense_offset), today + dt.timedelta(days=submit_offset), window)
    if accepted:
        check_submission_window(*args)
    else:
        with pytest.raises(ReimbursementValidationError):
            check_submission_window(*args)


@pytest.mark.parametrize(
    ("source", "target", "role"),
    [
        (RS.PENDING_PHC_REVIEW, RS.PENDING_ACCOUNTS, "phc_staff"),
        (RS.PENDING_ACCOUNTS, RS.PENDING_SANCTION, "accounts_audit"),
        (RS.PENDING_SANCTION, RS.APPROVED_FOR_PAYMENT, "approving_authority"),
        (RS.PENDING_SANCTION, RS.REJECTED, "approving_authority"),
        (RS.APPROVED_FOR_PAYMENT, RS.REIMBURSED, "accounts_audit"),
    ],
    ids=["phc-forward", "accounts-verify", "authority-approve", "authority-reject", "payment"],
)
def test_fr_each_documented_claim_transition_is_allowed(source, target, role):
    advance_claim(source, target, role)


@pytest.mark.parametrize(
    ("source", "target", "role"),
    [
        (RS.PENDING_PHC_REVIEW, RS.PENDING_SANCTION, "phc_staff"),
        (RS.PENDING_PHC_REVIEW, RS.REJECTED, "phc_staff"),
        (RS.PENDING_PHC_REVIEW, RS.PENDING_ACCOUNTS, "accounts_audit"),
        (RS.PENDING_PHC_REVIEW, RS.PENDING_ACCOUNTS, "approving_authority"),
        (RS.PENDING_ACCOUNTS, RS.APPROVED_FOR_PAYMENT, "accounts_audit"),
        (RS.PENDING_ACCOUNTS, RS.REJECTED, "accounts_audit"),
        (RS.PENDING_ACCOUNTS, RS.PENDING_SANCTION, "phc_staff"),
        (RS.PENDING_ACCOUNTS, RS.PENDING_SANCTION, "approving_authority"),
        (RS.PENDING_SANCTION, RS.REIMBURSED, "approving_authority"),
        (RS.PENDING_SANCTION, RS.APPROVED_FOR_PAYMENT, "accounts_audit"),
        (RS.PENDING_SANCTION, RS.REJECTED, "accounts_audit"),
        (RS.APPROVED_FOR_PAYMENT, RS.REJECTED, "approving_authority"),
        (RS.APPROVED_FOR_PAYMENT, RS.REIMBURSED, "phc_staff"),
        (RS.APPROVED_FOR_PAYMENT, RS.REIMBURSED, "approving_authority"),
    ],
    ids=["skip-review", "phc-reject", "wrong-reviewer-accounts", "wrong-reviewer-authority", "skip-sanction", "accounts-reject", "wrong-verify-phc", "wrong-verify-authority", "skip-payment", "wrong-approve-accounts", "wrong-reject-accounts", "reopen-approved", "wrong-payment-phc", "wrong-payment-authority"],
)
def test_fr_claim_transition_rejects_skips_and_wrong_roles(source, target, role):
    with pytest.raises(InvalidClaimTransition):
        advance_claim(source, target, role)


@pytest.mark.parametrize(
    ("quantity", "threshold", "expected"),
    [
        ("0", "0", False), ("0", "1", True), ("1", "1", False),
        ("1.99", "2", True), ("2", "2", False), ("2.01", "2", False),
        ("99.99", "100", True), ("100", "100", False),
    ],
    ids=["zero-equal", "zero-below", "equal-one", "fraction-below", "equal-two", "above-two", "fraction-below-hundred", "equal-hundred"],
)
def test_fr_inventory_threshold_comparisons(quantity, threshold, expected):
    item = InventoryItem(stock_quantity=Decimal(quantity), reorder_threshold=Decimal(threshold))
    assert item.is_low_stock is expected


@pytest.mark.django_db
@pytest.mark.parametrize("day", ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"])
def test_fr_schedule_accepts_each_specified_weekday(day):
    from modules.phc.services.schedules import create_schedule_slot

    slot = create_schedule_slot(
        doctor_name="Dr Scenario", day_of_week=day, start_time="09:00", end_time="10:00",
        actor_user_id=900,
    )
    assert slot.day_of_week == day


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("start", "end"), [("09:00", "09:00"), ("10:00", "09:00"), ("23:59", "00:00")],
    ids=["zero-length", "reversed", "cross-midnight-not-supported"],
)
def test_fr_schedule_rejects_non_positive_time_ranges(start, end):
    from core.api.exceptions import BadRequestError
    from modules.phc.services.schedules import create_schedule_slot

    with pytest.raises(BadRequestError):
        create_schedule_slot(
            doctor_name="Dr Invalid", day_of_week="MON", start_time=start, end_time=end,
            actor_user_id=900,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("status", ["available", "departed"], ids=["available", "departed"])
def test_fr_attendance_accepts_each_specified_status(status):
    from modules.phc.models import DoctorSchedule
    from modules.phc.services.schedules import mark_attendance

    schedule = DoctorSchedule.objects.create(
        doctor_name="Dr Attendance", day_of_week="MON", start_time="09:00", end_time="10:00",
        created_by_user_id=900,
    )
    attendance = mark_attendance(
        schedule=schedule, status=status, date="2026-11-23", actor_user_id=900
    )
    assert attendance.status == status
    assert attendance.marked_by_user_id == 900


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ids", ["", "abc", ",,,"], ids=["all-records-empty-filter", "non-numeric-id", "empty-id-list"]
)
def test_fr_pdf_download_rejects_malformed_or_empty_selection(ids, phc_client):
    client = phc_client(uid=1001, permissions=("phc.record.view_self",))
    response = client.get(f"/api/v1/phc/my/visits/download/?ids={ids}")
    if ids == "":
        assert response.status_code == 404
    else:
        assert response.status_code == 400


@pytest.mark.django_db
def test_fr_schedule_allows_minimum_positive_one_minute_slot():
    from modules.phc.services.schedules import create_schedule_slot

    slot = create_schedule_slot(
        doctor_name="Dr Boundary", day_of_week="SUN", start_time="00:00", end_time="00:01",
        actor_user_id=900,
    )
    assert slot.start_time < slot.end_time
