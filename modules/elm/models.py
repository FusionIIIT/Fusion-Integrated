"""Employee leave records and policy-owned configuration."""
from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class OrganizationUnit(TimeStampedModel):
    code = models.CharField(max_length=48, unique=True)
    name = models.CharField(max_length=120)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_organization_unit"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class EmployeeProfile(TimeStampedModel):
    TYPES = [("faculty", "Faculty"), ("staff", "Staff")]

    user_id = models.IntegerField(primary_key=True)
    employee_type = models.CharField(max_length=12, choices=TYPES)
    designation = models.CharField(max_length=120, blank=True)
    organization_unit = models.ForeignKey(
        OrganizationUnit, on_delete=models.PROTECT, related_name="employees",
        null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_employee_profile"


class LeavePolicy(TimeStampedModel):
    CATEGORIES = [
        ("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"), ("VL", "Vacation Leave"),
    ]
    category = models.CharField(max_length=3, choices=CATEGORIES, unique=True)
    annual_entitlement = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0"))
    faculty_only = models.BooleanField(default=False)
    continuous_days = models.BooleanField(default=False)
    carry_forward = models.BooleanField(default=False)
    allow_half_day = models.BooleanField(default=False)
    medical_evidence_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_policy"
        ordering = ["category"]


class LeaveCalendarDate(TimeStampedModel):
    TYPES = [
        ("restricted_holiday", "Restricted Holiday"),
        ("closed_holiday", "Closed Holiday"),
        ("vacation", "Vacation"),
    ]
    date = models.DateField()
    kind = models.CharField(max_length=24, choices=TYPES)
    label = models.CharField(max_length=160, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_calendar_date"
        ordering = ["date", "kind"]
        constraints = [
            models.UniqueConstraint(fields=["date", "kind"],
                                    name="elm_calendar_date_kind_unique"),
        ]
        indexes = [models.Index(fields=["kind", "date", "is_published"],
                                name="elm_calendar_effective_idx")]


class ApprovalRoute(TimeStampedModel):
    """Current configured final-authority route, more specific routes win."""
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORIES)
    organization_unit = models.ForeignKey(
        OrganizationUnit, on_delete=models.CASCADE, null=True, blank=True,
        related_name="approval_routes")
    approver_user_id = models.IntegerField(null=True, blank=True)
    approver_role = models.CharField(max_length=100, blank=True)
    permission_code = models.CharField(max_length=100, default="elm.leave.sanction")
    establishment_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_approval_route"
        constraints = [
            models.UniqueConstraint(
                fields=["category", "organization_unit"],
                name="elm_approval_route_category_unit_unique"),
            models.UniqueConstraint(
                fields=["category"],
                condition=Q(organization_unit__isnull=True),
                name="elm_route_global_category_unique"),
        ]


class LeaveAccount(TimeStampedModel):
    user_id = models.IntegerField()
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORIES)
    year = models.PositiveSmallIntegerField()
    opening_balance = models.DecimalField(max_digits=8, decimal_places=2,
                                          default=Decimal("0"))
    credited = models.DecimalField(max_digits=8, decimal_places=2,
                                   default=Decimal("0"))
    used = models.DecimalField(max_digits=8, decimal_places=2,
                               default=Decimal("0"))
    lapsed = models.DecimalField(max_digits=8, decimal_places=2,
                                 default=Decimal("0"))
    year_end_processed = models.BooleanField(default=False)
    closing_balance = models.DecimalField(max_digits=8, decimal_places=2,
                                          default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_account"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "category", "year"],
                                    name="elm_leave_account_unique"),
            models.CheckConstraint(condition=Q(closing_balance__gte=0),
                                  name="elm_account_nonnegative_balance"),
        ]
        indexes = [models.Index(fields=["user_id", "year"],
                                name="elm_account_user_year_idx")]

    @property
    def balance(self) -> Decimal:
        return self.opening_balance + self.credited - self.used - self.lapsed


