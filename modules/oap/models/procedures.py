from decimal import Decimal
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class OAPAuditTrail(TimeStampedModel):
    procedure_type = models.CharField(max_length=50)  # 'LEAVE', 'BONAFIDE', 'NODUES', 'ASSISTANTSHIP', 'SEMINAR', 'ASSIGNMENT'
    record_id = models.IntegerField()
    action = models.CharField(max_length=100)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=100)
    previous_state = models.CharField(max_length=50, null=True, blank=True)
    new_state = models.CharField(max_length=50)
    remarks = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']


class StudentLeave(UserScopedModel, TimeStampedModel):
    department = models.CharField(max_length=100)
    leave_type = models.CharField(max_length=50, default='CASUAL')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    chargeable_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('1.0'))
    medical_certificate_attached = models.BooleanField(default=False)
    document_reference = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, default='SUBMITTED', choices=[
        ('SUBMITTED', 'Submitted – Awaiting HoD Decision'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected')
    ])
    hod_user_id = models.IntegerField(null=True, blank=True)
    hod_remarks = models.TextField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)


class BonafideRequest(UserScopedModel, TimeStampedModel):
    purpose = models.CharField(max_length=255)
    certificate_type = models.CharField(max_length=100, default='STANDARD')
    status = models.CharField(max_length=20, default='SUBMITTED', choices=[
        ('SUBMITTED', 'Submitted – Awaiting Academic Administrator'),
        ('APPROVED', 'Approved – Certificate Available'),
        ('REJECTED', 'Rejected')
    ])
    academic_admin_user_id = models.IntegerField(null=True, blank=True)
    admin_remarks = models.TextField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    certificate_number = models.CharField(max_length=100, null=True, blank=True)
    verification_hash = models.CharField(max_length=64, null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    is_expired = models.BooleanField(default=False)


class NoDuesRequest(UserScopedModel, TimeStampedModel):
    program = models.CharField(max_length=10, choices=[('UG', 'Undergraduate'), ('PG', 'Postgraduate')], default='UG')
    department = models.CharField(max_length=100)
    status = models.CharField(max_length=50, default='VERIFICATION_IN_PROGRESS', choices=[
        ('VERIFICATION_IN_PROGRESS', 'Verification In Progress'),
        ('VERIFICATION_COMPLETE_ALL_CLEAR', 'Verification Complete – All Clear'),
        ('VERIFICATION_COMPLETE_DUES_PENDING', 'Verification Complete – Dues Pending'),
        ('FINALIZED', 'Finalized – Certificate Available'),
        ('REJECTED', 'Rejected')
    ])
    all_domains_cleared = models.BooleanField(default=False)
    finalized_by_user_id = models.IntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    certificate_number = models.CharField(max_length=100, null=True, blank=True)
    verification_hash = models.CharField(max_length=64, null=True, blank=True)
    finalization_remarks = models.TextField(null=True, blank=True)


class NoDuesAuthorityClearance(TimeStampedModel):
    no_dues_request = models.ForeignKey(NoDuesRequest, on_delete=models.CASCADE, related_name='clearances')
    domain = models.CharField(max_length=30, choices=[
        ('LIBRARY', 'Library'),
        ('HOSTEL', 'Hostel'),
        ('MESS', 'Mess'),
        ('DEPARTMENT', 'Respective Department'),
        ('LAB', 'Lab'),
        ('ACADEMIC_SECTION', 'Academic Section'),
        ('STUDENT_SECTION', 'Student Section')
    ])
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pending'),
        ('CLEARED', 'Cleared'),
        ('DUES_OUTSTANDING', 'Dues Outstanding')
    ])
    dues_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    fine_details = models.TextField(null=True, blank=True)
    receipt_reference = models.CharField(max_length=100, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    verifier_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['no_dues_request', 'domain'], name='unique_oap_request_domain')
        ]


