import pytest
from datetime import date, time, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from modules.oap.models import (
    StudentLeave, BonafideRequest, NoDuesRequest, NoDuesAuthorityClearance,
    ThesisSupervisorAssignment, TAAssignment, AssistantshipClaim,
    GraduateSeminarRequest, OAPNotification
)
from modules.oap.services import oap_service

@pytest.mark.django_db
def test_student_leave_workflow_approval_and_rejection():
    with pytest.raises(ValidationError):
        oap_service.submit_student_leave(student_user_id=101, department='CSE', leave_type='CASUAL', start_date=date.today()+timedelta(days=2), end_date=date.today(), reason='Invalid')

    leave = oap_service.submit_student_leave(student_user_id=101, department='CSE', leave_type='CASUAL', start_date=date.today(), end_date=date.today()+timedelta(days=2), reason='Medical')
    assert leave.status == 'SUBMITTED'

    approved = oap_service.decide_student_leave(leave_id=leave.id, hod_user_id=201, decision='APPROVED')
    assert approved.status == 'APPROVED'
    assert approved.hod_user_id == 201

    leave2 = oap_service.submit_student_leave(student_user_id=101, department='CSE', leave_type='CASUAL', start_date=date.today(), end_date=date.today()+timedelta(days=1), reason='Personal')
    rejected = oap_service.decide_student_leave(leave_id=leave2.id, hod_user_id=201, decision='REJECTED', remarks='Exam period')
    assert rejected.status == 'REJECTED'

@pytest.mark.django_db
def test_bonafide_certificate_approval_and_download_guard():
    req = oap_service.request_bonafide_certificate(student_user_id=102, purpose='Passport application')
    assert req.status == 'SUBMITTED'
    assert not oap_service.can_download_bonafide(req.id)

    approved = oap_service.decide_bonafide_request(request_id=req.id, admin_user_id=301, decision='APPROVED')
    assert approved.status == 'APPROVED'
    assert approved.certificate_number is not None
    assert oap_service.can_download_bonafide(approved.id)

@pytest.mark.django_db
def test_no_dues_clearance_7_authorities_and_finalization_guard():
    req = oap_service.initiate_no_dues_clearance(student_user_id=103, program='BTECH', department='CSE')
    clearances = list(NoDuesAuthorityClearance.objects.filter(no_dues_request=req))
    assert len(clearances) == 7
    assert all(c.status == 'PENDING' for c in clearances)

    with pytest.raises(ValidationError):
        oap_service.finalize_no_dues_clearance(request_id=req.id, admin_user_id=301)

    domains = [c.domain for c in clearances]
    for d in domains[:6]:
        oap_service.verify_no_dues_domain(request_id=req.id, domain=d, verifier_user_id=401, status='CLEARED')
    with pytest.raises(ValidationError):
        oap_service.finalize_no_dues_clearance(request_id=req.id, admin_user_id=301)

    # 7th domain outstanding dues
    oap_service.verify_no_dues_domain(request_id=req.id, domain=domains[6], verifier_user_id=402, status='DUES_OUTSTANDING', dues_amount=Decimal('500.00'))
    with pytest.raises(ValidationError):
        oap_service.finalize_no_dues_clearance(request_id=req.id, admin_user_id=301)

    # Clear 7th domain and finalize
    oap_service.verify_no_dues_domain(request_id=req.id, domain=domains[6], verifier_user_id=402, status='CLEARED', dues_amount=Decimal('0.00'))
    finalized = oap_service.finalize_no_dues_clearance(request_id=req.id, admin_user_id=301)
    assert finalized.status == 'FINALIZED'
    assert finalized.certificate_number is not None
    assert oap_service.can_download_no_dues_certificate(finalized.id) is True

