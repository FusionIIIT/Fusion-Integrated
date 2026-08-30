"""Entitlement, carry-forward and the year-end conversion."""
from decimal import Decimal

import pytest

from modules.leave.domain.categories import Category
from modules.leave.domain.entitlement import (
    Balance,
    CategoryPolicy,
    ConversionRounding,
    close_year,
    convert_vl_to_el,
    has_sufficient_balance,
)

D = Decimal


def policy(category, credit, carries, cap=None):
    return CategoryPolicy(category, D(credit), carries_forward=carries, carry_forward_cap=cap)


class TestBalance:
    def test_available_is_opening_plus_credit_less_consumed_plus_restored(self):
        b = Balance(Category.EL, opening=D(5), credited=D(30), consumed=D(12), restored=D(2))
        assert b.available == D(25)

    def test_a_request_within_balance_is_allowed(self):
        assert has_sufficient_balance(Balance(Category.CL, credited=D(8)), D(8))

    def test_a_request_beyond_balance_is_refused(self):
        assert not has_sufficient_balance(Balance(Category.CL, credited=D(8)), D("8.5"))


class TestVacationConversion:
    """BR-EL-007. Two VL buy one EL and fractions are permitted."""

    def test_an_even_balance_converts_cleanly(self):
        assert convert_vl_to_el(D(30), D(2)) == D("15.00")

    def test_an_odd_balance_keeps_the_half_by_default(self):
        assert convert_vl_to_el(D(5), D(2)) == D("2.50")

    @pytest.mark.parametrize(
        "rounding,expected",
        [
            (ConversionRounding.EXACT_HALF, D("2.50")),
            (ConversionRounding.FLOOR_TO_WHOLE, D(2)),
            (ConversionRounding.ROUND_TO_WHOLE, D(3)),
        ],
    )
    def test_the_rounding_choice_is_visible_and_changes_the_answer(self, rounding, expected):
        assert convert_vl_to_el(D(5), D(2), rounding) == expected

    def test_nothing_unused_converts_to_nothing(self):
        assert convert_vl_to_el(D(0), D(2)) == D(0)

    def test_a_ratio_must_be_positive(self):
        with pytest.raises(ValueError):
            convert_vl_to_el(D(10), D(0))

    def test_the_ratio_is_policy_not_a_constant(self):
        assert convert_vl_to_el(D(30), D(3)) == D("10.00")


class TestYearEnd:
    """BR-EL-002 to BR-EL-009 settled together, as the year-end run does."""

    def test_casual_leave_lapses(self):
        out = close_year(
            {Category.CL: Balance(Category.CL, credited=D(8), consumed=D(5))},
            {Category.CL: policy(Category.CL, 8, False)},
        )
        assert out.carried[Category.CL] == D(0)
        assert out.lapsed[Category.CL] == D(3)

    def test_earned_leave_carries(self):
        out = close_year(
            {Category.EL: Balance(Category.EL, opening=D(10), credited=D(30), consumed=D(4))},
            {Category.EL: policy(Category.EL, 30, True)},
        )
        assert out.carried[Category.EL] == D(36)
        assert out.lapsed[Category.EL] == D(0)

    def test_a_cap_limits_what_carries(self):
        out = close_year(
            {Category.EL: Balance(Category.EL, opening=D(280), credited=D(30))},
            {Category.EL: policy(Category.EL, 30, True, cap=300)},
        )
        assert out.carried[Category.EL] == D(300)
        assert out.lapsed[Category.EL] == D(10)

    def test_faculty_vacation_becomes_earned_leave_and_carries_the_same_year(self):
        out = close_year(
            {
                Category.VL: Balance(Category.VL, credited=D(60), consumed=D(45)),
                Category.EL: Balance(Category.EL, opening=D(3)),
            },
            {
                Category.VL: policy(Category.VL, 60, False),
                Category.EL: policy(Category.EL, 0, True),
            },
            vl_to_el_ratio=D(2),
        )
        assert out.converted_vl == D(15)
        assert out.el_from_conversion == D("7.50")
        assert out.carried[Category.EL] == D("10.50")
        assert out.carried[Category.VL] == D(0)

    def test_vacation_does_not_lapse_when_it_has_been_converted(self):
        out = close_year(
            {Category.VL: Balance(Category.VL, credited=D(60), consumed=D(20))},
            {Category.VL: policy(Category.VL, 60, False)},
            vl_to_el_ratio=D(2),
        )
        assert out.lapsed[Category.VL] == D(0)
        assert out.converted_vl == D(40)

    def test_vacation_lapses_when_no_conversion_is_configured(self):
        out = close_year(
            {Category.VL: Balance(Category.VL, credited=D(60), consumed=D(20))},
            {Category.VL: policy(Category.VL, 60, False)},
        )
        assert out.lapsed[Category.VL] == D(40)
        assert out.el_from_conversion == D(0)
