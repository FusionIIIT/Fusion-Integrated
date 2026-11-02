"""Business logic and workflow service layer for Other Academic Procedures (OAP).

Authoritatively implements all 17 Business Rules and 9 Workflows with
Phase 2 enterprise hardening:
- Immutable audit trail logging across all procedures
- Strict 7-domain authority validation and itemized dues tracking
- Dual-supervisor distinct role verification (Thesis + TA)
- Pro-rata stipend calculation with biometric attendance penalty
- Dynamic verification hash generation for certificates
- Venue collision prevention for graduate seminars
- Medical attachment guards for student leaves
"""
import hashlib
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone

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

MANDATORY_CLEARANCE_DOMAINS = [
    'LIBRARY', 'HOSTEL', 'MESS', 'DEPARTMENT', 'LAB', 'ACADEMIC_SECTION', 'STUDENT_SECTION'
]

DOMAIN_AUTHORITY_ROLE_MAP = {
    'LIBRARY': ['Librarian', 'admin'],
    'HOSTEL': ['Hostel Warden', 'admin'],
    'MESS': ['Mess In-charge', 'admin'],
    'DEPARTMENT': ['Department Administrator', 'admin'],
    'LAB': ['Lab Supervisor', 'admin'],
    'ACADEMIC_SECTION': ['Academic Administrator', 'admin'],
    'STUDENT_SECTION': ['Academic Administrator', 'Student Section', 'admin'],
}


# --- AUDIT TRAIL LOGGING ---

def record_audit_trail(procedure_type: str, record_id: int, action: str,
                       actor_user_id: int, actor_role: str,
                       previous_state: str, new_state: str,
                       remarks: str = None, metadata: dict = None) -> OAPAuditTrail:
    """Creates an immutable audit log entry for any OAP procedure transition."""
    return OAPAuditTrail.objects.create(
        procedure_type=procedure_type,
        record_id=record_id,
        action=action,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        previous_state=previous_state,
        new_state=new_state,
        remarks=remarks,
        metadata=metadata or {}
    )


# --- CHUNK 1: STUDENT LEAVE (OA-BR-11, BW-OAP-01, BW-OAP-02) ---

def submit_student_leave(student_user_id: int, department: str, leave_type: str,
                         start_date, end_date, reason: str,
                         document_reference: str = None,
                         medical_certificate_attached: bool = False) -> StudentLeave:
    if start_date > end_date:
        raise ValidationError("Start date must be before or equal to end date.")

    days = Decimal((end_date - start_date).days + 1)
    if leave_type.upper() == 'MEDICAL' and days > 3 and not medical_certificate_attached:
        raise ValidationError("Medical certificate attachment is mandatory for medical leave exceeding 3 days.")

    leave = StudentLeave.objects.create(
        user_id=student_user_id,
        department=department,
        leave_type=leave_type.upper(),
        start_date=start_date,
        end_date=end_date,
        chargeable_days=days,
        medical_certificate_attached=medical_certificate_attached,
        reason=reason,
        document_reference=document_reference,
        status='SUBMITTED'
    )
    record_audit_trail(
        procedure_type='LEAVE',
        record_id=leave.id,
        action='SUBMIT_LEAVE',
        actor_user_id=student_user_id,
        actor_role='student',
        previous_state=None,
        new_state='SUBMITTED',
        remarks=reason,
        metadata={'chargeable_days': float(days)}
    )
    send_oap_notification(student_user_id, 'ALERT', 'LEAVE_SUBMITTED',
                          f'Leave application submitted for {start_date} to {end_date} ({days} days).')
    return leave


def decide_student_leave(leave_id: int, hod_user_id: int, decision: str,
                         remarks: str = None) -> StudentLeave:
    decision_clean = decision.upper()
    if decision_clean not in ('APPROVED', 'REJECTED'):
        raise ValidationError("Decision must be APPROVED or REJECTED.")

    leave = StudentLeave.objects.get(id=leave_id)
    if leave.status != 'SUBMITTED':
        raise ValidationError(f"Cannot decide leave: current status is {leave.status}, must be SUBMITTED.")

    prev_state = leave.status
    leave.status = decision_clean
    leave.hod_user_id = hod_user_id
    leave.hod_remarks = remarks
    leave.decided_at = timezone.now()
    leave.save()

    record_audit_trail(
        procedure_type='LEAVE',
        record_id=leave.id,
        action=f'HOD_{decision_clean}',
        actor_user_id=hod_user_id,
        actor_role='HOD',
        previous_state=prev_state,
        new_state=decision_clean,
        remarks=remarks
    )
    send_oap_notification(leave.user_id, 'ALERT', 'LEAVE_DECIDED',
                          f'Your leave application has been {decision_clean}.')
    return leave


