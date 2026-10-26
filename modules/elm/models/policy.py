"""Configurable leave policy, calendars, and annual employee accounts."""
from django.db import models
from django.db.models import F, Q


class LeavePolicy(models.Model):
    COUNTING_CHOICES = (
        ("WORKING_DAYS", "Working days from the published calendar"),
        ("CALENDAR_DAYS", "Every calendar day in the period"),
        ("RH_DATE", "One date from the published RH calendar"),
        ("VACATION_DAYS", "Dates in the published vacation calendar"),
    )
    leave_type_code = models.CharField(max_length=3, unique=True)
    employee_kinds = models.JSONField(default=list)
    annual_entitlement_by_kind = models.JSONField(default=dict, blank=True)
    annual_entitlement = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    day_counting = models.CharField(
        max_length=20, choices=COUNTING_CHOICES, default="WORKING_DAYS"
    )
    carries_forward = models.BooleanField(default=False)
    half_day_allowed = models.BooleanField(default=False)
    requires_medical_evidence = models.BooleanField(default=False)
    conversion_target_code = models.CharField(max_length=3, blank=True, default="")
    conversion_divisor = models.DecimalField(
        max_digits=5, decimal_places=2, default=1
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("leave_type_code",)

    def __str__(self):
        return f"{self.leave_type_code} policy"


class LeaveCalendar(models.Model):
    KIND_CHOICES = (
        ("HOLIDAY", "Holiday calendar"),
        ("RH", "Restricted holiday calendar"),
        ("VACATION", "Institute vacation calendar"),
    )
    STATUS_CHOICES = (("DRAFT", "Draft"), ("PUBLISHED", "Published"))
    kind = models.CharField(max_length=12, choices=KIND_CHOICES)
    year = models.PositiveSmallIntegerField()
    revision = models.PositiveSmallIntegerField(default=1)
    label = models.CharField(max_length=120)
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default="DRAFT"
    )
    effective_from = models.DateField()
    effective_through = models.DateField(null=True, blank=True)
    working_weekdays = models.JSONField(default=list)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("kind", "year", "-revision")
        constraints = [
            models.UniqueConstraint(
                fields=("kind", "year", "revision"),
                name="elm_calendar_revision_uniq",
            ),
            models.CheckConstraint(
                condition=Q(effective_through__isnull=True)
                | Q(effective_through__gte=F("effective_from")),
                name="elm_calendar_effective_range_ck",
            ),
        ]

    def __str__(self):
        return f"{self.label} ({self.kind}, {self.year}, r{self.revision})"


class LeaveCalendarDate(models.Model):
    calendar = models.ForeignKey(
        LeaveCalendar, on_delete=models.CASCADE, related_name="dates"
    )
    day = models.DateField()
    label = models.CharField(max_length=160, blank=True, default="")

    class Meta:
        ordering = ("day",)
        constraints = [
            models.UniqueConstraint(
                fields=("calendar", "day"), name="elm_calendar_date_uniq"
            )
        ]

    def __str__(self):
        return f"{self.day}: {self.label}"


class LeaveBalance(models.Model):
    """Per-employee annual account; IAM identity remains an external integer."""
    user_id = models.IntegerField(db_index=True)
    leave_type_code = models.CharField(max_length=3)
    year = models.PositiveSmallIntegerField()
    opening_balance = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    annual_credit = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    used_days = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    reserved_days = models.DecimalField(
        max_digits=8, decimal_places=2, default=0
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user_id", "year", "leave_type_code")
        constraints = [
            models.UniqueConstraint(
                fields=("user_id", "leave_type_code", "year"),
                name="elm_balance_owner_type_year_uniq",
            ),
            models.CheckConstraint(
                condition=Q(opening_balance__gte=0)
                & Q(annual_credit__gte=0)
                & Q(used_days__gte=0)
                & Q(reserved_days__gte=0),
                name="elm_balance_values_nonnegative_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user_id", "year"), name="elm_balance_user_year_idx"
            )
        ]

    def __str__(self):
        return f"User {self.user_id} {self.leave_type_code} balance ({self.year})"

    @property
    def available_days(self):
        return (
            self.opening_balance
            + self.annual_credit
            - self.used_days
            - self.reserved_days
        )


class LeaveBalanceEvent(models.Model):
    EVENT_CHOICES = (
        ("CREDIT", "Credit"),
        ("RESERVE", "Reserve for pending request"),
        ("RELEASE", "Release reservation"),
        ("USE", "Approved leave used"),
        ("RESTORE", "Balance restored"),
        ("CONVERSION", "Year-end conversion"),
        ("ADJUSTMENT", "Administrative adjustment"),
        ("YEAR_END", "Year-end balance processing"),
    )
    balance = models.ForeignKey(
        LeaveBalance, on_delete=models.PROTECT, related_name="events"
    )
    request = models.ForeignKey(
        "elm.LeaveRequest",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="balance_events",
    )
    event_type = models.CharField(max_length=16, choices=EVENT_CHOICES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=250, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "id")
        indexes = [
            models.Index(
                fields=("balance", "created_at"), name="elm_balance_event_idx"
            )
        ]

    def __str__(self):
        return f"{self.event_type} {self.amount} for balance {self.balance_id}"
