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


class MessRoleAssignment(TimeStampedModel):
    mess_name = models.CharField(max_length=64)
    role = models.CharField(
        max_length=32,
        choices=[(r.value, r.name) for r in MessRole],
    )
    employee_id = models.IntegerField(db_index=True)
    is_active = models.BooleanField(default=True)
    assigned_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.mess_name} (Emp {self.employee_id})"


class RegistrationWindow(TimeStampedModel):
    semester = models.CharField(max_length=32)
    start_date = models.DateField()
    end_date = models.DateField()
    is_open = models.BooleanField(default=True)
    created_by_id = models.IntegerField()

    def __str__(self):
        return f"{self.semester} ({self.start_date} to {self.end_date})"


class MessRegistration(TimeStampedModel):
    student_id = models.IntegerField(db_index=True)
    mess_name = models.CharField(max_length=64)
    window = models.ForeignKey(
        RegistrationWindow,
        on_delete=models.CASCADE,
        related_name="registrations",
    )
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in RegistrationStatus],
        default=RegistrationStatus.PENDING.value,
    )
    registered_date = models.DateField(auto_now_add=True)
    deregistration_date = models.DateField(null=True, blank=True)
    reviewer_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Student {self.student_id} - {self.mess_name} [{self.status}]"


class DailyMenuItem(TimeStampedModel):
    mess_name = models.CharField(max_length=64)
    day_of_week = models.CharField(
        max_length=16,
        choices=[(d.value, d.name) for d in DayOfWeek],
    )
    meal_time = models.CharField(
        max_length=16,
        choices=[(m.value, m.name) for m in MealTime],
    )
    menu_description = models.TextField()
    last_updated_by_id = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("mess_name", "day_of_week", "meal_time")

    def __str__(self):
        return f"{self.mess_name} - {self.day_of_week} {self.meal_time}"


class RebateRequest(TimeStampedModel):
    student_id = models.IntegerField(db_index=True)
    mess_name = models.CharField(max_length=64)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.PositiveIntegerField()
    reason = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in RebateStatus],
        default=RebateStatus.PENDING.value,
    )
    reviewer_id = models.IntegerField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Rebate {self.student_id}: {self.start_date} to {self.end_date}"


class MessFeedback(TimeStampedModel):
    student_id = models.IntegerField(db_index=True)
    mess_name = models.CharField(max_length=64)
    category = models.CharField(
        max_length=32,
        choices=[(c.value, c.name) for c in FeedbackCategory],
        default=FeedbackCategory.GENERAL.value,
    )
    comment = models.TextField()
    is_addressed = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Feedback {self.student_id} - {self.category}"


class MessActionLog(TimeStampedModel):
    action_by_id = models.IntegerField()
    action_type = models.CharField(max_length=64)
    target_id = models.IntegerField(null=True, blank=True)
    details = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.action_type} by {self.action_by_id}"

