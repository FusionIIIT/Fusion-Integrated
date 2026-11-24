from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.department.domain import state_machine as sm
from modules.department.domain.rules import FEEDBACK_CATEGORIES


class Feedback(TimeStampedModel):
    """Confidential: readable only by its submitter and the handling office (BR-DEPT-017)."""

    STATUS = [
        (sm.FEEDBACK_NEW, "New"),
        (sm.FEEDBACK_UNDER_REVIEW, "Under review"),
        (sm.FEEDBACK_RESOLVED, "Resolved"),
        (sm.FEEDBACK_CLOSED, "Closed"),
    ]

    department = models.ForeignKey(
        "department.Department", on_delete=models.PROTECT, related_name="feedback"
    )
    submitter_id = models.IntegerField()
    submitter_kind = models.CharField(max_length=10)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    category = models.CharField(
        max_length=20, blank=True, choices=[(c, c) for c in FEEDBACK_CATEGORIES]
    )
    status = models.CharField(max_length=14, choices=STATUS, default=sm.FEEDBACK_NEW)
    reviewed_by = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    disposed_by = models.IntegerField(null=True, blank=True)
    disposed_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        db_table = "department_feedback"
        constraints = [
            models.CheckConstraint(
                condition=Q(status=sm.FEEDBACK_NEW, reviewed_by__isnull=True)
                | (~Q(status=sm.FEEDBACK_NEW) & Q(reviewed_by__isnull=False)),
                name="dept_fb_reviewed_iff_not_new",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[sm.FEEDBACK_RESOLVED, sm.FEEDBACK_CLOSED], disposed_by__isnull=False
                )
                | (
                    ~Q(status__in=[sm.FEEDBACK_RESOLVED, sm.FEEDBACK_CLOSED])
                    & Q(disposed_by__isnull=True)
                ),
                name="dept_fb_disposed_iff_terminal",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "status", "-id"], name="dept_fb_queue_idx"),
            models.Index(fields=["submitter_id", "-id"], name="dept_fb_mine_idx"),
        ]


class FeedbackNote(models.Model):
    """An HOD oversight note (UC-DEPT-014); append-only."""

    feedback = models.ForeignKey(Feedback, on_delete=models.CASCADE, related_name="notes")
    author_id = models.IntegerField()
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "department_feedback_note"
        constraints = [models.CheckConstraint(condition=~Q(body=""), name="dept_note_has_body")]
        indexes = [models.Index(fields=["feedback", "id"], name="dept_note_thread_idx")]

    def __str__(self) -> str:
        return f"note {self.pk} on feedback {self.feedback_id}"
