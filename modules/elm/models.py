"""ELM database models.

All user references are plain integer IDs (no cross-module FKs).
"""
from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeavePolicyConfig(TimeStampedModel):
    """System-wide leave policy parameters (CFR-EL-024, BR-EL-030)."""

    cl_annual_entitlement = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("8.00")
    )
    rh_annual_entitlement = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("2.00")
    )
    scl_annual_limit = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("15.00")
    )
    non_faculty_el_annual_credit = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("30.00")
    )
    faculty_vl_annual_entitlement = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("60.00")
    )
    col_annual_entitlement = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("20.00")
    )
    vl_to_el_conversion_ratio = models.DecimalField(
        max_digits=4, decimal_places=2, default=Decimal("0.50")
    )
    default_establishment_step_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_policy_config"

    def __str__(self) -> str:
        return f"ELM Policy Config (active={self.is_active})"


class HolidayCalendar(TimeStampedModel):
    """Calendar for a specific year (CFR-EL-025, BR-EL-031)."""

    year = models.PositiveSmallIntegerField(unique=True, db_index=True)
    label = models.CharField(max_length=100, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"Holiday Calendar {self.year} (published={self.is_published})"


class Holiday(TimeStampedModel):
    """Individual closed holiday or restricted holiday within a calendar."""

    HOLIDAY_TYPES = [
        ("closed_holiday", "Closed Holiday"),
        ("restricted_holiday", "Restricted Holiday"),
    ]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField(db_index=True)
    name = models.CharField(max_length=150)
    holiday_type = models.CharField(max_length=32, choices=HOLIDAY_TYPES)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elm_holiday"
        unique_together = [("calendar", "date", "holiday_type")]
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date} - {self.name} ({self.holiday_type})"


class VacationPeriod(TimeStampedModel):
    """Vacation periods supplied from the institute Academic Calendar for faculty VL (BR-EL-006)."""

    academic_year = models.CharField(max_length=32, db_index=True)  # e.g. "2026-27"
    name = models.CharField(max_length=100)                         # e.g. "Summer Vacation"
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_vacation_period"
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_date} to {self.end_date})"


class ApprovalHierarchy(TimeStampedModel):
    """Hierarchy routing resolution configuration (BR-EL-019, CFR-EL-014)."""

    department = models.CharField(max_length=80, blank=True, db_index=True)
    designation = models.CharField(max_length=80, blank=True, db_index=True)
    applicant_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    leave_category = models.CharField(max_length=16, blank=True)

    unit_head_user_id = models.IntegerField()
    establishment_user_id = models.IntegerField(null=True, blank=True)
    requires_establishment_step = models.BooleanField(default=True)
    sanctioning_authority_user_id = models.IntegerField()
    sanctioning_authority_role = models.CharField(max_length=64, default="Dean")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_approval_hierarchy"

    def __str__(self) -> str:
        dept = self.department or "*"
        desig = self.designation or "*"
        return f"Hierarchy: dept={dept} desig={desig} auth={self.sanctioning_authority_role}"


