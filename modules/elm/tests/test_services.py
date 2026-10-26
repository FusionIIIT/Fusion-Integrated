"""Integration tests for ELM services against database."""
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.elm import services
from modules.elm.domain.state_machine import LeaveStatus, SubstituteStatus
from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveTransaction,
    VacationCalendar,
)


@pytest.fixture(autouse=True)
def _clean_elm_tables(db):
    """Ensure clean tables before every test."""
    LeaveTransaction.objects.all().delete()
    LeaveApplication.objects.all().delete()
    LeaveBalance.objects.all().delete()
    HolidayCalendar.objects.all().delete()
    VacationCalendar.objects.all().delete()


def test_apply_and_ensure_balances():
    app = services.apply(
        user_id=101, kind="faculty", category="cl",
        start_date=date(2026, 11, 2), end_date=date(2026, 11, 3),  # Mon-Tue (2 days)
        half="full", purpose="Personal work", department="CSE",
    )
    assert app.id is not None
    assert app.status == LeaveStatus.SUBMITTED.value
    assert app.chargeable_days == Decimal("2.0")

    # Balances were auto-created
    cl_bal = LeaveBalance.objects.get(user_id=101, year=2026, category="cl")
    assert cl_bal.entitled == Decimal("8.0")
    assert cl_bal.used == Decimal("0.0")  # not deducted until approved
    assert cl_bal.available == Decimal("8.0")


def test_apply_reversed_dates():
    with pytest.raises(BadRequestError) as exc:
        services.apply(
            user_id=101, kind="faculty", category="cl",
            start_date=date(2026, 11, 5), end_date=date(2026, 11, 2),
            half="full", purpose="test",
        )
    assert exc.value.code == "dates_reversed"


def test_apply_half_day_multi_date():
    with pytest.raises(BadRequestError) as exc:
        services.apply(
            user_id=101, kind="faculty", category="cl",
            start_date=date(2026, 11, 2), end_date=date(2026, 11, 3),
            half="first", purpose="test",
        )
    assert exc.value.code == "half_day_multi_date"


def test_apply_half_day_unsupported_category():
    with pytest.raises(BadRequestError) as exc:
        services.apply(
            user_id=102, kind="staff", category="el",
            start_date=date(2026, 11, 2), end_date=date(2026, 11, 2),
            half="first", purpose="test",
        )
    assert exc.value.code == "half_day_unsupported"


def test_apply_insufficient_balance():
    services.ensure_balances(user_id=101, year=2026, kind="faculty")
    bal = LeaveBalance.objects.get(user_id=101, year=2026, category="cl")
    bal.used = Decimal("7.0")  # only 1.0 day available
    bal.save()

    with pytest.raises(ConflictError) as exc:
        services.apply(
            user_id=101, kind="faculty", category="cl",
            start_date=date(2026, 11, 2), end_date=date(2026, 11, 3),  # 2 days
            half="full", purpose="test",
        )
    assert exc.value.code == "insufficient_balance"


def test_apply_active_overlap():
    services.apply(
        user_id=101, kind="faculty", category="cl",
        start_date=date(2026, 11, 2), end_date=date(2026, 11, 4),
        half="full", purpose="First leave",
    )
    with pytest.raises(ConflictError) as exc:
        services.apply(
            user_id=101, kind="faculty", category="cl",
            start_date=date(2026, 11, 3), end_date=date(2026, 11, 5),
            half="full", purpose="Overlapping leave",
        )
    assert exc.value.code == "leave_overlap"


def test_apply_restricted_holiday():
    rh_date = date(2026, 11, 16)  # Monday (working day)
    # Not published yet
    with pytest.raises(ConflictError) as exc:
        services.apply(
            user_id=101, kind="faculty", category="rh",
            start_date=rh_date, end_date=rh_date,
            half="full", purpose="Festival",
        )
    assert exc.value.code == "rh_not_published"

    # Now publish RH date
    HolidayCalendar.objects.create(
        date=rh_date, kind=HolidayCalendar.RESTRICTED,
        label="Goverdhan Puja", is_published=True,
    )
    app = services.apply(
        user_id=101, kind="faculty", category="rh",
        start_date=rh_date, end_date=rh_date,
        half="full", purpose="Festival",
    )
    assert app.status == LeaveStatus.SUBMITTED.value
    assert app.chargeable_days == Decimal("1.0")


def test_apply_vacation_leave_rules():
    start = date(2026, 12, 15)
    end = date(2026, 12, 20)

    # Non-faculty cannot take VL
    with pytest.raises(ConflictError) as exc:
        services.apply(
            user_id=201, kind="staff", category="vl",
            start_date=start, end_date=end, half="full", purpose="Vacation",
        )
    assert exc.value.code == "vl_faculty_only"

    # Faculty cannot take VL outside published vacation periods
    with pytest.raises(ConflictError) as exc2:
        services.apply(
            user_id=101, kind="faculty", category="vl",
            start_date=start, end_date=end, half="full", purpose="Vacation",
        )
    assert exc2.value.code == "vl_outside_vacation"

    # Set up vacation period in Academic Calendar
    VacationCalendar.objects.create(
        name="Winter Vacation 2026",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 31),
        is_active=True,
    )
    app = services.apply(
        user_id=101, kind="faculty", category="vl",
        start_date=start, end_date=end, half="full", purpose="Vacation",
    )
    assert app.status == LeaveStatus.SUBMITTED.value
    assert app.chargeable_days == Decimal("6.0")  # continuous counting for VL