class ThesisSupervisorAssignment(TimeStampedModel):
    student_user_id = models.IntegerField()
    faculty_user_id = models.IntegerField()
    department = models.CharField(max_length=100)
    academic_year = models.CharField(max_length=20)
    assigned_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)


class TAAssignment(TimeStampedModel):
    student_user_id = models.IntegerField()
    faculty_user_id = models.IntegerField(null=True, blank=True)
    course_code = models.CharField(max_length=20, null=True, blank=True)
    course_name = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100)
    semester = models.CharField(max_length=20)
    academic_year = models.CharField(max_length=20)
    assigned_by_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)


class AssistantshipClaim(UserScopedModel, TimeStampedModel):
    month = models.IntegerField()
    year = models.IntegerField()
    stipend_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('12400.00'))
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('100.00'))
    pro_rata_stipend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('12400.00'))
    funding_source = models.CharField(max_length=50, default='INSTITUTE_MHRD')
    work_summary = models.TextField()
    hours_worked = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    thesis_supervisor_user_id = models.IntegerField()
    ta_supervisor_user_id = models.IntegerField()
    thesis_supervisor_verified = models.BooleanField(default=False)
    thesis_supervisor_role_verified = models.BooleanField(default=False)
    thesis_supervisor_remarks = models.TextField(null=True, blank=True)
    thesis_supervisor_verified_at = models.DateTimeField(null=True, blank=True)
    ta_supervisor_verified = models.BooleanField(default=False)
    ta_supervisor_role_verified = models.BooleanField(default=False)
    ta_supervisor_remarks = models.TextField(null=True, blank=True)
    ta_supervisor_verified_at = models.DateTimeField(null=True, blank=True)
    dept_admin_reviewed = models.BooleanField(default=False)
    dept_admin_remarks = models.TextField(null=True, blank=True)
    dept_admin_reviewed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default='AWAITING_DUAL_SUPERVISOR_VERIFICATION', choices=[
        ('AWAITING_DUAL_SUPERVISOR_VERIFICATION', 'Awaiting Dual Supervisor Verification'),
        ('AWAITING_OTHER_SUPERVISOR_VERIFICATION', 'Awaiting Other Supervisor Verification'),
        ('AWAITING_DEPARTMENT_REVIEW', 'Awaiting Department Review'),
        ('AWAITING_HOD_DECISION', 'Awaiting HoD Decision'),
        ('APPROVED_AWAITING_STIPEND', 'Approved – Awaiting Stipend Processing'),
        ('STIPEND_PROCESSED', 'Stipend Processed'),
        ('REJECTED', 'Rejected')
    ])
    hod_user_id = models.IntegerField(null=True, blank=True)
    hod_remarks = models.TextField(null=True, blank=True)
    hod_decided_at = models.DateTimeField(null=True, blank=True)
    disbursed_by_user_id = models.IntegerField(null=True, blank=True)
    disbursement_reference = models.CharField(max_length=100, null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)


class GraduateSeminarRequest(UserScopedModel, TimeStampedModel):
    topic = models.CharField(max_length=255)
    abstract = models.TextField()
    preferred_date = models.DateField()
    status = models.CharField(max_length=30, default='AWAITING_SCHEDULING', choices=[
        ('AWAITING_SCHEDULING', 'Awaiting Scheduling'),
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed')
    ])
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_time = models.TimeField(null=True, blank=True)
    venue = models.CharField(max_length=100, null=True, blank=True)
    scheduled_by_user_id = models.IntegerField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    evaluation_result = models.CharField(max_length=30, null=True, blank=True, choices=[
        ('SATISFACTORY', 'Satisfactory'),
        ('UNSATISFACTORY', 'Unsatisfactory')
    ])
    history_log = models.JSONField(default=list, blank=True)


class OAPNotification(TimeStampedModel):
    recipient_user_id = models.IntegerField()
    notification_type = models.CharField(max_length=20, choices=[('ALERT', 'Alert'), ('EMAIL', 'Email')])
    event_type = models.CharField(max_length=50)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