# --- CHUNK 2: BONAFIDE CERTIFICATES (OA-BR-21, OA-BR-22, BW-OAP-03, BW-OAP-04) ---

def request_bonafide_certificate(student_user_id: int, purpose: str,
                                certificate_type: str = 'STANDARD') -> BonafideRequest:
    request = BonafideRequest.objects.create(
        user_id=student_user_id,
        purpose=purpose,
        certificate_type=certificate_type.upper(),
        status='SUBMITTED'
    )
    record_audit_trail(
        procedure_type='BONAFIDE',
        record_id=request.id,
        action='REQUEST_BONAFIDE',
        actor_user_id=student_user_id,
        actor_role='student',
        previous_state=None,
        new_state='SUBMITTED',
        remarks=purpose
    )
    send_oap_notification(student_user_id, 'ALERT', 'BONAFIDE_REQUEST_SUBMITTED',
                          'Bonafide certificate request submitted.')
    return request


def decide_bonafide_request(request_id: int, admin_user_id: int, decision: str,
                            remarks: str = None) -> BonafideRequest:
    decision_clean = decision.upper()
    if decision_clean not in ('APPROVED', 'REJECTED'):
        raise ValidationError("Decision must be APPROVED or REJECTED.")

    req = BonafideRequest.objects.get(id=request_id)
    if req.status != 'SUBMITTED':
        raise ValidationError(f"Cannot decide bonafide request: current status is {req.status}, must be SUBMITTED.")

    prev_state = req.status
    req.status = decision_clean
    req.academic_admin_user_id = admin_user_id
    req.admin_remarks = remarks
    req.decided_at = timezone.now()

    if decision_clean == 'APPROVED':
        issue_date = timezone.now().date()
        req.issue_date = issue_date
        req.valid_until = issue_date + timedelta(days=180)
        req.certificate_number = f"BONAFIDE-{request_id}-{issue_date.strftime('%Y%m%d')}"
        raw_token = f"BONAFIDE:{request_id}:{req.user_id}:{issue_date.isoformat()}"
        req.verification_hash = hashlib.sha256(raw_token.encode()).hexdigest()[:16]

    req.save()
    record_audit_trail(
        procedure_type='BONAFIDE',
        record_id=req.id,
        action=f'ADMIN_{decision_clean}',
        actor_user_id=admin_user_id,
        actor_role='Academic Administrator',
        previous_state=prev_state,
        new_state=decision_clean,
        remarks=remarks,
        metadata={'certificate_number': req.certificate_number} if req.certificate_number else {}
    )
    send_oap_notification(req.user_id, 'ALERT', 'BONAFIDE_REQUEST_DECIDED',
                          f'Your Bonafide certificate request has been {decision_clean}.')
    return req


def can_download_bonafide(request_id: int) -> bool:
    req = BonafideRequest.objects.get(id=request_id)
    return req.status == 'APPROVED' and not req.is_expired


def get_certificate_data(instance) -> dict:
    if isinstance(instance, BonafideRequest):
        if not can_download_bonafide(instance.id):
            raise PermissionDenied("Bonafide certificate is not approved or has expired.")
        return {
            'certificate_type': 'BONAFIDE',
            'certificate_number': instance.certificate_number,
            'verification_hash': instance.verification_hash,
            'student_id': instance.user_id,
            'purpose': instance.purpose,
            'issue_date': str(instance.issue_date),
            'valid_until': str(instance.valid_until),
            'status': 'VERIFIED_VALID'
        }
    elif isinstance(instance, NoDuesRequest):
        if not can_download_no_dues_certificate(instance.id):
            raise PermissionDenied("No-dues certificate is not finalized.")
        return {
            'certificate_type': 'NO_DUES_CLEARANCE',
            'certificate_number': instance.certificate_number,
            'verification_hash': instance.verification_hash,
            'student_id': instance.user_id,
            'department': instance.department,
            'program': instance.program,
            'finalized_at': str(instance.finalized_at),
            'domains_cleared': 7,
            'status': 'ALL_CLEARED'
        }
    raise ValidationError("Unsupported certificate request.")


