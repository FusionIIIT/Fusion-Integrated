"""Employee Leave Management domain tables.

People are referenced by plain `user_id` integers — no user table exists in
this database and cross-boundary references stay unconstrained.
"""

from django.db import models
from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    """Current configured parameters per leave category (BR-EL-030).
    No draft/publish/effective-version lifecycle."""

    CATEGORY = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]
    COUNTING_METHOD = [
        ("continuous", "Continuous (weekends/holidays in interval count)"),
        ("non_continuous", "Non-continuous (working days only)"),
    ]
    APPLIES_TO = [
        ("faculty", "Faculty"),
        ("staff", "Staff"),
        ("all", "All employees"),
    ]

    category = models.CharField(max_length=3, choices=CATEGORY, unique=True)
    name = models.CharField(max_length=60)
    annual_entitlement = models.DecimalField(max_digits=4, decimal_places=1)
    carry_forward = models.BooleanField(default=False)
    counting_method = models.CharField(max_length=15, choices=COUNTING_METHOD, default="non_continuous")
    applies_to = models.CharField(max_length=10, choices=APPLIES_TO, default="all")
    requires_vacation_period = models.BooleanField(default=False)
    requires_holiday_calendar = models.BooleanField(default=False)
    requires_medical_evidence = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_leave_policy"

    def __str__(self) -> str:
        return self.name


class LeaveBalance(TimeStampedModel):
    """Per-employee, per-category annual leave account (BR-EL-002–009)."""

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, db_index=True)
    year = models.PositiveIntegerField()

    entitlement = models.DecimalField(max_digits=4, decimal_places=1)
    balance = models.DecimalField(max_digits=4, decimal_places=2)
    used = models.DecimalField(max_digits=4, decimal_places=1)
    carried_forward = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "category", "year"], name="balance_unique_ucy"),
        ]
        indexes = [
            models.Index(fields=["user_id", "-year"], name="balance_user_year_idx"),
        ]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.category} {self.year}: {self.balance}d"


class LeaveApplication(TimeStampedModel):
    """A leave request and its lifecycle (CW-EL-01/02/03/04).

    Statuses: submitted, recommended, not_recommended, approved, rejected,
    withdrawn, cancelled.
    """

    CATEGORY_CHOICES = LeavePolicy.CATEGORY
    STATUS = [
        ("submitted", "Submitted"),
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]
    SUBSTITUTE_STATUS = [
        ("not_requested", "Not Requested"),
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]
    HALF_DAY = [("morning", "Morning"), ("afternoon", "Afternoon")]

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, db_index=True, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS, default="submitted", db_index=True)

    leave_start = models.DateField()
    leave_end = models.DateField()
    is_half_day = models.BooleanField(default=False)
    half_day = models.CharField(max_length=10, choices=HALF_DAY, blank=True)

    purpose = models.TextField()

    station_leave_required = models.BooleanField(default=False)
    station_leave_city = models.CharField(max_length=200, blank=True)
    station_leave_purpose = models.CharField(max_length=500, blank=True)

    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(max_length=12, choices=SUBSTITUTE_STATUS, default="not_requested")
    substitute_noted_at = models.DateTimeField(null=True, blank=True)

    is_extension = models.BooleanField(default=False)
    extension_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="extensions",
    )

    is_cancellation = models.BooleanField(default=False)
    cancellation_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="cancellations",
    )

    is_resumption = models.BooleanField(default=False)
    resumption_for = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="resumptions",
    )
    actual_resumption_date = models.DateField(null=True, blank=True)

    is_offline_sanctioned = models.BooleanField(default=False)
    offline_sanction_reference = models.CharField(max_length=300, blank=True)
    offline_sanctioned_by_user_id = models.IntegerField(null=True, blank=True)
    offline_sanctioned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        indexes = [
            models.Index(fields=["user_id", "status"], name="app_user_status_idx"),
            models.Index(fields=["user_id", "leave_start", "leave_end"], name="app_user_period_idx"),
        ]

    def __str__(self) -> str:
        return f"Leave #{self.pk} ({self.category}) u{self.user_id} [{self.status}]"


