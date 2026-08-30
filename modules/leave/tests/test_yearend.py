"""Closing a year: lapse, carry-forward and the vacation conversion."""
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.models import EntryReason, LedgerEntry
from modules.leave.selectors import balances
from modules.leave.services import yearend
from modules.leave.tests.factories import credit, make_calendar, make_policy

pytestmark = pytest.mark.django_db

STAFF, FACULTY = 501, 502
D = Decimal


@pytest.fixture
def configured():
    policy = make_policy()
    make_calendar()
    make_calendar(2027)
    return policy


def consume(user_id, category, days, year=2026):
    LedgerEntry.objects.create(
        user_id=user_id, year=year, category=category.value, days=-D(days),
        reason=EntryReason.CONSUMED,
    )


class TestCredit:
    def test_a_new_year_is_credited_from_policy(self, configured):
        written = yearend.credit_year(user_id=STAFF, year=2026, faculty=False)
        assert written > 0
        assert balances.available(STAFF, 2026, Category.CL) == D(8)
        assert balances.available(STAFF, 2026, Category.EL) == D(30)

    def test_faculty_are_credited_vacation_not_earned_leave(self, configured):
        yearend.credit_year(user_id=FACULTY, year=2026, faculty=True)
        assert balances.available(FACULTY, 2026, Category.VL) == D(60)
        assert balances.available(FACULTY, 2026, Category.EL) == D(0)

    def test_crediting_twice_does_not_double(self, configured):
        yearend.credit_year(user_id=STAFF, year=2026, faculty=False)
        second = yearend.credit_year(user_id=STAFF, year=2026, faculty=False)
        assert second == 0
        assert balances.available(STAFF, 2026, Category.CL) == D(8)


class TestClosing:
    def test_casual_leave_lapses_and_earned_leave_carries(self, configured):
        credit(STAFF, Category.CL, 8)
        credit(STAFF, Category.EL, 30)
        consume(STAFF, Category.CL, 5)
        consume(STAFF, Category.EL, 10)

        moved = yearend.close(user_id=STAFF, year=2026, faculty=False)
        assert moved["lapsed"] == D(3)
        assert balances.available(STAFF, 2027, Category.EL) == D(20)
        assert balances.available(STAFF, 2027, Category.CL) == D(0)

    def test_unused_vacation_becomes_earned_leave(self, configured):
        credit(FACULTY, Category.VL, 60)
        consume(FACULTY, Category.VL, 45)

        moved = yearend.close(user_id=FACULTY, year=2026, faculty=True)
        assert moved["converted_vl"] == D(15)
        assert moved["el_from_conversion"] == D("7.50")
        # BR-EL-026 aside, the converted leave is usable the next year.
        assert balances.available(FACULTY, 2027, Category.EL) == D("7.50")
        assert balances.available(FACULTY, 2027, Category.VL) == D(0)

    def test_the_conversion_leaves_a_trail_on_both_sides(self, configured):
        credit(FACULTY, Category.VL, 60)
        consume(FACULTY, Category.VL, 50)
        yearend.close(user_id=FACULTY, year=2026, faculty=True)

        out = [
            e for e in balances.statement(FACULTY, 2026, Category.VL)
            if e.reason == EntryReason.CONVERTED_OUT
        ]
        into = [
            e for e in balances.statement(FACULTY, 2026, Category.EL)
            if e.reason == EntryReason.CONVERTED_IN
        ]
        assert out[0].days == D(-10)
        assert into[0].days == D(5)
        assert "2 VL to 1 EL" in out[0].note

    def test_a_year_cannot_be_closed_twice(self, configured):
        credit(STAFF, Category.CL, 8)
        yearend.close(user_id=STAFF, year=2026, faculty=False)
        with pytest.raises(ConflictError) as exc:
            yearend.close(user_id=STAFF, year=2026, faculty=False)
        assert exc.value.code == "year_already_closed"

    def test_every_closing_row_names_the_policy_it_used(self, configured):
        credit(STAFF, Category.CL, 8)
        yearend.close(user_id=STAFF, year=2026, faculty=False)
        closing = LedgerEntry.objects.filter(
            user_id=STAFF, reason__in=[EntryReason.LAPSED, EntryReason.OPENING_BALANCE]
        )
        assert closing.exists()
        assert all(e.policy_id is not None for e in closing)