def verify_bonafide_authenticity(certificate_number: str, verification_hash: str) -> dict:
    req = BonafideRequest.objects.filter(certificate_number=certificate_number, verification_hash=verification_hash).first()
    if not req or req.status != 'APPROVED':
        return {'is_valid': False, 'message': 'Invalid certificate token or not approved.'}
    if req.valid_until and timezone.now().date() > req.valid_until:
        return {'is_valid': False, 'message': 'Certificate has expired.'}
    return {
        'is_valid': True,
        'certificate_number': req.certificate_number,
        'student_id': req.user_id,
        'purpose': req.purpose,
        'issue_date': str(req.issue_date)
    }


# --- CHUNK 3: NO-DUES CLEARANCE (OA-BR-31..34, BW-OAP-05, BW-OAP-06) ---

def initiate_no_dues_clearance(student_user_id: int, program: str, department: str) -> NoDuesRequest:
    existing = NoDuesRequest.objects.filter(
        user_id=student_user_id,
        status__in=['VERIFICATION_IN_PROGRESS', 'FINALIZED']
    ).first()
    if existing and existing.status == 'FINALIZED':
        raise ValidationError("Student has already finalized no-dues clearance.")
    if existing and existing.status == 'VERIFICATION_IN_PROGRESS':
        return existing

    req = NoDuesRequest.objects.create(
        user_id=student_user_id,
        program=program.upper(),
        department=department,
        status='VERIFICATION_IN_PROGRESS'
    )
    for domain in MANDATORY_CLEARANCE_DOMAINS:
        NoDuesAuthorityClearance.objects.create(
            no_dues_request=req,
            domain=domain,
            status='PENDING',
            dues_amount=Decimal('0.00')
        )
    record_audit_trail(
        procedure_type='NODUES',
        record_id=req.id,
        action='INITIATE_NODUES',
        actor_user_id=student_user_id,
        actor_role='student',
        previous_state=None,
        new_state='VERIFICATION_IN_PROGRESS'
    )
    send_oap_notification(student_user_id, 'ALERT', 'NODUES_INITIATED',
                          'No-dues clearance workflow initiated across all 7 domains.')
    return req


def verify_no_dues_domain(request_id: int, domain: str, verifier_user_id: int,
                          status: str, verifier_role: str = None,
                          dues_amount: Decimal = Decimal('0.00'),
                          fine_details: str = None,
                          receipt_reference: str = None,
                          remarks: str = None) -> NoDuesAuthorityClearance:
    domain_clean = domain.upper()
    status_clean = status.upper()

    if domain_clean not in MANDATORY_CLEARANCE_DOMAINS:
        raise ValidationError(f"Invalid clearance domain: {domain_clean}")
    if status_clean not in ('CLEARED', 'DUES_OUTSTANDING'):
        raise ValidationError(f"Invalid status: {status_clean}")

    # Enforce domain-specific authority role restriction (OA-BR-31)
    if verifier_role:
        allowed_roles = DOMAIN_AUTHORITY_ROLE_MAP.get(domain_clean, ['admin'])
        if verifier_role not in allowed_roles and 'admin' not in verifier_role:
            raise PermissionDenied(f"Role '{verifier_role}' is not authorized to clear domain '{domain_clean}'.")

    clearance = NoDuesAuthorityClearance.objects.get(no_dues_request_id=request_id, domain=domain_clean)
    prev_state = clearance.status

    if status_clean == 'DUES_OUTSTANDING' and dues_amount <= Decimal('0.00'):
        dues_amount = Decimal('100.00')  # Default dues penalty if none specified

    clearance.status = status_clean
    clearance.dues_amount = dues_amount
    clearance.fine_details = fine_details
    clearance.receipt_reference = receipt_reference
    clearance.remarks = remarks
    clearance.verifier_user_id = verifier_user_id
    clearance.verified_at = timezone.now()
    clearance.save()

    record_audit_trail(
        procedure_type='NODUES_DOMAIN',
        record_id=clearance.id,
        action=f'VERIFY_DOMAIN_{domain_clean}',
        actor_user_id=verifier_user_id,
        actor_role=verifier_role or 'Authority',
        previous_state=prev_state,
        new_state=status_clean,
        remarks=remarks,
        metadata={'domain': domain_clean, 'dues_amount': float(dues_amount)}
    )

    # Re-evaluate consolidation status independently (OA-BR-32)
    all_cl = NoDuesAuthorityClearance.objects.filter(no_dues_request_id=request_id)
    if all_cl.count() == 7 and not all_cl.filter(status='PENDING').exists():
        req = NoDuesRequest.objects.get(id=request_id)
        if all_cl.filter(status='DUES_OUTSTANDING').exists():
            req.status = 'VERIFICATION_COMPLETE_DUES_PENDING'
            req.all_domains_cleared = False
        else:
            req.status = 'VERIFICATION_COMPLETE_ALL_CLEAR'
            req.all_domains_cleared = True
        req.save()

    return clearance


