"""Relational models for the Mess Management System (MMS).

Zero cross-module foreign keys (ADR-0001).
All references to users, students, and employees use indexed integer IDs.
"""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.mms.domain.constants import (
    DayOfWeek,
    FeedbackCategory,
    MealTime,
    MessRole,
    RebateStatus,
    RegistrationStatus,
)

MESS_ROLE_CHOICES = [(r.value, r.name) for r in MessRole]
REGISTRATION_STATUS_CHOICES = [(s.value, s.name) for s in RegistrationStatus]
REBATE_STATUS_CHOICES = [(s.value, s.name) for s in RebateStatus]
MEAL_TIME_CHOICES = [(m.value, m.name) for m in MealTime]
DAY_OF_WEEK_CHOICES = [(d.value, d.name) for d in DayOfWeek]
FEEDBACK_CATEGORY_CHOICES = [(c.value, c.name) for c in FeedbackCategory]


class MessRoleAssignment(TimeStampedModel):
    """Assignment of Caretaker or Warden to a mess facility (BR-MMS-003, BR-MMS-004)."""

    employee_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=20, choices=MESS_ROLE_CHOICES, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_by_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "mms_role_assignments"
        indexes = [
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self) -> str:
        status = "Active" if self.is_active else "Inactive"
        return f"{self.role.capitalize()} (Employee {self.employee_id}) - {status}"


class RegistrationWindow(TimeStampedModel):
    """Administrative window for student mess registrations (BR-MMS-008)."""

    name = models.CharField(max_length=100)
    mess_name = models.CharField(max_length=50, default="Central Mess", db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_open = models.BooleanField(default=True, db_index=True)
    opened_by_id = models.IntegerField()

    class Meta:
        db_table = "mms_registration_windows"
        ordering = ["-start_date"]

    def __str__(self) -> str:
        status = "Open" if self.is_open else "Closed"
        return f"{self.name} ({self.start_date} to {self.end_date}) - {status}"


class MessRegistration(TimeStampedModel):
    """Student registration record for a mess cycle (BR-MMS-009 through BR-MMS-013)."""

    student_id = models.IntegerField(db_index=True)
    window_id = models.IntegerField(null=True, blank=True, db_index=True)
    mess_name = models.CharField(max_length=50, default="Central Mess")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=REGISTRATION_STATUS_CHOICES,
        default=RegistrationStatus.PENDING.value,
        db_index=True,
    )
    remarks = models.TextField(blank=True)
    reviewed_by_id = models.IntegerField(null=True, blank=True)
    deregistration_date = models.DateField(null=True, blank=True)
    deregistration_reason = models.TextField(blank=True)

    class Meta:
        db_table = "mms_registrations"
        indexes = [
            models.Index(fields=["student_id", "status"]),
            models.Index(fields=["mess_name", "status"]),
        ]

    def __str__(self) -> str:
        return f"Registration #{self.id}: Student {self.student_id} ({self.status})"


class DailyMenuItem(TimeStampedModel):
    """Weekly recurring meal schedule per mess, day, and meal time (BR-MMS-014)."""

    mess_name = models.CharField(max_length=50, default="Central Mess", db_index=True)
    day_of_week = models.CharField(max_length=15, choices=DAY_OF_WEEK_CHOICES, db_index=True)
    meal_time = models.CharField(max_length=15, choices=MEAL_TIME_CHOICES, db_index=True)
    items = models.TextField()
    is_active = models.BooleanField(default=True)
    updated_by_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mms_daily_menu_items"
        unique_together = ("mess_name", "day_of_week", "meal_time")
        ordering = ["day_of_week", "meal_time"]

    def __str__(self) -> str:
        return f"{self.mess_name} - {self.day_of_week} {self.meal_time}"


class RebateRequest(TimeStampedModel):
    """Student meal rebate application (BR-MMS-021 through BR-MMS-025)."""

    student_id = models.IntegerField(db_index=True)
    mess_name = models.CharField(max_length=50, default="Central Mess")
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.PositiveIntegerField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=REBATE_STATUS_CHOICES,
        default=RebateStatus.PENDING.value,
        db_index=True,
    )
    approved_start_date = models.DateField(null=True, blank=True)
    approved_end_date = models.DateField(null=True, blank=True)
    reviewed_by_id = models.IntegerField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "mms_rebates"
        indexes = [
            models.Index(fields=["student_id", "status"]),
        ]

    def __str__(self) -> str:
        return (
            f"Rebate #{self.id}: Student {self.student_id} "
            f"({self.start_date} to {self.end_date}) [{self.status}]"
        )


class MessFeedback(TimeStampedModel):
    """Student dining service ratings and feedback (BR-MMS-020)."""

    student_id = models.IntegerField(db_index=True)
    mess_name = models.CharField(max_length=50, default="Central Mess")
    rating = models.PositiveSmallIntegerField()  # 1 to 5 stars
    category = models.CharField(
        max_length=30,
        choices=FEEDBACK_CATEGORY_CHOICES,
        default=FeedbackCategory.GENERAL.value,
    )
    comments = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        db_table = "mms_feedbacks"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Feedback #{self.id} ({self.rating}*): {self.category}"


class MessActionLog(TimeStampedModel):
    """Immutable audit trail for all operational transitions (BR-MMS-041)."""

    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.IntegerField(db_index=True)
    actor_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=50)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "mms_action_logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Log #{self.id}: {self.action} on {self.entity_type} #{self.entity_id}"
