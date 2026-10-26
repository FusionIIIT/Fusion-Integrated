from django.db import models
from django.utils import timezone


class LeaveType(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    max_days_per_year = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveApplication(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    applicant_id = models.CharField(max_length=64, db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="applications")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    reviewer_id = models.CharField(max_length=64, blank=True, default="")
    review_remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.applicant_id} - {self.leave_type.code} ({self.status})"
