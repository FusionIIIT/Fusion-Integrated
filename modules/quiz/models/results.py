"""Evaluation and released result records."""

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel


class ResponseEvaluation(TimeStampedModel):
    """Objective or human evaluation, with advisory marks stored separately."""

    METHOD = [("objective", "Objective"), ("manual", "Manual"), ("ai_assisted", "AI assisted")]

    response = models.OneToOneField(
        "quiz.Response", on_delete=models.PROTECT, related_name="evaluation"
    )
    method = models.CharField(max_length=16, choices=METHOD)
    maximum_marks = models.DecimalField(max_digits=9, decimal_places=2)
    awarded_marks = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    suggested_marks = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    reasoning = models.JSONField(default=dict, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    missing_concepts = models.JSONField(default=list, blank=True)
    finalized_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "quiz_response_evaluation"
        constraints = [
            models.CheckConstraint(
                condition=Q(awarded_marks__isnull=True)
                | Q(awarded_marks__gte=0, awarded_marks__lte=F("maximum_marks")),
                name="response_evaluation_awarded_range_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"evaluation#{self.pk} response#{self.response_id} ({self.method})"


class QuizResult(TimeStampedModel):
    """One proposed result record per Attempt, with explicit release metadata."""

    STATUS = [
        ("not_evaluated", "Not evaluated"),
        ("partially_evaluated", "Partially evaluated"),
        ("evaluated", "Evaluated"),
        ("released", "Released"),
    ]

    attempt = models.OneToOneField("quiz.Attempt", on_delete=models.PROTECT, related_name="result")
    status = models.CharField(max_length=20, choices=STATUS, default="not_evaluated")
    total_marks = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    marks_obtained = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    correct_count = models.PositiveIntegerField(null=True, blank=True)
    incorrect_count = models.PositiveIntegerField(null=True, blank=True)
    unanswered_count = models.PositiveIntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    released_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "quiz_result"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        status="released",
                        released_at__isnull=False,
                        released_by_user_id__isnull=False,
                    )
                    | (
                        ~Q(status="released")
                        & Q(released_at__isnull=True, released_by_user_id__isnull=True)
                    )
                ),
                name="quiz_result_release_fields_ck",
            ),
        ]
        indexes = [models.Index(fields=["status", "released_at"], name="quiz_result_release_idx")]

    def __str__(self) -> str:
        return f"result#{self.pk} attempt#{self.attempt_id} ({self.status})"
