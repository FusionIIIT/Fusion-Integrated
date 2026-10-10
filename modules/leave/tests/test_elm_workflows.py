from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase

from ..models import (
    LeaveCategory, ApplicationStatus, SubstituteStatus, HalfDayType,
    LeavePolicy, LeaveBalance, LeaveApplication, HolidayCalendar
)
from ..services import ELMService, LeaveValidationError


class ELMWorkflowTestCase(TestCase):
    def setUp(self):
        # Create Leave Policies
        LeavePolicy.objects.create(category=LeaveCategory.CL, annual_entitlement=8, allows_half_day=True, is_continuous_counting=False)
        LeavePolicy.objects.create(category=LeaveCategory.RH, annual_entitlement=2, allows_half_day=False, is_continuous_counting=False)
        LeavePolicy.objects.create(category=LeaveCategory.EL, annual_entitlement=30, allows_half_day=False, is_continuous_counting=True, allows_carry_forward=True)
        LeavePolicy.objects.create(category=LeaveCategory.VL, annual_entitlement=60, allows_half_day=False, is_continuous_counting=True, faculty_only=True)

        # Allocate initial balances for test user 2026
        LeaveBalance.objects.create(user_id="EMP101", username="Dr. Smith", user_category="FACULTY", category=LeaveCategory.CL, balance=8.0, year=2026)
        LeaveBalance.objects.create(user_id="EMP101", username="Dr. Smith", user_category="FACULTY", category=LeaveCategory.EL, balance=30.0, year=2026)
        LeaveBalance.objects.create(user_id="EMP101", username="Dr. Smith", user_category="FACULTY", category=LeaveCategory.VL, balance=10.0, year=2026)
        LeaveBalance.objects.create(user_id="EMP102", username="Prof. Jones", user_category="FACULTY", category=LeaveCategory.CL, balance=8.0, year=2026)

    def test_bw_el_01_casual_leave_no_substitute_unit_head_approve(self):
        """BW-EL-01: Apply CL (No substitute) -> Unit Head Approve"""
        start = date(2026, 10, 12) # Monday
        end = date(2026, 10, 13) # Tuesday

        app = ELMService.apply_for_leave(
            applicant_id="EMP101",
            applicant_name="Dr. Smith",
            applicant_category="FACULTY",
            applicant_role="EMPLOYEE",
            department="CSE",
            category=LeaveCategory.CL,
            start_date=start,
            end_date=end,
            purpose="Personal work"
        )

        self.assertEqual(app.status, ApplicationStatus.AWAITING_UNIT_HEAD)
        self.assertEqual(app.requested_days, Decimal("2.0"))

        # Unit Head Approves
        updated_app = ELMService.review_unit_head("UH001", "HOD CSE", app.id, "APPROVE", "Approved.")
        self.assertEqual(updated_app.status, ApplicationStatus.APPROVED)

        # Check Balance (8.0 - 2.0 = 6.0)
        bal = LeaveBalance.objects.get(user_id="EMP101", category=LeaveCategory.CL, year=2026)
        self.assertEqual(bal.balance, Decimal("6.0"))
        self.assertEqual(bal.availed, Decimal("2.0"))

    def test_bw_el_02_and_03_substitute_decline_and_replacement_loop(self):
        """BW-EL-02 & 03: Substitute decline -> Nominate replacement -> Accept -> Unit Head Approve"""
        start = date(2026, 10, 14)
        end = date(2026, 10, 15)

        app = ELMService.apply_for_leave(
            applicant_id="EMP101",
            applicant_name="Dr. Smith",
            applicant_category="FACULTY",
            applicant_role="EMPLOYEE",
            department="CSE",
            category=LeaveCategory.CL,
            start_date=start,
            end_date=end,
            purpose="Conference",
            substitute_id="EMP102",
            substitute_name="Prof. Jones"
        )

        self.assertEqual(app.status, ApplicationStatus.AWAITING_SUBSTITUTE)
        self.assertEqual(app.substitute_status, SubstituteStatus.AWAITING_RESPONSE)

        # Substitute Declines
        app_declined = ELMService.respond_to_substitute_request("EMP102", app.id, "DECLINE", "Busy with lectures.")
        self.assertEqual(app_declined.status, ApplicationStatus.APPLICANT_ACTION_REQUIRED)

        # Applicant Nominates Replacement (UC-019)
        app_replaced = ELMService.nominate_replacement_substitute("EMP101", app.id, "EMP103", "Dr. Alan")
        self.assertEqual(app_replaced.status, ApplicationStatus.AWAITING_SUBSTITUTE)
        self.assertEqual(app_replaced.substitute_name, "Dr. Alan")

        # Replacement Accepts
        app_accepted = ELMService.respond_to_substitute_request("EMP103", app.id, "ACCEPT", "Glad to help.")
        self.assertEqual(app_accepted.status, ApplicationStatus.AWAITING_UNIT_HEAD)

    def test_bw_el_05_higher_sanction_leave_full_chain(self):
        """BW-EL-05: EL application -> Substitute Accept -> Unit Head Recommend -> Establishment -> Final Sanction"""
        start = date(2026, 11, 2) # Monday
        end = date(2026, 11, 6) # Friday (5 continuous days)

        app = ELMService.apply_for_leave(
            applicant_id="EMP101",
            applicant_name="Dr. Smith",
            applicant_category="FACULTY",
            applicant_role="EMPLOYEE",
            department="CSE",
            category=LeaveCategory.EL,
            start_date=start,
            end_date=end,
            purpose="Research Workshop",
            substitute_id="EMP102",
            substitute_name="Prof. Jones"
        )

        # 1. Substitute Accept
        ELMService.respond_to_substitute_request("EMP102", app.id, "ACCEPT")
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.AWAITING_UNIT_HEAD)

        # 2. Unit Head Recommend
        ELMService.review_unit_head("UH001", "HOD CSE", app.id, "RECOMMENDED", "Strongly recommended.")
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.AWAITING_ESTABLISHMENT)

        # 3. Establishment Verification
        ELMService.verify_establishment("EST001", "DR Establishment", app.id, "Verified eligibility.")
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.AWAITING_FINAL_SANCTION)

        # 4. Final Sanction Decision (Dean/Registrar)
        ELMService.make_final_sanction_decision("DEAN01", "Dean Academics", "DEAN", app.id, "APPROVE", "Sanctioned.")
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.APPROVED)

        # Check EL balance (30 - 5 = 25)
        bal = LeaveBalance.objects.get(user_id="EMP101", category=LeaveCategory.EL, year=2026)
        self.assertEqual(bal.balance, Decimal("25.0"))

    def test_pending_withdrawal_releases_balance(self):
        """CW-EL-01: Withdraw pending request -> restores pending balance"""
        start = date(2026, 10, 20)
        end = date(2026, 10, 21)

        app = ELMService.apply_for_leave(
            applicant_id="EMP101",
            applicant_name="Dr. Smith",
            applicant_category="FACULTY",
            applicant_role="EMPLOYEE",
            department="CSE",
            category=LeaveCategory.CL,
            start_date=start,
            end_date=end,
            purpose="Personal"
        )

        bal_pending = LeaveBalance.objects.get(user_id="EMP101", category=LeaveCategory.CL, year=2026)
        self.assertEqual(bal_pending.pending, Decimal("2.0"))

        # Withdraw
        ELMService.withdraw_pending_request("EMP101", app.id)
        app.refresh_from_db()
        self.assertEqual(app.status, ApplicationStatus.WITHDRAWN)

        bal_after = LeaveBalance.objects.get(user_id="EMP101", category=LeaveCategory.CL, year=2026)
        self.assertEqual(bal_after.pending, Decimal("0.0"))

    def test_year_end_faculty_vl_conversion(self):
        """UC-020: Year-end processing converts 10 VL to 5 EL (2:1 ratio)"""
        ELMService.execute_year_end_processing(2026)

        # VL balance set to 0 in 2026
        vl_bal = LeaveBalance.objects.get(user_id="EMP101", category=LeaveCategory.VL, year=2026)
        self.assertEqual(vl_bal.balance, Decimal("0.0"))

        # EL credited in 2027 (30.0 carried forward EL + 5.0 converted VL = 35.0 days)
        el_2027 = LeaveBalance.objects.get(user_id="EMP101", category=LeaveCategory.EL, year=2027)
        self.assertEqual(el_2027.balance, Decimal("35.0"))
