"""Non-overlap, and the one case where a date may be shared."""
from datetime import date

import pytest

from modules.leave.domain.counting import Half
from modules.leave.domain.overlap import Period, first_conflict, overlaps

DAY = date(2026, 9, 1)


class TestOverlap:
    """BR-EL-012."""

    def test_identical_periods_collide(self):
        assert overlaps(Period(DAY, DAY), Period(DAY, DAY))

    def test_partial_intersection_collides(self):
        assert overlaps(
            Period(date(2026, 9, 1), date(2026, 9, 5)),
            Period(date(2026, 9, 4), date(2026, 9, 8)),
        )

    def test_touching_at_the_boundary_collides(self):
        assert overlaps(
            Period(date(2026, 9, 1), date(2026, 9, 3)),
            Period(date(2026, 9, 3), date(2026, 9, 5)),
        )

    def test_separated_periods_do_not_collide(self):
        assert not overlaps(
            Period(date(2026, 9, 1), date(2026, 9, 2)),
            Period(date(2026, 9, 3), date(2026, 9, 4)),
        )


class TestHalfDays:
    """The exception: different halves of one date are not a collision."""

    def test_opposite_halves_are_permitted(self):
        assert not overlaps(Period(DAY, DAY, Half.FIRST), Period(DAY, DAY, Half.SECOND))

    def test_the_same_half_twice_is_not(self):
        assert overlaps(Period(DAY, DAY, Half.FIRST), Period(DAY, DAY, Half.FIRST))

    def test_a_half_day_still_collides_with_a_full_day(self):
        assert overlaps(Period(DAY, DAY, Half.FIRST), Period(DAY, DAY))

    def test_a_half_day_collides_with_a_block_containing_it(self):
        assert overlaps(
            Period(DAY, DAY, Half.SECOND),
            Period(date(2026, 8, 28), date(2026, 9, 3)),
        )


class TestConflictReporting:
    def test_the_earliest_conflict_is_reported(self):
        existing = [
            Period(date(2026, 9, 10), date(2026, 9, 12)),
            Period(date(2026, 9, 2), date(2026, 9, 4)),
        ]
        hit = first_conflict(Period(date(2026, 9, 1), date(2026, 9, 30)), existing)
        assert hit.start == date(2026, 9, 2)

    def test_no_conflict_reports_nothing(self):
        assert first_conflict(Period(DAY, DAY), []) is None

    def test_a_period_cannot_end_before_it_starts(self):
        with pytest.raises(ValueError):
            Period(date(2026, 9, 5), date(2026, 9, 1))

    def test_a_half_day_cannot_span_dates(self):
        with pytest.raises(ValueError):
            Period(date(2026, 9, 1), date(2026, 9, 2), Half.FIRST)
