"""The year-end run across everyone, and the rehearsal that writes nothing."""
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.directory.models import UserRef
from modules.leave.domain.categories import Category
from modules.leave.models import EntryReason, LedgerEntry
from modules.leave.selectors import balances
from modules.leave.tests import factories

pytestmark = pytest.mark.django_db

D = Decimal
FACULTY = 501
STAFF = 502
YEAR = factories.YEAR


@pytest.fixture
def accounts():
    factories.make_policy()
    for uid, kind in ((FACULTY, "faculty"), (STAFF, "staff")):
        UserRef.objects.create(
            user_id=uid, username=f"u{uid}", display_name=f"User {uid}",
            kind=kind, department="CSE")
    # Faculty carry vacation leave and convert what they do not use.
    factories.credit(FACULTY, Category.VL, 60)
    factories.credit(FACULTY, Category.CL, 8)
    factories.credit(STAFF, Category.CL, 8)
    factories.credit(STAFF, Category.EL, 30)


def run(*args) -> str:
    out = StringIO()
    call_command("leave_year_end", *args, stdout=out, stderr=StringIO())
    return out.getvalue()


def test_it_closes_every_account_that_has_entries(accounts):
    output = run(str(YEAR))

    assert "closed      2" in output
    assert f"{YEAR} closed" in output


def test_unused_casual_leave_lapses(accounts):
    run(str(YEAR))

    assert balances.balance_for(STAFF, YEAR, Category.CL).available == D(0)


def test_earned_leave_carries_into_the_next_year(accounts):
    run(str(YEAR))

    assert balances.balance_for(STAFF, YEAR + 1, Category.EL).available == D(30)


def test_faculty_vacation_converts_to_earned_leave(accounts):
    run(str(YEAR))

    entries = LedgerEntry.objects.filter(
        user_id=FACULTY, reason=EntryReason.CONVERTED_IN)
    assert entries.count() == 1
    # 60 VL at the policy's 2:1 ratio.
    assert entries.get().days == D(30)


def test_staff_get_no_conversion(accounts):
    run(str(YEAR))

    assert not LedgerEntry.objects.filter(
        user_id=STAFF, reason=EntryReason.CONVERTED_IN).exists()


def test_a_dry_run_writes_nothing(accounts):
    before = LedgerEntry.objects.count()

    output = run(str(YEAR), "--dry-run")

    assert "nothing was written" in output
    assert LedgerEntry.objects.count() == before


def test_running_twice_skips_rather_than_settling_twice(accounts):
    run(str(YEAR))
    after_first = LedgerEntry.objects.count()

    output = run(str(YEAR))

    assert "skipped     2" in output
    assert LedgerEntry.objects.count() == after_first


def test_one_employee_can_be_re_run_alone(accounts):
    output = run(str(YEAR), "--user", str(STAFF))

    assert "closed      1" in output
    assert not LedgerEntry.objects.filter(
        user_id=FACULTY, reason=EntryReason.CONVERTED_OUT).exists()


def test_crediting_the_next_year_is_opt_in(accounts):
    run(str(YEAR), "--credit-next")

    credited = LedgerEntry.objects.filter(
        user_id=STAFF, year=YEAR + 1, reason=EntryReason.ANNUAL_CREDIT)
    assert credited.filter(category=Category.CL.value).get().days == D(8)


def test_a_year_with_no_accounts_is_an_error_not_a_silent_success(accounts):
    with pytest.raises(CommandError, match="No leave accounts"):
        run("1999")


class TestItRefusesToGuessWhoIsFaculty:
    """The classification decides what is destroyed.

    Faculty vacation converts to earned leave; everybody else's lapses. The
    command read the flag with a default of False, so an employee the directory
    failed to return had up to sixty days lapsed instead of converted -- during
    the one operation that cannot be undone -- and --credit-next would then have
    granted them the wrong entitlement for the new year on top.
    """

    def test_an_unclassified_employee_stops_the_run(self, accounts, stub_iam):
        # The directory no longer knows one of the people holding a leave account.
        UserRef.objects.filter(user_id=FACULTY).delete()

        with pytest.raises(CommandError, match="could not be classified"):
            run(str(YEAR))

    def test_it_names_who_is_missing(self, accounts, stub_iam):
        UserRef.objects.filter(user_id=FACULTY).delete()

        with pytest.raises(CommandError, match=str(FACULTY)):
            run(str(YEAR))

    def test_nothing_is_written_when_it_refuses(self, accounts, stub_iam):
        UserRef.objects.filter(user_id=FACULTY).delete()
        before = LedgerEntry.objects.count()

        with pytest.raises(CommandError):
            run(str(YEAR))

        assert LedgerEntry.objects.count() == before

    def test_naming_only_the_known_employees_still_works(self, accounts, stub_iam):
        UserRef.objects.filter(user_id=FACULTY).delete()

        output = run(str(YEAR), "--user", str(STAFF))

        assert "closed      1" in output

    def test_a_faculty_member_the_directory_knows_still_converts(self, accounts):
        run(str(YEAR))

        # The guard must not have made the ordinary case stricter.
        assert LedgerEntry.objects.filter(
            user_id=FACULTY, reason=EntryReason.CONVERTED_IN).exists()
