"""Domain rules with no database: counting, overlap, validation, entitlement, year-end, resumption."""
from datetime import date, timedelta
from decimal import Decimal as D

import pytest

from modules.leave.domain import categories as cat
from modules.leave.domain import entitlement, resumption, yearend
from modules.leave.domain import policy as pol
from modules.leave.domain.counting import chargeable_days
from modules.leave.domain.overlap import Interval, collides
from modules.leave.domain.validation import (
    CalendarView,
    Context,
    Draft,
    extension_problems,
    new_leave_problems,
    substitute_problems,
)

MON = date(2026, 3, 2)
HOLI = date(2026, 3, 4)
RH_DAY = date(2026, 3, 10)


def ctx(**over):
    base = {"applicant_id": 1, "applicant_kind": "faculty", "today": MON, "policy": pol.baseline(),
                "calendar": CalendarView(True, frozenset({HOLI}), frozenset({RH_DAY})),
                "available": D(8), "existing": [],
                "vacations": ((date(2026, 5, 15), date(2026, 7, 20)),)}
    base.update(over)
    return Context(**base)


def draft(**over):
    base = {"category": "CL", "start": MON + timedelta(days=7), "end": MON + timedelta(days=7),
                "purpose": "Family function"}
    base.update(over)
    return Draft(**base)


def codes(problems):
    return [p.code for p in problems]


# -- BR-EL-010/011 counting --------------------------------------------------------
def test_cl_skips_weekends_and_closed_holidays():
    assert chargeable_days("CL", MON, MON + timedelta(days=6),
                           closed_holidays=frozenset({HOLI})) == D(4)


def test_el_counts_every_calendar_day_including_weekends_and_holidays():
    assert chargeable_days("EL", MON, MON + timedelta(days=6),
                           closed_holidays=frozenset({HOLI})) == D(7)


@pytest.mark.parametrize("code", ["COL", "VL"])
def test_col_and_vl_are_continuous(code):
    assert chargeable_days(code, MON, MON + timedelta(days=13)) == D(14)


@pytest.mark.parametrize("code", ["SCL", "RH"])
def test_scl_and_rh_are_not_continuous(code):
    assert chargeable_days(code, MON, MON + timedelta(days=6)) == D(5)


def test_half_day_cl_is_half():
    assert chargeable_days("CL", MON, MON, half="first") == D("0.5")


def test_half_day_only_for_cl():
    with pytest.raises(ValueError, match="half day"):
        chargeable_days("EL", MON, MON, half="first")


def test_half_day_over_two_dates_is_refused():
    with pytest.raises(ValueError):
        chargeable_days("CL", MON, MON + timedelta(days=1), half="first")


def test_weekend_days_are_policy():
    assert chargeable_days("CL", MON, MON + timedelta(days=6), weekend_days=frozenset({6})) == 6


# -- BR-EL-012 overlap -------------------------------------------------------------
def test_different_cl_halves_on_one_date_do_not_collide():
    assert not collides(Interval(MON, MON, "first"), Interval(MON, MON, "second"))


def test_same_half_collides():
    assert collides(Interval(MON, MON, "first"), Interval(MON, MON, "first"))


def test_half_and_full_day_collide():
    assert collides(Interval(MON, MON, "first"), Interval(MON, MON))


def test_adjacent_intervals_do_not_collide():
    assert not collides(Interval(MON, MON), Interval(MON + timedelta(days=1), MON +
                                                     timedelta(days=2)))


# -- validation, the plain case first ----------------------------------------------
def test_a_plain_one_day_cl_passes():
    assert new_leave_problems(draft(), ctx()) == []


def test_unknown_category_is_named():
    assert codes(new_leave_problems(draft(category="ML"), ctx())) == ["unknown_category"]


def test_vl_is_not_available_to_staff():
    assert codes(new_leave_problems(draft(category="VL"), ctx(applicant_kind="staff"))) == [
        "category_not_applicable"]


def test_el_is_available_to_faculty_who_hold_it():
    d = draft(category="EL")
    assert new_leave_problems(d, ctx(available=D(5))) == []


def test_end_before_start():
    assert codes(new_leave_problems(draft(end=MON), ctx())) == ["invalid_period"]


def test_purpose_required():
    assert codes(new_leave_problems(draft(purpose="  "), ctx())) == ["purpose_required"]


