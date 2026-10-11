from django.conf import settings
from django.db import models


class LeaveRequest(models.Model):
    class LeaveType(models.TextChoices):
        CL = "CL", "Casual Leave"
        RH = "RH", "Restricted Holiday"
        SCL = "SCL", "Special Casual Leave"
        EL = "EL", "Earned Leave"
        VL = "VL", "Vacation Leave"
        COL = "COL", "Commuted Leave"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        CANCELLED = "cancelled", "Cancelled"

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="elm_leave_requests",
    )
    leave_type = models.CharField(
        max_length=10,
        choices=LeaveType.choices,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date cannot be before start date."}
            )

    def __str__(self):
        return (
            f"{self.employee_id} - {self.leave_type} "
            f"({self.start_date} to {self.end_date})"
        )
