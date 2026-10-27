import datetime
from decimal import Decimal
import pytest

from modules.elm.models import (
    LeaveCategory, LeaveApplicationStatus, LeaveBalance, LeaveApplication,
    SubstituteAssignment, ApprovalHistory, LeaveCancellation, LeaveExtension,
    LeaveResumption, OfflineLeaveRecord, SLAConfig
)
from modules.elm.services import leave_service


@pytest.mark.django_db
def test_continuous_counting_el_col_vl():
    # Friday to Monday = 4 calendar days (including Saturday & Sunday)
    start = datetime.date(2026, 10, 23) # Friday
    end = datetime.date(2026, 10, 26)   # Monday
    
    days_el = leave_service.calculate_chargeable_days('EL', start, end)
    days_col = leave_service.calculate_chargeable_days('COL', start, end)
    days_vl = leave_service.calculate_chargeable_days('VL', start, end)
    
    assert days_el == Decimal('4.0')
    assert days_col == Decimal('4.0')
    assert days_vl == Decimal('4.0')


@pytest.mark.django_db
def test_working_day_counting_cl_scl_rh():
    # Friday to Monday = 2 working days (Friday and Monday, excluding Sat & Sun)
    start = datetime.date(2026, 10, 23) # Friday
    end = datetime.date(2026, 10, 26)   # Monday
    
    days_cl = leave_service.calculate_chargeable_days('CL', start, end)
    days_scl = leave_service.calculate_chargeable_days('SCL', start, end)
    days_rh = leave_service.calculate_chargeable_days('RH', start, end)
    
    assert days_cl == Decimal('2.0')
    assert days_scl == Decimal('2.0')
    assert days_rh == Decimal('2.0')


@pytest.mark.django_db
def test_half_day_cl_deduction():
    # Half day CL consumes exactly 0.5 days
    dt = datetime.date(2026, 11, 2)
    days_first = leave_service.calculate_chargeable_days('CL', dt, dt, half_day_type='FIRST_HALF')
    days_second = leave_service.calculate_chargeable_days('CL', dt, dt, half_day_type='SECOND_HALF')
    
    assert days_first == Decimal('0.5')
    assert days_second == Decimal('0.5')


@pytest.mark.django_db
def test_overlap_detection_and_half_day_exception():
    user_id = 901
    d1 = datetime.date(2026, 11, 10)
    
    # 1. Create half-day FIRST_HALF leave
    app1 = LeaveApplication.objects.create(
        user_id=user_id,
        leave_category='CL',
        start_date=d1,
        end_date=d1,
        half_day_type='FIRST_HALF',
        chargeable_days=Decimal('0.5'),
        reason="Morning dentist",
        status='APPROVED'
    )
    
    # 2. Applying SECOND_HALF on same day is ALLOWED (BR-EL-012)
    has_overlap_diff_half = leave_service.check_leave_overlap(
        user_id=user_id,
        start_date=d1,
        end_date=d1,
        half_day_type='SECOND_HALF'
    )
    assert not has_overlap_diff_half
    
    # 3. Applying FIRST_HALF again on same day is an impermissible OVERLAP
    has_overlap_same_half = leave_service.check_leave_overlap(
        user_id=user_id,
        start_date=d1,
        end_date=d1,
        half_day_type='FIRST_HALF'
    )
    assert has_overlap_same_half


@pytest.mark.django_db
def test_substitute_validation():
    applicant_id = 101
    substitute_id = 102
    d1 = datetime.date(2026, 11, 15)
    d2 = datetime.date(2026, 11, 18)
    
    # Cannot nominate self (BR-EL-014)
    with pytest.raises(leave_service.DomainError, match="Applicant cannot be own substitute"):
        leave_service.validate_substitute(applicant_id, applicant_id, d1, d2)
        
    # Valid substitute
    assert leave_service.validate_substitute(substitute_id, applicant_id, d1, d2)


