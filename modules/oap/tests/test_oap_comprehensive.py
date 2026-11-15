"""Comprehensive Phase 2 Verification Suite for Other Academic Procedures (OAP).

Covers all 17 Business Rules, 9 Workflows, security access restrictions,
pro-rata calculations, audit trails, and negative boundary guards.
"""
import pytest
from datetime import date, time, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError, PermissionDenied

from modules.oap.models import (
    OAPAuditTrail,
    StudentLeave,
    BonafideRequest,
    NoDuesRequest,
    NoDuesAuthorityClearance,
    ThesisSupervisorAssignment,
    TAAssignment,
    AssistantshipClaim,
    GraduateSeminarRequest,
    OAPNotification,
)
from modules.oap.services import oap_service


# ==============================================================================
# 1. STUDENT LEAVE TESTS (OA-BR-11, BW-OAP-01, BW-OAP-02)
# ==============================================================================

@pytest.mark.django_db
def test_student_leave_happy_path_approval():
    leave = oap_service.submit_student_leave(
        student_user_id=101, department='CSE', leave_type='CASUAL',
        start_date=date(2026, 11, 10), end_date=date(2026, 11, 12),
        reason='Family function'
    )
    assert leave.status == 'SUBMITTED'
    assert leave.chargeable_days == Decimal('3.0')

    approved = oap_service.decide_student_leave(
        leave_id=leave.id, hod_user_id=201, decision='APPROVED', remarks='Granted'
    )
    assert approved.status == 'APPROVED'
    assert approved.hod_user_id == 201
    assert approved.hod_remarks == 'Granted'


@pytest.mark.django_db
def test_student_leave_rejection():
    leave = oap_service.submit_student_leave(
        student_user_id=101, department='CSE', leave_type='CASUAL',
        start_date=date(2026, 11, 15), end_date=date(2026, 11, 16),
        reason='Personal'
    )
    rejected = oap_service.decide_student_leave(
        leave_id=leave.id, hod_user_id=201, decision='REJECTED', remarks='Mid-semester examinations'
    )
    assert rejected.status == 'REJECTED'
    assert rejected.hod_remarks == 'Mid-semester examinations'


@pytest.mark.django_db
def test_student_leave_negative_date_range():
    with pytest.raises(ValidationError, match="Start date must be before or equal to end date"):
        oap_service.submit_student_leave(
            student_user_id=101, department='CSE', leave_type='CASUAL',
            start_date=date(2026, 11, 20), end_date=date(2026, 11, 18),
            reason='Invalid dates'
        )


@pytest.mark.django_db
def test_student_leave_medical_proof_requirement():
    # Medical leave > 3 days without proof must fail
    with pytest.raises(ValidationError, match="Medical certificate attachment is mandatory"):
        oap_service.submit_student_leave(
            student_user_id=101, department='CSE', leave_type='MEDICAL',
            start_date=date(2026, 11, 10), end_date=date(2026, 11, 15),
            reason='Severe flu', medical_certificate_attached=False
        )

    # With proof, it must succeed
    leave = oap_service.submit_student_leave(
        student_user_id=101, department='CSE', leave_type='MEDICAL',
        start_date=date(2026, 11, 10), end_date=date(2026, 11, 15),
        reason='Severe flu', medical_certificate_attached=True, document_reference='MED-DOC-9821'
    )
    assert leave.status == 'SUBMITTED'
    assert leave.medical_certificate_attached is True


@pytest.mark.django_db
def test_student_leave_invalid_transition_guard():
    leave = oap_service.submit_student_leave(
        student_user_id=101, department='CSE', leave_type='CASUAL',
        start_date=date(2026, 11, 10), end_date=date(2026, 11, 11),
        reason='Personal'
    )
    oap_service.decide_student_leave(leave_id=leave.id, hod_user_id=201, decision='APPROVED')

    # Cannot re-decide an already approved leave
    with pytest.raises(ValidationError, match="must be SUBMITTED"):
        oap_service.decide_student_leave(leave_id=leave.id, hod_user_id=201, decision='REJECTED')


# ==============================================================================
# 2. BONAFIDE CERTIFICATE TESTS (OA-BR-21, OA-BR-22, BW-OAP-03, BW-OAP-04)
# ==============================================================================

