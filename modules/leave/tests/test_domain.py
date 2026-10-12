"""Pure-domain rules: counting, overlap, the state machine, year-end plans.

No database, no HTTP — these are the rules everything else delegates to.
"""
from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain import counting, states as st, validation as v
from modules.leave.domain import year_end as ye


# -- counting ---------------------------------------------------------------
def test_continuous_categories_count_every_day():
    # 2026-01-01 is a Thursday; span includes Sat 3 and Sun 4.
    days = counting.chargeable_days(
        category="el", start=date(2026, 1, 1), end=date(2026, 1, 4))
    assert days == Decimal(4)


def test_cl_skips_weekends_and_closed_holidays():
    # Wed 2026-01-07 … Tue 2026-01-13; Sat 10 and Sun 11 are weekends,
    # Mon 12 is a closed holiday.
    days = counting.chargeable_days(
        category="cl", start=date(2026, 1, 7), end=date(2026, 1, 13),
        closed_holidays={date(2026, 1, 12)})
    assert days == Decimal(4)     # Wed, Thu, Fri, Tue


def test_half_day_cl_is_half():
    days = counting.chargeable_days(
        category="cl", start=date(2026, 1, 7), end=date(2026, 1, 7),
        half_day="first")
    assert days == Decimal("0.5")


def test_half_day_el_is_not_a_thing():
    # The service refuses it; the counter simply does not halve EL.
    days = counting.chargeable_days(
        category="el", start=date(2026, 1, 7), end=date(2026, 1, 7),
        half_day="first")
    assert days == Decimal(1)


# -- validation -------------------------------------------------------------
def test_half_day_must_be_single_day():
    with pytest.raises(v.ValidationError) as exc:
        v.check_interval(start=date(2026, 1, 7), end=date(2026, 1, 8),
                         half_day="first", category="cl")
    assert exc.value.code == "half_day_must_be_single_day"


def test_half_day_only_for_cl():
    with pytest.raises(v.ValidationError) as exc:
        v.check_interval(start=date(2026, 1, 7), end=date(2026, 1, 7),
                         half_day="second", category="el")
    assert exc.value.code == "half_day_not_supported"


def test_rh_must_hit_a_published_restricted_day():
    with pytest.raises(v.ValidationError) as exc:
        v.check_rh_calendar(start=date(2026, 1, 7), end=date(2026, 1, 7),
                            restricted_dates={date(2026, 11, 8)})
    assert exc.value.code == "rh_not_applicable"
    v.check_rh_calendar(start=date(2026, 1, 7), end=date(2026, 1, 7),
                        restricted_dates={date(2026, 1, 7)})


def test_vl_only_inside_a_vacation_period():
    with pytest.raises(v.ValidationError) as exc:
        v.check_vl_vacation_period(start=date(2026, 1, 7), end=date(2026, 1, 7),
                                   vacation_periods=[(date(2026, 12, 21),
                                                      date(2027, 1, 1))])
    assert exc.value.code == "vl_outside_vacation"


def test_same_day_half_day_cls_do_not_overlap():
    # BR-EL-012: opposite halves of the same date coexist.
    v.check_overlap(start=date(2026, 1, 7), end=date(2026, 1, 7),
                    half_day="first", category="cl",
                    existing=[v.Interval(date(2026, 1, 7), date(2026, 1, 7),
                                         "second", "cl")])
    # ... but same-half on the same date does.
    with pytest.raises(v.ValidationError) as exc:
        v.check_overlap(start=date(2026, 1, 7), end=date(2026, 1, 7),
                        half_day="first", category="cl",
                        existing=[v.Interval(date(2026, 1, 7), date(2026, 1, 7),
                                             "first", "cl")])
    assert exc.value.code == "overlapping_leave"


def test_balance_shortfall_is_refused():
    with pytest.raises(v.ValidationError) as exc:
        v.check_balance(available=Decimal(2), required=Decimal(3),
                        category="cl")
    assert exc.value.code == "insufficient_balance"


def test_substitute_must_be_someone_else_in_the_directory():
    with pytest.raises(v.ValidationError) as exc:
        v.check_substitute(nominee=1, applicant=1, employee_ids={1, 2})
    assert exc.value.code == "self_substitute"
    with pytest.raises(v.ValidationError) as exc:
        v.check_substitute(nominee=9, applicant=1, employee_ids={1, 2})
    assert exc.value.code == "substitute_not_employee"


# -- state machine ----------------------------------------------------------
def test_unit_head_final_edges_only():
    t = st.resolve(st.AWAITING_UH_REVIEW, st.APPROVED, st.UNIT_HEAD)
    assert "unit_head_final" in t.guards
    with pytest.raises(st.InvalidTransition):
        st.resolve(st.AWAITING_UH_REVIEW, st.AWAITING_FINAL, st.SUBSTITUTE)


def test_substitute_cannot_sanction():
    with pytest.raises(st.ActorNotAllowed):
        st.resolve(st.AWAITING_FINAL, st.APPROVED, st.SUBSTITUTE)


def test_withdrawable_is_exactly_the_pending_states():
    assert st.WITHDRAWABLE == st.PENDING
    assert st.APPROVED not in st.WITHDRAWABLE
    assert st.CANCELLED not in st.WITHDRAWABLE


# -- year-end plan ----------------------------------------------------------
def test_lapse_convert_carry():
    plan = ye.plan_year_end(
        year=2026,
        balances=[(1, "cl", Decimal(5)), (1, "vl", Decimal(60)),
                  (1, "el", Decimal(10)), (2, "col", Decimal(4)),
                  (2, "scl", Decimal(1.5))],
        is_faculty={1: True, 2: False},
        vl_to_el_numerator=Decimal(2), vl_to_el_denominator=Decimal(1),
        carry_forward_enabled={"el": True, "col": True},
    )
    kinds = {(e.user_id, e.category, e.year, e.kind) for e in plan.entries}
    assert (1, "cl", 2026, "year_end_lapse") in kinds
    assert (1, "vl", 2026, "vl_to_el_conversion") in kinds
    assert (1, "el", 2027, "vl_to_el_conversion") in kinds
    assert (1, "el", 2027, "carry_forward") in kinds
    assert (1, "el", 2026, "carry_forward") in kinds     # source debited too
    assert (2, "col", 2027, "carry_forward") in kinds
    assert (2, "scl", 2026, "year_end_lapse") in kinds
    el_in = [e for e in plan.entries
             if e.user_id == 1 and e.category == "el" and e.year == 2027
             and e.kind == "vl_to_el_conversion"]
    assert el_in[0].days == Decimal("30.00")


def test_faculty_vl_converts_staff_vl_lapses():
    plan = ye.plan_year_end(
        year=2026, balances=[(1, "vl", Decimal(10)), (2, "vl", Decimal(10))],
        is_faculty={1: True, 2: False},
        vl_to_el_numerator=Decimal(2), vl_to_el_denominator=Decimal(1),
        carry_forward_enabled={},
    )
    dest = [e for e in plan.entries if e.year == 2027]
    assert len(dest) == 1 and dest[0].user_id == 1
    lapses = [e for e in plan.entries if e.kind == "year_end_lapse"]
    assert [e.user_id for e in lapses] == [2]


def test_zero_balances_plan_nothing():
    plan = ye.plan_year_end(
        year=2026, balances=[(1, "cl", Decimal(0))], is_faculty={1: False},
        vl_to_el_numerator=Decimal(2), vl_to_el_denominator=Decimal(1),
        carry_forward_enabled={})
    assert plan.entries == ()