@pytest.mark.django_db
def test_cw_el_01_cl_workflow_unit_head_final():
    user_id = 201
    substitute_id = 202
    hod_id = 301
    year = 2026
    
    # Initialize balance: 8 CL days
    LeaveBalance.objects.create(
        user_id=user_id,
        year=year,
        leave_category='CL',
        opening_balance=Decimal('8.0'),
        credited=Decimal('0.0'),
        availed=Decimal('0.0'),
        pending_approval=Decimal('0.0'),
        converted_from_vl=Decimal('0.0'),
        lapsed=Decimal('0.0'),
        carried_forward=Decimal('0.0')
    )
    
    start = datetime.date(2026, 11, 4) # Wednesday
    end = datetime.date(2026, 11, 5)   # Thursday (2 days)
    
    # Apply
    app = leave_service.submit_leave_application(
        user_id=user_id,
        category='CL',
        start_date=start,
        end_date=end,
        reason="Family function",
        substitute_id=substitute_id
    )
    assert app.status == 'AWAITING_SUBSTITUTE'
    assert app.chargeable_days == Decimal('2.0')
    
    # Check pending balance reserved
    bal = LeaveBalance.objects.get(user_id=user_id, year=year, leave_category='CL')
    assert bal.pending_approval == Decimal('2.0')
    
    # Substitute accepts
    assign = SubstituteAssignment.objects.get(leave_application=app)
    leave_service.respond_to_substitute(assign.id, substitute_id, 'ACCEPTED', "I can cover")
    app.refresh_from_db()
    assert app.status == 'UNDER_REVIEW_UNIT_HEAD'
    
    # Unit Head final approval (BR-EL-016)
    leave_service.review_by_unit_head(app.id, hod_id, 'APPROVED', "Approved by HOD")
    app.refresh_from_db()
    assert app.status == 'APPROVED'
    
    # Balance updated: pending=0, availed=2, available=6
    bal.refresh_from_db()
    assert bal.pending_approval == Decimal('0.0')
    assert bal.availed == Decimal('2.0')
    assert bal.available_balance() == Decimal('6.0')


@pytest.mark.django_db
def test_cw_el_01_higher_sanction_recommendation():
    user_id = 205
    hod_id = 301
    dean_id = 401
    year = 2026
    
    LeaveBalance.objects.create(
        user_id=user_id,
        year=year,
        leave_category='EL',
        opening_balance=Decimal('30.0'),
        credited=Decimal('0.0'),
        availed=Decimal('0.0'),
        pending_approval=Decimal('0.0'),
        converted_from_vl=Decimal('0.0'),
        lapsed=Decimal('0.0'),
        carried_forward=Decimal('0.0')
    )
    
    start = datetime.date(2026, 11, 10)
    end = datetime.date(2026, 11, 14) # 5 days
    
    app = leave_service.submit_leave_application(
        user_id=user_id,
        category='EL',
        start_date=start,
        end_date=end,
        reason="Research leave"
    )
    assert app.status == 'UNDER_REVIEW_UNIT_HEAD'
    
    # Unit Head recommends (BR-EL-017: Unit Head cannot reject higher-sanction; routes to sanctioning authority)
    leave_service.review_by_unit_head(app.id, hod_id, 'RECOMMENDED', "Strongly recommended")
    app.refresh_from_db()
    assert app.status == 'UNDER_SANCTION'
    
    # Competent Authority makes final approval (BR-EL-018)
    leave_service.make_sanctioning_decision(app.id, dean_id, 'Dean', 'APPROVED', "Sanctioned")
    app.refresh_from_db()
    assert app.status == 'APPROVED'
    
    bal = LeaveBalance.objects.get(user_id=user_id, year=year, leave_category='EL')
    assert bal.availed == Decimal('5.0')
    assert bal.available_balance() == Decimal('25.0')


@pytest.mark.django_db
def test_director_self_sanction():
    director_id = 1
    year = 2026
    LeaveBalance.objects.create(
        user_id=director_id,
        year=year,
        leave_category='CL',
        opening_balance=Decimal('8.0'),
        credited=Decimal('0.0'),
        availed=Decimal('0.0'),
        pending_approval=Decimal('0.0'),
        converted_from_vl=Decimal('0.0'),
        lapsed=Decimal('0.0'),
        carried_forward=Decimal('0.0')
    )
    start = datetime.date(2026, 11, 20)
    
    # Director self-sanction route (BR-EL-020)
    app = leave_service.submit_leave_application(
        user_id=director_id,
        category='CL',
        start_date=start,
        end_date=start,
        reason="Official meeting",
        is_director=True
    )
    assert app.status == 'UNDER_SANCTION'
    
    # Director self-approves
    leave_service.make_sanctioning_decision(app.id, director_id, 'Director', 'APPROVED', "Self-sanctioned")
    app.refresh_from_db()
    assert app.status == 'APPROVED'


@pytest.mark.django_db
def test_immediate_withdrawal():
    user_id = 210
    year = 2026
    LeaveBalance.objects.create(
        user_id=user_id,
        year=year,
        leave_category='CL',
        opening_balance=Decimal('8.0'),
        credited=Decimal('0.0'),
        availed=Decimal('0.0'),
        pending_approval=Decimal('0.0'),
        converted_from_vl=Decimal('0.0'),
        lapsed=Decimal('0.0'),
        carried_forward=Decimal('0.0')
    )
    start = datetime.date(2026, 12, 1)
    
    app = leave_service.submit_leave_application(
        user_id=user_id, category='CL', start_date=start, end_date=start, reason="Pending plan"
    )
    assert app.status == 'UNDER_REVIEW_UNIT_HEAD'
    
    # Immediate withdrawal (BR-EL-022, BR-EL-034)
    leave_service.withdraw_leave(app.id, user_id)
    app.refresh_from_db()
    assert app.status == 'WITHDRAWN'
    
    # Pending balance released back to available
    bal = LeaveBalance.objects.get(user_id=user_id, year=year, leave_category='CL')
    assert bal.pending_approval == Decimal('0.0')
    assert bal.available_balance() == Decimal('8.0')