@pytest.mark.django_db
def test_bonafide_certificate_approval_and_token():
    req = oap_service.request_bonafide_certificate(
        student_user_id=102, purpose='Passport verification', certificate_type='PASSPORT'
    )
    assert req.status == 'SUBMITTED'
    assert not oap_service.can_download_bonafide(req.id)

    approved = oap_service.decide_bonafide_request(
        request_id=req.id, admin_user_id=301, decision='APPROVED', remarks='Verified enrolled student'
    )
    assert approved.status == 'APPROVED'
    assert approved.certificate_number.startswith('BONAFIDE-')
    assert approved.verification_hash is not None
    assert approved.valid_until == approved.issue_date + timedelta(days=180)
    assert oap_service.can_download_bonafide(approved.id) is True


@pytest.mark.django_db
def test_bonafide_rejection():
    req = oap_service.request_bonafide_certificate(
        student_user_id=102, purpose='Bank loan'
    )
    rejected = oap_service.decide_bonafide_request(
        request_id=req.id, admin_user_id=301, decision='REJECTED', remarks='Incomplete academic profile'
    )
    assert rejected.status == 'REJECTED'
    assert oap_service.can_download_bonafide(rejected.id) is False


@pytest.mark.django_db
def test_bonafide_download_guard_and_payload():
    req = oap_service.request_bonafide_certificate(
        student_user_id=102, purpose='Internship NOC'
    )
    with pytest.raises(PermissionDenied):
        oap_service.get_certificate_data(req)

    approved = oap_service.decide_bonafide_request(request_id=req.id, admin_user_id=301, decision='APPROVED')
    payload = oap_service.get_certificate_data(approved)
    assert payload['certificate_number'] == approved.certificate_number
    assert payload['verification_hash'] == approved.verification_hash
    assert payload['status'] == 'VERIFIED_VALID'


@pytest.mark.django_db
def test_bonafide_authenticity_verification():
    req = oap_service.request_bonafide_certificate(student_user_id=102, purpose='Visa')
    approved = oap_service.decide_bonafide_request(request_id=req.id, admin_user_id=301, decision='APPROVED')

    valid_info = oap_service.verify_bonafide_authenticity(approved.certificate_number, approved.verification_hash)
    assert valid_info['is_valid'] is True
    assert valid_info['student_id'] == 102

    invalid_info = oap_service.verify_bonafide_authenticity(approved.certificate_number, 'FAKE_HASH_XYZ')
    assert invalid_info['is_valid'] is False


# ==============================================================================
# 3. MULTI-DOMAIN NO-DUES TESTS (OA-BR-31..34, BW-OAP-05, BW-OAP-06)
# ==============================================================================

@pytest.mark.django_db
def test_no_dues_initiation_and_7_clearance_creation():
    req = oap_service.initiate_no_dues_clearance(student_user_id=103, program='UG', department='CSE')
    assert req.status == 'VERIFICATION_IN_PROGRESS'
    clearances = list(NoDuesAuthorityClearance.objects.filter(no_dues_request=req))
    assert len(clearances) == 7
    expected_domains = {'LIBRARY', 'HOSTEL', 'MESS', 'DEPARTMENT', 'LAB', 'ACADEMIC_SECTION', 'STUDENT_SECTION'}
    assert set(c.domain for c in clearances) == expected_domains
    assert all(c.status == 'PENDING' for c in clearances)


@pytest.mark.django_db
def test_no_dues_authority_role_restriction():
    req = oap_service.initiate_no_dues_clearance(student_user_id=103, program='UG', department='CSE')

    # A Hostel Warden cannot clear Library domain (OA-BR-31)
    with pytest.raises(PermissionDenied, match="not authorized to clear domain 'LIBRARY'"):
        oap_service.verify_no_dues_domain(
            request_id=req.id, domain='LIBRARY', verifier_user_id=401,
            status='CLEARED', verifier_role='Hostel Warden'
        )

    # Librarian can clear Library
    cl = oap_service.verify_no_dues_domain(
        request_id=req.id, domain='LIBRARY', verifier_user_id=402,
        status='CLEARED', verifier_role='Librarian'
    )
    assert cl.status == 'CLEARED'


@pytest.mark.django_db
def test_no_dues_independent_status_updates():
    req = oap_service.initiate_no_dues_clearance(student_user_id=103, program='UG', department='CSE')
    oap_service.verify_no_dues_domain(
        request_id=req.id, domain='MESS', verifier_user_id=403,
        status='CLEARED', verifier_role='Mess In-charge'
    )

    # Other 6 domains remain PENDING (OA-BR-32)
    other_pending = NoDuesAuthorityClearance.objects.filter(no_dues_request=req, status='PENDING')
    assert other_pending.count() == 6