def test_backdating_refused_by_default():
    assert codes(new_leave_problems(draft(start=MON - timedelta(days=1),
                                          end=MON - timedelta(days=1)), ctx())) == ["backdated"]


def test_backdating_allowed_within_policy():
    policy = pol.Policy(rules=pol.baseline().rules, max_backdate_days=3)
    friday = MON - timedelta(days=3)
    assert new_leave_problems(draft(start=friday, end=friday), ctx(policy=policy)) == []


def test_unpublished_calendar_blocks():
    assert codes(new_leave_problems(draft(), ctx(calendar=CalendarView(False)))) == [
        "calendar_not_published"]


def test_rh_only_on_a_restricted_holiday():
    assert codes(new_leave_problems(draft(category="RH"), ctx())) == ["not_restricted_holiday"]
    assert new_leave_problems(draft(category="RH", start=RH_DAY, end=RH_DAY), ctx()) == []


def test_vl_only_inside_a_vacation():
    assert codes(new_leave_problems(draft(category="VL"), ctx(available=D(60)))) == [
        "outside_vacation"]
    inside = draft(category="VL", start=date(2026, 6, 1), end=date(2026, 6, 10))
    assert new_leave_problems(inside, ctx(available=D(60))) == []


def test_vl_straddling_the_vacation_end_is_refused():
    d = draft(category="VL", start=date(2026, 7, 15), end=date(2026, 7, 25))
    assert codes(new_leave_problems(d, ctx(available=D(60)))) == ["outside_vacation"]


def test_only_holidays_means_nothing_to_apply_for():
    sat = MON + timedelta(days=5)
    assert codes(new_leave_problems(draft(start=sat, end=sat + timedelta(days=1)), ctx())) == [
        "no_chargeable_days"]


def test_overlap_with_own_leave():
    d = draft()
    assert "overlaps_own_leave" in codes(new_leave_problems(d, ctx(existing=[
        Interval(d.start, d.start)])))


def test_insufficient_balance_counts_pending():
    assert codes(new_leave_problems(draft(), ctx(available=D("0.5")))) == ["insufficient_balance"]


def test_station_leave_needs_details():
    assert codes(new_leave_problems(draft(station_leave=True), ctx())) == [
        "station_details_required"]


def test_station_leave_must_touch_the_leave():
    d = draft(station_leave=True, station_from=MON + timedelta(days=20),
              station_to=MON + timedelta(days=21), station_address="Delhi")
    assert codes(new_leave_problems(d, ctx())) == ["station_outside_leave"]


def test_col_evidence_at_threshold():
    d = draft(category="COL", start=MON + timedelta(days=7), end=MON + timedelta(days=9))
    assert codes(new_leave_problems(d, ctx(available=D(20)))) == ["evidence_required"]
    ok = draft(category="COL", start=d.start, end=d.end, evidence_reference="Med cert 12")
    assert new_leave_problems(ok, ctx(available=D(20))) == []


# -- BR-EL-014 substitute ----------------------------------------------------------
PERIOD = Interval(MON + timedelta(days=7), MON + timedelta(days=8))


def sub(**over):
    base = {"applicant_id": 1, "nominee_id": 2, "nominee_kind": "faculty", "nominee_active": True,
                "nominee_leave": [], "period": PERIOD}
    base.update(over)
    return codes(substitute_problems(**base))


def test_substitute_plain_case():
    assert sub() == []


def test_substitute_not_self():
    assert sub(nominee_id=1) == ["substitute_is_applicant"]


def test_substitute_must_be_employee():
    assert sub(nominee_kind="student") == ["substitute_not_employee"]
    assert sub(nominee_active=False) == ["substitute_not_employee"]


def test_substitute_not_away_themselves():
    assert sub(nominee_leave=[PERIOD]) == ["substitute_on_leave"]


def test_substitute_missing():
    assert sub(nominee_id=None) == ["substitute_required"]


