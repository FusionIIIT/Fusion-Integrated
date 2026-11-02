from django.db import models
from django.db.models import Q
from django.utils import timezone


class LeavePolicy(models.Model):
    CATEGORIES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    category = models.CharField(max_length=3, choices=CATEGORIES, unique=True)
    faculty_entitlement = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    staff_entitlement = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    faculty_eligible = models.BooleanField(default=True)
    staff_eligible = models.BooleanField(default=True)
    continuous_days = models.BooleanField(default=False)
    vacation_period_required = models.BooleanField(default=False)
    evidence_required = models.BooleanField(default=False)
    substitute_required = models.BooleanField(default=False)
    carry_forward = models.BooleanField(default=False)
    carry_forward_cap = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.category

    def entitlement_for(self, employee_kind):
        return getattr(self, f"{employee_kind}_entitlement")


class LeaveBalance(models.Model):
    employee_id = models.PositiveIntegerField()
    employee_kind = models.CharField(max_length=16, choices=[
        ("faculty", "Faculty"), ("staff", "Staff"),
    ])
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORIES)
    year = models.PositiveSmallIntegerField()
    entitlement = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    carried_in = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    converted_in = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    remaining = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("employee_id", "category", "year"),
                name="elm_balance_employee_cat_year",
            ),
        ]
        indexes = [
            models.Index(fields=("employee_id", "year"), name="elm_balance_emp_year"),
        ]

    def __str__(self):
        return f"{self.category} u{self.employee_id} {self.year}: {self.remaining}"


class LeaveLedgerEntry(models.Model):
    TYPES = [
        ("credit", "Annual entitlement"),
        ("carry", "Carry forward"),
        ("conversion", "VL to EL conversion"),
        ("debit", "Approved leave"),
        ("restore", "Restored leave"),
        ("adjustment", "Resumption adjustment"),
        ("lapse", "Lapsed leave"),
    ]

    balance = models.ForeignKey(
        LeaveBalance, on_delete=models.CASCADE, related_name="entries",
    )
    entry_type = models.CharField(max_length=12, choices=TYPES)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    reference = models.CharField(max_length=120, unique=True)
    note = models.CharField(max_length=300, blank=True)
    actor_user_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")

    def __str__(self):
        return f"{self.entry_type} {self.amount} ({self.reference})"


class HolidayCalendar(models.Model):
    name = models.CharField(max_length=120)
    year = models.PositiveSmallIntegerField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-year", "-published_at")

    def __str__(self):
        return f"{self.name} ({self.year})"

    def publish(self):
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=("is_published", "published_at"))


class HolidayDate(models.Model):
    calendar = models.ForeignKey(
        HolidayCalendar, on_delete=models.CASCADE, related_name="dates",
    )
    date = models.DateField()
    is_closed = models.BooleanField(default=True)
    is_restricted = models.BooleanField(default=False)
    label = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("calendar", "date"), name="elm_calendar_date_unique",
            ),
        ]

    def __str__(self):
        return f"{self.date} {self.label}"


class VacationPeriod(models.Model):
    year = models.PositiveSmallIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    source_reference = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_vacation_period_order",
            ),
        ]

    def __str__(self):
        return f"{self.year}: {self.start_date} - {self.end_date}"


class LeaveHierarchy(models.Model):
    department = models.CharField(max_length=120)
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORIES)
    unit_head_user_id = models.PositiveIntegerField()
    final_authority_user_id = models.PositiveIntegerField(null=True, blank=True)
    establishment_user_id = models.PositiveIntegerField(null=True, blank=True)
    updated_by_user_id = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("department", "category"),
                name="elm_hierarchy_dept_category",
            ),
        ]

    def __str__(self):
        return f"{self.department}/{self.category}"


