"""ELM-owned leave records; institute identities are referenced by IAM id."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    CATEGORIES = [(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    category = models.CharField(max_length=3, choices=CATEGORIES, unique=True)
    faculty_entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    staff_entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    faculty_eligible = models.BooleanField(default=True)
    staff_eligible = models.BooleanField(default=True)
    carries_forward = models.BooleanField(default=False)
    max_carry_forward = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    continuous_count = models.BooleanField(default=False)
    requires_medical_evidence = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_leave_policy"
        constraints = [
            models.CheckConstraint(
                condition=Q(faculty_entitlement__gte=0), name="elm_fac_entitlement_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(staff_entitlement__gte=0), name="elm_staff_entitlement_nonnegative"
            ),
        ]


class OrganizationUnit(TimeStampedModel):
    name = models.CharField(max_length=160, unique=True)
    unit_head_user_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_organization_unit"


class EmployeeProfile(TimeStampedModel):
    FACULTY = "faculty"
    STAFF = "staff"
    user_id = models.PositiveIntegerField(unique=True, db_index=True)
    employee_kind = models.CharField(
        max_length=10, choices=[(FACULTY, "Faculty"), (STAFF, "Staff")]
    )
    designation = models.CharField(max_length=120, blank=True)
    unit = models.ForeignKey(OrganizationUnit, on_delete=models.PROTECT, related_name="employees")

    class Meta:
        db_table = "elm_employee_profile"


class HolidayCalendar(TimeStampedModel):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    year = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=160)
    status = models.CharField(
        max_length=12,
        choices=[(DRAFT, "Draft"), (PUBLISHED, "Published"), (ARCHIVED, "Archived")],
        default=DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        constraints = [
            models.UniqueConstraint(fields=["year", "title"], name="elm_calendar_year_title_uniq")
        ]


class Holiday(models.Model):
    PUBLIC = "public"
    RESTRICTED = "restricted"
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=[(PUBLIC, "Public"), (RESTRICTED, "Restricted")])

    class Meta:
        db_table = "elm_holiday"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date"], name="elm_holiday_date_uniq")
        ]

    def __str__(self):
        return f"{self.date}: {self.name}"


class VacationPeriod(models.Model):
    """Vacation windows synchronized from the institute Academic Calendar."""

    source_reference = models.CharField(max_length=160)
    starts_on = models.DateField()
    ends_on = models.DateField()
    academic_year = models.CharField(max_length=12)

    class Meta:
        db_table = "elm_vacation_period"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=models.F("starts_on")), name="elm_vacation_period_valid"
            )
        ]

    def __str__(self):
        return f"{self.academic_year}: {self.source_reference}"


class ApprovalRoute(TimeStampedModel):
    """Current configured higher-sanction path for a unit and leave category."""

    unit = models.ForeignKey(
        OrganizationUnit,
        on_delete=models.CASCADE,
        related_name="approval_routes",
        null=True,
        blank=True,
    )
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORIES)
    designation = models.CharField(max_length=120, blank=True)
    sequence = models.PositiveSmallIntegerField()
    stage = models.CharField(max_length=32)
    authority_user_id = models.PositiveIntegerField(null=True, blank=True)
    is_establishment = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_approval_route"
        constraints = [
            models.UniqueConstraint(
                fields=["unit", "category", "sequence"],
                name="elm_route_unit_category_sequence_uniq",
            )
        ]
        ordering = ["sequence"]


class LeaveAccount(TimeStampedModel):
    employee_user_id = models.PositiveIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORIES)
    year = models.PositiveSmallIntegerField()
    opening_balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    available_balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    entitlement = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_account"
        constraints = [
            models.UniqueConstraint(
                fields=["employee_user_id", "category", "year"],
                name="elm_account_employee_category_year_uniq",
            ),
            models.CheckConstraint(
                condition=Q(available_balance__gte=0), name="elm_account_balance_nonnegative"
            ),
        ]


class LeaveRequest(TimeStampedModel):
    CATEGORIES = LeavePolicy.CATEGORIES
    KINDS = [("leave", "Leave"), ("cancellation", "Cancellation"), ("extension", "Extension")]
    STATUSES = [
        (x, x.replace("_", " ").title())
        for x in (
            "awaiting_substitute",
            "applicant_action_required",
            "awaiting_unit_head",
            "awaiting_establishment",
            "awaiting_final_sanction",
            "awaiting_director_self",
            "approved",
            "rejected",
            "withdrawn",
            "cancelled",
        )
    ]
    employee_user_id = models.PositiveIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=CATEGORIES)
    request_kind = models.CharField(max_length=14, choices=KINDS, default="leave")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="related_requests"
    )
    starts_on = models.DateField()
    ends_on = models.DateField()
    chargeable_days = models.DecimalField(max_digits=6, decimal_places=2)
    cl_part = models.CharField(
        max_length=6, blank=True, choices=[("first", "First half"), ("second", "Second half")]
    )
    reason = models.CharField(max_length=1000)
    medical_evidence_reference = models.CharField(max_length=500, blank=True)
    station_leave = models.BooleanField(default=False)
    station_details = models.CharField(max_length=500, blank=True)
    substitute_user_id = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=32, choices=STATUSES, default="awaiting_unit_head", db_index=True
    )
    assigned_user_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    assigned_stage = models.CharField(max_length=32, blank=True)
    route_sequence = models.PositiveSmallIntegerField(default=0)
    director_self_sanction = models.BooleanField(default=False)
    unit_head_recommendation = models.CharField(
        max_length=16,
        blank=True,
        choices=[("recommended", "Recommended"), ("not_recommended", "Not recommended")],
    )
    decision_reason = models.CharField(max_length=1000, blank=True)
    sanction_reference = models.CharField(max_length=240, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    task_assigned_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalation_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["employee_user_id", "status"], name="elm_req_employee_status_idx"),
            models.Index(fields=["assigned_user_id", "status"], name="elm_req_assignee_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=models.F("starts_on")), name="elm_request_period_valid"
            )
        ]


class LeaveTransaction(TimeStampedModel):
    account = models.ForeignKey(LeaveAccount, on_delete=models.PROTECT, related_name="transactions")
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    kind = models.CharField(
        max_length=20,
        choices=[
            (x, x.replace("_", " ").title())
            for x in (
                "annual_credit",
                "carry_forward",
                "leave_debit",
                "cancellation_credit",
                "adjustment",
                "year_end_conversion",
                "lapse",
            )
        ],
    )
    reference = models.CharField(max_length=160, unique=True)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "elm_leave_transaction"
        ordering = ["created_at", "id"]


class LeaveRequestEvent(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="events")
    actor_user_id = models.PositiveIntegerField(null=True, blank=True)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    action = models.CharField(max_length=32)
    note = models.CharField(max_length=1000, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_request_event"
        ordering = ["at", "id"]

    def __str__(self):
        return f"{self.action}: leave request {self.request_id}"


class Resumption(models.Model):
    PENDING = "pending"
    REVIEWED = "reviewed"
    request = models.OneToOneField(
        LeaveRequest, on_delete=models.PROTECT, related_name="resumption"
    )
    actual_date = models.DateField()
    details = models.CharField(max_length=1000)
    status = models.CharField(
        max_length=12, default=PENDING, choices=[(PENDING, "Pending"), (REVIEWED, "Reviewed")]
    )
    reviewed_by_user_id = models.PositiveIntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(
        max_length=16,
        blank=True,
        choices=[("normal", "Normal"), ("early", "Early"), ("late", "Late")],
    )

    class Meta:
        db_table = "elm_resumption"

    def __str__(self):
        return f"Resumption for request {self.request_id}"


class WorkflowSetting(TimeStampedModel):
    reminder_hours = models.PositiveSmallIntegerField(default=24)
    escalation_hours = models.PositiveSmallIntegerField(default=72)
    escalation_user_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_workflow_setting"


class ELMNotification(models.Model):
    user_id = models.PositiveIntegerField(db_index=True)
    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_notification"
        ordering = ["-created_at"]

    def __str__(self):
        return self.message
