"""Day counting, including the case the specification leaves open."""
from datetime import date
from decimal import Decimal

import pytest

from modules.leave.domain.categories import Category
from modules.leave.domain.counting import (
    Calendar,
    Half,
    TailPolicy,
    actual_days_on_early_return,
    chargeable_days,
    restored_days,
)

# Mon 10 Aug 2026 to Mon 17 Aug. Sat 15 is a closed holiday as well as a weekend.
MON, FRI, SAT, SUN, NEXT_MON = (
    date(2026, 8, 10), date(2026, 8, 14), date(2026, 8, 15),
    date(2026, 8, 16), date(2026, 8, 17),
)
CAL = Calendar(holidays=frozenset({SAT}))


class TestContinuousCounting:
    """BR-EL-011. EL, COL and VL swallow the weekend; CL, SCL and RH do not."""

    @pytest.mark.parametrize("category", [Category.EL, Category.COL, Category.VL])
    def test_intervening_closed_days_are_charged(self, category):
        assert chargeable_days(category, MON, NEXT_MON, CAL) == Decimal(8)

    @pytest.mark.parametrize("category", [Category.CL, Category.SCL, Category.RH])
    def test_only_working_days_are_charged(self, category):
        assert chargeable_days(category, MON, NEXT_MON, CAL) == Decimal(6)

    def test_a_weekend_alone_costs_a_continuous_leave_two_days(self):
        assert chargeable_days(Category.EL, SAT, SUN, CAL) == Decimal(2)

    def test_a_weekend_alone_costs_a_casual_leave_nothing(self):
        assert chargeable_days(Category.CL, SAT, SUN, CAL) == Decimal(0)


class TestHalfDay:
    """BR-EL-010. Half days are a casual-leave affair and cost 0.5."""

    def test_half_day_costs_half(self):
        assert chargeable_days(Category.CL, MON, MON, CAL, half=Half.FIRST) == Decimal("0.5")

    def test_a_half_day_cannot_span_dates(self):
        with pytest.raises(ValueError):
            chargeable_days(Category.CL, MON, FRI, CAL, half=Half.FIRST)

    def test_an_interval_cannot_end_before_it_starts(self):
        with pytest.raises(ValueError):
            chargeable_days(Category.CL, FRI, MON, CAL)


class TestEarlyReturn:
    """BR-EL-028, and the question the specification does not settle.

    Approved Mon to Mon, eight continuous days. The employee comes back on the
    Monday, so the last day away was Sunday. Whether the weekend was spent on
    leave is a policy choice, and the two answers differ by two days of balance.
    """

    def test_default_trims_the_closed_tail(self):
        assert actual_days_on_early_return(
            Category.EL, MON, NEXT_MON, NEXT_MON, CAL
        ) == Decimal(5)

    def test_the_alternative_charges_through_the_weekend(self):
        assert actual_days_on_early_return(
            Category.EL, MON, NEXT_MON, NEXT_MON, CAL, TailPolicy.CHARGE_TO_RESUMPTION
        ) == Decimal(7)

    def test_the_choice_is_worth_two_days_of_balance(self):
        trimmed = restored_days(Category.EL, MON, NEXT_MON, NEXT_MON, CAL)
        charged = restored_days(
            Category.EL, MON, NEXT_MON, NEXT_MON, CAL, TailPolicy.CHARGE_TO_RESUMPTION
        )
        assert trimmed - charged == Decimal(2)

    def test_returning_after_the_approved_end_charges_the_whole_period(self):
        later = date(2026, 8, 20)
        assert actual_days_on_early_return(
            Category.EL, MON, NEXT_MON, later, CAL
        ) == chargeable_days(Category.EL, MON, NEXT_MON, CAL)

    def test_returning_on_the_first_day_charges_nothing(self):
        assert actual_days_on_early_return(Category.EL, MON, NEXT_MON, MON, CAL) == Decimal(0)

    def test_nothing_is_restored_when_the_full_period_is_taken(self):
        after = date(2026, 8, 18)
        assert restored_days(Category.EL, MON, NEXT_MON, after, CAL) == Decimal(0)

    def test_restored_plus_actual_always_equals_approved(self):
        for day in (date(2026, 8, 11), FRI, SAT, SUN, NEXT_MON):
            actual = actual_days_on_early_return(Category.EL, MON, NEXT_MON, day, CAL)
            restored = restored_days(Category.EL, MON, NEXT_MON, day, CAL)
            assert actual + restored == chargeable_days(Category.EL, MON, NEXT_MON, CAL)