class ApprovalStep(TimeStampedModel):
    """One approval/recommendation action in the routing chain (BR-EL-016–020).

    CL/RH: Unit Head step is the final decision.
    SCL/EL/COL/VL: Unit Head recommends, higher authority is final.
    Establishment Processing step inserted where configured (BR-EL-019).
    Director self-sanction per BR-EL-020.
    """

    ROLE = [
        ("unit_head", "Unit Head"),
        ("deputy_registrar_estt", "Deputy Registrar (Estt.)"),
        ("dean", "Dean"),
        ("registrar", "Registrar"),
        ("director", "Director"),
        ("establishment_processing", "Establishment Processing"),
    ]
    STEP_TYPE = [
        ("recommendation", "Recommendation (not final)"),
        ("final_decision", "Final Decision"),
        ("establishment_verification", "Establishment Processing Step"),
    ]
    DECISION = ["pending", "approved", "rejected", "recommended", "not_recommended"]

    application = models.ForeignKey(
        "LeaveApplication", on_delete=models.CASCADE,
        related_name="approval_steps",
    )
    step_order = models.PositiveSmallIntegerField()
    assigned_user_id = models.IntegerField()
    assigned_role = models.CharField(max_length=30, choices=ROLE)
    step_type = models.CharField(max_length=30, choices=STEP_TYPE)

    decision = models.CharField(max_length=16, choices=DECISION, default="pending")
    comment = models.CharField(max_length=500, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_approval_step"
        indexes = [
            models.Index(fields=["application", "step_order"], name="step_app_order_idx"),
            models.Index(fields=["assigned_user_id", "decision"], name="step_assignee_open_idx"),
        ]

    def __str__(self) -> str:
        return f"#{self.application_id} s{self.step_order} {self.assigned_role} -> {self.decision}"


class HolidayCalendarEntry(TimeStampedModel):
    """Currently effective published holiday/RH calendar (BR-EL-031)."""

    date = models.DateField(db_index=True)
    is_restricted_holiday = models.BooleanField(default=False)
    published_at = models.DateTimeField()
    published_by_user_id = models.IntegerField(null=True, blank=True)
    year = models.PositiveIntegerField(db_index=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        indexes = [
            models.Index(fields=["year", "date", "published_at"], name="calendar_ydp_idx"),
        ]

    def __str__(self) -> str:
        suffix = " (RH)" if self.is_restricted_holiday else ""
        return f"{self.date}{suffix} pub:{self.year}"


class LeaveBalanceTransaction(TimeStampedModel):
    """Immutable audit row for every balance movement (BR-EL-028/029)."""

    REASON = [
        ("entitlement_grant", "Entitlement grant for the year"),
        ("carry_forward", "Carried forward from previous year"),
        ("vl_to_el_conversion", "Year-end VL to EL conversion"),
        ("leave_approved", "Leave approved - balance deducted"),
        ("leave_withdrawn", "Leave withdrawn - balance restored"),
        ("cancellation_approved", "Cancellation approved - balance restored"),
        ("cancellation_rejected", "Cancellation rejected - no change"),
        ("resumption_adjusted", "Resumption date adjustment"),
        ("offline_sanctioned", "Offline-sanctioned leave recorded"),
        ("admin_correction", "Administrative correction"),
    ]

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, db_index=True)
    year = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=4, decimal_places=2)
    reason = models.CharField(max_length=40, choices=REASON)
    related_application = models.ForeignKey(
        "LeaveApplication", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="balance_transactions",
    )
    reference = models.CharField(max_length=200, blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_balance_transaction"
        indexes = [
            models.Index(fields=["user_id", "category", "year", "-created_at"], name="tx_user_cat_year_idx"),
        ]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.category} {self.year} {self.amount:+.2f}d ({self.reason})"
