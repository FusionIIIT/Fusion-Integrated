from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalance(TimeStampedModel, UserScopedModel):
    leave_type = models.CharField(max_length=10)  # CL, RH, SCL, EL, VL, COL
    balance = models.IntegerField(default=0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "leave_type")

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.leave_type}: {self.balance}"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    )

    leave_type = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    station_leave = models.BooleanField(default=False)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    review_remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Leave #{self.pk} (User {self.user_id}) - {self.leave_type} [{self.status}]"


class SubstituteRequest(TimeStampedModel):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("REJECTED", "Rejected"),
    )

    leave_application = models.OneToOneField(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="substitute_request",
    )
    substitute_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    class Meta:
        db_table = "elm_substitute_request"

    def __str__(self) -> str:
        return f"Substitute for Leave #{self.leave_application_id} - User {self.substitute_user_id}"


class HolidayCalendar(TimeStampedModel):
    date = models.DateField(unique=True)
    description = models.CharField(max_length=255)
    is_rh = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date}: {self.description}{' (RH)' if self.is_rh else ''}"


class LeavePolicy(TimeStampedModel):
    leave_type = models.CharField(max_length=10, unique=True)
    max_days = models.IntegerField()
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "elm_leave_policy"

    def __str__(self) -> str:
        return f"{self.leave_type}: {self.max_days} days"
