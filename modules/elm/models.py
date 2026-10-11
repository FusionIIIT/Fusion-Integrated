from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.elm.domain.constants import LeaveType, HalfDayChoice, ApplicationStatus


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Leave balance account for an employee per year and leave category."""

    year = models.PositiveSmallIntegerField(default=2026, db_index=True)
    leave_type = models.CharField(
        max_length=8,
        choices=[(t.value, t.value) for t in LeaveType],
        db_index=True,
    )
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "year", "leave_type")
        ordering = ["year", "leave_type"]

    @property
    def available_balance(self) -> float:
        return float(self.allocated - self.availed - self.pending)

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.leave_type} ({self.year}): Avail {self.available_balance}"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Single leave application including optional Station Leave."""

    leave_type = models.CharField(
        max_length=8,
        choices=[(t.value, t.value) for t in LeaveType],
        db_index=True,
    )
    start_date = models.DateField(db_index=True)
    start_half = models.CharField(
        max_length=16,
        choices=[(h.value, h.value) for h in HalfDayChoice],
        default=HalfDayChoice.FULL.value,
    )
    end_date = models.DateField(db_index=True)
    end_half = models.CharField(
        max_length=16,
        choices=[(h.value, h.value) for h in HalfDayChoice],
        default=HalfDayChoice.FULL.value,
    )
    days_requested = models.DecimalField(max_digits=5, decimal_places=1, default=1.0)
    reason = models.TextField(max_length=1000)

    # Station leave fields
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=255, blank=True, default="")
    station_contact = models.CharField(max_length=32, blank=True, default="")
    emergency_contact = models.CharField(max_length=32, blank=True, default="")

    # Workflow references (plain user_ids, no cross-module FKs per ADR-0013)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    unit_head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True, db_index=True)

    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in ApplicationStatus],
        default=ApplicationStatus.SUBMITTED.value,
        db_index=True,
    )
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Leave #{self.id} (User {self.user_id}) - {self.leave_type} [{self.status}]"


class LeaveActionHistory(TimeStampedModel):
    """Audit log of actions taken on a leave application."""

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    actor_user_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=32)
    comments = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_action_history"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Leave #{self.application_id} Action {self.action} by User {self.actor_user_id}"


class Holiday(TimeStampedModel):
    """Institute calendar holidays and restricted holidays."""

    date = models.DateField(unique=True, db_index=True)
    name = models.CharField(max_length=120)
    is_restricted = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_holiday"
        ordering = ["date"]

    def __str__(self) -> str:
        tag = "RH" if self.is_restricted else "Holiday"
        return f"{self.date}: {self.name} ({tag})"
