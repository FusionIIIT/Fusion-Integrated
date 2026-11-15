"""ELM-owned data. Fusion identities remain plain IAM user-id references."""
from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel

LEAVE_CATEGORIES = [
    ("CL", "Casual Leave"),
    ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"),
    ("EL", "Earned Leave"),
    ("COL", "Commuted Leave"),
    ("VL", "Vacation Leave"),
]


class OrgUnit(TimeStampedModel):
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    unit_head_user_id = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_org_unit"
        ordering = ["name"]

    def __str__(self):
        return self.name


class EmployeeProfile(TimeStampedModel):
    """ELM's leave-routing attributes for an employee; identity is owned by IAM."""
    user_id = models.IntegerField(primary_key=True)
    employee_kind = models.CharField(
        max_length=12, choices=[("faculty", "Faculty"), ("staff", "Staff")])
    unit = models.ForeignKey(
        OrgUnit, null=True, blank=True, on_delete=models.PROTECT,
        related_name="employees")
    designation = models.CharField(max_length=100, blank=True)
    requires_substitute = models.BooleanField(default=False)
    is_director = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_employee_profile"
        indexes = [models.Index(fields=["unit", "is_active"],
                                name="elm_employee_unit_idx")]


class LeavePolicy(TimeStampedModel):
    """Current policy parameters; no draft/publish policy-version lifecycle."""
    year = models.PositiveSmallIntegerField(unique=True)
    casual_days = models.DecimalField(max_digits=6, decimal_places=2,
                                     default=Decimal("8"))
    restricted_holiday_days = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("2"))
    special_casual_days = models.DecimalField(max_digits=6, decimal_places=2,
                                              default=Decimal("15"))
    earned_days = models.DecimalField(max_digits=6, decimal_places=2,
                                      default=Decimal("30"))
    commuted_days = models.DecimalField(max_digits=6, decimal_places=2,
                                        default=Decimal("20"))
    vacation_days = models.DecimalField(max_digits=6, decimal_places=2,
                                        default=Decimal("60"))
    reminder_after_hours = models.PositiveIntegerField(default=48)
    escalate_after_hours = models.PositiveIntegerField(default=96)

    class Meta:
        db_table = "elm_leave_policy"


class LeaveAccount(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LEAVE_CATEGORIES)
    year = models.PositiveSmallIntegerField()
    entitlement = models.DecimalField(max_digits=8, decimal_places=2,
                                      default=Decimal("0"))
    carry_forward = models.DecimalField(max_digits=8, decimal_places=2,
                                        default=Decimal("0"))
    used = models.DecimalField(max_digits=8, decimal_places=2,
                               default=Decimal("0"))
    balance = models.DecimalField(max_digits=8, decimal_places=2,
                                  default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_account"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "category", "year"],
                                    name="elm_account_user_cat_year_uniq"),
            models.CheckConstraint(condition=models.Q(balance__gte=0),
                                   name="elm_account_balance_nonnegative"),
        ]
        indexes = [models.Index(fields=["user_id", "year"],
                                name="elm_account_user_year_idx")]


class HolidayCalendar(TimeStampedModel):
    STATUS = [("draft", "Draft"), ("published", "Published"),
              ("superseded", "Superseded")]

    year = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=STATUS, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        constraints = [
            models.UniqueConstraint(
                fields=["year"], condition=models.Q(status="published"),
                name="elm_one_published_calendar_year"),
        ]
        ordering = ["-year", "-created_at"]


class Holiday(TimeStampedModel):
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=16, choices=[
        ("closed", "Closed Holiday"),
        ("restricted", "Restricted Holiday"),
    ])

    class Meta:
        db_table = "elm_holiday"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date", "kind"],
                                    name="elm_holiday_calendar_date_kind_uniq"),
        ]
        ordering = ["date", "name"]


class VacationPeriod(TimeStampedModel):
    """Vacation dates imported from the institute Academic Calendar."""
    academic_year = models.CharField(max_length=12)
    label = models.CharField(max_length=100)
    starts_on = models.DateField()
    ends_on = models.DateField()
    source = models.CharField(max_length=100, default="Institute Academic Calendar")

    class Meta:
        db_table = "elm_vacation_period"
        constraints = [
            models.CheckConstraint(condition=models.Q(ends_on__gte=models.F("starts_on")),
                                   name="elm_vacation_dates_ordered"),
        ]


