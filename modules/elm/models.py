from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalance(TimeStampedModel, UserScopedModel):
    year = models.PositiveSmallIntegerField(default=2026, db_index=True)
    leave_type = models.CharField(max_length=10, db_index=True)
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "elm_leave_account"
        unique_together = ("user_id", "year", "leave_type")

    @property
    def remaining(self) -> float:
        return float(self.allocated - self.availed - self.pending)


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    leave_type = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    days_count = models.DecimalField(max_digits=5, decimal_places=1, default=1.0)
    reason = models.TextField(max_length=800)
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=250, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    admin_remark = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]


class LeaveActionHistory(TimeStampedModel):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="actions")
    actor_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=30)
    remark = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_audit_log"
