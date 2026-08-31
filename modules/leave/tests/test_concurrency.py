"""Two transactions at once, actually run at once.

Every claim about a lock elsewhere in this module is proved sequentially: do a
thing, do it again, see the refusal. That proves the check exists, not that it
holds when two workers reach it together -- and "the second caller reads the
balance before the first has written it" is exactly the case a sequential test
cannot produce.

These use real threads and real connections, so `transaction=True`: the usual
per-test transaction would hide every thread's writes from every other and the
tests would pass without touching the thing they are about.
"""
from __future__ import annotations

import threading
from datetime import date
from decimal import Decimal as D

import pytest
from django.db import close_old_connections, connection

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.models import EntryReason, LedgerEntry, YearEndClosure
from modules.leave.selectors import balances
from modules.leave.services import decisions, yearend
from modules.leave.services import requests as service
from modules.leave.tests import factories
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db(transaction=True)

U = 701


def in_parallel(*callables):
    """Run each callable in its own thread, released together.

    The barrier is what makes this a race rather than two sequential calls that
    happen to be on different threads.
    """
    gate = threading.Barrier(len(callables))
    outcomes: list = [None] * len(callables)

    def run(index, fn):
        try:
            gate.wait(timeout=10)
            outcomes[index] = ("ok", fn())
        except BaseException as exc:            # noqa: BLE001 - reported, not swallowed
            outcomes[index] = ("raised", exc)
        finally:
            close_old_connections()
            connection.close()

    threads = [
        threading.Thread(target=run, args=(i, fn)) for i, fn in enumerate(callables)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), "a thread did not finish — suspected deadlock"
    return outcomes


def kinds(outcomes):
    return [o[0] for o in outcomes]


def raised(outcomes):
    return [o[1] for o in outcomes if o[0] == "raised"]


class TestClosingAYearTwiceAtOnce:
    def test_exactly_one_close_succeeds(self):
        factories.make_policy()
        factories.credit(U, Category.EL, 10)

        outcomes = in_parallel(
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False),
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False),
        )

        assert sorted(kinds(outcomes)) == ["ok", "raised"]

    def test_the_loser_is_told_why(self):
        factories.make_policy()
        factories.credit(U, Category.EL, 10)

        outcomes = in_parallel(
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False),
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False),
        )

        assert all(isinstance(e, ConflictError) for e in raised(outcomes))

    def test_the_opening_balance_is_carried_once(self):
        factories.make_policy()
        factories.credit(U, Category.EL, 10)

        in_parallel(
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False),
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False),
        )

        # Sequentially this produced 20 before the closure record existed.
        assert balances.balance_for(U, YEAR + 1, Category.EL).available == D(10)

    def test_only_one_closure_record_exists(self):
        factories.make_policy()
        factories.credit(U, Category.EL, 10)

        in_parallel(
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False),
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False),
        )

        assert YearEndClosure.objects.filter(user_id=U, year=YEAR).count() == 1

    def test_three_at_once_still_close_once(self):
        factories.make_policy()
        factories.credit(U, Category.EL, 10)

        outcomes = in_parallel(*[
            lambda: yearend.close(user_id=U, year=YEAR, faculty=False)
            for _ in range(3)
        ])

        assert kinds(outcomes).count("ok") == 1
        assert balances.balance_for(U, YEAR + 1, Category.EL).available == D(10)


class TestCreditingTwiceAtOnce:
    def test_the_entitlement_is_credited_once(self):
        factories.make_policy()

        in_parallel(
            lambda: yearend.credit_year(user_id=U, year=YEAR, faculty=False),
            lambda: yearend.credit_year(user_id=U, year=YEAR, faculty=False),
        )

        assert balances.balance_for(U, YEAR, Category.CL).available == D(8)

    def test_no_category_is_credited_twice(self):
        factories.make_policy()

        in_parallel(
            lambda: yearend.credit_year(user_id=U, year=YEAR, faculty=False),
            lambda: yearend.credit_year(user_id=U, year=YEAR, faculty=False),
        )

        rows = LedgerEntry.objects.filter(
            user_id=U, year=YEAR, reason=EntryReason.ANNUAL_CREDIT)
        categories = [r.category for r in rows]
        assert len(categories) == len(set(categories)), categories


