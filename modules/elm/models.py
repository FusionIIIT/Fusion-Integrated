from decimal import Decimal
from django.db import models
from django.utils import timezone


class LeaveType(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    VL = "VL", "Vacation Leave (Faculty)"
    COL = "COL", "Commuted Leave"


class LeaveStatus(models.TextChoices):
    # Lifecycle states per WF-EL-01 through WF-EL-05
    DRAFT = "DRAFT", "Draft"
    AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE", "Awaiting Substitute Response"
    SUBSTITUTE_DECLINED = "SUBSTITUTE_DECLINED", "Substitute Declined"
    AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"
    AWAITING_SANCTION = "AWAITING_SANCTION", "Awaiting Final Sanction"
    AWAITING_DIRECTOR_SELF_SANCTION = "AWAITING_DIRECTOR_SELF_SANCTION", "Awaiting Director Self-Sanction"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    AWAITING_CANCELLATION = "AWAITING_CANCELLATION", "Awaiting Cancellation Review"
    CANCELLED = "CANCELLED", "Cancelled"
    AWAITING_RESUMPTION_VERIFICATION = "AWAITING_RESUMPTION_VERIFICATION", "Awaiting Resumption Verification"
    CLOSED = "CLOSED", "Resumed / Closed"


class LeaveBalance(models.Model):
    employee_id = models.CharField(max_length=64, db_index=True)
    is_faculty = models.BooleanField(default=False)
    year = models.PositiveIntegerField()
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices)
    
    total_allocated = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    carried_forward = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    lapsed_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    converted_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("employee_id", "year", "leave_type")
        ordering = ["year", "leave_type"]

    @property
    def remaining_days(self) -> Decimal:
        return (self.total_allocated + self.carried_forward) - self.used_days

    def __str__(self):
        return f"{self.employee_id} - {self.leave_type} ({self.year}): {self.remaining_days} rem"


class LeaveApplication(models.Model):
    applicant_id = models.CharField(max_length=64, db_index=True)
    is_faculty = models.BooleanField(default=False)
    is_director = models.BooleanField(default=False)
    
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    is_half_day = models.BooleanField(default=False)
    reason = models.TextField()

    # Station Leave details (coupled per BR-EL-013)
    requires_station_leave = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True, default="")
    station_departure_datetime = models.DateTimeField(null=True, blank=True)
    station_arrival_datetime = models.DateTimeField(null=True, blank=True)

    # Substitute details (BR-EL-014, BR-EL-015)
    substitute_id = models.CharField(max_length=64, blank=True, default="")
    substitute_status = models.CharField(
        max_length=20,
        choices=[("NONE", "None"), ("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("DECLINED", "Declined")],
        default="NONE"
    )
    substitute_remarks = models.TextField(blank=True, default="")
    substitute_responded_at = models.DateTimeField(null=True, blank=True)

    # Workflow state
    status = models.CharField(
        max_length=35,
        choices=LeaveStatus.choices,
        default=LeaveStatus.DRAFT,
        db_index=True,
    )

    # Unit Head Review (BR-EL-016, BR-EL-017)
    unit_head_id = models.CharField(max_length=64, blank=True, default="")
    unit_head_recommendation = models.CharField(
        max_length=20,
        choices=[("NONE", "None"), ("RECOMMENDED", "Recommended"), ("REJECTED", "Rejected"), ("APPROVED_FINAL", "Approved Final")],
        default="NONE"
    )
    unit_head_remarks = models.TextField(blank=True, default="")
    unit_head_reviewed_at = models.DateTimeField(null=True, blank=True)

    # Higher Sanctioning Authority (BR-EL-018, BR-EL-019, BR-EL-020)
    sanctioner_id = models.CharField(max_length=64, blank=True, default="")
    sanction_decision = models.CharField(
        max_length=20,
        choices=[("NONE", "None"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")],
        default="NONE"
    )
    sanction_remarks = models.TextField(blank=True, default="")
    sanctioned_at = models.DateTimeField(null=True, blank=True)

    # Extension tracking (WF-EL-04, BR-EL-025)
    is_extension = models.BooleanField(default=False)
    parent_leave = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extensions"
    )

    # Resumption tracking (WF-EL-05, BR-EL-027, BR-EL-028)
    actual_resumption_date = models.DateField(null=True, blank=True)
    actual_days_availed = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    resumption_verified_by = models.CharField(max_length=64, blank=True, default="")
    resumption_verified_at = models.DateTimeField(null=True, blank=True)

    # Offline-sanctioned recording (WF-EL-06, BR-EL-029)
    is_offline_record = models.BooleanField(default=False)
    offline_sanction_ref = models.CharField(max_length=128, blank=True, default="")
    offline_sanction_date = models.DateField(null=True, blank=True)

    # SLA tracking (WF-EL-08, BR-EL-032, BR-EL-033)
    last_actionable_task_at = models.DateTimeField(default=timezone.now)
    sla_reminder_sent = models.BooleanField(default=False)
    sla_escalation_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Leave #{self.id} [{self.leave_type}] by {self.applicant_id} ({self.status})"


class LeaveHistory(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="history")
    actor_id = models.CharField(max_length=64)
    from_status = models.CharField(max_length=35)
    to_status = models.CharField(max_length=35)
    action = models.CharField(max_length=64)
    remarks = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_history"
        ordering = ["timestamp"]

    def __str__(self):
        return f"Leave #{self.application_id}: {self.from_status} -> {self.to_status} by {self.actor_id}"
