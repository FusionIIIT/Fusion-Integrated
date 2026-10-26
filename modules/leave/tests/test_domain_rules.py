# modules/leave/tests/test_domain_rules.py

from datetime import date
from decimal import Decimal

from modules.leave.domain.categories import (
    EL,
    VL,
    Interval,
    weekend_dates,
    year_end_action,
)


def test_weekend_dates():
    assert weekend_dates(date(2026, 10, 9), date(2026, 10, 11)) == {date(2026, 10, 10), date(2026, 10, 11)}
    assert weekend_dates(date(2026, 10, 10), date(2026, 10, 15)) == {date(2026, 10, 10), date(2026, 10, 11)}
    assert weekend_dates(date(2026, 10, 10), date(2026, 10, 10)) == {date(2026, 10, 10)}

def test_interval_overlap():
    cl_first = Interval(date(2026, 10, 10), date(2026, 10, 10), "first")
    cl_second = Interval(date(2026, 10, 10), date(2026, 10, 10), "second")
    full_day = Interval(date(2026, 10, 10), date(2026, 10, 10), None)
    disjoint = Interval(date(2026, 10, 11), date(2026, 10, 11), None)

    assert cl_first.overlaps(cl_first) is True
    assert cl_first.overlaps(cl_second) is False
    assert cl_first.overlaps(full_day) is True
    assert cl_first.overlaps(disjoint) is False

def test_year_end_action():
    vl_action = year_end_action(VL, Decimal(10), vl_per_el=2)
    assert vl_action.kind == "convert"
    assert vl_action.amount == Decimal(5)
    assert vl_action.target == EL

    vl_action = year_end_action(VL, Decimal(7), vl_per_el=2)
    assert vl_action.amount == Decimal("3.5")

    el_action = year_end_action(EL, Decimal(4))
    assert el_action.kind != "lapse"