class TestApprovingTwoRequestsAtOnce:
    """The case the sequential test cannot make: both read the balance before
    either has written to it."""

    def _two_pending(self, available: int, each_days: int):
        factories.setup_all(999)
        LedgerEntry.objects.filter(user_id=U).delete()
        factories.credit(U, Category.CL, available)
        starts = (date(YEAR, 3, 2), date(YEAR, 3, 16))
        return [
            service.submit(
                user_id=U, category=Category.CL, starts_on=s,
                ends_on=date(s.year, s.month, s.day + each_days - 1),
                reason="x", unit="CSE", faculty=False,
                designations=frozenset({"Assistant Professor"}))
            for s in starts
        ]

    def test_only_one_approval_gets_through(self):
        first, second = self._two_pending(available=2, each_days=2)

        outcomes = in_parallel(
            lambda: decisions.unit_head_decides(
                request=first, actor_user_id=900, approve=True),
            lambda: decisions.unit_head_decides(
                request=second, actor_user_id=900, approve=True),
        )

        assert kinds(outcomes).count("ok") == 1, [str(e) for e in raised(outcomes)]

    def test_the_balance_is_never_left_negative(self):
        first, second = self._two_pending(available=2, each_days=2)

        in_parallel(
            lambda: decisions.unit_head_decides(
                request=first, actor_user_id=900, approve=True),
            lambda: decisions.unit_head_decides(
                request=second, actor_user_id=900, approve=True),
        )

        assert balances.balance_for(U, YEAR, Category.CL).available >= D(0)

    def test_both_get_through_when_the_balance_covers_both(self):
        first, second = self._two_pending(available=8, each_days=2)

        outcomes = in_parallel(
            lambda: decisions.unit_head_decides(
                request=first, actor_user_id=900, approve=True),
            lambda: decisions.unit_head_decides(
                request=second, actor_user_id=900, approve=True),
        )

        assert kinds(outcomes) == ["ok", "ok"]
        assert balances.balance_for(U, YEAR, Category.CL).available == D(4)

    def test_three_at_once_against_a_balance_for_two(self):
        factories.setup_all(999)
        LedgerEntry.objects.filter(user_id=U).delete()
        factories.credit(U, Category.CL, 4)
        pending = [
            service.submit(
                user_id=U, category=Category.CL, starts_on=date(YEAR, 3, d),
                ends_on=date(YEAR, 3, d + 1), reason="x", unit="CSE", faculty=False,
                designations=frozenset({"Assistant Professor"}))
            for d in (2, 16, 23)
        ]

        outcomes = in_parallel(*[
            (lambda r=r: decisions.unit_head_decides(
                request=r, actor_user_id=900, approve=True))
            for r in pending
        ])

        assert kinds(outcomes).count("ok") == 2
        assert balances.balance_for(U, YEAR, Category.CL).available == D(0)


def test_the_database_itself_refuses_a_second_annual_credit():
    """Not the service's read, the constraint.

    The service still checks first, because the common case should not cost an
    exception. But the check is a courtesy and the constraint is the guarantee.
    """
    from django.db import IntegrityError

    factories.make_policy()
    factories.credit(U, Category.CL, 8)

    with pytest.raises(IntegrityError):
        LedgerEntry.objects.create(
            user_id=U, year=YEAR, category=Category.CL.value, days=D(8),
            reason=EntryReason.ANNUAL_CREDIT)


def test_a_correction_against_a_credited_category_is_still_allowed():
    """The constraint is scoped to ANNUAL_CREDIT, so the ledger stays append-only.

    A blanket unique constraint would have made reversing a credit impossible,
    which is the one thing the ledger exists to allow.
    """
    factories.make_policy()
    factories.credit(U, Category.CL, 8)
    original = LedgerEntry.objects.get(
        user_id=U, year=YEAR, category=Category.CL.value)

    LedgerEntry.objects.create(
        user_id=U, year=YEAR, category=Category.CL.value, days=D(-8),
        reason=EntryReason.CORRECTION, reverses_id=original.pk)

    assert balances.balance_for(U, YEAR, Category.CL).available == D(0)


def test_consuming_the_same_category_twice_is_still_allowed():
    factories.make_policy()
    factories.credit(U, Category.CL, 8)

    for _ in range(2):
        LedgerEntry.objects.create(
            user_id=U, year=YEAR, category=Category.CL.value, days=D(-2),
            reason=EntryReason.CONSUMED)

    assert balances.balance_for(U, YEAR, Category.CL).available == D(4)
