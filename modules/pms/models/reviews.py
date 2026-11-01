"""Director assignment and review models."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class DirectorAssignment(TimeStampedModel):
    """Assignment of an application to a Director for technical review."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="director_assignments"
    )
    director_user_id = models.IntegerField(db_index=True)
    assigned_by_user_id = models.IntegerField()
    due_at = models.DateTimeField()
    status = models.CharField(max_length=50, default="assigned")  # assigned, completed, reassigned

    class Meta:
        db_table = "pms_director_assignment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["director_user_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"App {self.application_id} -> Director {self.director_user_id}"


class DirectorReview(TimeStampedModel):
    """Director technical evaluation and decision (BR-PMS-029, 030)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="director_reviews"
    )
    director_user_id = models.IntegerField(db_index=True)
    decision = models.CharField(max_length=50, db_index=True)  # approve, reject, needs_revision
    justification = models.TextField()  # Minimum 50 chars enforced by BR-PMS-030
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pms_director_review"
        ordering = ["-decided_at"]

    def __str__(self) -> str:
        return f"{self.decision.upper()} by {self.director_user_id} on {self.application_id}"