# -- BR-EL-025 extension -----------------------------------------------------------
def test_extension_must_follow_directly_and_be_ongoing():
    base_start, end = MON - timedelta(days=3), MON + timedelta(days=2)
    good = draft(category="EL", start=end + timedelta(days=1), end=end + timedelta(days=4))
    kw = {"base_category": "EL", "base_start": base_start, "base_effective_end": end}
    assert extension_problems(draft=good, ctx=ctx(available=D(30)), **kw) == []
    gap = draft(category="EL", start=end + timedelta(days=2), end=end + timedelta(days=4))
    assert codes(extension_problems(draft=gap, ctx=ctx(available=D(30)), **kw)) == [
        "extension_not_contiguous"]
    assert codes(extension_problems(draft=good, ctx=ctx(available=D(30)), base_category="CL",
                                    base_start=base_start, base_effective_end=end)) == [
        "not_extendable"]
    assert codes(extension_problems(draft=good, ctx=ctx(available=D(30)), base_category="EL",
                                    base_start=MON + timedelta(days=1),
                                    base_effective_end=end)) == ["not_ongoing"]


# -- entitlement and year-end ------------------------------------------------------
def test_annual_credit_by_kind():
    p = pol.baseline()
    assert entitlement.annual_credits(p, "faculty") == {
        "CL": D(8), "RH": D(2), "SCL": D(15), "COL": D(20), "VL": D(60)}
    assert entitlement.annual_credits(p, "staff") == {
        "CL": D(8), "RH": D(2), "SCL": D(15), "EL": D(30), "COL": D(20)}
    assert entitlement.annual_credits(p, "student") == {}


def test_year_end_lapses_carries_and_converts_with_fractions():
    moves = yearend.outcome({"CL": D("2.5"), "RH": D(1), "SCL": D(3), "EL": D(10),
                             "COL": D(4), "VL": D(7)})
    by = {(m.entry_type, m.category): m for m in moves}
    assert by[("lapse", "CL")].delta == D("-2.5")
    assert by[("lapse", "RH")].delta == D(-1)
    assert by[("lapse", "SCL")].delta == D(-3)
    assert by[("carry_out", "EL")].delta == D(-10) and by[("carry_in", "EL")].next_year
    assert by[("carry_in", "COL")].delta == D(4)
    assert by[("convert_out", "VL")].delta == D(-7)
    assert by[("convert_in", "EL")].delta == D("3.50") and by[("convert_in", "EL")].next_year
    closing = sum(m.delta for m in moves if not m.next_year)
    assert closing == -sum([D("2.5"), D(1), D(3), D(10), D(4), D(7)])


def test_year_end_refuses_a_negative_balance():
    with pytest.raises(ValueError):
        yearend.outcome({"CL": D(-1)})


def test_nothing_to_close_is_nothing():
    assert yearend.outcome({}) == []


# -- resumption --------------------------------------------------------------------
def test_resumption_classification():
    end = date(2026, 3, 10)
    assert resumption.classify(approved_end=end, resumption_date=date(2026, 3, 11)).kind == "normal"
    early = resumption.classify(approved_end=end, resumption_date=date(2026, 3, 8))
    assert (early.kind, early.adjustment, early.actual_end) == ("early", D(3), date(2026, 3, 7))
    late = resumption.classify(approved_end=end, resumption_date=date(2026, 3, 13))
    assert (late.kind, late.adjustment) == ("late", D(-2))


def test_resumption_submission_rules():
    kw = {"category": "EL", "leave_start": date(2026, 3, 1), "today": date(2026, 3, 9)}
    resumption.check_submission(resumption_date=date(2026, 3, 9), **kw)
    for bad, code in ((date(2026, 3, 10), "resumption_in_future"),
                      (date(2026, 3, 1), "resumption_before_leave")):
        with pytest.raises(resumption.ResumptionRefused) as e:
            resumption.check_submission(resumption_date=bad, **kw)
        assert e.value.code == code
    with pytest.raises(resumption.ResumptionRefused):
        resumption.check_submission(category="CL", leave_start=date(2026, 3, 1),
                                    resumption_date=date(2026, 3, 3), today=date(2026, 3, 9))


# -- policy validation ---------------------------------------------------------------
def test_policy_validation_names_every_problem():
    rules = dict(pol.baseline().rules)
    rules["CL"] = pol.CategoryRule("CL", D(-1), substitute="sometimes")
    del rules["VL"]
    with pytest.raises(pol.PolicyInvalid) as e:
        pol.validate(pol.Policy(rules=rules, weekend_days=frozenset({9}), max_backdate_days=99))
    assert len(e.value.problems) >= 5


def test_baseline_is_valid_and_matches_the_problem_statement():
    p = pol.baseline()
    pol.validate(p)
    assert {c: p.rule(c).annual_entitlement for c in cat.ALL} == pol.BASELINE_ENTITLEMENTS