class ApprovalRoute(TimeStampedModel):
    """Ordered higher-sanction path, resolved from unit/designation/category."""
    category = models.CharField(max_length=3, choices=LEAVE_CATEGORIES)
    unit = models.ForeignKey(OrgUnit, null=True, blank=True,
                             on_delete=models.CASCADE, related_name="approval_routes")
    designation = models.CharField(max_length=100, blank=True)
    steps = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_approval_route"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "unit", "designation"],
                name="elm_route_category_unit_designation_uniq"),
        ]


class LeaveRequest(TimeStampedModel):
    CATEGORY_CHOICES = LEAVE_CATEGORIES
    TYPE_CHOICES = [
        ("leave", "Leave application"),
        ("cancellation", "Approved leave cancellation"),
        ("extension", "Leave extension"),
        ("resumption", "Resumption of duty"),
    ]
    STATUS_CHOICES = [
        ("substitute_pending", "Awaiting substitute"),
        ("pending", "Pending approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    applicant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    request_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="leave")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="pending")
    starts_on = models.DateField()
    ends_on = models.DateField()
    half_day_part = models.CharField(
        max_length=12, choices=[("first_half", "First half"),
                                ("second_half", "Second half")],
        blank=True)
    requested_days = models.DecimalField(max_digits=8, decimal_places=2,
                                         default=Decimal("0"))
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=160, blank=True)
    station_contact = models.CharField(max_length=40, blank=True)
    medical_evidence = models.CharField(max_length=500, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(
        max_length=12, choices=[("pending", "Pending"), ("accepted", "Accepted"),
                                ("declined", "Declined")],
        blank=True)
    parent = models.ForeignKey("self", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="follow_ups")
    actual_resume_date = models.DateField(null=True, blank=True)
    offline_reference = models.CharField(max_length=160, blank=True)
    offline_sanctioned_on = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["applicant_user_id", "status"],
                         name="elm_request_app_status_idx"),
            models.Index(fields=["request_type", "status"],
                         name="elm_request_type_status_idx"),
            models.Index(fields=["starts_on", "ends_on"],
                         name="elm_request_dates_idx"),
        ]


class WorkflowTask(TimeStampedModel):
    STATUS = [
        ("waiting", "Waiting"), ("pending", "Pending"),
        ("approved", "Approved"), ("rejected", "Rejected"),
        ("recommended", "Recommended"), ("not_recommended", "Not recommended"),
        ("cancelled", "Cancelled"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="tasks")
    sequence = models.PositiveSmallIntegerField()
    role = models.CharField(max_length=80)
    assigned_user_id = models.IntegerField(db_index=True)
    is_final = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    assigned_at = models.DateTimeField(auto_now_add=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalation_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_workflow_task"
        constraints = [
            models.UniqueConstraint(fields=["request", "sequence"],
                                    name="elm_task_request_sequence_uniq"),
        ]
        ordering = ["sequence"]
        indexes = [models.Index(fields=["assigned_user_id", "status"],
                                name="elm_task_assignee_status_idx")]


class LeaveTransaction(TimeStampedModel):
    TYPE = [
        ("annual_credit", "Annual entitlement"),
        ("carry_forward", "Carry forward"),
        ("leave_debit", "Approved leave"),
        ("cancellation_restore", "Cancellation restoration"),
        ("resumption_adjustment", "Resumption adjustment"),
        ("year_end_lapse", "Year-end lapse"),
        ("vl_conversion", "VL to EL conversion"),
        ("offline_entry", "Offline-sanctioned leave"),
    ]

    account = models.ForeignKey(LeaveAccount, on_delete=models.PROTECT,
                                related_name="transactions")
    request = models.ForeignKey(LeaveRequest, null=True, blank=True,
                                on_delete=models.PROTECT,
                                related_name="transactions")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_type = models.CharField(max_length=24, choices=TYPE)
    reference = models.CharField(max_length=100, blank=True)
    idempotency_key = models.CharField(max_length=120, unique=True)
    actor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_transaction"
        ordering = ["created_at", "pk"]


class RequestEvent(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="events")
    actor_user_id = models.IntegerField(null=True, blank=True)
    event = models.CharField(max_length=40)
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_request_event"
        ordering = ["created_at", "pk"]


class YearEndRun(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processed_accounts = models.PositiveIntegerField(default=0)
    exceptions = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "elm_year_end_run"
