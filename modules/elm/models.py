from django.db import models


class LeaveType(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    employee_name = models.CharField(max_length=255)
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )
    reason = models.TextField()

    def __str__(self):
        return f"{self.employee_name} - {self.leave_type.name} ({self.start_date} to {self.end_date})"