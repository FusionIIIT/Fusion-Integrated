"""Employee Leave Management domain models.

Identity is referenced by IAM user id; this module does not create user accounts.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Employee(models.Model):
    # IAM owns identities. Nullable only to permit staged migration of legacy rows.
    user_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)

    class Meta:
        ordering = ("name", "id")

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELED = "canceled"
    STATUS_EXTENDED = "extended"
    STATUS_RESUMED = "resumed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_EXTENDED, "Extended"),
        (STATUS_RESUMED, "Resumed"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT,
                                 related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_PENDING)
    reason = models.TextField()
    decision_note = models.TextField(blank=True, default="")
    decided_by_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("employee", "status"), name="elm_emp_status_idx"),
            models.Index(fields=("start_date", "end_date"), name="elm_leave_dates_idx"),
        ]
        permissions = [
            ("view_all_leave_requests", "Can view all employee leave requests"),
            ("can_submit_leave", "Can submit leave"),
            ("can_approve_leave", "Can approve leave"),
            ("can_reject_leave", "Can reject leave"),
            ("can_withdraw_leave", "Can withdraw leave"),
            ("can_cancel_leave", "Can cancel leave"),
            ("can_extend_leave", "Can extend leave"),
            ("can_resume_leave", "Can resume leave"),
            ("can_view_leave_history", "Can view leave history"),
        ]

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1

    def clean(self):
        super().clean()
        errors = {}
        if self.start_date and self.end_date and self.end_date < self.start_date:
            errors["end_date"] = "End date cannot be earlier than start date."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.employee} — {self.start_date} to {self.end_date}"