def finalize_no_dues_clearance(request_id: int, admin_user_id: int,
                               remarks: str = None) -> NoDuesRequest:
    req = NoDuesRequest.objects.get(id=request_id)
    clearances = NoDuesAuthorityClearance.objects.filter(no_dues_request=req)

    # Enforce strict 7-domain finalization guard (OA-BR-33)
    if clearances.count() != 7:
        raise ValidationError("Cannot finalize no-dues clearance: missing authority clearances.")
    if clearances.filter(status='PENDING').exists():
        pending_domains = list(clearances.filter(status='PENDING').values_list('domain', flat=True))
        raise ValidationError(f"Cannot finalize: pending clearances remain for: {', '.join(pending_domains)}")
    if clearances.filter(status='DUES_OUTSTANDING').exists():
        outstanding = list(clearances.filter(status='DUES_OUTSTANDING').values_list('domain', flat=True))
        raise ValidationError(f"Cannot finalize: outstanding dues remain in: {', '.join(outstanding)}")

    prev_state = req.status
    req.status = 'FINALIZED'
    req.all_domains_cleared = True
    req.finalized_by_user_id = admin_user_id
    req.finalized_at = timezone.now()
    req.finalization_remarks = remarks

    issue_date = timezone.now().strftime('%Y%m%d')
    req.certificate_number = f"NODUES-{request_id}-{issue_date}"
    raw_hash = f"NODUES:{request_id}:{req.user_id}:{timezone.now().isoformat()}"
    req.verification_hash = hashlib.sha256(raw_hash.encode()).hexdigest()[:16]
    req.save()

    record_audit_trail(
        procedure_type='NODUES',
        record_id=req.id,
        action='FINALIZE_NODUES',
        actor_user_id=admin_user_id,
        actor_role='Academic Administrator',
        previous_state=prev_state,
        new_state='FINALIZED',
        remarks=remarks,
        metadata={'certificate_number': req.certificate_number}
    )
    send_oap_notification(req.user_id, 'ALERT', 'NODUES_FINALIZED',
                          f'Your No-Dues clearance is finalized. Certificate {req.certificate_number} is available.')
    return req


def can_download_no_dues_certificate(request_id: int) -> bool:
    req = NoDuesRequest.objects.get(id=request_id)
    return req.status == 'FINALIZED' and req.all_domains_cleared


# --- CHUNK 4: SUPERVISOR & TA ASSIGNMENTS (OA-BR-51, OA-BR-52) ---

def record_thesis_supervisor_assignment(student_user_id: int, faculty_user_id: int,
                                        department: str, academic_year: str,
                                        assigned_by_user_id: int) -> ThesisSupervisorAssignment:
    # Check for active duplicate assignment
    existing = ThesisSupervisorAssignment.objects.filter(
        student_user_id=student_user_id,
        academic_year=academic_year,
        is_active=True
    ).first()
    if existing:
        raise ValidationError(f"Student already has an active thesis supervisor for academic year {academic_year}.")

    assignment = ThesisSupervisorAssignment.objects.create(
        student_user_id=student_user_id,
        faculty_user_id=faculty_user_id,
        department=department,
        academic_year=academic_year,
        assigned_by_user_id=assigned_by_user_id,
        is_active=True
    )
    record_audit_trail(
        procedure_type='ASSIGNMENT',
        record_id=assignment.id,
        action='ASSIGN_THESIS_SUPERVISOR',
        actor_user_id=assigned_by_user_id,
        actor_role='Department Administrator',
        previous_state=None,
        new_state='ACTIVE',
        remarks=f'Assigned faculty {faculty_user_id} to student {student_user_id}'
    )
    return assignment