@pytest.mark.django_db
def test_no_dues_finalization_blocked_on_pending():
    req = oap_service.initiate_no_dues_clearance(student_user_id=103, program='UG', department='CSE')
    domains = [c.domain for c in req.clearances.all()]

    # Clear only 6 domains
    for d in domains[:6]:
        oap_service.verify_no_dues_domain(
            request_id=req.id, domain=d, verifier_user_id=401, status='CLEARED', verifier_role='admin'
        )

    # 7th domain is still PENDING -> Finalization must fail (OA-BR-33)
    with pytest.raises(ValidationError, match="pending clearances remain"):
        oap_service.finalize_no_dues_clearance(request_id=req.id, admin_user_id=301)


@pytest.mark.django_db
def test_no_dues_finalization_blocked_on_dues_outstanding():
    req = oap_service.initiate_no_dues_clearance(student_user_id=103, program='UG', department='CSE')
    domains = [c.domain for c in req.clearances.all()]

    for d in domains[:6]:
        oap_service.verify_no_dues_domain(
            request_id=req.id, domain=d, verifier_user_id=401, status='CLEARED', verifier_role='admin'
        )

    # 7th domain has outstanding dues
    oap_service.verify_no_dues_domain(
        request_id=req.id, domain=domains[6], verifier_user_id=401,
        status='DUES_OUTSTANDING', verifier_role='admin', dues_amount=Decimal('1500.00'), fine_details='Lost books'
    )

    with pytest.raises(ValidationError, match="outstanding dues remain"):
        oap_service.finalize_no_dues_clearance(request_id=req.id, admin_user_id=301)


@pytest.mark.django_db
def test_no_dues_finalization_happy_path_and_certificate():
    req = oap_service.initiate_no_dues_clearance(student_user_id=103, program='UG', department='CSE')
    for c in req.clearances.all():
        oap_service.verify_no_dues_domain(
            request_id=req.id, domain=c.domain, verifier_user_id=401,
            status='CLEARED', verifier_role='admin'
        )

    finalized = oap_service.finalize_no_dues_clearance(
        request_id=req.id, admin_user_id=301, remarks='All clear'
    )
    assert finalized.status == 'FINALIZED'
    assert finalized.all_domains_cleared is True
    assert finalized.certificate_number.startswith('NODUES-')
    assert finalized.verification_hash is not None
    assert oap_service.can_download_no_dues_certificate(finalized.id) is True

    cert_data = oap_service.get_certificate_data(finalized)
    assert cert_data['status'] == 'ALL_CLEARED'
    assert cert_data['domains_cleared'] == 7


# ==============================================================================
# 4. SUPERVISOR & TA ASSIGNMENT TESTS (OA-BR-51, OA-BR-52)
# ==============================================================================

@pytest.mark.django_db
def test_thesis_supervisor_assignment_and_duplicate_guard():
    thesis = oap_service.record_thesis_supervisor_assignment(
        student_user_id=104, faculty_user_id=501, department='CSE',
        academic_year='2026-2027', assigned_by_user_id=401
    )
    assert thesis.student_user_id == 104
    assert thesis.is_active is True

    # Duplicate active assignment in the same academic year must fail
    with pytest.raises(ValidationError, match="already has an active thesis supervisor"):
        oap_service.record_thesis_supervisor_assignment(
            student_user_id=104, faculty_user_id=502, department='CSE',
            academic_year='2026-2027', assigned_by_user_id=401
        )


@pytest.mark.django_db
def test_ta_assignment_and_duplicate_guard():
    ta = oap_service.record_ta_assignment(
        student_user_id=104, department='CSE', semester='AUTUMN',
        academic_year='2026-2027', assigned_by_user_id=401,
        course_code='CS301', course_name='Operating Systems'
    )
    assert ta.course_code == 'CS301'
    assert ta.is_active is True

    # Duplicate TA assignment in the same course/semester must fail
    with pytest.raises(ValidationError, match="already assigned as TA for CS301"):
        oap_service.record_ta_assignment(
            student_user_id=104, department='CSE', semester='AUTUMN',
            academic_year='2026-2027', assigned_by_user_id=401,
            course_code='CS301', course_name='Operating Systems'
        )


# ==============================================================================
# 5. PG ASSISTANTSHIP CLAIM TESTS (OA-BR-41..46, BW-OAP-07, BW-OAP-08)
# ==============================================================================

@pytest.mark.django_db
def test_pg_assistantship_eligibility_guard():
    # UG students cannot submit assistantship claims (OA-BR-41)
    with pytest.raises(ValidationError, match="Only PG students are eligible"):
        oap_service.submit_assistantship_claim(
            student_user_id=105, is_pg=False, month=10, year=2026,
            work_summary='TA lab work', hours_worked=Decimal('40.0'),
            thesis_supervisor_user_id=501, ta_supervisor_user_id=502
        )


