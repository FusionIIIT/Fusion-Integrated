"""Course-scoped Quiz definitions and their question associations."""

from uuid import uuid4

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel


class Quiz(TimeStampedModel):
    """A course quiz; external course and creator identities are scalar IDs."""

    STATUS = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("available", "Available"),
        ("closed", "Closed"),
        ("archived", "Archived"),
    ]
    QUESTION_SELECTION_MODE = [
        ("fixed", "Fixed question set"),
        ("random_sample", "Random sample"),
    ]

    public_id = models.UUIDField(default=uuid4, editable=False)
    course_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_by_user_id = models.PositiveBigIntegerField()
    title = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    maximum_marks = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    passing_marks = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    permitted_attempts = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="draft")
    start_at = models.DateTimeField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)
    question_selection_mode = models.CharField(
        max_length=16, choices=QUESTION_SELECTION_MODE, default="fixed"
    )
    sample_count = models.PositiveSmallIntegerField(null=True, blank=True)
    shuffle_questions = models.BooleanField(default=False)
    shuffle_options = models.BooleanField(default=False)
    back_navigation_allowed = models.BooleanField(default=True)
    one_question_at_a_time = models.BooleanField(default=False)
    unanswered_allowed = models.BooleanField(default=True)
    tab_block_enabled = models.BooleanField(default=False)
    negative_marking_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "quiz_quiz"
        constraints = [
            models.UniqueConstraint(fields=["public_id"], name="quiz_public_id_uniq"),
            models.CheckConstraint(
                condition=Q(duration_seconds__isnull=True) | Q(duration_seconds__gt=0),
                name="quiz_duration_positive_ck",
            ),
            models.CheckConstraint(
                condition=Q(maximum_marks__isnull=True) | Q(maximum_marks__gt=0),
                name="quiz_max_marks_positive_ck",
            ),
            models.CheckConstraint(
                condition=Q(passing_marks__isnull=True) | Q(passing_marks__gte=0),
                name="quiz_passing_marks_nonnegative_ck",
            ),
            models.CheckConstraint(
                condition=Q(permitted_attempts__isnull=True) | Q(permitted_attempts__gt=0),
                name="quiz_attempt_limit_positive_ck",
            ),
            models.CheckConstraint(
                condition=Q(start_at__isnull=True)
                | Q(close_at__isnull=True)
                | Q(close_at__gt=F("start_at")),
                name="quiz_window_order_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "start_at", "close_at"], name="quiz_status_window_idx"),
            models.Index(fields=["course_id", "status"], name="quiz_course_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.title or 'Untitled quiz'} ({self.status})"


class QuizQuestion(TimeStampedModel):
    """A reusable Question attached to a quiz with an authored order."""

    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="quiz_questions")
    question = models.ForeignKey(
        "quiz.Question", on_delete=models.PROTECT, related_name="quiz_attachments"
    )
    position = models.PositiveIntegerField()
    marks_override = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    negative_mark_override = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = "quiz_quiz_question"
        constraints = [
            models.UniqueConstraint(fields=["quiz", "question"], name="quiz_question_pair_uniq"),
            models.UniqueConstraint(
                fields=["quiz", "position"], name="quiz_question_position_uniq"
            ),
        ]

    def __str__(self) -> str:
        return f"quiz#{self.quiz_id} question#{self.question_id} at {self.position}"
