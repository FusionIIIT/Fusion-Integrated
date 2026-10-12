from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class LeaveStatus(models.TextChoices):
    PENDING_SUBSTITUTE = "PENDING_SUBSTITUTE", "Pending Substitute"
    PENDING_APPROVAL = "PENDING_APPROVAL", "Pending Approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    year = models.PositiveSmallIntegerField(db_index=True)
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "year", "leave_type")

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.leave_type}: {self.balance}"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.CharField(max_length=10, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    purpose = models.TextField()
    status = models.CharField(
        max_length=25,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING_APPROVAL,
    )
    # Coupled station leave (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_address = models.TextField(blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_accepted = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"

    def __str__(self) -> str:
        return f"Leave #{self.pk} - User {self.user_id} ({self.status})"
