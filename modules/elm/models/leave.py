"""Data models for Employee Leave Management (ELM)."""
from django.db import models


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    VL = "VL", "Vacation Leave"
    COL = "COL", "Commuted Leave"


class LeaveStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    AWAITING_SUBSTITUTE_RESPONSE = "AWAITING_SUBSTITUTE_RESPONSE", "Awaiting Substitute Response"
    AWAITING_APPLICANT_ACTION = "AWAITING_APPLICANT_ACTION", "Awaiting Applicant Action"
    AWAITING_UNIT_HEAD_REVIEW = "AWAITING_UNIT_HEAD_REVIEW", "Awaiting Unit Head Review"
    AWAITING_ESTABLISHMENT_REVIEW = "AWAITING_ESTABLISHMENT_REVIEW", "Awaiting Establishment Review"
    AWAITING_SANCTION_AUTHORITY_REVIEW = "AWAITING_SANCTION_AUTHORITY_REVIEW", "Awaiting Sanction Authority Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    AWAITING_CANCELLATION_REVIEW = "AWAITING_CANCELLATION_REVIEW", "Awaiting Cancellation Review"
    CANCELLED = "CANCELLED", "Cancelled"
    AWAITING_EXTENSION_REVIEW = "AWAITING_EXTENSION_REVIEW", "Awaiting Extension Review"
    AWAITING_RESUMPTION_REVIEW = "AWAITING_RESUMPTION_REVIEW", "Awaiting Resumption Review"


class LeaveRequest(models.Model):
    applicant_id = models.BigIntegerField(db_index=True)
    category = models.CharField(max_length=10, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=5, decimal_places=2)
    is_half_day = models.BooleanField(default=False)
    half_day_type = models.CharField(max_length=20, blank=True, null=True)
    reason = models.TextField()
    is_station_leave = models.BooleanField(default=False)
    station_address = models.TextField(blank=True, default="")
    emergency_contact = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(
        max_length=50,
        choices=LeaveStatus.choices,
        default=LeaveStatus.DRAFT,
        db_index=True,
    )
    unit_head_recommendation = models.CharField(max_length=30, blank=True, default="")
    unit_head_remarks = models.TextField(blank=True, default="")
    sanctioning_authority_remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]


class SubstituteAssignment(models.Model):
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="substitute_assignments"
    )
    substitute_id = models.BigIntegerField(db_index=True)
    status = models.CharField(max_length=20, default="PENDING")
    remarks = models.TextField(blank=True, default="")
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_substitute_assignment"


class LeaveAccount(models.Model):
    employee_id = models.BigIntegerField(db_index=True)
    category = models.CharField(max_length=10, choices=LeaveCategory.choices)
    year = models.IntegerField(db_index=True)
    allotted = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pending = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    available = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_account"
        unique_together = ("employee_id", "category", "year")


class LeaveTransaction(models.Model):
    account = models.ForeignKey(
        LeaveAccount, on_delete=models.CASCADE, related_name="transactions"
    )
    delta = models.DecimalField(max_digits=6, decimal_places=2)
    transaction_type = models.CharField(max_length=50)
    reference_id = models.CharField(max_length=100, blank=True, default="")
    idempotency_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_transaction"
        ordering = ["-created_at"]


class HolidayCalendarEntry(models.Model):
    year = models.IntegerField(db_index=True)
    date = models.DateField(db_index=True)
    name = models.CharField(max_length=200)
    is_rh = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_holiday_calendar"
        unique_together = ("date", "is_rh")


class LeavePolicyConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_policy_config"


class LeaveResumptionRecord(models.Model):
    request = models.OneToOneField(
        LeaveRequest, on_delete=models.CASCADE, related_name="resumption_record"
    )
    actual_resumption_date = models.DateField()
    adjustment_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    resumption_type = models.CharField(max_length=20)
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_resumption_record"
