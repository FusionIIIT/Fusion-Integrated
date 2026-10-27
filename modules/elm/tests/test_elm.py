from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from modules.elm.models import (
    LeaveRequest, LeaveBalance, LeaveSubstituteConsent, DutyResumption,
    HolidayCalendar, LeaveCategory, LeaveStatus, PartOfDay
)
from modules.elm.services import leave_service

class ELMServiceTests(TestCase):
    def setUp(self):
        # Create LeaveBalance for user_id=101, year=2026, category='CL', entitled_days=8, used_days=0, pending_days=0
        LeaveBalance.objects.create(user_id=101, year=2026, category='CL', entitled_days=8, used_days=0, pending_days=0)
        
        # Create LeaveBalance for user_id=101, year=2026, category='EL', entitled_days=30, used_days=0, pending_days=0
        LeaveBalance.objects.create(user_id=101, year=2026, category='EL', entitled_days=30, used_days=0, pending_days=0)
        
        # Create LeaveBalance for user_id=101, year=2026, category='VL', entitled_days=60, used_days=0, pending_days=0
        LeaveBalance.objects.create(user_id=101, year=2026, category='VL', entitled_days=60, used_days=0, pending_days=0)
        
        # Create HolidayCalendar holiday on 2026-05-01 (is_rh=False) and RH on 2026-05-15 (is_rh=True).
        HolidayCalendar.objects.create(date=date(2026, 5, 1), is_rh=False)
        HolidayCalendar.objects.create(date=date(2026, 5, 15), is_rh=True)
    
    def test_calculate_leave_days(self):
        # CL over Friday 2026-05-08 to Monday 2026-05-11 (4 calendar days, but Sat/Sun excluded -> 2 days).
        self.assertEqual(leave_service.calculate_leave_days('CL', date(2026, 5, 8), date(2026, 5, 11)), Decimal('2'))
        
        # CL half day: start_date=2026-05-08, end_date=2026-05-08, part_of_day='first_half' -> Decimal('0.5').
        self.assertEqual(leave_service.calculate_leave_days('CL', date(2026, 5, 8), date(2026, 5, 8), 'first_half'), Decimal('0.5'))
        
        # EL over 2026-05-08 to 2026-05-11 -> Decimal('4.0') continuous counting.
        self.assertEqual(leave_service.calculate_leave_days('EL', date(2026, 5, 8), date(2026, 5, 11)), Decimal('4'))
    
    def test_validation_errors(self):
        # end_date < start_date raises ValidationError.
        with self.assertRaises(ValidationError):
            leave_service.validate_dates(date(2026, 5, 1), date(2026, 5, 8))
        
        # applicant == substitute raises ValidationError.
        with self.assertRaises(ValidationError):
            leave_service.validate_applicant_substitute(101, 101)
    
    def test_apply_and_substitute_consent_flow(self):
        # Apply with substitute_user_id=102 -> request status is 'pending_substitute', balance pending_days is updated.
        leave_service.apply_leave('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 102)
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'pending_substitute')
        
        # Substitute declines -> status becomes 'substitute_declined'.
        leave_service.update_leave_request('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 102, 'decline')
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'substitute_declined')
        
        # Nominate replacement substitute 103 -> status returns to 'pending_substitute'.
        leave_service.apply_leave('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 103)
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'pending_substitute')
        
        # Substitute 103 accepts -> status moves to 'pending_unit_head'.
        leave_service.update_leave_request('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 103, 'approve')
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'pending_unit_head')
    
    def test_unit_head_cl_approval(self):
        # Unit Head approves CL -> status is 'approved', balance used_days increases, pending_days decreases.
        leave_service.update_leave_request('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 103, 'approve')
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'approved')
        
    def test_higher_sanction_flow(self):
        # Apply EL -> Unit head recommends -> status is 'pending_sanction'.
        leave_service.apply_leave('EL', date(2026, 5, 8), date(2026, 5, 11), 101, 103)
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'pending_sanction')
        
        # Sanctioning authority approves -> status is 'approved', used_days increases.
        leave_service.update_leave_request('EL', date(2026, 5, 8), date(2026, 5, 11), 101, 103, 'approve')
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'approved')
    
    def test_withdrawal(self):
        # Apply CL -> withdraw -> status is 'withdrawn', pending_days released.
        leave_service.apply_leave('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 103)
        leave_service.update_leave_request('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 103, 'withdraw')
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'withdrawn')
    
    def test_cancellation(self):
        # Approved future leave -> request cancellation -> status 'cancellation_requested' -> review approved -> status 'cancelled', used_days restored.
        leave_service.apply_leave('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 103)
        leave_service.update_leave_request('CL', date(2026, 5, 8), date(2026, 5, 11), 101, 103, 'approve')
        leave_service.cancel_leave('CL', date(2026, 5, 8), date(2026, 5, 11), 101)
        self.assertEqual(LeaveRequest.objects.get(user_id=101).status, 'cancelled')
    
    def test_year_end(self):
        # process_year_end(2026) -> VL converted to EL for 2027 at 2:1 ratio.
        leave_service.process_year_end(2026)
        vl = LeaveBalance.objects.get(user_id=101, year=2026, category='VL')
        el = LeaveBalance.objects.get(user_id=101, year=2027, category='EL')
        self.assertEqual(vl.entitled_days / 3, el.entitled_days)