def record_ta_assignment(student_user_id: int, department: str, semester: str,
                         academic_year: str, assigned_by_user_id: int,
                         faculty_user_id: int = None, course_code: str = None,
                         course_name: str = None) -> TAAssignment:
    if course_code:
        existing = TAAssignment.objects.filter(
            student_user_id=student_user_id,
            course_code=course_code,
            semester=semester,
            academic_year=academic_year,
            is_active=True
        ).first()
        if existing:
            raise ValidationError(f"Student already assigned as TA for {course_code} in {semester} {academic_year}.")

    assignment = TAAssignment.objects.create(
        student_user_id=student_user_id,
        department=department,
        semester=semester,
        academic_year=academic_year,
        assigned_by_user_id=assigned_by_user_id,
        faculty_user_id=faculty_user_id,
        course_code=course_code,
        course_name=course_name,
        is_active=True
    )
    record_audit_trail(
        procedure_type='ASSIGNMENT',
        record_id=assignment.id,
        action='ASSIGN_TA',
        actor_user_id=assigned_by_user_id,
        actor_role='Department Administrator',
        previous_state=None,
        new_state='ACTIVE',
        remarks=f'Assigned TA for course {course_code}'
    )
    return assignment


# --- CHUNK 5: PG ASSISTANTSHIP CLAIMS (OA-BR-41..46, BW-OAP-07, BW-OAP-08) ---

def submit_assistantship_claim(student_user_id: int, is_pg: bool, month: int, year: int,
                               work_summary: str, hours_worked: Decimal,
                               thesis_supervisor_user_id: int, ta_supervisor_user_id: int,
                               stipend_amount: Decimal = Decimal('12400.00'),
                               attendance_percentage: Decimal = Decimal('100.00'),
                               funding_source: str = 'INSTITUTE_MHRD') -> AssistantshipClaim:
    if not is_pg:
        raise ValidationError("Only PG students are eligible to submit assistantship claims.")

    # Calculate pro-rata stipend based on biometric attendance threshold (< 80%)
    if attendance_percentage < Decimal('80.00'):
        pro_rata = stipend_amount * (attendance_percentage / Decimal('100.00'))
    else:
        pro_rata = stipend_amount

    claim = AssistantshipClaim.objects.create(
        user_id=student_user_id,
        month=month,
        year=year,
        work_summary=work_summary,
        hours_worked=hours_worked,
        thesis_supervisor_user_id=thesis_supervisor_user_id,
        ta_supervisor_user_id=ta_supervisor_user_id,
        stipend_amount=stipend_amount,
        attendance_percentage=attendance_percentage,
        pro_rata_stipend=pro_rata,
        funding_source=funding_source,
        status='AWAITING_DUAL_SUPERVISOR_VERIFICATION'
    )
    record_audit_trail(
        procedure_type='ASSISTANTSHIP',
        record_id=claim.id,
        action='SUBMIT_CLAIM',
        actor_user_id=student_user_id,
        actor_role='student',
        previous_state=None,
        new_state='AWAITING_DUAL_SUPERVISOR_VERIFICATION',
        remarks=work_summary,
        metadata={'pro_rata_stipend': float(pro_rata), 'attendance': float(attendance_percentage)}
    )
    send_oap_notification(student_user_id, 'ALERT', 'ASSISTANTSHIP_SUBMITTED',
                          f'Assistantship claim for {month}/{year} submitted.')
    return claim


def verify_assistantship_supervisor(claim_id: int, supervisor_role: str,
                                    supervisor_user_id: int,
                                    remarks: str = None) -> AssistantshipClaim:
    role_clean = supervisor_role.upper()
    claim = AssistantshipClaim.objects.get(id=claim_id)
    prev_state = claim.status

    if role_clean in ('THESIS', 'THESIS_SUPERVISOR'):
        claim.thesis_supervisor_verified = True
        claim.thesis_supervisor_role_verified = True
        claim.thesis_supervisor_remarks = remarks
        claim.thesis_supervisor_verified_at = timezone.now()
    elif role_clean in ('TA', 'TA_SUPERVISOR'):
        claim.ta_supervisor_verified = True
        claim.ta_supervisor_role_verified = True
        claim.ta_supervisor_remarks = remarks
        claim.ta_supervisor_verified_at = timezone.now()
    else:
        raise ValidationError(f"Invalid supervisor role: {supervisor_role}. Must be THESIS or TA.")

    # Both roles required (OA-BR-42)
    if claim.thesis_supervisor_role_verified and claim.ta_supervisor_role_verified:
        claim.status = 'AWAITING_DEPARTMENT_REVIEW'
    else:
        claim.status = 'AWAITING_OTHER_SUPERVISOR_VERIFICATION'

    claim.save()
    record_audit_trail(
        procedure_type='ASSISTANTSHIP',
        record_id=claim.id,
        action=f'VERIFY_SUPERVISOR_{role_clean}',
        actor_user_id=supervisor_user_id,
        actor_role='faculty',
        previous_state=prev_state,
        new_state=claim.status,
        remarks=remarks
    )
    return claim


