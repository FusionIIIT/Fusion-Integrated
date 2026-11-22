"""Feedback (BR-MMS-020; UC-012/013)."""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class Feedback(TimeStampedModel, UserScopedModel):
    text = models.TextField()

    class Meta:
        db_table = "mms_feedback"
        indexes = [
            models.Index(fields=["user_id", "-created_at"], name="feedback_student_idx"),
        ]

    def __str__(self) -> str:
        return f"feedback:{self.pk}"