class LeaveRequest(TimeStampedModel):
    CATEGORIES = LeavePolicy.CATEGORIES
    STATUSES = [
        ("awaiting_substitute", "Awaiting Substitute"),
        ("pending_unit_head", "Pending Unit Head"),
        ("pending_sanction", "Pending Sanction"),
        ("approved", "Approved"), ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"), ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]
    HALF_DAYS = [("none", "Full Day"), ("first_half", "First Half"),
                 ("second_half", "Second Half")]

    applicant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=12, choices=HALF_DAYS, default="none")
    purpose = models.TextField(max_length=2000)
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=200, blank=True)
    medical_evidence_ref = models.CharField(max_length=500, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(
        max_length=12, choices=[("pending", "Pending"), ("accepted", "Accepted"),
                                ("declined", "Declined")],
        blank=True)
    status = models.CharField(max_length=32, choices=STATUSES, db_index=True)
    workflow_stage = models.CharField(max_length=32, blank=True)
    assigned_user_id = models.IntegerField(null=True, blank=True)
    assigned_permission = models.CharField(max_length=100, blank=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    approved_days = models.DecimalField(max_digits=7, decimal_places=2,
                                        default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["applicant_user_id", "status"],
                         name="elm_request_owner_status_idx"),
            models.Index(fields=["status", "assigned_permission"],
                         name="elm_request_queue_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                  name="elm_leave_dates_ordered"),
        ]


class LeaveCase(TimeStampedModel):
    TYPES = [
        ("cancellation", "Cancellation"), ("extension", "Extension"),
        ("resumption", "Resumption"),
    ]
    STATUSES = [
        ("awaiting_substitute", "Awaiting Substitute"),
        ("applicant_action_required", "Applicant Action Required"),
        ("pending_unit_head", "Pending Unit Head"),
        ("pending_sanction", "Pending Sanction"),
        ("approved", "Approved"), ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"), ("completed", "Completed"),
    ]

    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="cases")
    case_type = models.CharField(max_length=16, choices=TYPES)
    requested_start = models.DateField(null=True, blank=True)
    requested_end = models.DateField(null=True, blank=True)
    actual_resumption_date = models.DateField(null=True, blank=True)
    medical_evidence_ref = models.CharField(max_length=500, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(max_length=12, blank=True)
    reason = models.TextField(max_length=2000)
    status = models.CharField(max_length=32, choices=STATUSES, db_index=True)
    assigned_user_id = models.IntegerField(null=True, blank=True)
    assigned_permission = models.CharField(max_length=100, blank=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_case"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "assigned_permission"],
                                name="elm_case_queue_idx")]


class LeaveTransaction(TimeStampedModel):
    TYPES = [
        ("annual_credit", "Annual Credit"), ("leave_debit", "Leave Debit"),
        ("cancellation_credit", "Cancellation Credit"),
        ("extension_debit", "Extension Debit"), ("year_end_lapse", "Year-end Lapse"),
        ("vl_to_el", "VL to EL Conversion"), ("manual_adjustment", "Manual Adjustment"),
        ("resumption_adjustment", "Resumption Adjustment"),
    ]
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeavePolicy.CATEGORIES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_type = models.CharField(max_length=24, choices=TYPES)
    reference_request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.PROTECT,
        related_name="transactions")
    reference_case = models.ForeignKey(
        LeaveCase, null=True, blank=True, on_delete=models.PROTECT,
        related_name="transactions")
    description = models.CharField(max_length=240, blank=True)
    performed_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_transaction"
        ordering = ["-created_at"]


class LeaveAuditEvent(TimeStampedModel):
    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="audit_events")
    case = models.ForeignKey(
        LeaveCase, null=True, blank=True, on_delete=models.CASCADE,
        related_name="audit_events")
    actor_user_id = models.IntegerField()
    action = models.CharField(max_length=32)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_audit_event"
        ordering = ["created_at"]


class LeaveNotificationOutbox(TimeStampedModel):
    STATUSES = [
        ("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed"),
    ]
    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    recipient_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=12, choices=STATUSES, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_notification_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"], name="elm_notify_pending_idx"),
        ]
