"""Attempt, selected question and current response persistence."""

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel


class Attempt(TimeStampedModel):
    """One Student attempt; the external Student identity is a scalar ID."""

    STATUS = [("in_progress", "In progress"), ("submitted", "Submitted")]
    SUBMISSION_METHOD = [("manual", "Manual"), ("time_expiry", "Time expiry")]

    quiz = models.ForeignKey("quiz.Quiz", on_delete=models.PROTECT, related_name="attempts")
    student_user_id = models.PositiveBigIntegerField()
    attempt_number = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=STATUS, default="in_progress")
    started_at = models.DateTimeField()
    deadline_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    submission_method = models.CharField(
        max_length=16, choices=SUBMISSION_METHOD, default="", blank=True
    )

    class Meta:
        db_table = "quiz_attempt"
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "student_user_id", "attempt_number"],
                name="quiz_attempt_number_uniq",
            ),
            models.CheckConstraint(
                condition=Q(attempt_number__gt=0), name="quiz_attempt_number_positive_ck"
            ),
            models.CheckConstraint(
                condition=Q(deadline_at__gt=F("started_at")),
                name="quiz_attempt_deadline_after_start_ck",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="in_progress",
                        submitted_at__isnull=True,
                        submission_method="",
                    )
                    | Q(
                        status="submitted",
                        submitted_at__isnull=False,
                        submission_method__gt="",
                    )
                ),
                name="quiz_attempt_submission_state_ck",
            ),
        ]
        indexes = [models.Index(fields=["status", "deadline_at"], name="quiz_attempt_deadline_idx")]

    def __str__(self) -> str:
        return f"attempt#{self.pk} quiz#{self.quiz_id} student#{self.student_user_id}"


class AttemptQuestion(TimeStampedModel):
    """Question presentation data frozen for one attempt."""

    attempt = models.ForeignKey(Attempt, on_delete=models.PROTECT, related_name="items")
    question = models.ForeignKey(
        "quiz.Question", on_delete=models.PROTECT, related_name="attempt_presentations"
    )
    display_order = models.PositiveIntegerField()
    displayed_option_keys = models.JSONField(default=list, blank=True)
    marks_at_start = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        db_table = "quiz_attempt_question"
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "display_order"], name="attempt_question_order_uniq"
            ),
        ]

    def __str__(self) -> str:
        return f"attempt#{self.attempt_id} question#{self.question_id}"


class Response(TimeStampedModel):
    """The latest answer payload for one question presented in an attempt."""

    attempt_question = models.OneToOneField(
        AttemptQuestion, on_delete=models.PROTECT, related_name="response"
    )
    answer_payload = models.JSONField(null=True, blank=True)
    saved_at = models.DateTimeField()
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "quiz_response"
        constraints = [
            models.CheckConstraint(
                condition=Q(revision__gt=0), name="response_revision_positive_ck"
            ),
        ]

    def __str__(self) -> str:
        return f"response#{self.pk} attempt_question#{self.attempt_question_id}"