def review_and_forward_assistantship(claim_id: int, dept_admin_user_id: int,
                                     remarks: str = None) -> AssistantshipClaim:
    claim = AssistantshipClaim.objects.get(id=claim_id)

    # Department review prerequisite guard (OA-BR-43)
    if not (claim.thesis_supervisor_role_verified and claim.ta_supervisor_role_verified):
        raise ValidationError("Cannot forward claim: dual supervisor verification is incomplete.")

    prev_state = claim.status
    claim.dept_admin_reviewed = True
    claim.dept_admin_remarks = remarks
    claim.dept_admin_reviewed_at = timezone.now()
    claim.status = 'AWAITING_HOD_DECISION'
    claim.save()

    record_audit_trail(
        procedure_type='ASSISTANTSHIP',
        record_id=claim.id,
        action='DEPT_ADMIN_REVIEW_FORWARD',
        actor_user_id=dept_admin_user_id,
        actor_role='Department Administrator',
        previous_state=prev_state,
        new_state='AWAITING_HOD_DECISION',
        remarks=remarks
    )
    return claim


def decide_assistantship_hod(claim_id: int, hod_user_id: int, decision: str,
                             remarks: str = None) -> AssistantshipClaim:
    decision_clean = decision.upper()
    claim = AssistantshipClaim.objects.get(id=claim_id)

    if claim.status != 'AWAITING_HOD_DECISION':
        raise ValidationError(f"Cannot decide claim: current status is {claim.status}, must be AWAITING_HOD_DECISION.")

    prev_state = claim.status
    if decision_clean == 'APPROVED':
        claim.status = 'APPROVED_AWAITING_STIPEND'
    elif decision_clean == 'REJECTED':
        claim.status = 'REJECTED'
    else:
        raise ValidationError("Decision must be APPROVED or REJECTED.")

    claim.hod_user_id = hod_user_id
    claim.hod_remarks = remarks
    claim.hod_decided_at = timezone.now()
    claim.save()

    record_audit_trail(
        procedure_type='ASSISTANTSHIP',
        record_id=claim.id,
        action=f'HOD_{decision_clean}',
        actor_user_id=hod_user_id,
        actor_role='HOD',
        previous_state=prev_state,
        new_state=claim.status,
        remarks=remarks
    )
    return claim


def process_stipend_disbursement(claim_id: int, admin_user_id: int,
                                 disbursement_reference: str) -> AssistantshipClaim:
    claim = AssistantshipClaim.objects.get(id=claim_id)

    # Stipend processing prerequisite guard (OA-BR-45)
    if claim.status != 'APPROVED_AWAITING_STIPEND':
        raise ValidationError("Cannot process stipend: claim is not approved by HoD.")

    prev_state = claim.status
    claim.status = 'STIPEND_PROCESSED'
    claim.disbursed_by_user_id = admin_user_id
    claim.disbursement_reference = disbursement_reference
    claim.disbursed_at = timezone.now()
    claim.save()

    record_audit_trail(
        procedure_type='ASSISTANTSHIP',
        record_id=claim.id,
        action='DISBURSE_STIPEND',
        actor_user_id=admin_user_id,
        actor_role='Academic Administrator',
        previous_state=prev_state,
        new_state='STIPEND_PROCESSED',
        remarks=f'Reference: {disbursement_reference}',
        metadata={'disbursed_amount': float(claim.pro_rata_stipend)}
    )
    send_oap_notification(claim.user_id, 'ALERT', 'STIPEND_PROCESSED',
                          f'Your assistantship stipend of INR {claim.pro_rata_stipend} has been disbursed.')
    return claim


# --- CHUNK 6: GRADUATE SEMINARS (OA-BR-61..63, BW-OAP-09) ---

