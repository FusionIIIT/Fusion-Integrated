"""Leave Management models — Django ORM only, no business logic."""
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    VL = "VL", "Vacation Leave"
    COL = "COL", "Commuted Leave"


class LeaveStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    SUBSTITUTE_PENDING = "substitute_pending", "Substitute Pending"
    UNIT_HEAD_REVIEW = "unit_head_review", "Unit Head Review"
    ESTABLISHMENT_REVIEW = "establishment_review", "Establishment Review"
    FINAL_SANCTION = "final_sanction", "Final Sanction"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
    CANCELLED = "cancelled", "Cancelled"
    EXTENSION_REQUESTED = "extension_requested", "Extension Requested"
    RESUMPTION_PENDING = "resumption_pending", "Resumption Pending"
    RESUMED = "resumed", "Resumed"


class EmployeeType(models.TextChoices):
    FACULTY = "faculty", "Faculty"
    NON_FACULTY = "non_faculty", "Non-Faculty"


class LeavePolicy(TimeStampedModel):
    """Effective leave policy parameters per category and employee type."""
    category = models.CharField(max_length=4, choices=LeaveCategory.choices, db_index=True)
    employee_type = models.CharField(max_length=12, choices=EmployeeType.choices, db_index=True)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=2)
    carries_forward = models.BooleanField(default=False)
    half_day_allowed = models.BooleanField(default=False)
    requires_medical_certificate = models.BooleanField(default=False)
    max_per_request = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    effective_from = models.DateField(db_index=True)
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["category", "employee_type", "effective_from"],
                name="leave_policy_unique_effective",
            ),
        ]
        indexes = [
            models.Index(fields=["category", "employee_type", "is_active", "-effective_from"],
                         name="leave_policy_lookup_idx"),
        ]

    def __str__(self):
        return f"{self.category} ({self.employee_type}) from {self.effective_from}"


class HolidayCalendar(TimeStampedModel):
    """Holiday and Restricted Holiday calendar."""
    date = models.DateField(db_index=True)
    name = models.CharField(max_length=200)
    is_restricted = models.BooleanField(default=False)  # True = RH, False = Holiday
    year = models.IntegerField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["date", "is_restricted"],
                name="holiday_calendar_unique_date_type",
            ),
        ]
        indexes = [
            models.Index(fields=["year", "is_restricted", "is_active"], name="holiday_cal_year_idx"),
        ]

    def __str__(self):
        return f"{self.date} - {self.name} ({'RH' if self.is_restricted else 'Holiday'})"


class LeaveBalance(TimeStampedModel):
    """Leave balance per user, category, and year."""
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=4, choices=LeaveCategory.choices, db_index=True)
    year = models.IntegerField(db_index=True)
    opening_balance = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    credited = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    availed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    lapsed = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "category", "year"],
                name="leave_balance_unique_user_cat_year",
            ),
            models.CheckConstraint(
                check=models.Q(closing_balance__gte=0),
                name="leave_balance_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "year", "category"], name="leave_bal_user_year_idx"),
        ]

    def __str__(self):
        return f"User {self.user_id} - {self.category} {self.year}: {self.closing_balance}"


class LeaveRequest(TimeStampedModel):
    """Main leave request entity."""
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=4, choices=LeaveCategory.choices, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    half_day = models.BooleanField(default=False)
    half_day_session = models.CharField(max_length=10, blank=True)  # forenoon/afternoon
    total_days = models.DecimalField(max_digits=5, decimal_places=2)
    purpose = models.TextField(max_length=1000)
    station_leave = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True)
    substitute_id = models.IntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=24,
        choices=LeaveStatus.choices,
        default=LeaveStatus.DRAFT,
        db_index=True,
    )
    medical_certificate = models.FileField(upload_to="leave/medical/", null=True, blank=True)
    unit_head_id = models.IntegerField(null=True, blank=True)
    unit_head_remark = models.TextField(blank=True)
    unit_head_action_at = models.DateTimeField(null=True, blank=True)
    establishment_id = models.IntegerField(null=True, blank=True)
    establishment_remark = models.TextField(blank=True)
    establishment_action_at = models.DateTimeField(null=True, blank=True)
    final_authority_id = models.IntegerField(null=True, blank=True)
    final_authority_remark = models.TextField(blank=True)
    final_authority_action_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    extension_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extensions",
    )
    original_request = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancellations",
    )
    resumption_date = models.DateField(null=True, blank=True)
    resumption_verified_by = models.IntegerField(null=True, blank=True)
    resumption_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_date__gte=models.F("start_date")),
                name="leave_request_end_after_start",
            ),
            models.CheckConstraint(
                check=models.Q(total_days__gt=0),
                name="leave_request_positive_days",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status", "-created_at"], name="leave_req_user_status_idx"),
            models.Index(fields=["status", "-created_at"], name="leave_req_status_idx"),
            models.Index(fields=["substitute_id", "status"], name="leave_req_substitute_idx"),
            models.Index(fields=["unit_head_id", "status"], name="leave_req_unit_head_idx"),
            models.Index(fields=["start_date", "end_date", "status"], name="leave_req_date_range_idx"),
        ]

    def __str__(self):
        return f"LeaveRequest {self.id} - User {self.user_id} - {self.category} - {self.status}"


class LeaveRequestTransition(TimeStampedModel):
    """Append-only audit trail for leave request status transitions."""
    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=24, choices=LeaveStatus.choices)
    to_status = models.CharField(max_length=24, choices=LeaveStatus.choices)
    actor_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    actor_role = models.CharField(max_length=50, blank=True)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["leave_request", "-created_at"], name="leave_trans_req_idx"),
            models.Index(fields=["actor_user_id", "-created_at"], name="leave_trans_actor_idx"),
        ]

    def __str__(self):
        return f"{self.leave_request_id}: {self.from_status} -> {self.to_status}"


class SubstituteRequest(TimeStampedModel):
    """Substitute nomination and acceptance."""
    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="substitute_requests",
    )
    substitute_id = models.IntegerField(db_index=True)
    nominated_by = models.IntegerField()  # original applicant
    status = models.CharField(
        max_length=16,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
        ],
        default="pending",
        db_index=True,
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["leave_request", "substitute_id", "status"],
                condition=models.Q(status="pending"),
                name="sub_req_unique_pending",
            ),
        ]
        indexes = [
            models.Index(fields=["substitute_id", "status"], name="sub_req_sub_status_idx"),
        ]

    def __str__(self):
        return f"SubReq {self.id} for LR {self.leave_request_id} - {self.status}"


class OfflineLeaveEntry(TimeStampedModel):
    """Record of previously sanctioned leave entered offline."""
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=4, choices=LeaveCategory.choices, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=2)
    sanction_order_number = models.CharField(max_length=100)
    sanction_order_date = models.DateField()
    sanctioning_authority = models.CharField(max_length=100)
    remarks = models.TextField(blank=True)
    entered_by = models.IntegerField()  # leave administrator
    verified = models.BooleanField(default=False)
    verified_by = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "-created_at"], name="offline_leave_user_idx"),
        ]

    def __str__(self):
        return f"OfflineLeave {self.id} - User {self.user_id} - {self.category}"


class YearEndProcessing(TimeStampedModel):
    """Record of year-end leave processing runs."""
    year = models.IntegerField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=[
            ("pending", "Pending"),
            ("running", "Running"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    processed_users = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["year"], name="year_end_unique_year"),
        ]

    def __str__(self):
        return f"YearEnd {self.year} - {self.status}"