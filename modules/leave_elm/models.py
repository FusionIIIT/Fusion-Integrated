"""Database models for Employee Leave Management."""

from django.db import models


class LeaveApplication(models.Model):
    class Category(models.TextChoices):
        CL = "CL", "Casual Leave"
        RH = "RH", "Restricted Holiday"
        SCL = "SCL", "Special Casual Leave"
        EL = "EL", "Earned Leave"
        COL = "COL", "Commuted Leave"
        VL = "VL", "Vacation Leave"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    employee_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=Category.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(max_length=2000)
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["employee_id", "status"],
                name="elm_employee_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.category} application #{self.pk}"