class LeaveAccount(TimeStampedModel, UserScopedModel):
    """Balance for a user, year, and category (CFR-EL-022, BR-EL-002..009)."""

    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=16, choices=CATEGORY_CHOICES, db_index=True)
    credited = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    carried_forward = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    availed = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    balance = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "elm_leave_account"
        unique_together = [("user_id", "year", "category")]
        indexes = [
            models.Index(fields=["user_id", "year"], name="elm_acc_user_year_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.category} ({self.year}): balance={self.balance}"


class LeaveBalanceTransaction(TimeStampedModel, UserScopedModel):
    """Audit log of balance changes (CFR-EL-028, AFR-EL-028.4)."""

    leave_account = models.ForeignKey(
        LeaveAccount, on_delete=models.CASCADE, related_name="transactions", null=True, blank=True
    )
    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=16, db_index=True)
    transaction_type = models.CharField(max_length=32, db_index=True)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    balance_after = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    reference_id = models.CharField(max_length=64, blank=True)
    remarks = models.TextField(blank=True)
    performed_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_balance_transaction"
        ordering = ["-created_at"]


class HalfDaySessionChoice(models.TextChoices):
    FIRST_HALF = "first_half", "First Half"
    SECOND_HALF = "second_half", "Second Half"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Leave request representing CW-EL-01 and CW-EL-02."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("awaiting_substitute", "Awaiting Substitute Response"),
        ("applicant_action_required", "Applicant Action Required"),
        ("awaiting_unit_head", "Awaiting Unit Head Review"),
        ("awaiting_director", "Awaiting Director Self-Sanction"),
        ("awaiting_establishment", "Awaiting Establishment Routing"),
        ("awaiting_final_decision", "Awaiting Final Sanction Decision"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancellation_pending_unit_head", "Cancellation Pending — Unit Head Review"),
        ("cancellation_pending_establishment", "Cancellation Pending — Establishment"),
        ("cancellation_pending_final", "Cancellation Pending — Final Decision"),
        ("cancelled", "Cancelled"),
    ]

    category = models.CharField(max_length=16, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    is_half_day = models.BooleanField(default=False)
    half_day_session = models.CharField(
        max_length=16,
        blank=True,
        default="",
        choices=HalfDaySessionChoice.choices,
    )
    chargeable_days = models.DecimalField(max_digits=5, decimal_places=2)
    purpose = models.TextField()
    medical_certificate = models.TextField(blank=True)

    # Station Leave Coupling (BR-EL-013, CFR-EL-002)
    is_station_leave = models.BooleanField(default=False)
    station_leave_departure = models.DateTimeField(null=True, blank=True)
    station_leave_return = models.DateTimeField(null=True, blank=True)
    station_destination = models.CharField(max_length=200, blank=True)
    station_address = models.TextField(blank=True)
    station_emergency_contact = models.CharField(max_length=100, blank=True)

    # Substitute Gate (BR-EL-014, BR-EL-015)
    requires_substitute = models.BooleanField(default=False)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(max_length=32, default="none")
    substitute_responded_at = models.DateTimeField(null=True, blank=True)
    substitute_remarks = models.TextField(blank=True)

    # Routing snapshot
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    establishment_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_authority_role = models.CharField(max_length=64, blank=True)

    # Unit Head Review (BR-EL-016, BR-EL-017)
    unit_head_recommendation = models.CharField(max_length=32, blank=True)
    unit_head_action_at = models.DateTimeField(null=True, blank=True)
    unit_head_remarks = models.TextField(blank=True)

    # Establishment Review (EL-UC-004)
    establishment_action_at = models.DateTimeField(null=True, blank=True)
    establishment_remarks = models.TextField(blank=True)

    # Final Sanction (EL-UC-005)
    final_decision = models.CharField(max_length=32, blank=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)
    final_decision_by_user_id = models.IntegerField(null=True, blank=True)
    final_decision_remarks = models.TextField(blank=True)

    # Lifecycle State
    status = models.CharField(
        max_length=48, choices=STATUS_CHOICES, default="awaiting_unit_head", db_index=True
    )
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawn_reason = models.TextField(blank=True)

    # Cancellation (CW-EL-02)
    cancellation_reason = models.TextField(blank=True)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    cancellation_decision = models.CharField(max_length=32, blank=True)
    cancellation_decision_at = models.DateTimeField(null=True, blank=True)
    cancellation_decision_by_user_id = models.IntegerField(null=True, blank=True)

    # Offline Sanction Entry (CFR-EL-027, BR-EL-029)
    is_offline_record = models.BooleanField(default=False)
    offline_reference_no = models.CharField(max_length=100, blank=True)
    offline_sanction_date = models.DateField(null=True, blank=True)
    offline_sanctioning_authority = models.CharField(max_length=150, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_app_user_status_idx"),
            models.Index(fields=["status", "category"], name="elm_app_status_cat_idx"),
        ]

    def __str__(self) -> str:
        return f"Leave #{self.id} (user={self.user_id}, {self.category}, {self.status})"


class LeaveExtension(TimeStampedModel):
    """Ongoing leave extension request (CW-EL-03, BR-EL-025, CFR-EL-020)."""

    STATUS_CHOICES = [
        ("awaiting_substitute", "Awaiting Extension Substitute Response"),
        ("applicant_action_required", "Extension Applicant Action Required"),
        ("awaiting_unit_head", "Awaiting Extension Unit Head Review"),
        ("awaiting_establishment", "Extension Pending — Establishment"),
        ("awaiting_final_decision", "Extension Pending — Final Decision"),
        ("approved", "Extended Leave in Effect — Incremental Period Posted"),
        ("rejected", "Original Ongoing Leave Unchanged"),
        ("withdrawn", "Extension Withdrawn"),
    ]

    leave_application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="extensions"
    )
    applicant_user_id = models.IntegerField(db_index=True)
    extended_start_date = models.DateField()
    extended_end_date = models.DateField()
    incremental_days = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField()

    # Substitute
    requires_substitute = models.BooleanField(default=False)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=32, default="none")
    substitute_responded_at = models.DateTimeField(null=True, blank=True)

    # Unit Head
    unit_head_recommendation = models.CharField(max_length=32, blank=True)
    unit_head_action_at = models.DateTimeField(null=True, blank=True)
    unit_head_remarks = models.TextField(blank=True)

    # Establishment
    establishment_action_at = models.DateTimeField(null=True, blank=True)
    establishment_remarks = models.TextField(blank=True)

    # Final decision
    status = models.CharField(
        max_length=48, choices=STATUS_CHOICES, default="awaiting_unit_head", db_index=True
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_extension"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Extension #{self.id} for Leave #{self.leave_application_id} ({self.status})"


class LeaveResumption(TimeStampedModel):
    """Resumption review for EL/COL/VL (CW-EL-04, BR-EL-027, BR-EL-028, CFR-EL-021)."""

    STATUS_CHOICES = [
        ("pending_review", "Resumption Review Pending"),
        ("reviewed_no_adjustment", "Resumption Reviewed — No Adjustment"),
        ("reviewed_early_adjusted", "Resumption Reviewed — Early Return Synchronized"),
        ("reviewed_late_adjusted", "Resumption Reviewed — Late Return Synchronized"),
    ]

    leave_application = models.OneToOneField(
        LeaveApplication, on_delete=models.CASCADE, related_name="resumption"
    )
    applicant_user_id = models.IntegerField(db_index=True)
    approved_end_date = models.DateField()
    actual_resumption_date = models.DateField()
    return_type = models.CharField(max_length=16)  # normal, early, late
    adjustment_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    resumption_details = models.TextField()

    status = models.CharField(
        max_length=48, choices=STATUS_CHOICES, default="pending_review", db_index=True
    )
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_resumption"

    def __str__(self) -> str:
        return f"Resumption for Leave #{self.leave_application_id} ({self.status})"


class WorkflowTask(TimeStampedModel):
    """Actionable workflow work item with SLA tracking (CFR-EL-030..032)."""

    TASK_STATUS = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    leave_application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True
    )
    extension = models.ForeignKey(
        LeaveExtension, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True
    )
    resumption = models.ForeignKey(
        LeaveResumption, on_delete=models.CASCADE, related_name="tasks", null=True, blank=True
    )

    task_type = models.CharField(max_length=48, db_index=True)
    assigned_to_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=24, choices=TASK_STATUS, default="pending", db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # SLA tracking
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_count = models.PositiveIntegerField(default=0)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalated_to_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_workflow_task"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assigned_to_user_id", "status"], name="elm_task_assignee_idx"),
        ]

    def __str__(self) -> str:
        return f"Task {self.task_type} -> user {self.assigned_to_user_id} ({self.status})"


