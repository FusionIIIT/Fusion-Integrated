from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveApplication(TimeStampedModel):
    class Category(models.TextChoices):
        CASUAL = "casual", "Casual Leave"
        MEDICAL = "medical", "Medical Leave"
        SPECIAL_CASUAL = "special_casual", "Special Casual Leave"
        EARNED = "earned", "Earned Leave"
        COMPENSATORY = "compensatory", "Compensatory Off Leave"
        VACATION = "vacation", "Vacation Leave"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user_id = models.BigIntegerField(db_index=True)
    category = models.CharField(max_length=32, choices=Category.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=Status.choices,
                              default=Status.PENDING)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applied_at"]
        indexes = [models.Index(fields=["user_id", "-applied_at"],
                                name="elm_user_applied_idx")]

    def __str__(self) -> str:
        return f"Leave application {self.pk}"