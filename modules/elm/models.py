from django.db import models
from django.db.models import Q


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Compensatory Leave"
    VL = "VL", "Vacation Leave"


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending Approval"
        APPROVED = "APPROVED", "Recommended / Approved"
        NOT_RECOMMENDED = "NOT_RECOMMENDED", "Not Recommended"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"
        CANCELLED = "CANCELLED", "Cancelled"

    class ApprovalStage(models.TextChoices):
        UNIT_HEAD = "UNIT_HEAD", "Unit Head"
        HIERARCHY = "HIERARCHY", "Higher Authority"
        DIRECTOR = "DIRECTOR", "Director"
        COMPLETED = "COMPLETED", "Completed"

    employee_id = models.PositiveBigIntegerField(db_index=True)
    leave_category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING,
        db_index=True,
    )
    approval_stage = models.CharField(
        max_length=12, choices=ApprovalStage.choices,
        default=ApprovalStage.UNIT_HEAD,
    )
    station_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    substitute_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    substitute_accepted = models.BooleanField(null=True, blank=True)
    final_approver_id = models.PositiveBigIntegerField(null=True, blank=True)
    final_approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_leave_dates_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["employee_id", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.employee_id}: {self.leave_category} ({self.start_date} to {self.end_date})"


class LeaveBalance(models.Model):
    employee_id = models.PositiveBigIntegerField(db_index=True)
    leave_category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    year = models.PositiveSmallIntegerField()
    entitled_days = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    used_days = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    carried_forward_days = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee_id", "leave_category", "year"],
                name="elm_unique_employee_leave_balance",
            ),
            models.CheckConstraint(
                condition=Q(entitled_days__gte=0) & Q(used_days__gte=0)
                & Q(carried_forward_days__gte=0),
                name="elm_balance_values_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.employee_id} - {self.leave_category} ({self.year})"

    @property
    def available_days(self):
        return self.entitled_days + self.carried_forward_days - self.used_days


class RestrictedHoliday(models.Model):
    date = models.DateField()
    name = models.CharField(max_length=150)
    station_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "station_id", "name"],
                name="elm_unique_restricted_holiday",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.date})"


class LeaveApproval(models.Model):
    class Decision(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Recommended / Approved"
        NOT_RECOMMENDED = "NOT_RECOMMENDED", "Not Recommended"
        REJECTED = "REJECTED", "Rejected"

    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="approvals"
    )
    approver_id = models.PositiveBigIntegerField(db_index=True)
    stage = models.CharField(
        max_length=12, choices=LeaveRequest.ApprovalStage.choices
    )
    decision = models.CharField(
        max_length=20, choices=Decision.choices, default=Decision.PENDING
    )
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["leave_request", "stage"],
                name="elm_unique_approval_stage",
            ),
        ]


    def __str__(self):
        return f"Leave request {self.leave_request_id} - {self.stage}: {self.decision}"


class LeaveAuditEvent(models.Model):
    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="audit_events"
    )
    actor_id = models.PositiveBigIntegerField(db_index=True)
    action = models.CharField(max_length=40)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Leave request {self.leave_request_id}: {self.action}"
