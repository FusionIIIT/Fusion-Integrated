"""Data models for Employee Leave Management (ELM).

Implements all entities, entitlements, balances, requests, and lifecycle states
specified in ELM Specification v1.4/v1.6 and Fusion ERP platform constraints.
"""
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.TextChoices):
    CASUAL_LEAVE = "CL", "Casual Leave"
    RESTRICTED_HOLIDAY = "RH", "Restricted Holiday"
    SPECIAL_CASUAL_LEAVE = "SCL", "Special Casual Leave"
    EARNED_LEAVE = "EL", "Earned Leave"
    COMMUTED_LEAVE = "COL", "Commuted Leave"
    VACATION_LEAVE = "VL", "Vacation Leave"


class HalfDayType(models.TextChoices):
    NONE = "none", "Full Day"
    FIRST_HALF = "first_half", "First Half"
    SECOND_HALF = "second_half", "Second Half"


class SubstituteStatus(models.TextChoices):
    NOT_APPLICABLE = "none", "Not Applicable"
    PENDING = "pending", "Pending Consent"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"


class LeaveStatus(models.TextChoices):
    PENDING_SUBSTITUTE = "pending_substitute", "Pending Substitute Consent"
    PENDING_UNIT_HEAD = "pending_unit_head", "Pending Unit Head Review"
    PENDING_ESTT = "pending_estt", "Pending Establishment Processing"
    PENDING_SANCTION = "pending_sanction", "Pending Final Sanction"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
    CANCELLATION_PENDING = "cancellation_pending", "Cancellation Under Review"
    CANCELLED = "cancelled", "Cancelled"


class UnitHeadRecommendation(models.TextChoices):
    NONE = "none", "None"
    RECOMMENDED = "recommended", "Recommended"
    NOT_RECOMMENDED = "not_recommended", "Not Recommended"


class LeavePolicyConfig(TimeStampedModel):
    """Configurable ELM leave policy parameters (BR-EL-030)."""
    cl_entitlement = models.PositiveSmallIntegerField(default=8)
    rh_entitlement = models.PositiveSmallIntegerField(default=2)
    scl_entitlement = models.PositiveSmallIntegerField(default=15)
    el_non_faculty_entitlement = models.PositiveSmallIntegerField(default=30)
    vl_faculty_entitlement = models.PositiveSmallIntegerField(default=60)
    col_entitlement = models.PositiveSmallIntegerField(default=20)
    vl_to_el_ratio = models.FloatField(default=0.5)  # 2 VL = 1 EL (1/2 = 0.5)
    sla_reminder_days = models.PositiveSmallIntegerField(default=3)
    sla_escalation_days = models.PositiveSmallIntegerField(default=7)

    class Meta:
        db_table = "elm_policy_config"
        verbose_name = "ELM Policy Configuration"


class HolidayCalendar(TimeStampedModel):
    """Effective published holiday / Restricted Holiday calendar (BR-EL-003, BR-EL-031)."""
    class HolidayType(models.TextChoices):
        CLOSED = "closed", "Closed Holiday"
        RESTRICTED = "rh", "Restricted Holiday"

    name = models.CharField(max_length=150)
    date = models.DateField(db_index=True)
    year = models.PositiveSmallIntegerField(db_index=True)
    holiday_type = models.CharField(max_length=16, choices=HolidayType.choices, default=HolidayType.CLOSED)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        unique_together = ("date", "holiday_type")
        ordering = ["date"]


class AcademicVacationPeriod(TimeStampedModel):
    """Vacation period from Academic Calendar for VL applicability (EXT-01, BR-EL-006)."""
    name = models.CharField(max_length=150)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    academic_year = models.CharField(max_length=16)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_vacation_period"
        ordering = ["start_date"]


class LeaveBalance(UserScopedModel, TimeStampedModel):
    """Current and historical leave ledger per employee (BR-EL-002..009)."""
    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=LeaveCategory.choices, db_index=True)
    credited = models.FloatField(default=0.0)
    consumed = models.FloatField(default=0.0)
    pending = models.FloatField(default=0.0)
    carried_forward = models.FloatField(default=0.0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "year", "category")
        indexes = [
            models.Index(fields=["user_id", "year"]),
        ]

    @property
    def available_balance(self) -> float:
        return max(0.0, self.credited + self.carried_forward - self.consumed - self.pending)

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.category} ({self.year}): Avail {self.available_balance}"


