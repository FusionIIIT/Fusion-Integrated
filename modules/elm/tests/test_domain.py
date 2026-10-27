from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.leave import (
    Category, LeaveRuleError, Stage, chargeable_days, employee_is_eligible,
    requests_overlap, validate_route, yearly_charges,
)


@pytest.mark.parametrize(("category", "kind", "expected"), [
    (Category.CL, "faculty", True), (Category.RH, "staff", True),
    (Category.SCL, "faculty", True), (Category.EL, "staff", True),
    (Category.EL, "faculty", False), (Category.COL, "staff", True),
    (Category.VL, "faculty", True), (Category.VL, "staff", False),
])
def test_category_employee_eligibility(category, kind, expected):
    assert employee_is_eligible(category, kind) is expected


def test_counting_and_year_split_share_same_rules():
    close = {date(2026, 1, 1)}
    parts = yearly_charges(Category.CL, date(2025, 12, 31), date(2026, 1, 2),
                           closed_dates=close)
    assert parts == {2025: Decimal(1), 2026: Decimal(1)}
    assert chargeable_days(Category.CL, date(2025, 12, 31), date(2026, 1, 2),
                           closed_dates=close) == sum(parts.values())


def test_half_day_and_restricted_holiday_validation():
    assert chargeable_days(Category.CL, date(2026, 2, 2), date(2026, 2, 2),
                           half_day="first") == Decimal("0.5")
    with pytest.raises(LeaveRuleError):
        chargeable_days(Category.CL, date(2026, 2, 2), date(2026, 2, 3), half_day="first")
    with pytest.raises(LeaveRuleError):
        chargeable_days(Category.RH, date(2026, 2, 2), date(2026, 2, 2))


def test_only_opposite_cl_halves_may_share_a_day():
    args = dict(start=date(2026, 2, 2), end=date(2026, 2, 2), category=Category.CL,
                other_start=date(2026, 2, 2), other_end=date(2026, 2, 2),
                other_category=Category.CL, other_half_day="second")
    assert not requests_overlap(**args, half_day="first")
    assert requests_overlap(**args, half_day="second")


def test_routing_shapes_and_director_rule():
    validate_route(Category.CL, [Stage.UNIT_HEAD])
    validate_route(Category.EL, [Stage.UNIT_HEAD, Stage.ESTABLISHMENT, Stage.FINAL])
    validate_route(Category.VL, [Stage.DIRECTOR_SELF], director=True)
    with pytest.raises(LeaveRuleError):
        validate_route(Category.CL, [Stage.FINAL])
    with pytest.raises(LeaveRuleError):
        validate_route(Category.EL, [Stage.DIRECTOR_SELF])
