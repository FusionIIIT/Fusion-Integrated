from datetime import date
from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from modules.elm.models import LeaveAccount, LeaveRequest
from modules.elm.services import validation as v


class DayCountTests(SimpleTestCase):
    def test_el_counts_weekends(self):
        # Mon 5 Oct to Sun 11 Oct 2026 = 7 days
        self.assertEqual(v.chargeable_days("EL", date(2026, 10, 5), date(2026, 10, 11)), 7)

    def test_cl_skips_weekends(self):
        self.assertEqual(v.chargeable_days("CL", date(2026, 10, 5), date(2026, 10, 11)), 5)

    def test_cl_skips_closed_holiday(self):
        closed = frozenset({date(2026, 10, 7)})
        self.assertEqual(
            v.chargeable_days("CL", date(2026, 10, 5), date(2026, 10, 9), closed_days=closed), 4)

    def test_half_day_cl(self):
        d = date(2026, 10, 6)
        self.assertEqual(v.chargeable_days("CL", d, d, half="first"), Decimal("0.5"))

    def test_half_day_rejected_for_el(self):
        d = date(2026, 10, 6)
        with self.assertRaises(v.LeaveValidationError):
            v.chargeable_days("EL", d, d, half="first")

    def test_end_before_start(self):
        with self.assertRaises(v.LeaveValidationError):
            v.chargeable_days("EL", date(2026, 10, 6), date(2026, 10, 5))


class OverlapRuleTests(SimpleTestCase):
    def test_different_halves_same_day_do_not_overlap(self):
        d = date(2026, 10, 6)
        self.assertFalse(v.ranges_overlap(d, d, "first", d, d, "second"))

    def test_same_half_overlaps(self):
        d = date(2026, 10, 6)
        self.assertTrue(v.ranges_overlap(d, d, "first", d, d, "first"))

    def test_half_inside_full_range_overlaps(self):
        d = date(2026, 10, 6)
        self.assertTrue(v.ranges_overlap(d, d, "first", date(2026, 10, 5), date(2026, 10, 8), ""))

    def test_disjoint(self):
        self.assertFalse(v.ranges_overlap(
            date(2026, 10, 1), date(2026, 10, 2), "", date(2026, 10, 3), date(2026, 10, 4), ""))


class DbRuleTests(TestCase):
    def _leave(self, user, start, end, half="", status="approved", leave_type="EL"):
        return LeaveRequest.objects.create(
            applicant_id=user, leave_type=leave_type, start_date=start, end_date=end,
            half=half, reason="x", status=status)

    def test_draft_does_not_block(self):
        self._leave(1, date(2026, 10, 5), date(2026, 10, 9), status="draft")
        v.check_no_overlap(1, date(2026, 10, 6), date(2026, 10, 7))

    def test_approved_blocks(self):
        self._leave(1, date(2026, 10, 5), date(2026, 10, 9))
        with self.assertRaises(v.LeaveValidationError):
            v.check_no_overlap(1, date(2026, 10, 6), date(2026, 10, 7))

    def test_modify_ignores_itself(self):
        r = self._leave(1, date(2026, 10, 5), date(2026, 10, 9))
        v.check_no_overlap(1, date(2026, 10, 5), date(2026, 10, 9), exclude_id=r.pk)

    def test_substitute_cannot_be_applicant(self):
        with self.assertRaises(v.LeaveValidationError):
            v.check_substitute(1, 1, date(2026, 10, 5), date(2026, 10, 9))

    def test_substitute_with_leave_rejected(self):
        self._leave(2, date(2026, 10, 6), date(2026, 10, 6))
        with self.assertRaises(v.LeaveValidationError):
            v.check_substitute(1, 2, date(2026, 10, 5), date(2026, 10, 9))

    def test_balance(self):
        LeaveAccount.objects.create(user_id=1, year=2026, leave_type="CL", balance=Decimal("1.5"))
        v.check_balance(1, 2026, "CL", Decimal("1.5"))
        with self.assertRaises(v.LeaveValidationError):
            v.check_balance(1, 2026, "CL", Decimal("2"))