def request_graduate_seminar(student_user_id: int, is_pg: bool, topic: str,
                             abstract: str, preferred_date) -> GraduateSeminarRequest:
    if not is_pg:
        raise ValidationError("Only PG students are eligible to request graduate seminar scheduling.")

    req = GraduateSeminarRequest.objects.create(
        user_id=student_user_id,
        topic=topic,
        abstract=abstract,
        preferred_date=preferred_date,
        status='AWAITING_SCHEDULING'
    )
    record_audit_trail(
        procedure_type='SEMINAR',
        record_id=req.id,
        action='REQUEST_SEMINAR',
        actor_user_id=student_user_id,
        actor_role='student',
        previous_state=None,
        new_state='AWAITING_SCHEDULING',
        remarks=topic
    )
    send_oap_notification(student_user_id, 'ALERT', 'SEMINAR_REQUESTED',
                          'Your seminar request has been received.')
    return req


def schedule_graduate_seminar(seminar_id: int, dept_admin_user_id: int,
                              scheduled_date, scheduled_time, venue: str) -> GraduateSeminarRequest:
    # Collision check: venue + date + time conflict
    collision = GraduateSeminarRequest.objects.filter(
        venue=venue,
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        status='SCHEDULED'
    ).exclude(id=seminar_id).first()
    if collision:
        raise ValidationError(f"Venue '{venue}' is already booked for date {scheduled_date} at {scheduled_time}.")

    seminar = GraduateSeminarRequest.objects.get(id=seminar_id)
    prev_state = seminar.status

    seminar.status = 'SCHEDULED'
    seminar.scheduled_date = scheduled_date
    seminar.scheduled_time = scheduled_time
    seminar.venue = venue
    seminar.scheduled_by_user_id = dept_admin_user_id
    seminar.scheduled_at = timezone.now()

    if not isinstance(seminar.history_log, list):
        seminar.history_log = []
    seminar.history_log.append({
        'action': 'SCHEDULED',
        'date': str(scheduled_date),
        'time': str(scheduled_time),
        'venue': venue,
        'by': dept_admin_user_id,
        'timestamp': timezone.now().isoformat()
    })
    seminar.save()

    record_audit_trail(
        procedure_type='SEMINAR',
        record_id=seminar.id,
        action='SCHEDULE_SEMINAR',
        actor_user_id=dept_admin_user_id,
        actor_role='Department Administrator',
        previous_state=prev_state,
        new_state='SCHEDULED',
        remarks=f'Venue: {venue}, Date: {scheduled_date} {scheduled_time}'
    )
    send_oap_notification(seminar.user_id, 'ALERT', 'SEMINAR_SCHEDULED',
                          f'Your seminar has been scheduled on {scheduled_date} at {venue}')
    return seminar


def evaluate_graduate_seminar(seminar_id: int, faculty_user_id: int, result: str,
                              remarks: str = None) -> GraduateSeminarRequest:
    result_clean = result.upper()
    if result_clean not in ('SATISFACTORY', 'UNSATISFACTORY'):
        raise ValidationError("Result must be SATISFACTORY or UNSATISFACTORY.")

    seminar = GraduateSeminarRequest.objects.get(id=seminar_id)
    if seminar.status != 'SCHEDULED':
        raise ValidationError("Can only evaluate seminars that are in SCHEDULED status.")

    prev_state = seminar.status
    seminar.status = 'COMPLETED'
    seminar.evaluation_result = result_clean
    seminar.history_log.append({
        'action': 'EVALUATED',
        'result': result_clean,
        'by': faculty_user_id,
        'remarks': remarks,
        'timestamp': timezone.now().isoformat()
    })
    seminar.save()

    record_audit_trail(
        procedure_type='SEMINAR',
        record_id=seminar.id,
        action=f'EVALUATE_{result_clean}',
        actor_user_id=faculty_user_id,
        actor_role='faculty',
        previous_state=prev_state,
        new_state='COMPLETED',
        remarks=remarks,
        metadata={'evaluation_result': result_clean}
    )
    return seminar


# --- NOTIFICATIONS (OA-BR-03) ---

def send_oap_notification(recipient_user_id: int, notification_type: str,
                          event_type: str, message: str) -> OAPNotification:
    return OAPNotification.objects.create(
        recipient_user_id=recipient_user_id,
        notification_type=notification_type,
        event_type=event_type,
        message=message,
        is_read=False
    )
