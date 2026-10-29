from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.elm.domain.state_machine import LeaveCategory, LeaveStatus


class LeaveApplication(TimeStampedModel):
    class Category(models.TextChoices):
        CASUAL = LeaveCategory.CASUAL.value, "Casual Leave"
        MEDICAL = LeaveCategory.MEDICAL.value, "Medical Leave"
        SPECIAL_CASUAL = LeaveCategory.SPECIAL_CASUAL.value, "Special Casual Leave"
        EARNED = LeaveCategory.EARNED.value, "Earned Leave"
        COMPENSATORY = LeaveCategory.COMPENSATORY.value, "Compensatory Off Leave"
        VACATION = LeaveCategory.VACATION.value, "Vacation Leave"

    class Status(models.TextChoices):
        PENDING = LeaveStatus.PENDING.value, "Pending"
        APPROVED = LeaveStatus.APPROVED.value, "Approved"
        REJECTED = LeaveStatus.REJECTED.value, "Rejected"
        CANCELLED = LeaveStatus.CANCELLED.value, "Cancelled"

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=32, choices=Category.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in LeaveStatus]),
                name="elm_leave_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(category__in=[c.value for c in LeaveCategory]),
                name="elm_leave_category_valid",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="elm_leave_date_range_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "-created_at"], name="elm_user_created_idx"),
            models.Index(fields=["status", "-created_at"], name="elm_status_created_idx"),
            models.Index(
                fields=["user_id", "status", "start_date", "end_date"],
                name="elm_user_overlap_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"LeaveApplication(id={self.pk}, user_id={self.user_id}, status={self.status})"
