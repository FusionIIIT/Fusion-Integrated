from django.db import models


class LeaveRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    LEAVE_TYPE_CASUAL = "casual"
    LEAVE_TYPE_EARNED = "earned"
    LEAVE_TYPE_MEDICAL = "medical"
    LEAVE_TYPE_CHOICES = [
        (LEAVE_TYPE_CASUAL, "Casual"),
        (LEAVE_TYPE_EARNED, "Earned"),
        (LEAVE_TYPE_MEDICAL, "Medical"),
    ]

    employee_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_leave_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.employee_id}:{self.leave_type}:{self.start_date}"