class LeaveRequest(UserScopedModel, TimeStampedModel):
    """Main Leave Application entity (CFR-EL-002, WF-EL-01, BR-EL-013)."""
    category = models.CharField(max_length=8, choices=LeaveCategory.choices, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    half_day = models.CharField(max_length=16, choices=HalfDayType.choices, default=HalfDayType.NONE)
    duration_days = models.FloatField()
    purpose = models.TextField()

    # Station Leave fields (BR-EL-013 - coupled within the same application)
    is_station_leave = models.BooleanField(default=False)
    station_address = models.TextField(blank=True, default="")
    station_contact = models.CharField(max_length=64, blank=True, default="")
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)

    # Substitute fields (BR-EL-014, BR-EL-015)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(max_length=16, choices=SubstituteStatus.choices, default=SubstituteStatus.NOT_APPLICABLE)
    substitute_remarks = models.TextField(blank=True, default="")
    substitute_acted_at = models.DateTimeField(null=True, blank=True)

    # Workflow & Sanction fields
    current_status = models.CharField(max_length=32, choices=LeaveStatus.choices, default=LeaveStatus.PENDING_UNIT_HEAD, db_index=True)
    current_assignee_role = models.CharField(max_length=64, blank=True, default="unit_head")
    unit_head_recommendation = models.CharField(max_length=16, choices=UnitHeadRecommendation.choices, default=UnitHeadRecommendation.NONE)
    unit_head_remarks = models.TextField(blank=True, default="")
    unit_head_acted_at = models.DateTimeField(null=True, blank=True)

    sanctioning_authority_role = models.CharField(max_length=64, blank=True, default="")
    sanction_remarks = models.TextField(blank=True, default="")
    sanction_acted_at = models.DateTimeField(null=True, blank=True)
    final_decision_by_id = models.IntegerField(null=True, blank=True)

    is_offline_sanctioned = models.BooleanField(default=False)
    offline_reference = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["user_id", "current_status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Leave #{self.id} (User {self.user_id}, {self.category}, {self.duration_days}d, {self.current_status})"


class LeaveActionHistory(models.Model):
    """Immutable audit trail for all workflow transitions (CFR-EL-016)."""
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="actions")
    actor_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=48)
    previous_status = models.CharField(max_length=32, blank=True, default="")
    new_status = models.CharField(max_length=32, blank=True, default="")
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_action_history"
        ordering = ["created_at"]


class LeaveExtension(TimeStampedModel):
    """Extension of ongoing EL/COL/VL (BR-EL-025, WF-EL-04)."""
    class ExtensionStatus(models.TextChoices):
        PENDING_SUBSTITUTE = "pending_substitute", "Pending Substitute"
        PENDING_UNIT_HEAD = "pending_unit_head", "Pending Unit Head"
        PENDING_SANCTION = "pending_sanction", "Pending Sanction"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="extensions")
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.FloatField()
    reason = models.TextField()

    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=16, choices=SubstituteStatus.choices, default=SubstituteStatus.NOT_APPLICABLE)
    status = models.CharField(max_length=32, choices=ExtensionStatus.choices, default=ExtensionStatus.PENDING_UNIT_HEAD)
    unit_head_recommendation = models.CharField(max_length=16, choices=UnitHeadRecommendation.choices, default=UnitHeadRecommendation.NONE)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_extension"
        ordering = ["-created_at"]


class LeaveResumption(TimeStampedModel):
    """Formal duty resumption review for EL/COL/VL (BR-EL-027, BR-EL-028, WF-EL-05)."""
    class ResumptionType(models.TextChoices):
        NORMAL = "normal", "Normal Resumption"
        EARLY = "early", "Early Resumption"
        LATE = "late", "Late Resumption"

    class ResumptionStatus(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        REVIEWED = "reviewed", "Reviewed & Adjusted"

    leave_request = models.OneToOneField(LeaveRequest, on_delete=models.CASCADE, related_name="resumption")
    expected_date = models.DateField()
    actual_resumption_date = models.DateField()
    resumption_type = models.CharField(max_length=16, choices=ResumptionType.choices)
    adjusted_duration_days = models.FloatField()
    status = models.CharField(max_length=16, choices=ResumptionStatus.choices, default=ResumptionStatus.SUBMITTED)
    reviewer_id = models.IntegerField(null=True, blank=True)
    reviewer_remarks = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_resumption"


class OfflineSanctionRecord(TimeStampedModel):
    """Retrospective record synchronization for offline-sanctioned leave (BR-EL-029)."""
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.FloatField()
    offline_reference_no = models.CharField(max_length=128, unique=True)
    sanctioning_authority_name = models.CharField(max_length=128)
    sanction_date = models.DateField()
    recorded_by_id = models.IntegerField()
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_offline_record"
        ordering = ["-created_at"]