@pytest.mark.django_db
def test_cw_el_02_cancellation_pre_start():
    user_id = 220
    hod_id = 301
    year = 2026
    LeaveBalance.objects.create(
        user_id=user_id,
        year=year,
        leave_category='CL',
        opening_balance=Decimal('8.0'),
        credited=Decimal('0.0'),
        availed=Decimal('0.0'),
        pending_approval=Decimal('0.0'),
        converted_from_vl=Decimal('0.0'),
        lapsed=Decimal('0.0'),
        carried_forward=Decimal('0.0')
    )
    start = datetime.date(2026, 12, 10)
    app = leave_service.submit_leave_application(user_id=user_id, category='CL', start_date=start, end_date=start, reason="Trip")
    leave_service.review_by_unit_head(app.id, hod_id, 'APPROVED', "Approved")
    
    bal = LeaveBalance.objects.get(user_id=user_id, year=year, leave_category='CL')
    assert bal.availed == Decimal('1.0')
    
    # Request pre-start cancellation (BR-EL-023)
    cancel = leave_service.request_cancellation(app.id, user_id, "Trip cancelled")
    leave_service.review_cancellation(cancel.id, hod_id, 'APPROVED', "Cancellation accepted")
    
    app.refresh_from_db()
    assert app.status == 'CANCELLED'
    bal.refresh_from_db()
    assert bal.availed == Decimal('0.0')
    assert bal.available_balance() == Decimal('8.0')


@pytest.mark.django_db
def test_year_end_processing_conversion():
    user_id = 250
    year = 2026
    
    # Faculty with 8 CL (unused), 2 RH (unused), 30 VL (unused)
    LeaveBalance.objects.create(user_id=user_id, year=year, leave_category='CL', opening_balance=Decimal('8.0'), credited=Decimal('0'), availed=Decimal('0'), pending_approval=Decimal('0'), converted_from_vl=Decimal('0'), lapsed=Decimal('0'), carried_forward=Decimal('0'))
    LeaveBalance.objects.create(user_id=user_id, year=year, leave_category='RH', opening_balance=Decimal('2.0'), credited=Decimal('0'), availed=Decimal('0'), pending_approval=Decimal('0'), converted_from_vl=Decimal('0'), lapsed=Decimal('0'), carried_forward=Decimal('0'))
    LeaveBalance.objects.create(user_id=user_id, year=year, leave_category='VL', opening_balance=Decimal('30.0'), credited=Decimal('0'), availed=Decimal('0'), pending_approval=Decimal('0'), converted_from_vl=Decimal('0'), lapsed=Decimal('0'), carried_forward=Decimal('0'))
    
    # Process Year-End (BR-EL-002, BR-EL-007: CL/RH lapse, 30 VL converts to 15 EL at 2:1 ratio)
    leave_service.process_year_end(user_id, year)
    
    cl_bal = LeaveBalance.objects.get(user_id=user_id, year=year, leave_category='CL')
    assert cl_bal.lapsed == Decimal('8.0')
    
    rh_bal = LeaveBalance.objects.get(user_id=user_id, year=year, leave_category='RH')
    assert rh_bal.lapsed == Decimal('2.0')
    
    # Converted EL in year+1
    next_el = LeaveBalance.objects.get(user_id=user_id, year=year+1, leave_category='EL')
    assert next_el.converted_from_vl == Decimal('15.0')
    assert next_el.opening_balance == Decimal('15.0')


@pytest.mark.django_db
def test_offline_leave_synchronization():
    user_id = 260
    admin_id = 999
    year = 2026
    LeaveBalance.objects.create(user_id=user_id, year=year, leave_category='CL', opening_balance=Decimal('8.0'), credited=Decimal('0'), availed=Decimal('0'), pending_approval=Decimal('0'), converted_from_vl=Decimal('0'), lapsed=Decimal('0'), carried_forward=Decimal('0'))
    
    d = datetime.date(2026, 9, 15)
    rec = leave_service.record_offline_leave(
        user_id=user_id, admin_user_id=admin_id, category='CL', start_date=d, end_date=d,
        ref="DIR/OFFLINE/2026/042", sanctioned_by="Director", reason="Medical emergency offline sanction"
    )
    assert rec.offline_sanction_reference == "DIR/OFFLINE/2026/042"
    
    bal = LeaveBalance.objects.get(user_id=user_id, year=year, leave_category='CL')
    assert bal.availed == Decimal('1.0')
    assert bal.available_balance() == Decimal('7.0')