@pytest.mark.django_db
def test_pg_assistantship_pro_rata_attendance_penalty():
    # Normal attendance (>= 80%) gets full stipend
    normal_claim = oap_service.submit_assistantship_claim(
        student_user_id=105, is_pg=True, month=10, year=2026,
        work_summary='Lab duties', hours_worked=Decimal('40.0'),
        thesis_supervisor_user_id=501, ta_supervisor_user_id=502,
        stipend_amount=Decimal('12400.00'), attendance_percentage=Decimal('90.00')
    )
    assert normal_claim.pro_rata_stipend == Decimal('12400.00')

    # Sub-80% attendance receives pro-rata penalty
    penalized_claim = oap_service.submit_assistantship_claim(
        student_user_id=106, is_pg=True, month=10, year=2026,
        work_summary='Lab duties', hours_worked=Decimal('20.0'),
        thesis_supervisor_user_id=501, ta_supervisor_user_id=502,
        stipend_amount=Decimal('12400.00'), attendance_percentage=Decimal('50.00')
    )
    assert penalized_claim.pro_rata_stipend == Decimal('6200.00')


@pytest.mark.django_db
def test_pg_assistantship_dual_supervisor_verification():
    claim = oap_service.submit_assistantship_claim(
        student_user_id=105, is_pg=True, month=10, year=2026,
        work_summary='Research and Grading', hours_worked=Decimal('40.0'),
        thesis_supervisor_user_id=501, ta_supervisor_user_id=502
    )
    assert claim.status == 'AWAITING_DUAL_SUPERVISOR_VERIFICATION'

    # Thesis supervisor verifies first (OA-BR-42)
    claim = oap_service.verify_assistantship_supervisor(
        claim_id=claim.id, supervisor_role='THESIS', supervisor_user_id=501, remarks='Research satisfactory'
    )
    assert claim.status == 'AWAITING_OTHER_SUPERVISOR_VERIFICATION'
    assert claim.thesis_supervisor_role_verified is True
    assert claim.ta_supervisor_role_verified is False

    # Cannot forward to department yet (OA-BR-43)
    with pytest.raises(ValidationError, match="dual supervisor verification is incomplete"):
        oap_service.review_and_forward_assistantship(claim_id=claim.id, dept_admin_user_id=401)

    # TA supervisor verifies
    claim = oap_service.verify_assistantship_supervisor(
        claim_id=claim.id, supervisor_role='TA', supervisor_user_id=502, remarks='Course grading on time'
    )
    assert claim.status == 'AWAITING_DEPARTMENT_REVIEW'
    assert claim.ta_supervisor_role_verified is True


@pytest.mark.django_db
def test_pg_assistantship_dept_review_and_hod_gate():
    claim = oap_service.submit_assistantship_claim(
        student_user_id=105, is_pg=True, month=10, year=2026,
        work_summary='Lab duties', hours_worked=Decimal('40.0'),
        thesis_supervisor_user_id=501, ta_supervisor_user_id=502
    )
    oap_service.verify_assistantship_supervisor(claim.id, 'THESIS', 501)
    oap_service.verify_assistantship_supervisor(claim.id, 'TA', 502)

    claim = oap_service.review_and_forward_assistantship(claim.id, dept_admin_user_id=401, remarks='Forwarded to HOD')
    assert claim.status == 'AWAITING_HOD_DECISION'

    # HOD approval (OA-BR-44)
    claim = oap_service.decide_assistantship_hod(claim.id, hod_user_id=201, decision='APPROVED', remarks='Approved')
    assert claim.status == 'APPROVED_AWAITING_STIPEND'


@pytest.mark.django_db
def test_pg_assistantship_stipend_disbursement():
    claim = oap_service.submit_assistantship_claim(
        student_user_id=105, is_pg=True, month=10, year=2026,
        work_summary='Lab duties', hours_worked=Decimal('40.0'),
        thesis_supervisor_user_id=501, ta_supervisor_user_id=502
    )
    # Cannot disburse before HOD approval (OA-BR-45)
    with pytest.raises(ValidationError, match="not approved by HoD"):
        oap_service.process_stipend_disbursement(claim.id, admin_user_id=301, disbursement_reference='REF-01')

    oap_service.verify_assistantship_supervisor(claim.id, 'THESIS', 501)
    oap_service.verify_assistantship_supervisor(claim.id, 'TA', 502)
    oap_service.review_and_forward_assistantship(claim.id, dept_admin_user_id=401)
    oap_service.decide_assistantship_hod(claim.id, hod_user_id=201, decision='APPROVED')

    # Now disburse
    disbursed = oap_service.process_stipend_disbursement(
        claim.id, admin_user_id=301, disbursement_reference='STIPEND-2026-OCT-105'
    )
    assert disbursed.status == 'STIPEND_PROCESSED'
    assert disbursed.disbursement_reference == 'STIPEND-2026-OCT-105'
    assert disbursed.disbursed_at is not None


