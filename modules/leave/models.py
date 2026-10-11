"""Database models for Employee Leave Management (ELM).
Adheres strictly to Fusion architecture:
- No foreign key crosses module boundary (uses user_id string/integer)
- Module owns its own tables and data integrity.
"""
from django.db import models
from django.utils import timezone


class LeavePolicy(models.Model):
    """Leave policy configuration parameters (CFR-EL-024, BR-EL-030).
    No publish lifecycle: current values govern.
    """
    category = models.CharField(max_length=10, unique=True)
    annual_entitlement = models.FloatField(default=0.0)
    allows_half_day = models.BooleanField(default=False)
    allows_carry_forward = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
    requires_medical_proof = models.BooleanField(default=False)
    is_continuous_count = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_policy"


class HolidayCalendar(models.Model):
    """Published holiday and Restricted Holiday (RH) calendar (CFR-EL-025, BR-EL-031)."""
    date = models.DateField(unique=True)
    description = models.CharField(max_length=255)
    is_restricted_holiday = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_holiday_calendar"


class VacationPeriod(models.Model):
    """Academic Calendar vacation periods for Faculty VL (BR-EL-006, EXT-01)."""
    title = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "leave_vacation_period"


class LeaveBalance(models.Model):
    """Annual and accumulated balance for an employee."""
    user_id = models.CharField(max_length=64, db_index=True)
    employee_type = models.CharField(max_length=20, default="faculty")  # faculty or staff
    category = models.CharField(max_length=10)
    year = models.IntegerField(default=timezone.now().year)
    balance = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_balance"
        unique_together = ("user_id", "category", "year")


class LeaveApplication(models.Model):
    """Core leave application supporting new, extension, cancellation, resumption (CW-EL-01 to 04)."""
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AWAITING_SUBSTITUTE", "Awaiting Substitute Response"),
        ("APPLICANT_ACTION_REQUIRED", "Applicant Action Required"),
        ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
        ("AWAITING_ESTABLISHMENT", "Awaiting Establishment Routing"),
        ("AWAITING_SANCTION", "Awaiting Final Sanction Decision"),
        ("AWAITING_DIRECTOR", "Awaiting Director Self-Sanction"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("CANCELLED", "Cancelled"),
        ("CANCELLATION_PENDING_UH", "Cancellation Pending - Unit Head"),
        ("CANCELLATION_PENDING_EST", "Cancellation Pending - Establishment"),
        ("CANCELLATION_PENDING_SANCTION", "Cancellation Pending - Sanction"),
        ("RESUMPTION_PENDING", "Resumption Review Pending"),
    ]

    applicant_id = models.CharField(max_length=64, db_index=True)
    applicant_role = models.CharField(max_length=50, default="faculty")  # faculty, staff, director
    category = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    chargeable_days = models.FloatField(default=1.0)
    purpose = models.TextField()

    # Half day CL support (BR-EL-010)
    is_half_day = models.BooleanField(default=False)
    half_day_type = models.CharField(max_length=15, blank=True, null=True)  # 'FIRST_HALF', 'SECOND_HALF'

    # Station leave coupling (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_leave_destination = models.CharField(max_length=255, blank=True, null=True)
    station_start_date = models.DateField(blank=True, null=True)
    station_end_date = models.DateField(blank=True, null=True)

    # Substitute coverage (BR-EL-014, 015)
    requires_substitute = models.BooleanField(default=False)
    substitute_id = models.CharField(max_length=64, blank=True, null=True)
    substitute_status = models.CharField(max_length=20, default="NOT_REQUIRED")  # PENDING, ACCEPTED, DECLINED

    # Hierarchy and routing
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, default="AWAITING_UNIT_HEAD")
    unit_head_id = models.CharField(max_length=64, blank=True, null=True)
    unit_head_recommendation = models.CharField(max_length=20, blank=True, null=True)  # RECOMMENDED, NOT_RECOMMENDED
    sanctioning_authority_id = models.CharField(max_length=64, blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    # Extension tracking (BR-EL-025)
    parent_leave = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extensions"
    )
    is_extension = models.BooleanField(default=False)

    # Resumption tracking (BR-EL-027, 028)
    actual_resumption_date = models.DateField(blank=True, null=True)
    resumption_status = models.CharField(max_length=20, blank=True, null=True)  # PENDING, REVIEWED

    # Offline synchronization (BR-EL-029)
    is_offline_sanctioned = models.BooleanField(default=False)
    offline_sanction_evidence = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_application"


class LeaveWorkflowActionLog(models.Model):
    """Audit log for all workflow transitions and SLA events (BR-EL-032, 033)."""
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="logs")
    actor_id = models.CharField(max_length=64)
    action = models.CharField(max_length=50)  # SUBMIT, ACCEPT_SUBSTITUTE, UH_RECOMMEND, APPROVE, REJECT, WITHDRAW, etc.
    from_status = models.CharField(max_length=35)
    to_status = models.CharField(max_length=35)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_action_log"


class LeaveSLAConfig(models.Model):
    """Configurable SLA reminder and escalation thresholds (CFR-EL-029, BR-EL-038)."""
    task_name = models.CharField(max_length=50, unique=True)
    reminder_threshold_hours = models.IntegerField(default=24)
    escalation_threshold_hours = models.IntegerField(default=48)
    escalation_role = models.CharField(max_length=50, default="registrar")

    class Meta:
        db_table = "leave_sla_config"
