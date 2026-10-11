from __future__ import annotations

from datetime import datetime

from django.db.models import Q, Sum
from core.db.mixins import UserScopedModel
from modules.elm.models import Leave, CasualLeave, RestrictedHoliday, SpecialCasualLeave, \
    NonFacultyEarnedLeave, FacultyVacationLeave, VLToELConversion, CommutedLeave, HalfDayCL, StationLeave, Substitute, PendingRequestWithdrawal, \
    ApprovedLeaveCancellation

def get_user_leave_balance(user):
    # BR-EL-001: Supported leave-category eligibility
    casual_leaves = CasualLeave.objects.filter(user_id=user).aggregate(total_days=Sum('days'))
    restricted_holidays = RestrictedHoliday.objects.filter(date__year=datetime.now().year).count()
    special_casual_leaves = SpecialCasualLeave.objects.filter(user_id=user).aggregate(total_days=Sum('days'))
    non_faculty_earned_leaves = NonFacultyEarnedLeave.objects.filter(user_id=user).aggregate(total_days=Sum('days'))
    faculty_vacation_leaves = FacultyVacationLeave.objects.filter(user_id=user).aggregate(total_days=Sum('days'))

    # BR-EL-002: Casual Leave entitlement and lapse
    casual_leave_entitlement = 8.0

    # BR-EL-003: Restricted Holiday entitlement and applicability
    restricted_holiday_entitlement = restricted_holidays

    # BR-EL-004: Special Casual Leave entitlement and admissibility
    special_casual_leave_entitlement = special_casual_leaves['total_days'] if special_casual_leaves else 0.0

    # BR-EL-005: Non-faculty Earned Leave credit and carry-forward
    non_faculty_earned_leave_entitlement = non_faculty_earned_leaves['total_days'] if non_faculty_earned_leaves else 0.0

    # BR-EL-006: Faculty Vacation Leave entitlement and vacation-period applicability
    faculty_vacation_leave_entitlement = faculty_vacation_leaves['total_days'] if faculty_vacation_leaves else 0.0

    # BR-EL-007: VL-to-EL year-end conversion
    vl_to_el_conversions = VLToELConversion.objects.filter(user_id=user).aggregate(total_days=Sum('days'))
    vl_to_el_conversion_entitlement = vl_to_el_conversions['total_days'] if vl_to_el_conversions else 0.0

    # BR-EL-009: Commuted Leave entitlement and treatment
    commuted_leaves = CommutedLeave.objects.filter(user_id=user).aggregate(total_days=Sum('days'))
    commuted_leave_entitlement = commuted_leaves['total_days'] if commuted_leaves else 0.0

    # BR-EL-010: Half-day CL treatment
    half_day_cls = HalfDayCL.objects.filter(user_id=user).aggregate(total_days=Sum('days'))
    half_day_cl_entitlement = half_day_cls['total_days'] if half_day_cls else 0.0

    # BR-EL-013: Station Leave coupling
    station_leaves = StationLeave.objects.filter(user_id=user).count()

    total_leave_balance = (
        casual_leave_entitlement +
        restricted_holiday_entitlement +
        special_casual_leave_entitlement +
        non_faculty_earned_leave_entitlement +
        faculty_vacation_leave_entitlement +
        vl_to_el_conversion_entitlement +
        commuted_leave_entitlement +
        half_day_cl_entitlement +
        station_leaves
    )

    return total_leave_balance

def get_user_pending_requests(user):
    # BR-EL-012: Applicant non-overlap with half-day CL exception
    pending_half_day_cl = HalfDayCL.objects.filter(user_id=user, start_date__lte=datetime.now(), end_date__gte=datetime.now()).count()

    # BR-EL-014: Substitute eligibility
    substitute_eligible = Substitute.objects.filter(user_id=user).exists()

    return {
        'pending_half_day_cl': pending_half_day_cl,
        'substitute_eligible': substitute_eligible,
    }

def get_user_approved_requests(user):
    # BR-EL-021: Immediate withdrawal of pending request
    pending_request_withdrawal = PendingRequestWithdrawal.objects.filter(user_id=user).exists()

    # BR-EL-023: Cancellation of approved leave before start
    approved_leave_cancellations = ApprovedLeaveCancellation.objects.filter(user_id=user).exists()

    return {
        'pending_request_withdrawal': pending_request_withdrawal,
        'approved_leave_cancellations': approved_leave_cancellations,
    }

def get_user_resumed_requests(user):
    # BR-EL-026: Immediate withdrawal of pending request
    resumed_requests = Leave.objects.filter(user_id=user, status='resumed').count()

    return {
        'resumed_requests': resumed_requests,
    }
