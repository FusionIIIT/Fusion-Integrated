"""Employee Leave Management persistence; IAM keeps authoritative user identities."""

from django.db import models

CATEGORIES = [
    ("CL", "Casual Leave"),
    ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"),
    ("EL", "Earned Leave"),
    ("COL", "Commuted Leave"),
    ("VL", "Vacation Leave"),
]

APPLICATION_STATUSES = [
    ("AWAITING_SUB", "Awaiting substitute response"),
    ("ACTION_REQUIRED", "Applicant action required"),
    ("PENDING", "Awaiting Unit Head review"),
    ("AWAITING_ESTABLISHMENT", "Awaiting establishment routing"),
    ("RECOMMENDED", "Under higher sanction"),
    ("AWAITING_DIRECTOR", "Awaiting Director self-sanction"),
    ("APPROVED", "Approved"),
    ("REJECTED", "Rejected"),
    ("WITHDRAWN", "Withdrawn"),
    ("CANCELLATION_PENDING", "Cancellation pending Unit Head review"),
    ("CANCELLATION_ESTABLISHMENT", "Cancellation pending establishment routing"),
    ("CANCELLATION_SANCTION", "Cancellation pending final decision"),
    ("CANCELLED", "Cancelled"),
    ("EXTENSION_AWAITING_SUB", "Extension awaiting substitute response"),
    ("EXTENSION_ACTION_REQUIRED", "Extension applicant action required"),
    ("EXTENSION_PENDING", "Extension awaiting Unit Head review"),
    ("EXTENSION_ESTABLISHMENT", "Extension awaiting establishment routing"),
    ("EXTENSION_SANCTION", "Extension awaiting final decision"),
    ("RESUMPTION_PENDING", "Resumption review pending"),
    ("COMPLETED", "Completed"),
]


class EmployeeLeaveProfile(models.Model):
    user_id = models.PositiveIntegerField(unique=True)
    category = models.CharField(max_length=10, choices=[("faculty", "Faculty"), ("staff", "Staff")])
    designation = models.CharField(max_length=255, blank=True)
    unit = models.CharField(max_length=255)
    unit_head_user_id = models.PositiveIntegerField(null=True, blank=True)
    establishment_user_id = models.PositiveIntegerField(null=True, blank=True)
    sanction_authority_user_id = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"ELM employee {self.user_id}"


class LeaveBalance(models.Model):
    employee_id = models.PositiveIntegerField()
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=CATEGORIES)
    allotted = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=7, decimal_places=1, default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee_id", "year", "category"], name="elm_unique_balance"
            )
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} {self.year} {self.category}"


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=255)
    kind = models.CharField(
        max_length=8,
        choices=[
            ("RH", "Restricted Holiday"),
            ("CLOSED", "Closed holiday"),
            ("VACATION", "Vacation window"),
        ],
    )
    published = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.date} {self.name}"


class LeaveApplication(models.Model):
    employee_id = models.PositiveIntegerField()
    category = models.CharField(max_length=3, choices=CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=6,
        choices=[("NONE", "Full day"), ("FIRST", "First half"), ("SECOND", "Second half")],
        default="NONE",
    )
    duration = models.DecimalField(max_digits=7, decimal_places=1)
    reason = models.TextField()
    medical_evidence = models.TextField(blank=True)
    station_leave = models.BooleanField(default=False)
    station_location = models.CharField(max_length=255, blank=True)
    substitute_user_id = models.PositiveIntegerField(null=True, blank=True)
    substitute_status = models.CharField(
        max_length=12,
        choices=[
            ("NOT_REQUIRED", "Not required"),
            ("PENDING", "Pending"),
            ("ACCEPTED", "Accepted"),
            ("DECLINED", "Declined"),
        ],
        default="NOT_REQUIRED",
    )
    status = models.CharField(
        max_length=32,
        choices=APPLICATION_STATUSES,
        default="PENDING",
    )
    unit_head_id = models.PositiveIntegerField(null=True, blank=True)
    establishment_id = models.PositiveIntegerField(null=True, blank=True)
    sanction_authority_id = models.PositiveIntegerField(null=True, blank=True)
    recommendation = models.CharField(max_length=24, blank=True)
    approver_id = models.PositiveIntegerField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    extended_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extensions"
    )
    actual_resumption_date = models.DateField(null=True, blank=True)
    resumption_remarks = models.TextField(blank=True)
    resumed_at = models.DateField(null=True, blank=True)
    is_offline = models.BooleanField(default=False)
    sanction_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"ELM application {self.pk}: {self.employee_id}"


class LeaveEvent(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.PROTECT, related_name="events"
    )
    actor_id = models.PositiveIntegerField()
    action = models.CharField(max_length=50)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"ELM event {self.pk}: {self.action}"


class SlaConfig(models.Model):
    task_type = models.CharField(max_length=64, unique=True)
    reminder_hours = models.PositiveIntegerField(default=24)
    escalation_hours = models.PositiveIntegerField(default=72)
    escalate_to_user_id = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"SLA config for {self.task_type}"


class LeaveNotification(models.Model):
    recipient_id = models.PositiveIntegerField()
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    topic = models.CharField(max_length=64)
    message = models.TextField()
    is_reminder = models.BooleanField(default=False)
    is_escalation = models.BooleanField(default=False)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification to {self.recipient_id}: {self.topic}"


class LeaveAccountTransaction(models.Model):
    employee_id = models.PositiveIntegerField()
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=CATEGORIES)
    transaction_type = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=7, decimal_places=1)
    balance_after = models.DecimalField(max_digits=7, decimal_places=1)
    reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.employee_id} {self.year} {self.category} {self.transaction_type} {self.amount}"
        )
