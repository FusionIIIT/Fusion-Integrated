"""Domain tests: pure Python, no database, milliseconds.

Every rule here is a business rule from `04_MMS_Business_Rule_Specifications`;
the BR id sits in each test name so a failure says which rule broke.
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from modules.mms.domain import state_machine as sm

D = Decimal
d = date


# ---- BR-MMS-021: minimum rebate duration -------------------------------------
@pytest.mark.parametrize(("start", "end", "days"), [
    (d(2026, 5, 10), d(2026, 5, 12), 3),     # exactly the minimum, inclusive count
    (d(2026, 5, 10), d(2026, 5, 20), 11),
    (d(2026, 2, 27), d(2026, 3, 1), 3),      # 2026 is not a leap year
    (d(2028, 2, 28), d(2028, 3, 1), 3),      # 2028 is: 28, 29, 1
    (d(2026, 12, 30), d(2027, 1, 2), 4),     # year boundary
])
def test_br021_accepts_three_or_more_inclusive_days(start, end, days):
    assert sm.validate_rebate_duration(start, end) == days


@pytest.mark.parametrize(("start", "end"), [
    (d(2026, 5, 10), d(2026, 5, 10)),        # one day
    (d(2026, 5, 10), d(2026, 5, 11)),        # two days: the off-by-one that matters
])
def test_br021_rejects_fewer_than_three_days(start, end):
    with pytest.raises(sm.RuleViolation) as e:
        sm.validate_rebate_duration(start, end)
    assert e.value.rule_id == "BR-MMS-021"


def test_br021_rejects_end_before_start():
    with pytest.raises(sm.RuleViolation) as e:
        sm.validate_rebate_duration(d(2026, 5, 10), d(2026, 5, 9))
    assert e.value.rule_id == "BR-MMS-021"


@given(start=st.dates(min_value=d(2020, 1, 1), max_value=d(2040, 1, 1)),
       extra=st.integers(min_value=2, max_value=400))
def test_br021_property_duration_is_inclusive_day_count(start, extra):
    assert sm.validate_rebate_duration(start, start + timedelta(days=extra)) == extra + 1


@given(start=st.dates(min_value=d(2020, 1, 1), max_value=d(2040, 1, 1)),
       extra=st.integers(min_value=0, max_value=1))
def test_br021_property_one_or_two_days_always_rejected(start, extra):
    with pytest.raises(sm.RuleViolation):
        sm.validate_rebate_duration(start, start + timedelta(days=extra))


# ---- BR-MMS-022 / BR-MMS-028: one-calendar-day lead time ----------------------
LEAD_CASES = [(-3, False), (-1, False), (0, False), (1, True), (2, True), (30, True)]


@pytest.mark.parametrize(("lead_days", "ok"), LEAD_CASES)
@pytest.mark.parametrize(("check", "rule"), [
    (sm.validate_rebate_lead_time, "BR-MMS-022"),
    (sm.validate_special_food_lead_time, "BR-MMS-028"),
])
def test_lead_time_needs_at_least_one_calendar_day(check, rule, lead_days, ok):
    submitted = d(2026, 5, 13)
    target = submitted + timedelta(days=lead_days)
    if ok:
        assert check(target, submitted) is None
    else:
        with pytest.raises(sm.RuleViolation) as e:
            check(target, submitted)
        assert e.value.rule_id == rule


def test_lead_time_is_calendar_days_not_hours():
    """Submitting at 23:59 for a date that starts in two minutes still has a one-day
    lead by calendar arithmetic — the rule is on dates, the domain never sees a time."""
    assert sm.validate_special_food_lead_time(d(2026, 5, 14), d(2026, 5, 13)) is None


# ---- BR-MMS-013: deregistration takes effect the next calendar day ------------
@pytest.mark.parametrize(("decision", "effective"), [
    (d(2026, 5, 13), d(2026, 5, 14)),
    (d(2026, 5, 31), d(2026, 6, 1)),         # month end
    (d(2026, 12, 31), d(2027, 1, 1)),        # year end
    (d(2028, 2, 28), d(2028, 2, 29)),        # leap day exists
    (d(2026, 2, 28), d(2026, 3, 1)),         # ... and does not
])
def test_br013_effective_date_is_next_calendar_day(decision, effective):
    assert sm.calculate_deregistration_effective_date(decision) == effective


# ---- BR-MMS-017: bill = base + special food - rebate --------------------------
@pytest.mark.parametrize(("base", "special", "rebate", "total"), [
    ("3000.00", "0.00", "0.00", "3000.00"),
    ("3000.00", "150.00", "0.00", "3150.00"),
    ("3000.00", "0.00", "300.00", "2700.00"),
    ("3000.00", "150.00", "300.00", "2850.00"),
    ("3000.00", "0.00", "3000.00", "0.00"),
    ("3000.00", "0.00", "9999.00", "0.00"),     # a bill is never negative
    ("0.00", "0.00", "0.00", "0.00"),
])
def test_br017_bill_total(base, special, rebate, total):
    assert sm.calculate_bill_total(D(base), D(special), D(rebate)) == D(total)


def test_br017_bill_total_is_exact_decimal_arithmetic():
    assert sm.calculate_bill_total(D("0.10"), D("0.20"), D("0.00")) == D("0.30")


@given(base=st.decimals(0, 10_000, places=2), special=st.decimals(0, 5_000, places=2),
       rebate=st.decimals(0, 20_000, places=2))
def test_br017_property_total_never_negative_and_never_exceeds_charges(base, special, rebate):
    total = sm.calculate_bill_total(base, special, rebate)
    assert D("0.00") <= total <= base + special


# ---- BR-MMS-031: special-food lifecycle ---------------------------------------
SF = [sm.SPECIAL_FOOD_REQUESTED, sm.SPECIAL_FOOD_APPROVED, sm.SPECIAL_FOOD_REJECTED,
      sm.SPECIAL_FOOD_SERVED, sm.SPECIAL_FOOD_CANCELLED]
SF_LEGAL = {
    (sm.SPECIAL_FOOD_REQUESTED, sm.SPECIAL_FOOD_APPROVED),
    (sm.SPECIAL_FOOD_REQUESTED, sm.SPECIAL_FOOD_REJECTED),
    (sm.SPECIAL_FOOD_APPROVED, sm.SPECIAL_FOOD_SERVED),
    (sm.SPECIAL_FOOD_APPROVED, sm.SPECIAL_FOOD_CANCELLED),
}


@pytest.mark.parametrize("frm", SF)
@pytest.mark.parametrize("to", SF)
def test_br031_full_special_food_transition_matrix(frm, to):
    """Exhaustive 5x5: legal exactly when in the spec's table (BW-MMS-11..15)."""
    if (frm, to) in SF_LEGAL:
        assert sm.validate_special_food_transition(frm, to) == to
    else:
        with pytest.raises(sm.InvalidTransition) as e:
            sm.validate_special_food_transition(frm, to)
        assert (e.value.from_state, e.value.to_state) == (frm, to)