class SlaThresholdConfig(TimeStampedModel):
    """Configurable reminder and escalation thresholds (BR-EL-038, CFR-EL-029)."""

    task_type = models.CharField(max_length=48, unique=True, db_index=True)
    reminder_threshold_hours = models.PositiveIntegerField(default=24)
    escalation_threshold_hours = models.PositiveIntegerField(default=48)
    escalation_action = models.CharField(
        max_length=32, default="notify_only",
        choices=[
            ("notify_only", "Notify Only"),
            ("escalate_routing", "Escalate Routing/Responsibility"),
        ],
    )
    escalation_target_role = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_sla_threshold_config"

    def __str__(self) -> str:
        return (
            f"SLA Config for {self.task_type}: remind={self.reminder_threshold_hours}h, "
            f"esc={self.escalation_threshold_hours}h"
        )


class LeaveAuditLog(TimeStampedModel):
    """Audit log for all workflow transitions and administrative actions."""

    leave_application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=48, db_index=True)
    from_state = models.CharField(max_length=48, blank=True)
    to_state = models.CharField(max_length=48, blank=True)
    remarks = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "elm_audit_log"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"Audit: {self.action} ({self.from_state} -> {self.to_state}) "
            f"by user {self.actor_user_id}"
        )


class YearEndRun(TimeStampedModel):
    """Audit evidence for event-triggered year-end processing (EL-UC-020, CFR-EL-028)."""

    year = models.PositiveSmallIntegerField(db_index=True)
    run_date = models.DateTimeField(auto_now_add=True)
    accounts_processed = models.PositiveIntegerField(default=0)
    cl_lapsed_count = models.PositiveIntegerField(default=0)
    rh_lapsed_count = models.PositiveIntegerField(default=0)
    scl_lapsed_count = models.PositiveIntegerField(default=0)
    vl_converted_count = models.PositiveIntegerField(default=0)
    total_el_credited_from_vl = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00")
    )
    el_carried_forward_count = models.PositiveIntegerField(default=0)
    col_carried_forward_count = models.PositiveIntegerField(default=0)
    exceptions = models.JSONField(default=list, blank=True)
    executed_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_year_end_run"
        ordering = ["-run_date"]

    def __str__(self) -> str:
        return f"Year-End Run for {self.year} at {self.run_date}"
