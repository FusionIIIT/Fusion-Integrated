from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalance(TimeStampedModel, UserScopedModel):
    year = models.PositiveSmallIntegerField(default=2026, db_index=True)
    leave_type = models.CharField(max_length=8, db_index=True)
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "year", "leave_type")

    @property
    def available_balance(self) -> float:
        return float(self.allocated - self.availed - self.pending)


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("RECOMMENDED", "Recommended"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    leave_type = models.CharField(max_length=8)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(max_digits=5, decimal_places=1, default=1.0)
    reason = models.TextField(max_length=1000)
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SUBMITTED")
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]


class LeaveActionHistory(TimeStampedModel):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="actions")
    actor_user_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=32)
    comments = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_action_history"
