"""The ledger (BR-06, BR-13) and the manual adjustment path."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.elm.models import LeaveBalanceEntry
from modules.elm.selectors import queries
from modules.elm.services import balances as service
from modules.elm.tests.support import APPROVER_PERMS, principal

pytestmark = pytest.mark.django_db

YEAR = 2026


def stub_payroll(monkeypatch, *user_ids: int) -> None:
    """The directory projection, stubbed: these tests are about the ledger."""
    known = {uid: SimpleNamespace(user_id=uid, display_name=f"User {uid}")
             for uid in user_ids}
    monkeypatch.setattr(directory, "get_employees", lambda: list(known.values()))
    monkeypatch.setattr(directory, "get_users",
                        lambda ids: {i: known[i] for i in ids if i in known})


class TestAnnualGrant:

    def test_the_grant_is_recorded_once(self, make_type):
        leave_type = make_type()
        first = service.ensure_annual_grant(user_id=1001,
                                            leave_type=leave_type, year=YEAR)
        second = service.ensure_annual_grant(user_id=1001,
                                             leave_type=leave_type, year=YEAR)
        assert first is True
        assert second is False
        assert LeaveBalanceEntry.objects.filter(kind="grant").count() == 1

    def test_a_zero_entitlement_type_grants_nothing(self, make_type):
        leave_type = make_type(code="COL", name="Compensatory Off",
                               entitlement="0.0", allows_half_day=False,
                               requires_reason=True)
        assert service.ensure_annual_grant(user_id=1001,
                                           leave_type=leave_type, year=YEAR) is False
        assert not LeaveBalanceEntry.objects.exists()

    def test_the_accrual_covers_every_person_exactly_once(self, make_type,
                                                          monkeypatch):
        stub_payroll(monkeypatch, 1001, 1002)
        make_type()
        make_type(code="EL", name="Earned Leave", allows_half_day=False,
                  requires_reason=True)

        granted, already = service.grant_annual_leave(year=YEAR)
        assert (granted, already) == (4, 0)

        granted, already = service.grant_annual_leave(year=YEAR)
        assert (granted, already) == (0, 4)
        assert not LeaveBalanceEntry.objects.filter(user_id=9999).exists()


class TestAdjustments:

    def test_a_credit_needs_the_manage_permission(self, make_type,
                                                  monkeypatch):
        leave_type = make_type()
        stub_payroll(monkeypatch, 1001)
        approver = principal(user_id=2002, permissions=APPROVER_PERMS,
                             kind="faculty", roles=("Leave Approver",),
                             active_role="Leave Approver")
        with pytest.raises(PermissionDeniedError):
            service.adjust_balance(actor=approver, user_id=1001,
                                   leave_type_id=leave_type.pk, year=YEAR,
                                   days="1.0", note="Overtime")

    def test_a_credit_changes_the_available_balance(self, make_type,
                                                    administrator, monkeypatch):
        stub_payroll(monkeypatch, 1001)
        leave_type = make_type()
        service.adjust_balance(actor=administrator, user_id=1001,
                               leave_type_id=leave_type.pk, year=YEAR,
                               days=Decimal("2.0"),
                               note="Worked both weekend days")
        assert queries.available_days(1001, "CL", YEAR) == Decimal("2.0")

    def test_a_zero_day_adjustment_is_refused(self, make_type, administrator,
                                              monkeypatch):
        stub_payroll(monkeypatch, 1001)
        leave_type = make_type()
        with pytest.raises(ConflictError) as err:
            service.adjust_balance(actor=administrator, user_id=1001,
                                   leave_type_id=leave_type.pk, year=YEAR,
                                   days=0, note="Nothing")
        assert err.value.code == "zero_adjustment"

    def test_an_adjustment_without_a_note_is_refused(self, make_type,
                                                     administrator, monkeypatch):
        stub_payroll(monkeypatch, 1001)
        leave_type = make_type()
        with pytest.raises(ConflictError) as err:
            service.adjust_balance(actor=administrator, user_id=1001,
                                   leave_type_id=leave_type.pk, year=YEAR,
                                   days="1.0", note="   ")
        assert err.value.code == "adjustment_note_required"

    def test_an_unknown_person_is_refused(self, make_type, administrator,
                                          monkeypatch):
        stub_payroll(monkeypatch)
        leave_type = make_type()
        with pytest.raises(NotFoundError) as err:
            service.adjust_balance(actor=administrator, user_id=424242,
                                   leave_type_id=leave_type.pk, year=YEAR,
                                   days="1.0", note="Ghost")
        assert err.value.code == "person_not_found"

    def test_an_unknown_type_is_refused(self, administrator, monkeypatch):
        stub_payroll(monkeypatch, 1001)
        with pytest.raises(NotFoundError) as err:
            service.adjust_balance(actor=administrator, user_id=1001,
                                   leave_type_id=9999, year=YEAR,
                                   days="1.0", note="Typo")
        assert err.value.code == "leave_type_not_found"


class TestReadingTheLedger:

    def test_entitled_used_and_available_read_from_the_rows(self, make_type):
        leave_type = make_type()
        service.ensure_annual_grant(user_id=1001, leave_type=leave_type, year=YEAR)
        LeaveBalanceEntry.objects.create(user_id=1001, leave_type=leave_type,
                                         year=YEAR, kind="debit", days=Decimal("-3.0"))
        LeaveBalanceEntry.objects.create(user_id=1001, leave_type=leave_type,
                                         year=YEAR, kind="reversal", days=Decimal("1.0"))
        row = queries.balances_for(1001, YEAR)[0]
        assert (row.entitled, row.used, row.available) == (
            Decimal("8.0"), Decimal("2.0"), Decimal("6.0"))
