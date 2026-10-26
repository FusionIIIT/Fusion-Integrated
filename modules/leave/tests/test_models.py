import datetime
from decimal import Decimal
from django.test import TestCase
from modules.leave.models import (
    LeaveBalance,
    LeaveApplication,
    ApplicationStatus,
    LeaveCategory,
)
from modules.leave.domain.rules import (
    count_leave_days,
    get_category_entitlement,
    can_take_half_day,
    carries_forward,
)


class LeaveDomainRulesTest(TestCase):
    def test_count_leave_days(self):
        d1 = datetime.date(2026, 10, 1)  # Thursday
        d2 = datetime.date(2026, 10, 5)  # Monday
        # EL counts continuous days including weekend: 5 days
        self.assertEqual(count_leave_days(d1, d2, category="EL"), Decimal("5"))
        # CL excludes weekend (Sat, Sun): Oct 1, Oct 2, Oct 5 = 3 days
        self.assertEqual(count_leave_days(d1, d2, category="CL"), Decimal("3"))

    def test_half_day_cl(self):
        d1 = datetime.date(2026, 10, 1)
        self.assertEqual(count_leave_days(d1, d1, half_day=True), Decimal("0.5"))
        self.assertTrue(can_take_half_day("CL"))
        self.assertFalse(can_take_half_day("EL"))

    def test_category_entitlements(self):
        cl = get_category_entitlement("CL", "faculty")
        self.assertEqual(cl["days_per_year"], 8)
        self.assertFalse(carries_forward("CL"))
        self.assertTrue(carries_forward("EL"))
        # Test BR-EL-006 & BR-EL-009
        col = get_category_entitlement("COL", "staff")
        self.assertEqual(col["days_per_year"], 20)
        vl = get_category_entitlement("VL", "faculty")
        self.assertEqual(vl["days_per_year"], 60)

    def test_year_end_faculty_vl_conversion(self):
        from modules.leave.domain.rules import year_end_process
        balances = [
            {"category": "VL", "balance_days": Decimal("15.0")},
            {"category": "CL", "balance_days": Decimal("2.0")},
        ]
        adjustments = year_end_process(user_id=101, year="2026", balances=balances, employee_kind="faculty")
        vl_adj = next(a for a in adjustments if a["category"] == "VL")
        self.assertEqual(vl_adj["action"], "convert_to_el")
        self.assertEqual(vl_adj["credited_el"], Decimal("7.5"))
        cl_adj = next(a for a in adjustments if a["category"] == "CL")
        self.assertEqual(cl_adj["action"], "lapse")


class LeaveModelTest(TestCase):
    def test_create_leave_balance(self):
        lb = LeaveBalance.objects.create(
            user_id=101,
            category=LeaveCategory.CL,
            balance_days=Decimal("8.0"),
            year="2026",
        )
        self.assertEqual(lb.balance_days, Decimal("8.0"))
        self.assertEqual(str(lb), "u101 CL: 8.0 (2026)")

    def test_create_leave_application(self):
        app = LeaveApplication.objects.create(
            user_id=101,
            category=LeaveCategory.CL,
            start_date=datetime.date(2026, 10, 1),
            end_date=datetime.date(2026, 10, 2),
            reason="Family emergency",
            status=ApplicationStatus.PENDING,
        )
        self.assertEqual(app.status, ApplicationStatus.PENDING)
        self.assertEqual(app.days_requested, Decimal("2"))