# ==============================================================================
# 6. GRADUATE SEMINAR TESTS (OA-BR-61..63, BW-OAP-09)
# ==============================================================================

@pytest.mark.django_db
def test_graduate_seminar_request_and_scheduling():
    # Non-PG student rejected (OA-BR-61)
    with pytest.raises(ValidationError, match="Only PG students are eligible"):
        oap_service.request_graduate_seminar(
            student_user_id=107, is_pg=False, topic='Quantum Computing',
            abstract='Qubit states', preferred_date=date(2026, 11, 20)
        )

    sem = oap_service.request_graduate_seminar(
        student_user_id=107, is_pg=True, topic='Distributed Systems in Fusion',
        abstract='Consensus protocols in ERP', preferred_date=date(2026, 11, 20)
    )
    assert sem.status == 'AWAITING_SCHEDULING'

    scheduled = oap_service.schedule_graduate_seminar(
        seminar_id=sem.id, dept_admin_user_id=401,
        scheduled_date=date(2026, 11, 22), scheduled_time=time(15, 0), venue='Seminar Hall 1'
    )
    assert scheduled.status == 'SCHEDULED'
    assert scheduled.venue == 'Seminar Hall 1'


@pytest.mark.django_db
def test_graduate_seminar_venue_collision_guard():
    sem1 = oap_service.request_graduate_seminar(
        student_user_id=107, is_pg=True, topic='Topic 1', abstract='Abstract 1', preferred_date=date(2026, 11, 20)
    )
    oap_service.schedule_graduate_seminar(
        seminar_id=sem1.id, dept_admin_user_id=401,
        scheduled_date=date(2026, 11, 22), scheduled_time=time(15, 0), venue='Hall-A'
    )

    sem2 = oap_service.request_graduate_seminar(
        student_user_id=108, is_pg=True, topic='Topic 2', abstract='Abstract 2', preferred_date=date(2026, 11, 20)
    )
    # Booking same venue at same date and time must be blocked
    with pytest.raises(ValidationError, match="already booked"):
        oap_service.schedule_graduate_seminar(
            seminar_id=sem2.id, dept_admin_user_id=401,
            scheduled_date=date(2026, 11, 22), scheduled_time=time(15, 0), venue='Hall-A'
        )


@pytest.mark.django_db
def test_graduate_seminar_evaluation():
    sem = oap_service.request_graduate_seminar(
        student_user_id=107, is_pg=True, topic='Cloud Architecture', abstract='Microservices', preferred_date=date(2026, 11, 20)
    )
    oap_service.schedule_graduate_seminar(
        seminar_id=sem.id, dept_admin_user_id=401,
        scheduled_date=date(2026, 11, 25), scheduled_time=time(10, 0), venue='Hall-B'
    )
    evaluated = oap_service.evaluate_graduate_seminar(
        seminar_id=sem.id, faculty_user_id=501, result='SATISFACTORY', remarks='Excellent presentation'
    )
    assert evaluated.status == 'COMPLETED'
    assert evaluated.evaluation_result == 'SATISFACTORY'


# ==============================================================================
# 7. IMMUTABLE AUDIT TRAIL LOGGING TEST (PS 3.8, CFR-OAP-07)
# ==============================================================================

@pytest.mark.django_db
def test_oap_audit_trail_logging_verification():
    initial_count = OAPAuditTrail.objects.count()

    leave = oap_service.submit_student_leave(
        student_user_id=109, department='CSE', leave_type='CASUAL',
        start_date=date(2026, 11, 10), end_date=date(2026, 11, 11),
        reason='Audit test'
    )
    oap_service.decide_student_leave(leave_id=leave.id, hod_user_id=201, decision='APPROVED')

    final_count = OAPAuditTrail.objects.count()
    assert final_count == initial_count + 2

    latest_audit = OAPAuditTrail.objects.first()
    assert latest_audit.procedure_type == 'LEAVE'
    assert latest_audit.action == 'HOD_APPROVED'
    assert latest_audit.actor_user_id == 201
    assert latest_audit.new_state == 'APPROVED'
