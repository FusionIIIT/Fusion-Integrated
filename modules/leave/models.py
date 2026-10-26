"""Data models for Employee Leave Management (ELM) - Qwen 14B setup.
Enforces all domain entities, relational integrity inside module boundaries, and no cross-module foreign keys.
"""
from django.db import models
from django.utils import timezone


class LeavePolicyConfig(models.Model):
    """CFR-EL-024, BR-EL-030: Current configured policy parameters."""
    category = models.CharField(max_length=10, unique=True)
    annual_entitlement = models.FloatField(default=0.0)
    allows_half_day = models.BooleanField(default=False)
    allows_carry_forward = models.BooleanField(default=False)
    is_continuous_count = models.BooleanField(default=False)
    requires_substitute_default = models.BooleanField(default=False)
    requires_medical_proof = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_policy_config"


class HolidayCalendar(models.Model):
    """CFR-EL-025, BR-EL-031: Published holiday & restricted holiday calendar."""
    date = models.DateField(unique=True)
    title = models.CharField(max_length=200)
    is_restricted_holiday = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_holiday_calendar"


class AcademicVacationPeriod(models.Model):
    """EXT-01 & BR-EL-006: External academic calendar vacation periods for VL."""
    title = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "elm_vacation_period"


class LeaveAccount(models.Model):
    """Employee leave ledger and annual balance (CFR-EL-004-009)."""
    user_id = models.CharField(max_length=64, db_index=True)
    employee_type = models.CharField(max_length=20, default="faculty")
    category = models.CharField(max_length=10)
    year = models.IntegerField(default=timezone.now().year)
    balance = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_account"
        unique_together = ("user_id", "category", "year")


class LeaveRequest(models.Model):
    """Leave request entity governing all lifecycle paths (CW-EL-01, CW-EL-02, CW-EL-03, CW-EL-04)."""
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
        ("CANCELLATION_PENDING_UH", "Cancellation Pending - Unit Head Review"),
        ("CANCELLATION_PENDING_EST", "Cancellation Pending - Establishment"),
        ("CANCELLATION_PENDING_SANCTION", "Cancellation Pending - Sanctioning Decision"),
        ("RESUMPTION_PENDING", "Resumption Review Pending"),
        ("RESUMPTION_REVIEWED", "Resumption Reviewed"),
    ]

    applicant_id = models.CharField(max_length=64, db_index=True)
    applicant_role = models.CharField(max_length=50, default="faculty")
    department = models.CharField(max_length=100, default="CSE")
    category = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    chargeable_days = models.FloatField(default=1.0)
    purpose = models.TextField()

    # Half day attributes (BR-EL-010)
    is_half_day = models.BooleanField(default=False)
    half_day_type = models.CharField(max_length=20, blank=True, null=True)

    # Station Leave coupling (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=255, blank=True, null=True)
    station_address = models.TextField(blank=True, null=True)

    # Substitute Gate (BR-EL-014, BR-EL-015)
    requires_substitute = models.BooleanField(default=False)
    substitute_id = models.CharField(max_length=64, blank=True, null=True)
    substitute_status = models.CharField(max_length=20, default="NOT_REQUIRED")

    # Workflow routing and status
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="AWAITING_UNIT_HEAD")
    unit_head_id = models.CharField(max_length=64, blank=True, null=True)
    unit_head_recommendation = models.CharField(max_length=20, blank=True, null=True)
    establishment_user_id = models.CharField(max_length=64, blank=True, null=True)
    sanctioning_authority_id = models.CharField(max_length=64, blank=True, null=True)
    routing_config = models.ForeignKey(
        "LeaveHierarchyConfig", null=True, blank=True, on_delete=models.PROTECT,
        related_name="routed_requests",
    )
    final_decision_notes = models.TextField(blank=True, null=True)

    # Extension (CW-EL-03, BR-EL-025)
    parent_request = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extension_requests")
    is_extension = models.BooleanField(default=False)

    # Resumption (CW-EL-04, BR-EL-027, 028)
    actual_resumption_date = models.DateField(blank=True, null=True)
    resumption_notes = models.TextField(blank=True, null=True)

    # Offline synchronization (BR-EL-029)
    is_offline_sync = models.BooleanField(default=False)
    offline_sanction_reference = models.CharField(max_length=255, blank=True, null=True)
    offline_unavailable_reason = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_request"
        constraints = [models.UniqueConstraint(
            fields=("applicant_id", "offline_sanction_reference"),
            condition=models.Q(is_offline_sync=True),
            name="elm_offline_reference_unique",
        )]


class LeaveTransitionAudit(models.Model):
    """Complete state transition and audit trail (CFR-EL-016, BR-EL-032, 033)."""
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="audit_logs")
    actor_id = models.CharField(max_length=64)
    action = models.CharField(max_length=50)
    from_state = models.CharField(max_length=40)
    to_state = models.CharField(max_length=40)
    remarks = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_transition_audit"


class LeaveSLASettings(models.Model):
    """CFR-EL-029, BR-EL-038: SLA configuration thresholds."""
    task_code = models.CharField(max_length=50, unique=True)
    reminder_hours = models.IntegerField(default=24)
    escalation_hours = models.IntegerField(default=48)
    escalation_authority = models.CharField(max_length=64, default="director")

    class Meta:
        db_table = "elm_sla_settings"


class LeaveHierarchyConfig(models.Model):
    """Current route for a department, designation, and leave category."""
    department = models.CharField(max_length=100)
    applicant_role = models.CharField(max_length=50)
    category = models.CharField(max_length=10)
    unit_head_id = models.CharField(max_length=64, blank=True)
    establishment_user_id = models.CharField(max_length=64, blank=True)
    sanctioning_authority_id = models.CharField(max_length=64, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_hierarchy_config"
        constraints = [models.UniqueConstraint(
            fields=("department", "applicant_role", "category"),
            name="elm_hierarchy_route_unique",
        )]

    def __str__(self) -> str:
        return f"{self.department} / {self.applicant_role} / {self.category}"


class HolidayCalendarRelease(models.Model):
    """A staged calendar replacement; only one release governs validation."""
    name = models.CharField(max_length=120)
    is_current = models.BooleanField(default=False)
    created_by = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_calendar_release"
        constraints = [models.UniqueConstraint(
            fields=("is_current",), condition=models.Q(is_current=True),
            name="elm_one_current_calendar",
        )]

    def __str__(self) -> str:
        return self.name


class HolidayCalendarEntry(models.Model):
    """Date data belonging to a staged or published calendar release."""
    release = models.ForeignKey(
        HolidayCalendarRelease, on_delete=models.CASCADE, related_name="entries"
    )
    date = models.DateField()
    title = models.CharField(max_length=200)
    is_restricted_holiday = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_calendar_entry"
        constraints = [models.UniqueConstraint(
            fields=("release", "date"), name="elm_calendar_date_unique"
        )]

    def __str__(self) -> str:
        return f"{self.date}: {self.title}"


class AttendanceSyncOutbox(models.Model):
    """Durable event for downstream attendance synchronization."""
    STATUS_CHOICES = [
        ("pending", "Pending"), ("delivered", "Delivered"), ("failed", "Failed"),
    ]
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="attendance_sync_events"
    )
    event_key = models.CharField(max_length=160, unique=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_attendance_sync_outbox"
        indexes = [models.Index(fields=("status", "created_at"), name="elm_att_sync_pending_idx")]

    def __str__(self) -> str:
        return f"{self.event_key} [{self.status}]"