def test_director_self_sanction():
    app = services.apply(
        user_id=999, kind="faculty", category="cl",
        start_date=date(2026, 11, 2), end_date=date(2026, 11, 3),  # 2 days
        half="full", purpose="Official tour", department="Admin",
        is_director=True,
    )
    assert app.status == LeaveStatus.APPROVED.value
    assert app.decided_by_user_id == 999
    bal = LeaveBalance.objects.get(user_id=999, year=2026, category="cl")
    assert bal.used == Decimal("2.0")
    assert bal.available == Decimal("6.0")


def test_substitute_workflow_and_recovery():
    # Applicant cannot nominate self
    with pytest.raises(ConflictError) as exc:
        services.apply(
            user_id=101, kind="faculty", category="cl",
            start_date=date(2026, 11, 2), end_date=date(2026, 11, 3),
            half="full", purpose="Trip", substitute_user_id=101,
        )
    assert exc.value.code == "self_substitute"

    # Nominate colleague 102
    app = services.apply(
        user_id=101, kind="faculty", category="cl",
        start_date=date(2026, 11, 2), end_date=date(2026, 11, 3),
        half="full", purpose="Trip", substitute_user_id=102,
    )
    assert app.substitute_status == SubstituteStatus.PENDING.value

    # Colleague declines
    services.respond_substitute(user_id=102, application_id=app.id, accept=False)
    app.refresh_from_db()
    assert app.substitute_status == SubstituteStatus.DECLINED.value

    # Deciding while declined is blocked
    with pytest.raises(ConflictError) as exc_decide:
        services.decide(actor_user_id=200, application_id=app.id, approve=True)
    assert exc_decide.value.code == "substitute_declined"

    # Applicant re-nominates substitute 103 (EL-UC-019)
    services.renominate_substitute(user_id=101, application_id=app.id, substitute_user_id=103)
    app.refresh_from_db()
    assert app.substitute_user_id == 103
    assert app.substitute_status == SubstituteStatus.PENDING.value

    # Substitute 103 accepts
    services.respond_substitute(user_id=103, application_id=app.id, accept=True)
    app.refresh_from_db()
    assert app.substitute_status == SubstituteStatus.ACCEPTED.value

    # Now decision can proceed
    services.decide(actor_user_id=200, application_id=app.id, approve=True)
    app.refresh_from_db()
    assert app.status == LeaveStatus.APPROVED.value


def test_higher_sanction_recommendation_flow():
    # Staff EL requires higher sanction (BR-EL-017, BR-EL-018)
    app = services.apply(
        user_id=102, kind="staff", category="el",
        start_date=date(2026, 11, 2), end_date=date(2026, 11, 5),  # 4 days
        half="full", purpose="Family function", department="Accounts",
    )
    assert app.status == LeaveStatus.SUBMITTED.value

    # Direct decide is blocked before recommendation
    with pytest.raises(ConflictError) as exc_rec:
        services.decide(actor_user_id=300, application_id=app.id, approve=True)
    assert exc_rec.value.code == "recommendation_required"

    # Self-review is blocked
    with pytest.raises(ConflictError) as exc_self:
        services.recommend(actor_user_id=102, application_id=app.id, recommended=True)
    assert exc_self.value.code == "self_review"

    # Unit Head records recommendation
    services.recommend(
        actor_user_id=301, application_id=app.id, recommended=True,
        note="Work is covered; recommended.",
    )
    app.refresh_from_db()
    assert app.status == LeaveStatus.FORWARDED.value
    assert app.recommendation == "recommended"

    # Sanctioning authority approves
    services.decide(actor_user_id=400, application_id=app.id, approve=True, note="Sanctioned.")
    app.refresh_from_db()
    assert app.status == LeaveStatus.APPROVED.value
    bal = LeaveBalance.objects.get(user_id=102, year=2026, category="el")
    assert bal.used == Decimal("4.0")


def test_immediate_withdrawal():
    app = services.apply(
        user_id=101, kind="faculty", category="cl",
        start_date=date(2026, 11, 2), end_date=date(2026, 11, 3),
        half="full", purpose="Trip",
    )
    services.withdraw(user_id=101, application_id=app.id)
    app.refresh_from_db()
    assert app.status == LeaveStatus.WITHDRAWN.value

    # Cannot withdraw twice or after decision
    with pytest.raises(ConflictError):
        services.withdraw(user_id=101, application_id=app.id)