@pytest.mark.parametrize("terminal", [sm.SPECIAL_FOOD_REJECTED, sm.SPECIAL_FOOD_SERVED,
                                      sm.SPECIAL_FOOD_CANCELLED])
def test_br031_terminal_states_have_no_exits(terminal):
    assert not [t for (f, t) in SF_LEGAL if f == terminal]


def test_br031_served_and_cancelled_only_follow_approved():
    for frm, to in SF_LEGAL:
        if to in {sm.SPECIAL_FOOD_SERVED, sm.SPECIAL_FOOD_CANCELLED}:
            assert frm == sm.SPECIAL_FOOD_APPROVED


@given(st.text(max_size=12), st.text(max_size=12))
def test_br031_unknown_states_are_never_legal(frm, to):
    if (frm, to) not in SF_LEGAL:
        with pytest.raises(sm.InvalidTransition):
            sm.validate_special_food_transition(frm, to)


# ---- constants the rest of MMS leans on ---------------------------------------
def test_menu_structure_is_seven_days_by_three_meals():
    """BR-MMS-014."""
    assert len(sm.DAYS_OF_WEEK) == 7
    assert {"breakfast", "lunch", "dinner"} == sm.MEAL_TYPES


def test_only_caretaker_and_warden_are_assignable_operational_roles():
    """BR-MMS-003/004: the admin does not assign themselves, students are not assignable."""
    assert {"mess_caretaker", "mess_warden"} == sm.ALLOWED_OPERATIONAL_ROLES


def test_special_food_statuses_are_exactly_the_five_in_br031():
    assert {"requested", "approved", "rejected", "served", "cancelled"} == sm.SPECIAL_FOOD_STATUSES


def test_errors_carry_structured_context():
    rv = sm.RuleViolation("BR-MMS-999", "nope")
    assert rv.rule_id == "BR-MMS-999"
    assert "BR-MMS-999" in str(rv)
    it = sm.InvalidTransition("a", "b")
    assert (it.from_state, it.to_state) == ("a", "b")
