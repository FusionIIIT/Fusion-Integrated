"""Domain tests: pure Python, no database, milliseconds."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.leave.domain import categories as cat
from modules.leave.domain import counting, routing, yearend
from modules.leave.domain import ledger as led
from modules.leave.domain import sla as sla_domain
from modules.leave.domain.errors import RuleViolation
from modules.leave.domain.substitutes import (
    Interval,
    NominationFacts,
    validate_nomination,
)

MONDAY = date(2026, 3, 2)
FRIDAY = date(2026, 3, 6)
SATURDAY = date(2026, 3, 7)
MONDAY_NEXT = date(2026, 3, 9)


def test_categories_and_their_static_rules():
    assert cat.CATEGORIES == ("CL", "RH", "SCL", "EL", "COL", "VL")
    assert cat.ANNUAL_ENTITLEMENT[cat.CL] == 8
    assert cat.ANNUAL_ENTITLEMENT[cat.RH] == 2
    assert cat.ANNUAL_ENTITLEMENT[cat.SCL] == 15
    assert cat.ANNUAL_ENTITLEMENT[cat.EL] == 30
    assert cat.ANNUAL_ENTITLEMENT[cat.COL] == 20
    assert cat.ANNUAL_ENTITLEMENT[cat.VL] == 60
    assert cat.unit_head_is_final(cat.CL) and cat.unit_head_is_final(cat.RH)
    assert cat.requires_higher_sanction(cat.SCL)
    assert cat.lapses(cat.CL) and cat.lapses(cat.RH) and cat.lapses(cat.SCL)
    assert cat.carries_forward(cat.EL) and cat.carries_forward(cat.COL)


def test_vl_is_faculty_only():
    assert cat.applicable_to(cat.VL, is_faculty=True) is True
    assert cat.applicable_to(cat.VL, is_faculty=False) is False
    assert cat.applicable_to(cat.EL, is_faculty=False) is True


def test_continuous_counting_includes_the_weekend():
    """BR-EL-011: for EL the intervening weekend counts as leave."""
    days = counting.count_days(category=cat.EL, start=FRIDAY, end=MONDAY_NEXT)
    assert days == Decimal(4)


def test_cl_skips_the_weekend_and_closed_holidays():
    days = counting.count_days(category=cat.CL, start=FRIDAY, end=MONDAY_NEXT)
    assert days == Decimal(2)
    closed = counting.count_days(category=cat.CL, start=MONDAY, end=FRIDAY,
                                 closed_dates={FRIDAY})
    assert closed == Decimal(4)


def test_half_day_is_half_a_day_and_only_for_cl():
    assert counting.count_days(category=cat.CL, start=MONDAY, end=MONDAY,
                               half=counting.FIRST_HALF) == Decimal("0.5")
    with pytest.raises(RuleViolation) as exc:
        counting.count_days(category=cat.EL, start=MONDAY, end=MONDAY,
                            half=counting.FIRST_HALF)
    assert exc.value.code == "half_day_not_supported"


def test_half_day_must_be_one_date():
    with pytest.raises(RuleViolation):
        counting.count_days(category=cat.CL, start=MONDAY, end=FRIDAY,
                            half=counting.SECOND_HALF)


def test_two_cl_halves_on_one_date_do_not_overlap():
    assert counting.same_date_different_halves(
        category=cat.CL, half=counting.FIRST_HALF, start=MONDAY, end=MONDAY,
        other_category=cat.CL, other_half=counting.SECOND_HALF,
        other_start=MONDAY, other_end=MONDAY) is True
    assert counting.same_date_different_halves(
        category=cat.CL, half=counting.FIRST_HALF, start=MONDAY, end=MONDAY,
        other_category=cat.CL, other_half=counting.FIRST_HALF,
        other_start=MONDAY, other_end=MONDAY) is False


def test_the_ledger_sign_is_decided_in_one_place():
    assert led.signed_days(led.DEBIT, Decimal(2)) == Decimal(-2)
    assert led.signed_days(led.ACCRUAL, Decimal(-8)) == Decimal(8)
    assert led.project([(led.ACCRUAL, 8), (led.DEBIT, 3)]) == Decimal(5)
    assert led.project([(led.ACCRUAL, 8), (led.DEBIT, 3),
                        (led.CREDIT, 3)]) == Decimal(8)


def test_available_holds_the_committed_days():
    assert led.available(Decimal(8), Decimal("0.5")) == Decimal("7.5")


def test_year_end_lapses_carries_and_converts():
    assert yearend.settle(category=cat.CL, closing=Decimal(3)).lapsed == Decimal(3)
    assert yearend.settle(category=cat.EL,
                          closing=Decimal(4)).carried_forward == Decimal(4)
    outcome = yearend.settle(category=cat.VL, closing=Decimal(5))
    assert outcome.converted_el == Decimal("2.5")
    assert outcome.carried_forward == Decimal(0)


def test_converted_el_moves_out_of_vl_and_into_el():
    outcome = yearend.settle(category=cat.VL, closing=Decimal(5))
    assert (led.CONVERSION_OUT, Decimal(5)) in outcome.moves()
    assert (led.CONVERSION_IN, Decimal("2.5")) in outcome.moves()


def _path(category, steps, role=""):
    return routing.resolve(category=category, steps=steps, applicant_role=role)


def test_the_unit_head_is_final_for_cl_and_rh():
    steps = (routing.ConfiguredStep(10, routing.UNIT_HEAD, "HOD (CSE)"),
             routing.ConfiguredStep(30, routing.FINAL_AUTHORITY, "Registrar"))
    path = _path(cat.CL, steps)
    assert path.unit_head_final is True
    assert path.final is None
    assert path.first_designation == "HOD (CSE)"


def test_higher_sanction_routes_through_the_establishment_when_configured():
    steps = (routing.ConfiguredStep(10, routing.UNIT_HEAD, "HOD (CSE)"),
             routing.ConfiguredStep(20, routing.ESTABLISHMENT, "Deputy Registrar (Estt.)"),
             routing.ConfiguredStep(30, routing.FINAL_AUTHORITY, "Registrar"))
    path = _path(cat.EL, steps)
    assert path.establishment_designation == "Deputy Registrar (Estt.)"
    assert path.final_designation == "Registrar"


def test_an_unconfigured_hierarchy_refuses_rather_than_guessing():
    with pytest.raises(RuleViolation) as exc:
        _path(cat.EL, ())
    assert exc.value.code == "routing_not_configured"


def test_the_director_self_sanctions():
    path = _path(cat.EL, (), role="Director")
    assert path.self_sanction is True
    assert path.final is None


def _nomination(nominee=1002, employee=True, active=True, intervals=()):
    return NominationFacts(applicant_id=1001, nominee_id=nominee,
                           nominee_is_employee=employee, nominee_is_active=active,
                           period=Interval(MONDAY, FRIDAY), nominee_intervals=intervals)


def test_a_substitute_may_not_be_the_applicant():
    with pytest.raises(RuleViolation) as exc:
        validate_nomination(_nomination(nominee=1001))
    assert exc.value.code == "substitute_is_applicant"


def test_a_substitute_must_be_an_active_employee():
    with pytest.raises(RuleViolation):
        validate_nomination(_nomination(employee=False))
    with pytest.raises(RuleViolation):
        validate_nomination(_nomination(active=False))


def test_a_substitute_may_not_overlap_the_responsibility_period():
    with pytest.raises(RuleViolation) as exc:
        validate_nomination(_nomination(
            intervals=(Interval(MONDAY + timedelta(days=1),
                                FRIDAY + timedelta(days=1)),)))
    assert exc.value.code == "substitute_unavailable"
    validate_nomination(_nomination())


def test_sla_thresholds_must_be_ordered():
    with pytest.raises(RuleViolation):
        sla_domain.validate(sla_domain.Thresholds(reminder_hours=72,
                                                  escalation_hours=24))
    sla_domain.validate(sla_domain.Thresholds(reminder_hours=24,
                                              escalation_hours=48))


def test_sla_events_are_pending_only_and_one_shot():
    thresholds = sla_domain.Thresholds(reminder_hours=24, escalation_hours=48)
    assert sla_domain.events(thresholds=thresholds, age_hours=30, pending=False) == ()
    assert sla_domain.events(thresholds=thresholds, age_hours=30,
                             pending=True) == (sla_domain.REMIND,)
    assert sla_domain.events(thresholds=thresholds, age_hours=30, pending=True,
                             reminded=True) == ()
    assert sla_domain.events(thresholds=thresholds, age_hours=50,
                             pending=True) == (sla_domain.REMIND,
                                               sla_domain.ESCALATE)