def test_cancellation_workflow():
    # Future leave
    app = services.apply(
        user_id=101, kind="faculty", category="cl",
        start_date=date(2026, 12, 1), end_date=date(2026, 12, 2),  # 2 days
        half="full", purpose="Trip",
    )
    services.decide(actor_user_id=200, application_id=app.id, approve=True)
    bal = LeaveBalance.objects.get(user_id=101, year=2026, category="cl")
    assert bal.used == Decimal("2.0")

    # Request cancellation
    services.request_cancellation(user_id=101, application_id=app.id)
    app.refresh_from_db()
    assert app.status == LeaveStatus.CANCELLATION_REQUESTED.value
    # Balance is NOT refunded yet during review
    bal.refresh_from_db()
    assert bal.used == Decimal("2.0")

    # Authority rejects cancellation first -> stays approved
    services.decide_cancellation(actor_user_id=200, application_id=app.id, approve=False)
    app.refresh_from_db()
    assert app.status == LeaveStatus.APPROVED.value
    bal.refresh_from_db()
    assert bal.used == Decimal("2.0")

    # Request cancellation again and approve it
    services.request_cancellation(user_id=101, application_id=app.id)
    services.decide_cancellation(actor_user_id=200, application_id=app.id, approve=True)
    app.refresh_from_db()
    assert app.status == LeaveStatus.CANCELLED.value
    bal.refresh_from_db()
    assert bal.used == Decimal("0.0")  # refunded!


def test_resumption_workflow():
    # Staff EL for 5 days: Mon Nov 2 to Fri Nov 6
    app = services.apply(
        user_id=102, kind="staff", category="el",
        start_date=date(2026, 11, 2), end_date=date(2026, 11, 6),  # 5 days
        half="full", purpose="Personal",
    )
    services.recommend(actor_user_id=301, application_id=app.id, recommended=True)
    services.decide(actor_user_id=400, application_id=app.id, approve=True)
    bal = LeaveBalance.objects.get(user_id=102, year=2026, category="el")
    assert bal.used == Decimal("5.0")

    # Early resumption: employee returns on Thursday Nov 5 instead of Sat Nov 7
    # So leave was only Mon-Wed (3 days)
    services.submit_resumption(
        user_id=102, application_id=app.id,
        actual_resumption_date=date(2026, 11, 5), note="Returned early.",
    )
    app.refresh_from_db()
    assert app.status == LeaveStatus.RESUMPTION_REQUESTED.value

    # Review resumption
    services.review_resumption(actor_user_id=400, application_id=app.id, note="Verified.")
    app.refresh_from_db()
    assert app.status == LeaveStatus.RESUMED.value
    assert app.chargeable_days == Decimal("3.0")
    bal.refresh_from_db()
    assert bal.used == Decimal("3.0")  # 2 days refunded!


def test_offline_sanctioned_leave():
    app = services.record_offline_leave(
        admin_user_id=500, user_id=101, kind="faculty", category="cl",
        start_date=date(2026, 10, 1), end_date=date(2026, 10, 2),
        half="full", purpose="Medical emergency offline",
        sanction_reference="ESTT/LEAVE/2026/042", department="CSE",
    )
    assert app.status == LeaveStatus.APPROVED.value
    assert app.is_offline_record is True
    assert app.offline_sanction_reference == "ESTT/LEAVE/2026/042"
    bal = LeaveBalance.objects.get(user_id=101, year=2026, category="cl")
    assert bal.used == Decimal("2.0")


def test_year_end_processing():
    # User 101 (Faculty): has 4 CL left, 40 VL left
    services.ensure_balances(user_id=101, year=2026, kind="faculty")
    vl_bal = LeaveBalance.objects.get(user_id=101, year=2026, category="vl")
    vl_bal.used = Decimal("20.0")  # 40 VL remaining
    vl_bal.save()

    # User 102 (Staff): has 10 EL left, 15 COL left
    services.ensure_balances(user_id=102, year=2026, kind="staff")
    el_bal = LeaveBalance.objects.get(user_id=102, year=2026, category="el")
    el_bal.used = Decimal("20.0")  # 10 EL remaining
    el_bal.save()

    col_bal = LeaveBalance.objects.get(user_id=102, year=2026, category="col")
    col_bal.used = Decimal("5.0")  # 15 COL remaining
    col_bal.save()

    res = services.process_year_end(year=2026)
    assert res["users_processed"] >= 2

    # Year 2027 checks:
    # Faculty 101: 40 VL converted to 20 EL in 2027!
    next_el_101 = LeaveBalance.objects.get(user_id=101, year=2027, category="el")
    assert next_el_101.entitled == Decimal("20.0")

    # Staff 102: 10 EL carried forward to 2027! 15 COL carried forward to 2027!
    next_el_102 = LeaveBalance.objects.get(user_id=102, year=2027, category="el")
    assert next_el_102.entitled == Decimal("10.0")
    next_col_102 = LeaveBalance.objects.get(user_id=102, year=2027, category="col")
    assert next_col_102.entitled == Decimal("15.0")