class LeaveApplication(models.Model):
    REQUEST_TYPES = [
        ("leave", "Leave application"),
        ("extension", "Extension"),
        ("cancellation", "Cancellation"),
        ("offline", "Offline-sanctioned leave"),
    ]
    STATUS = [
        ("substitute_response", "Awaiting substitute response"),
        ("unit_head_review", "Awaiting Unit Head review"),
        ("establishment_review", "Awaiting Establishment processing"),
        ("final_review", "Awaiting final decision"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]
    HALF_DAY_PERIODS = [
        ("full", "Full day"),
        ("first_half", "First half"),
        ("second_half", "Second half"),
    ]

    employee_id = models.PositiveIntegerField(db_index=True)
    employee_kind = models.CharField(max_length=16, choices=[
        ("faculty", "Faculty"), ("staff", "Staff"),
    ])
    department = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORIES)
    request_type = models.CharField(
        max_length=12, choices=REQUEST_TYPES, default="leave",
    )
    status = models.CharField(
        max_length=24, choices=STATUS, default="unit_head_review", db_index=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    actual_end_date = models.DateField(null=True, blank=True)
    half_day_period = models.CharField(
        max_length=12, choices=HALF_DAY_PERIODS, default="full",
    )
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=200, blank=True)
    station_contact = models.CharField(max_length=80, blank=True)
    evidence_reference = models.CharField(max_length=500, blank=True)
    substitute_user_id = models.PositiveIntegerField(null=True, blank=True)
    substitute_accepted = models.BooleanField(null=True, blank=True)
    parent_application = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="related_requests",
    )
    assigned_user_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    assigned_role = models.CharField(max_length=48, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    unit_head_recommendation = models.CharField(
        max_length=16, choices=[("recommended", "Recommended"),
                                ("not_recommended", "Not recommended")],
        blank=True,
    )
    final_decision_by = models.PositiveIntegerField(null=True, blank=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalation_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("employee_id", "status"), name="elm_app_emp_status"),
            models.Index(fields=("assigned_user_id", "status"), name="elm_app_task_status"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_application_date_order",
            ),
        ]

    def __str__(self):
        return f"{self.category} u{self.employee_id} {self.start_date}:{self.status}"

    @property
    def is_pending(self):
        return self.status in {
            "substitute_response", "unit_head_review",
            "establishment_review", "final_review",
        }


class LeaveDecision(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="decisions",
    )
    actor_user_id = models.PositiveIntegerField()
    action = models.CharField(max_length=24)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")

    def __str__(self):
        return f"application#{self.application_id} {self.action}"


class LeaveResumption(models.Model):
    application = models.OneToOneField(
        LeaveApplication, on_delete=models.CASCADE, related_name="resumption",
    )
    actual_resume_date = models.DateField()
    details = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=[("pending", "Pending"), ("approved", "Reviewed"),
                 ("rejected", "Rejected")],
        default="pending",
    )
    assigned_user_id = models.PositiveIntegerField()
    assigned_at = models.DateTimeField(default=timezone.now)
    reviewed_by_user_id = models.PositiveIntegerField(null=True, blank=True)
    review_note = models.CharField(max_length=500, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalation_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"resumption#{self.pk} application#{self.application_id} {self.status}"


class LeaveSLAConfig(models.Model):
    REQUEST_TYPES = [
        *LeaveApplication.REQUEST_TYPES,
        ("resumption", "Resumption review"),
    ]

    request_type = models.CharField(max_length=12, choices=REQUEST_TYPES)
    reminder_after_hours = models.PositiveIntegerField(null=True, blank=True)
    escalation_after_hours = models.PositiveIntegerField(null=True, blank=True)
    escalation_user_id = models.PositiveIntegerField(null=True, blank=True)
    changes_assignment = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("request_type",), name="elm_sla_request_type_unique",
            ),
        ]

    def __str__(self):
        return f"{self.request_type} SLA"


class LeaveSLAEvent(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="sla_events",
        null=True, blank=True,
    )
    resumption = models.ForeignKey(
        LeaveResumption, on_delete=models.CASCADE, related_name="sla_events",
        null=True, blank=True,
    )
    event_type = models.CharField(max_length=12, choices=[
        ("reminder", "Reminder"), ("escalation", "Escalation"),
    ])
    stage_key = models.CharField(max_length=48)
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(application__isnull=False, resumption__isnull=True)
                    | Q(application__isnull=True, resumption__isnull=False)
                ),
                name="elm_sla_event_has_one_target",
            ),
            models.UniqueConstraint(
                fields=("application", "event_type", "stage_key"),
                name="elm_sla_event_once_per_stage",
            ),
            models.UniqueConstraint(
                fields=("resumption", "event_type", "stage_key"),
                name="elm_sla_resumption_event_once",
            ),
        ]

    def __str__(self):
        target = f"application#{self.application_id}" if self.application_id else (
            f"resumption#{self.resumption_id}"
        )
        return f"{self.event_type} {target}"


class LeaveYearEndRun(models.Model):
    employee_id = models.PositiveIntegerField()
    year = models.PositiveSmallIntegerField()
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("employee_id", "year"), name="elm_year_end_employee_year",
            ),
        ]

    def __str__(self):
        return f"u{self.employee_id} year-end {self.year}"


class LeaveYearEndConfig(models.Model):
    month = models.PositiveSmallIntegerField(null=True, blank=True)
    day = models.PositiveSmallIntegerField(null=True, blank=True)
    updated_by_user_id = models.PositiveIntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Year-end boundary: {self.month}/{self.day}"
