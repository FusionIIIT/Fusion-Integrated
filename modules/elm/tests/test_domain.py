"""Pure rules, no database."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.elm import registry
from modules.elm.domain import counting, overlap, routing
from modules.elm.domain import policy as pol
from modules.elm.domain import state_machine as sm
from modules.elm.domain.year_end import vl_to_el

MON = date(2026, 3, 2)
CAL = counting.Calendar(closed_holidays=frozenset({MON + timedelta(days=1)}),
                        restricted_holidays=frozenset({MON + timedelta(days=2)}),
                        vacations=((date(2026, 5, 1), date(2026, 6, 30)),))


def test_cl_skips_weekend_and_closed_holiday():
    assert counting.chargeable_days("CL", MON, MON + timedelta(days=6), None, CAL) == 4


def test_el_counts_intervening_weekend_and_holiday():
    assert counting.chargeable_days("EL", MON, MON + timedelta(days=6), None, CAL) == 7


def test_half_day_cl_is_half():
    assert counting.chargeable_days("CL", MON, MON, "first", CAL) == Decimal("0.5")


@pytest.mark.parametrize("cat", ["EL", "SCL", "RH"])
def test_only_cl_takes_half_days(cat):
    with pytest.raises(counting.InvalidPeriod):
        counting.chargeable_days(cat, MON, MON, "first", CAL)


def test_end_before_start_refused():
    with pytest.raises(counting.InvalidPeriod):
        counting.chargeable_days("CL", MON, MON - timedelta(days=1), None, CAL)


def test_rh_must_be_published():
    counting.validate_rh_dates(MON + timedelta(days=2), MON + timedelta(days=2), CAL)
    with pytest.raises(counting.InvalidPeriod):
        counting.validate_rh_dates(MON, MON, CAL)


def test_vl_only_inside_vacation():
    counting.validate_vacation(date(2026, 5, 4), date(2026, 5, 10), CAL)
    with pytest.raises(counting.InvalidPeriod):
        counting.validate_vacation(date(2026, 4, 28), date(2026, 5, 3), CAL)


def test_different_halves_do_not_overlap():
    a = overlap.Interval(MON, MON, "first")
    assert not overlap.overlaps(a, overlap.Interval(MON, MON, "second"))
    assert overlap.overlaps(a, overlap.Interval(MON, MON, "first"))
    assert overlap.overlaps(a, overlap.Interval(MON, MON))


def test_vl_converts_two_to_one_with_fractions():
    assert vl_to_el(Decimal("45"), Decimal("2")) == Decimal("22.50")
    assert vl_to_el(Decimal("0"), Decimal("2")) == 0


def test_staff_get_no_vl_and_faculty_no_el_credit():
    p = pol.parse(pol.DEFAULT_PARAMS)
    with pytest.raises(pol.NotEligible):
        p.check_eligible("staff", "VL")
    assert p.annual_credit_for("faculty", "EL") == 0
    assert p.annual_credit_for("staff", "EL") == 30
    assert p.annual_credit_for("faculty", "VL") == 60


H = registry.DEFAULT_HIERARCHY


def _route(cat, kind="faculty", unit="CSE", roles=("faculty",)):
    return [s.as_dict() for s in routing.resolve_route(
        category=cat, kind=kind, unit=unit, applicant_roles=roles, hierarchy=H)]


def test_cl_ends_at_unit_head():
    assert _route("CL") == [{"step": "unit_head", "role": "HOD (CSE)"}]


def test_faculty_el_goes_to_director_staff_el_to_registrar():
    assert [s["role"] for s in _route("EL")] == ["HOD (CSE)", "Deputy Registrar", "Director"]
    assert [s["role"] for s in _route("EL", kind="staff")][-1] == "Registrar"


def test_director_self_sanctions():
    assert _route("EL", roles=("faculty", "Director")) == [
        {"step": "director", "role": "Director"}]


def test_unmapped_unit_is_refused_with_its_name():
    with pytest.raises(routing.RouteUnresolved, match="Library"):
        _route("CL", unit="Library")


def test_substitute_gate_only_opens_on_accept():
    events = {t.event for t in sm.TRANSITIONS if t.frm == sm.AWAITING_SUBSTITUTE}
    assert events == {sm.SUBSTITUTE_ACCEPT, sm.SUBSTITUTE_DECLINE, sm.MODIFY, sm.WITHDRAW}


def test_nothing_leaves_a_terminal_state():
    assert not [t for t in sm.TRANSITIONS if t.frm in sm.TERMINAL]


def test_unit_head_cannot_finally_reject_higher_sanction():
    assert sm.decision_events("unit_head", False, False) == (sm.RECOMMEND, sm.NOT_RECOMMEND)
    assert sm.decision_events("unit_head", True, False) == (sm.APPROVE, sm.REJECT)


@pytest.mark.parametrize("frm", sm.STATES)
@pytest.mark.parametrize("event", [sm.APPROVE, sm.WITHDRAW, sm.VERIFY_RESUMPTION])
def test_every_unlisted_edge_is_refused(frm, event):
    for actor in (sm.EMPLOYEE, sm.UNIT_HEAD, sm.SANCTIONER, sm.VERIFIER):
        listed = [t for t in sm.TRANSITIONS
                  if t.frm == frm and t.event == event and t.actor == actor]
        if listed:
            continue
        with pytest.raises((sm.InvalidTransition, sm.ActorNotAllowed)):
            sm.resolve(frm, event, actor, sm.APPROVED)
