"""A module that cannot work does not appear."""
from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from modules.accesscontrol.models import Module
from modules.directory.models import UserRef
from modules.leave.models import AuthorityRule
from modules.leave.registry import readiness
from modules.leave.tests import factories

pytestmark = pytest.mark.django_db


def fully_ready():
    policy = factories.make_policy()
    factories.make_calendar(date.today().year)
    factories.make_authority(policy)
    UserRef.objects.create(user_id=501, username="u501", display_name="U",
                           kind="staff", department="CSE")
    factories.credit(501, __import__(
        "modules.leave.domain.categories", fromlist=["Category"]).Category.CL,
        8, year=date.today().year)
    return policy


def seed() -> str:
    out = StringIO()
    call_command("seed_modules", stdout=out)
    return out.getvalue()


class TestAFreshInstall:
    def test_nothing_is_ready(self):
        assert readiness() != []

    def test_it_says_the_policy_first_because_nothing_else_matters_without_one(self):
        # A missing policy explains everything else, so it is reported alone.
        assert len(readiness()) == 1
        assert "no leave policy is published" in readiness()[0]

    def test_the_module_is_registered_but_not_active(self):
        seed()

        assert Module.objects.get(code="leave").status == "planned"

    def test_seeding_says_why(self):
        output = seed()

        assert "NOT active" in output
        assert "seed_leave_policy" in output


class TestEachPrerequisite:
    def test_a_policy_without_authority_rules_is_not_ready(self):
        fully_ready()
        AuthorityRule.objects.all().delete()

        assert any("no authority rules" in r for r in readiness())

    def test_an_empty_directory_is_not_ready(self):
        fully_ready()
        UserRef.objects.all().delete()

        assert any("directory is empty" in r for r in readiness())

    def test_an_uncredited_year_is_not_ready(self):
        from modules.leave.models import EntryReason, LedgerEntry

        fully_ready()
        LedgerEntry.objects.filter(reason=EntryReason.ANNUAL_CREDIT).delete()

        # Otherwise every application fails for balance, which looks like a bug.
        assert any("entitlement" in r for r in readiness())

    def test_a_missing_calendar_for_this_year_is_not_ready(self):
        from modules.leave.models import HolidayCalendar

        fully_ready()
        HolidayCalendar.objects.update(published=False)

        assert any("holiday calendar" in r for r in readiness())


class TestOnceEverythingIsInPlace:
    def test_readiness_is_clear(self):
        fully_ready()

        assert readiness() == []

    def test_the_module_becomes_active(self):
        fully_ready()

        seed()

        assert Module.objects.get(code="leave").status == "active"

    def test_the_command_reports_it(self):
        fully_ready()
        seed()
        out = StringIO()

        call_command("leave_readiness", stdout=out)

        assert "ready and registered as active" in out.getvalue()

    def test_the_deploy_gate_exits_non_zero_when_it_is_not(self):
        out = StringIO()

        with pytest.raises(SystemExit):
            call_command("leave_readiness", "--fail", stdout=out)
