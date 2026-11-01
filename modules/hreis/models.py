from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class EmployeeRecord(models.Model):
    user_id = models.PositiveBigIntegerField(unique=True)
    category = models.CharField(max_length=16, choices=[("faculty", "Faculty"), ("staff", "Staff")])
    department = models.CharField(max_length=128)
    designation = models.CharField(max_length=128)
    appointment_date = models.DateField()
    service_history = models.JSONField(default=list, blank=True)
    retired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"Employee {self.user_id}"


class LeavePolicy(models.Model):
    code = models.CharField(
        max_length=32,
        unique=True,
        choices=[
            ("CASUAL", "Casual"),
            ("RESTRICTED", "Restricted"),
            ("MEDICAL", "Medical"),
            ("EARNED", "Earned"),
            ("VACATION", "Vacation"),
            ("SABBATICAL", "Sabbatical"),
        ],
    )
    label = models.CharField(max_length=100)
    eligible_categories = models.JSONField(default=list)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return self.label


class LeaveAccount(models.Model):
    employee = models.ForeignKey("EmployeeRecord", on_delete=models.CASCADE)
    policy = models.ForeignKey("LeavePolicy", on_delete=models.PROTECT)
    available = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(condition=Q(available__gte=0), name="available_non_negative"),
            models.UniqueConstraint(fields=["employee", "policy"], name="unique_employee_policy"),
        ]

    def __str__(self):
        return f"Account {self.employee_id}/{self.policy_id}"


class WorkflowRoute(models.Model):
    employee_category = models.CharField(
        max_length=16, choices=[("faculty", "Faculty"), ("staff", "Staff")]
    )
    request_kind = models.CharField(
        max_length=8, choices=[("LEAVE", "Leave"), ("LTC", "LTC"), ("CPDA", "CPDA")]
    )
    department = models.CharField(max_length=128, blank=True, default="")
    steps = models.JSONField(default=list)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=["employee_category", "request_kind", "department"], name="unique_route"
            )
        ]

    def __str__(self):
        return f"{self.request_kind}/{self.employee_category}/{self.department or chr(42)}"


class HRRequest(models.Model):
    employee = models.ForeignKey("EmployeeRecord", on_delete=models.PROTECT)
    kind = models.CharField(
        max_length=8, choices=[("LEAVE", "Leave"), ("LTC", "LTC"), ("CPDA", "CPDA")]
    )
    mode = models.CharField(max_length=16, blank=True, default="")
    policy = models.ForeignKey("LeavePolicy", on_delete=models.PROTECT, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    days = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    purpose = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    documents = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        default="SUBMITTED",
        choices=[
            ("SUBMITTED", "Submitted"),
            ("PENDING", "Pending"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected"),
            ("SETTLED", "Settled"),
        ],
    )
    route = models.JSONField(default=list, blank=True)
    step = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(condition=Q(days__gte=0), name="days_non_negative"),
            models.CheckConstraint(condition=Q(amount__gte=0), name="amount_non_negative"),
        ]

    def __str__(self):
        return f"{self.kind} request {self.pk}"


class AuditEvent(models.Model):
    actor_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=64)
    employee = models.ForeignKey("EmployeeRecord", on_delete=models.PROTECT, blank=True, null=True)
    request = models.ForeignKey("HRRequest", on_delete=models.PROTECT, blank=True, null=True)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.action} event {self.pk}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Modification of existing audit event is not allowed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Deletion of audit event is not allowed.")


class Notification(models.Model):
    recipient_id = models.PositiveBigIntegerField()
    request = models.ForeignKey("HRRequest", on_delete=models.PROTECT, blank=True, null=True)
    event = models.CharField(max_length=64)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.event} for {self.recipient_id}"
