"""Core Employee Leave Management records.

Employee references use IAM user IDs, never cross-module foreign keys.
Policy values are configurable; workflow services enforce transitions.
"""
from django.db import models
from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=80)
    annual_entitlement = models.DecimalField(
        max_digits=7, decimal_places=2, default=0
    )
    faculty_only = models.BooleanField(default=False)
    staff_only = models.BooleanField(default=False)
    carry_forward = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    requires_substitute = models.BooleanField(default=False)
    requires_medical_evidence = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_leave_policy"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    leave_code = models.CharField(max_length=8, db_index=True)
    leave_year = models.PositiveSmallIntegerField(db_index=True)
    opening_balance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    credited = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    consumed = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    adjusted = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_code", "leave_year"],
                name="elm_balance_user_type_year_uniq",
            ),
        ]

    @property
    def available(self):
        return self.opening_balance + self.credited + self.adjusted - self.consumed


class LeaveApplication(TimeStampedModel):
    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]
    STATES = [
        ("draft", "Draft"),
        ("awaiting_substitute", "Awaiting Substitute Response"),
        ("applicant_action", "Applicant Action Required"),
        ("unit_head_review", "Awaiting Unit Head Review"),
        ("establishment", "Awaiting Establishment Routing"),
        ("final_sanction", "Awaiting Final Sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]
    HALF_CHOICES = [
        ("full", "Full day"),
        ("first", "First half"),
        ("second", "Second half"),
    ]

    applicant_user_id = models.IntegerField(db_index=True)
    leave_code = models.CharField(max_length=8, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=8, choices=HALF_CHOICES, default="full"
    )
    purpose = models.TextField()
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=500, blank=True)
    medical_evidence_reference = models.CharField(max_length=500, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    responsibility_start = models.DateField(null=True, blank=True)
    responsibility_end = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=24, choices=STATES, default="draft", db_index=True
    )
    current_assignee_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    current_assignee_role = models.CharField(max_length=80, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)
    final_decision_by_user_id = models.IntegerField(null=True, blank=True)
    final_decision_reason = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["applicant_user_id", "status"],
                         name="elm_applicant_status_idx"),
            models.Index(fields=["current_assignee_user_id", "status"],
                         name="elm_assignee_status_idx"),
            models.Index(fields=["start_date", "end_date"],
                         name="elm_app_dates_idx"),
        ]

    def __str__(self):
        return f"{self.leave_code} #{self.pk} — user {self.applicant_user_id}"


class LeaveTransition(TimeStampedModel):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.PROTECT, related_name="history"
    )
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=40)
    remarks = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "elm_leave_transition"
        ordering = ["created_at"]


class LeaveCalendarDay(TimeStampedModel):
    DAY_TYPES = [
        ("holiday", "Holiday"),
        ("restricted", "Restricted Holiday"),
        ("vacation", "Vacation Period"),
        ("working", "Working Day"),
        ("closed", "Closed Day"),
    ]
    date = models.DateField(db_index=True)
    kind = models.CharField(max_length=16, choices=DAY_TYPES)
    title = models.CharField(max_length=160, blank=True)
    published = models.BooleanField(default=False)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    source_reference = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "elm_leave_calendar_day"
        indexes = [
            models.Index(fields=["date", "kind", "published"],
                         name="elm_calendar_lookup_idx"),
        ]


class LeaveHierarchyRule(TimeStampedModel):
    """Configurable routing step; role names are configured, not assumed."""
    leave_code = models.CharField(max_length=8, db_index=True)
    unit_code = models.CharField(max_length=80, blank=True)
    applicant_designation = models.CharField(max_length=100, blank=True)
    step_order = models.PositiveSmallIntegerField()
    actor_role = models.CharField(max_length=100)
    action_kind = models.CharField(
        max_length=20,
        choices=[
            ("recommend", "Recommendation"),
            ("process", "Processing"),
            ("sanction", "Final sanction"),
        ],
    )
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_hierarchy_rule"
        ordering = ["leave_code", "step_order"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "leave_code", "unit_code", "applicant_designation",
                    "step_order",
                ],
                name="elm_hierarchy_step_uniq",
            ),
        ]


class LeaveWorkflowSetting(TimeStampedModel):
    """Key/value settings for operational rules such as SLA durations."""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    description = models.CharField(max_length=300, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_workflow_setting"
