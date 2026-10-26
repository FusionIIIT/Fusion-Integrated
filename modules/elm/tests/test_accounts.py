from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.test import TestCase

from modules.elm.models import LeaveAccount, LeaveRequest, LeaveTransaction
from modules.elm.services import accounts as a
from modules.elm.services.policy import DEFAULT_PARAMS


class CreditTests(TestCase):
    def test_staff_gets_el_not_vl(self):
        a.credit_annual(1, 2026, "staff", DEFAULT_PARAMS)
        bal = {x.leave_type: x.balance for x in LeaveAccount.objects.filter(user_id=1)}
        self.assertEqual(bal, {"CL": 8, "RH": 2, "SCL": 15, "COL": 20, "EL": 30})

    def test_faculty_gets_vl_not_el(self):
        a.credit_annual(2, 2026, "faculty", DEFAULT_PARAMS)
        bal = {x.leave_type: x.balance for x in LeaveAccount.objects.filter(user_id=2)}
        self.assertEqual(bal, {"CL": 8, "RH": 2, "SCL": 15, "COL": 20, "VL": 60})

    def test_credit_is_idempotent(self):
        a.credit_annual(1, 2026, "staff", DEFAULT_PARAMS)
        again = a.credit_annual(1, 2026, "staff", DEFAULT_PARAMS)
        self.assertEqual(again, [])
        self.assertEqual(LeaveAccount.objects.get(user_id=1, leave_type="CL").balance, 8)


class DebitRestoreTests(TestCase):
    def setUp(self):
        a.credit_annual(1, 2026, "staff", DEFAULT_PARAMS)

    def _req(self, days, status="approved", leave_type="EL"):
        return LeaveRequest.objects.create(
            applicant_id=1, leave_type=leave_type, start_date=date(2026, 10, 5),
            end_date=date(2026, 10, 9), reason="x", days=Decimal(days), status=status)

    def test_debit_reduces_balance(self):
        a.debit_for_request(self._req(5))
        self.assertEqual(LeaveAccount.objects.get(user_id=1, leave_type="EL").balance, 25)

    def test_debit_requires_approved(self):
        with self.assertRaises(a.AccountError):
            a.debit_for_request(self._req(5, status="awaiting_final"))

    def test_double_debit_rejected(self):
        r = self._req(5)
        a.debit_for_request(r)
        with self.assertRaises(a.AccountError):
            a.debit_for_request(r)

    def test_insufficient_balance(self):
        with self.assertRaises(a.AccountError):
            a.debit_for_request(self._req(31))

    def test_early_resumption_restores_unused(self):
        r = self._req(5)
        a.debit_for_request(r)
        a.restore_unused(r, 2)
        self.assertEqual(LeaveAccount.objects.get(user_id=1, leave_type="EL").balance, 27)

    def test_cannot_restore_more_than_debited(self):
        r = self._req(5)
        a.debit_for_request(r)
        with self.assertRaises(a.AccountError):
            a.restore_unused(r, 6)

    def test_cancellation_reverses_everything(self):
        r = self._req(5)
        a.debit_for_request(r)
        a.reverse_for_request(r)
        self.assertEqual(LeaveAccount.objects.get(user_id=1, leave_type="EL").balance, 30)

    def test_ledger_sums_to_balance(self):
        r = self._req(5)
        a.debit_for_request(r)
        a.restore_unused(r, 2)
        acct = LeaveAccount.objects.get(user_id=1, leave_type="EL")
        total = LeaveTransaction.objects.filter(account=acct).aggregate(s=Sum("amount"))["s"]
        self.assertEqual(total, acct.balance)