@pytest.mark.django_db
def test_departmental_supervisor_and_ta_assignments():
    thesis = oap_service.record_thesis_supervisor_assignment(student_user_id=104, faculty_user_id=501, department='CSE', academic_year='2026-2027', assigned_by_user_id=401)
    assert thesis.student_user_id == 104
    assert thesis.faculty_user_id == 501

    ta = oap_service.record_ta_assignment(student_user_id=104, department='CSE', semester='AUTUMN', academic_year='2026-2027', assigned_by_user_id=401, faculty_user_id=502, course_code='CS301', course_name='OS')
    assert ta.student_user_id == 104
    assert ta.course_code == 'CS301'

@pytest.mark.django_db
def test_pg_assistantship_claim_full_workflow():
    with pytest.raises(ValidationError):
        oap_service.submit_assistantship_claim(student_user_id=105, is_pg=False, month=10, year=2026, work_summary='TA work', hours_worked=Decimal('40.0'), thesis_supervisor_user_id=501, ta_supervisor_user_id=502)

    claim = oap_service.submit_assistantship_claim(student_user_id=105, is_pg=True, month=10, year=2026, work_summary='TA work', hours_worked=Decimal('40.0'), thesis_supervisor_user_id=501, ta_supervisor_user_id=502)
    assert claim.status == 'AWAITING_DUAL_SUPERVISOR_VERIFICATION'

    with pytest.raises(ValidationError):
        oap_service.review_and_forward_assistantship(claim_id=claim.id, dept_admin_user_id=401)

    claim = oap_service.verify_assistantship_supervisor(claim_id=claim.id, supervisor_role='THESIS_SUPERVISOR', supervisor_user_id=501)
    assert claim.status == 'AWAITING_OTHER_SUPERVISOR_VERIFICATION'

    claim = oap_service.verify_assistantship_supervisor(claim_id=claim.id, supervisor_role='TA_SUPERVISOR', supervisor_user_id=502)
    assert claim.status == 'AWAITING_DEPARTMENT_REVIEW'

    claim = oap_service.review_and_forward_assistantship(claim_id=claim.id, dept_admin_user_id=401)
    assert claim.status == 'AWAITING_HOD_DECISION'

    with pytest.raises(ValidationError):
        oap_service.process_stipend_disbursement(claim_id=claim.id, admin_user_id=301, disbursement_reference='REF123')

    claim = oap_service.decide_assistantship_hod(claim_id=claim.id, hod_user_id=201, decision='APPROVED')
    assert claim.status == 'APPROVED_AWAITING_STIPEND'

    claim = oap_service.process_stipend_disbursement(claim_id=claim.id, admin_user_id=301, disbursement_reference='REF-OCT-001')
    assert claim.status == 'STIPEND_PROCESSED'
    assert claim.disbursement_reference == 'REF-OCT-001'

@pytest.mark.django_db
def test_graduate_seminar_request_and_scheduling():
    with pytest.raises(ValidationError):
        oap_service.request_graduate_seminar(student_user_id=106, is_pg=False, topic='AI', abstract='Study of ML', preferred_date=date.today()+timedelta(days=7))

    sem = oap_service.request_graduate_seminar(student_user_id=106, is_pg=True, topic='AI in Healthcare', abstract='Study of ML in diagnostics', preferred_date=date.today()+timedelta(days=7))
    assert sem.status == 'AWAITING_SCHEDULING'

    sem = oap_service.schedule_graduate_seminar(seminar_id=sem.id, dept_admin_user_id=401, scheduled_date=date.today()+timedelta(days=5), scheduled_time=time(14, 0), venue='CR-101')
    assert sem.status == 'SCHEDULED'
    assert sem.venue == 'CR-101'
    assert len(sem.history_log) > 0

@pytest.mark.django_db
def test_oap_event_notifications():
    notif = oap_service.send_oap_notification(recipient_user_id=101, notification_type='EMAIL', event_type='LEAVE_SUBMITTED', message='Leave submitted')
    assert notif.recipient_user_id == 101
    assert not notif.is_read
