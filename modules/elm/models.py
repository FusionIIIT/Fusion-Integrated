from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=128)
    max_days_per_year = models.DecimalField(max_digits=5, decimal_places=1)
    is_continuous_count = models.BooleanField(default=False)
    is_faculty_only = models.BooleanField(default=False)
    is_non_faculty_only = models.BooleanField(default=False)
    carries_forward = models.BooleanField(default=False)
    requires_document = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"

    def __str__(self):
        return f"{self.code} - {self.name}"


class LeaveBalance(TimeStampedModel):
    employee_id = models.IntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveSmallIntegerField()
    allotted = models.DecimalField(max_digits=5, decimal_places=1)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    credited_from_vl = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("employee_id", "leave_type", "year")

    @property
    def available(self) -> float:
        return float(self.allotted - self.used)


class LeaveApplication(TimeStampedModel):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AWAITING_SUBSTITUTE", "Awaiting Substitute Response"),
        ("APPLICANT_ACTION_REQUIRED", "Applicant Action Required"),
        ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
        ("AWAITING_ESTABLISHMENT", "Awaiting Establishment Routing"),
        ("AWAITING_SANCTION", "Awaiting Final Sanction Decision"),
        ("AWAITING_DIRECTOR_SELF_SANCTION", "Awaiting Director Self-Sanction"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("CANCELLED", "Cancelled"),
    ]

    employee_id = models.IntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(
        max_length=16,
        choices=[("NONE", "None"), ("FIRST_HALF", "First Half"), ("SECOND_HALF", "Second Half")],
        default="NONE",
    )
    days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="DRAFT")

    # Station Leave coupling (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=256, blank=True)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)
    station_address = models.TextField(blank=True)
    station_contact_no = models.CharField(max_length=32, blank=True)

    # Substitute / Responsibility Coverage (BR-EL-014, BR-EL-015)
    substitute_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(
        max_length=16,
        choices=[("NONE", "None"), ("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("DECLINED", "Declined")],
        default="NONE",
    )
    substitute_declined_reason = models.TextField(blank=True)
    substitute_responded_at = models.DateTimeField(null=True, blank=True)

    # Workflow Review & Sanction (BR-EL-016..020)
    unit_head_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(
        max_length=16,
        choices=[
            ("NONE", "None"),
            ("RECOMMENDED", "Recommended"),
            ("NOT_RECOMMENDED", "Not Recommended"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
        ],
        default="NONE",
    )
    unit_head_remarks = models.TextField(blank=True)
    unit_head_decided_at = models.DateTimeField(null=True, blank=True)

    establishment_id = models.IntegerField(null=True, blank=True)
    establishment_remarks = models.TextField(blank=True)
    establishment_routed_at = models.DateTimeField(null=True, blank=True)

    sanctioning_authority_id = models.IntegerField(null=True, blank=True)
    sanctioning_authority_role = models.CharField(max_length=64, blank=True)
    remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"


class HolidayCalendar(TimeStampedModel):
    """Effective published holiday and restricted holiday calendar (BR-EL-003, BR-EL-031)."""
    year = models.PositiveSmallIntegerField()
    date = models.DateField()
    name = models.CharField(max_length=128)
    is_restricted_holiday = models.BooleanField(default=False)
    is_closed_holiday = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        unique_together = ("year", "date")


class AcademicVacationPeriod(TimeStampedModel):
    """Vacation periods from Academic Calendar (EXT-01, BR-EL-006)."""
    year = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=128)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_vacation_period"


class LeaveCancellationRequest(TimeStampedModel):
    """Pre-start cancellation of approved leave (BR-EL-023, CW-EL-02)."""
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="cancellation_requests")
    employee_id = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=[
            ("PENDING_UNIT_HEAD", "Pending Unit Head Review"),
            ("PENDING_ESTABLISHMENT", "Pending Establishment"),
            ("PENDING_SANCTION", "Pending Sanction Decision"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
        ],
        default="PENDING_UNIT_HEAD",
    )
    unit_head_recommendation = models.CharField(max_length=16, default="NONE")
    approver_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_cancellation_request"


class LeaveExtensionRequest(TimeStampedModel):
    """Extension of ongoing EL/COL/VL (BR-EL-025, CW-EL-03)."""
    original_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="extension_requests")
    employee_id = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    substitute_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=16, default="NONE")
    status = models.CharField(
        max_length=32,
        choices=[
            ("AWAITING_SUBSTITUTE", "Awaiting Substitute Response"),
            ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
            ("AWAITING_SANCTION", "Awaiting Sanction Decision"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
            ("WITHDRAWN", "Withdrawn"),
        ],
        default="AWAITING_UNIT_HEAD",
    )
    approver_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_extension_request"


class LeaveResumptionReport(TimeStampedModel):
    """Duty resumption declaration and adjustment (BR-EL-027, BR-EL-028, CW-EL-04)."""
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="resumption_reports")
    employee_id = models.IntegerField()
    actual_resumption_date = models.DateField()
    resumption_type = models.CharField(
        max_length=16,
        choices=[("NORMAL", "Normal"), ("EARLY", "Early"), ("LATE", "Late")],
        default="NORMAL",
    )
    adjusted_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    reason_for_difference = models.TextField(blank=True)
    status = models.CharField(
        max_length=16,
        choices=[("SUBMITTED", "Submitted"), ("REVIEWED", "Reviewed")],
        default="SUBMITTED",
    )
    reviewer_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_resumption_report"


class OfflineSanctionRecord(TimeStampedModel):
    """Retrospective recording of offline/paper sanctioned leave (BR-EL-029, BR-EL-037)."""
    employee_id = models.IntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1)
    sanction_order_no = models.CharField(max_length=128)
    sanction_order_date = models.DateField()
    sanctioned_by_role = models.CharField(max_length=64)
    recorded_by_id = models.IntegerField()
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "elm_offline_sanction"


class LeaveAuditTrail(TimeStampedModel):
    """Append-only audit trail for all leave transitions and actions."""
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="audit_trail")
    actor_id = models.IntegerField()
    action = models.CharField(max_length=64)
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "elm_audit_trail"
        ordering = ["created_at"]
