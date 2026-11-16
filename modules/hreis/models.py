from django.db import models


class EmployeeRecord(models.Model):
    CATEGORY = [("faculty", "Faculty"), ("staff", "Staff")]
    user_id = models.PositiveIntegerField(unique=True)
    category = models.CharField(max_length=10, choices=CATEGORY)
    employee_name = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    appointment_date = models.DateField(null=True, blank=True)
    service_history = models.JSONField(default=list)
    leave_balances = models.JSONField(default=dict)
    retirement_status = models.CharField(max_length=80, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Employee {self.user_id}"


class WorkflowRoute(models.Model):
    category = models.CharField(max_length=10, choices=EmployeeRecord.CATEGORY)
    request_kind = models.CharField(
        max_length=10, choices=[("leave", "Leave"), ("ltc", "LTC"), ("cpda", "CPDA")]
    )
    authorities = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["category", "request_kind"], name="hreis_unique_route")
        ]

    def __str__(self) -> str:
        return f"Route {self.category}/{self.request_kind}"


class AppraisalWindow(models.Model):
    year = models.PositiveIntegerField(unique=True)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()

    def __str__(self) -> str:
        return f"Appraisal window {self.year}"


class LeaveRequest(models.Model):
    TYPES = [
        (name, name.title())
        for name in ("casual", "restricted", "medical", "earned", "vacation", "sabbatical")
    ]
    record = models.ForeignKey(
        EmployeeRecord, on_delete=models.PROTECT, related_name="leave_requests"
    )
    leave_type = models.CharField(max_length=20, choices=TYPES)
    days = models.DecimalField(max_digits=7, decimal_places=2)
    justification = models.TextField()
    status = models.CharField(
        max_length=12,
        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="pending",
    )
    current_step = models.PositiveIntegerField(default=0)
    approval_roles = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Leave request {self.pk}"


class Appraisal(models.Model):
    record = models.ForeignKey(EmployeeRecord, on_delete=models.PROTECT, related_name="appraisals")
    year = models.PositiveIntegerField()
    content = models.JSONField(default=dict)
    reviewer_roles = models.JSONField(default=list)
    current_step = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=12,
        choices=[("submitted", "Submitted"), ("review", "Review"), ("closed", "Closed")],
        default="submitted",
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["record", "year"], name="hreis_one_appraisal_per_year")
        ]

    def __str__(self) -> str:
        return f"Appraisal {self.pk}"


class Claim(models.Model):
    record = models.ForeignKey(EmployeeRecord, on_delete=models.PROTECT, related_name="claims")
    kind = models.CharField(max_length=4, choices=[("ltc", "LTC"), ("cpda", "CPDA")])
    claim_type = models.CharField(
        max_length=15, choices=[("advance", "Advance"), ("reimbursement", "Reimbursement")]
    )
    purpose = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    documents = models.JSONField(default=list)
    status = models.CharField(
        max_length=12,
        choices=[
            ("awaiting_hr", "Awaiting HR"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("processed", "Processed"),
        ],
        default="awaiting_hr",
    )
    current_step = models.PositiveIntegerField(default=0)
    approval_roles = models.JSONField(default=list)
    payment_status = models.CharField(max_length=100, blank=True)
    payment_reference = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Claim {self.pk}"


class AuditEntry(models.Model):
    entity_type = models.CharField(max_length=40)
    entity_id = models.PositiveIntegerField()
    action = models.CharField(max_length=100)
    actor_id = models.PositiveIntegerField()
    detail = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]

    def __str__(self) -> str:
        return f"Audit event {self.pk}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("Audit entries cannot be updated")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit entries cannot be deleted")


class Notification(models.Model):
    user_id = models.PositiveIntegerField()
    kind = models.CharField(max_length=40)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Notification {self.pk}"
