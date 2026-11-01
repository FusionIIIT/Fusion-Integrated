"""Validation before progression: one test per condition that must bite."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.leave.domain import categories as cat
from modules.leave.domain import validation
from modules.leave.domain.errors import RuleViolation

MONDAY = date(2026, 3, 2)
FRIDAY = date(2026, 3, 6)


def facts(**kw):
    base = {
        "user_id": 1001,
        "category": cat.CL,
        "start": MONDAY,
        "end": FRIDAY,
        "half": "",
        "is_faculty": False,
        "balance": Decimal(8),
        "committed": Decimal(0),
        "active_intervals": (),
        "closed_dates": frozenset(),
        "restricted_holiday_dates": frozenset(),
        "vacation_periods": (),
        "today": MONDAY,
        "max_backdate_days": 0,
    }
    base.update(kw)
    return validation.RequestFacts(**base)


def test_the_ordinary_case_passes_and_counts_five_days():
    assert validation.days_required(facts()) == Decimal(5)


def test_an_unknown_category_is_refused():
    with pytest.raises(RuleViolation) as exc:
        validation.days_required(facts(category="XX"))
    assert exc.value.code == "unknown_category"


def test_vl_is_refused_for_a_non_faculty_applicant():
    with pytest.raises(RuleViolation) as exc:
        validation.days_required(facts(category=cat.VL, is_faculty=False,
                                       vacation_periods=((MONDAY, FRIDAY),)))
    assert exc.value.code == "category_not_applicable"


def test_a_backdated_request_is_refused():
    with pytest.raises(RuleViolation) as exc:
        validation.days_required(facts(start=MONDAY - timedelta(days=3),
                                       end=FRIDAY))
    assert exc.value.code == "period_in_past"


def test_an_rh_needs_a_published_restricted_holiday():
    with pytest.raises(RuleViolation) as exc:
        validation.days_required(facts(category=cat.RH, balance=Decimal(2)))
    assert exc.value.code == "rh_not_published"
    assert validation.days_required(facts(category=cat.RH, balance=Decimal(2),
                                          restricted_holiday_dates=frozenset(
                                              {MONDAY, FRIDAY}))) > 0


def test_a_vl_needs_a_vacation_period():
    with pytest.raises(RuleViolation) as exc:
        validation.days_required(facts(category=cat.VL, is_faculty=True,
                                       balance=Decimal(60)))
    assert exc.value.code == "vacation_calendar_missing"
    with pytest.raises(RuleViolation) as outside:
        validation.days_required(facts(
            category=cat.VL, is_faculty=True, balance=Decimal(60),
            vacation_periods=((MONDAY + timedelta(days=30),
                               MONDAY + timedelta(days=40)),)))
    assert outside.value.code == "vl_outside_vacation"


def test_a_weekend_only_request_consumes_nothing_and_is_refused():
    saturday = MONDAY + timedelta(days=5)
    sunday = saturday + timedelta(days=1)
    with pytest.raises(RuleViolation) as exc:
        validation.days_required(facts(start=saturday, end=sunday, today=saturday))
    assert exc.value.code == "no_leave_days"


def test_an_overlapping_request_is_refused():
    existing = validation.Interval(start=MONDAY + timedelta(days=2), end=FRIDAY,
                                   category=cat.EL, reference="approved")
    with pytest.raises(RuleViolation) as exc:
        validation.days_required(facts(active_intervals=(existing,)))
    assert exc.value.code == "overlapping_leave"


def test_another_category_on_the_same_dates_still_overlaps():
    existing = validation.Interval(start=MONDAY, end=FRIDAY, category=cat.EL,
                                   reference="pending")
    with pytest.raises(RuleViolation):
        validation.days_required(facts(category=cat.SCL, balance=Decimal(15),
                                       active_intervals=(existing,)))


def test_two_cl_halves_on_the_same_date_are_allowed():
    monday = MONDAY
    existing = validation.Interval(start=monday, end=monday, half="second_half",
                                   category=cat.CL, reference="approved")
    assert validation.days_required(facts(start=monday, end=monday,
                                          half="first_half",
                                          active_intervals=(existing,))) == Decimal("0.5")


def test_the_balance_check_holds_what_is_already_committed():
    with pytest.raises(RuleViolation) as exc:
        validation.days_required(facts(balance=Decimal(5), committed=Decimal(3)))
    assert exc.value.code == "insufficient_balance"


def test_a_half_day_costs_half_a_day():
    monday = MONDAY
    assert validation.days_required(facts(start=monday, end=monday,
                                          half="first_half")) == Decimal("0.5")
