"""Quiz module models.

Institute people are referenced by plain user_id integers, never foreign keys.
Quiz and Question are owned by the quiz module only.
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.quiz.domain.state_machine import (
    AttemptStatus,
    QuizStatus,
    attempt_status_choices,
    quiz_status_choices,
)

# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

class Quiz(TimeStampedModel):
    """A quiz definition created and managed by a professor."""

    RESULT_VISIBILITY_CHOICES = [
        ("immediate", "Immediate — shown as soon as evaluated"),
        ("after_release", "After Release — professor releases explicitly"),
        ("never", "Never — professor-only"),
    ]
    STATUS_CHOICES = quiz_status_choices()

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    course = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=QuizStatus.DRAFT,
        db_index=True,
    )

    duration_minutes = models.PositiveIntegerField()
    max_marks = models.DecimalField(max_digits=8, decimal_places=2)
    passing_marks = models.DecimalField(max_digits=8, decimal_places=2,
                                        null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=1)

    start_at = models.DateTimeField(null=True, blank=True, db_index=True)
    close_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Assessment configuration
    allow_back_navigation = models.BooleanField(default=True)
    one_question_at_a_time = models.BooleanField(default=False)
    randomize_questions = models.BooleanField(default=False)
    randomize_options = models.BooleanField(default=False)
    allow_unanswered = models.BooleanField(default=True)
    tab_block = models.BooleanField(default=False)
    negative_marking = models.BooleanField(default=False)

    result_visibility = models.CharField(
        max_length=20,
        choices=RESULT_VISIBILITY_CHOICES,
        default="after_release",
    )

    # Creator — integer reference, no FK (ADR-0013)
    created_by_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "quiz_quiz"
        indexes = [
            models.Index(fields=["status", "start_at"], name="quiz_status_start_idx"),
            models.Index(fields=["created_by_user_id", "status"],
                         name="quiz_creator_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in QuizStatus]),
                name="quiz_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Quiz#{self.pk} '{self.title}' [{self.status}]"

    @property
    def is_editable(self) -> bool:
        return self.status == QuizStatus.DRAFT


# ---------------------------------------------------------------------------
# Question
# ---------------------------------------------------------------------------

class Question(models.Model):
    """A question belonging to a quiz, optionally stored in the question bank."""

    QUESTION_TYPE_CHOICES = [
        ("mcq",   "Multiple Choice (single answer)"),
        ("msq",   "Multiple Select (multiple answers)"),
        ("tf",    "True / False"),
        ("fitb",  "Fill in the Blank"),
        ("short", "Short Answer (subjective)"),
    ]

    DIFFICULTY_CHOICES = [
        ("easy",   "Easy"),
        ("medium", "Medium"),
        ("hard",   "Hard"),
    ]

    quiz = models.ForeignKey(
        Quiz, on_delete=models.CASCADE, related_name="questions"
    )
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES)
    text = models.TextField()
    image_url = models.URLField(max_length=500, blank=True, default="")

    marks = models.DecimalField(max_digits=6, decimal_places=2)
    negative_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    topic = models.CharField(max_length=200, blank=True)
    difficulty = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES, blank=True
    )
    order = models.PositiveIntegerField(default=0)

    # Question bank flag — reusable across quizzes (conceptually)
    is_bank_question = models.BooleanField(default=False)

    # Answer data (stored as JSON for flexibility)
    options = models.JSONField(
        null=True, blank=True,
        help_text="For MCQ/MSQ/TF: list of {id: str, text: str} dicts.",
    )
    correct_answer = models.JSONField(
        null=True, blank=True,
        help_text="Correct option id (MCQ/TF), list of ids (MSQ), or string (FITB).",
    )
    reference_answer = models.TextField(blank=True,
                                        help_text="Reference answer for AI evaluation.")
    evaluation_criteria = models.TextField(blank=True)

    class Meta:
        db_table = "quiz_question"
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["quiz", "order"], name="question_quiz_order_idx"),
            models.Index(
                fields=["is_bank_question"], name="question_bank_idx",
                condition=models.Q(is_bank_question=True),
            ),
        ]

    def __str__(self) -> str:
        return f"Q#{self.pk} [{self.question_type}] {self.text[:60]}"


# ---------------------------------------------------------------------------
# QuizAttempt
# ---------------------------------------------------------------------------

class QuizAttempt(TimeStampedModel, UserScopedModel):
    """One student's attempt at a quiz."""

    STATUS_CHOICES = attempt_status_choices()

    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="attempts")

    # user_id comes from UserScopedModel (IntegerField, db_index=True)

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default=AttemptStatus.IN_PROGRESS,
        db_index=True,
    )

    started_at = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)

    attempt_number = models.PositiveIntegerField(default=1)

    # Set after evaluation
    score = models.DecimalField(max_digits=8, decimal_places=2,
                                null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2,
                                     null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    time_taken_seconds = models.IntegerField(null=True, blank=True)

    tab_violations = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "quiz_attempt"
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "user_id", "attempt_number"],
                name="attempt_unique_per_quiz_user_number",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in AttemptStatus]),
                name="attempt_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["quiz", "status"], name="attempt_quiz_status_idx"),
            models.Index(fields=["user_id", "status"], name="attempt_user_status_idx"),
            models.Index(
                fields=["status", "started_at"],
                name="attempt_active_idx",
                condition=models.Q(status="in_progress"),
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Attempt#{self.pk} quiz={self.quiz_id} "
            f"u={self.user_id} [{self.status}]"
        )


# ---------------------------------------------------------------------------
# AttemptResponse
# ---------------------------------------------------------------------------

class AttemptResponse(models.Model):
    """One question's response within an attempt."""

    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="responses"
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT)

    response = models.JSONField(null=True, blank=True,
                                help_text="Student's answer (option id, list, text).")

    # Objective evaluation
    is_correct = models.BooleanField(null=True, blank=True)
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2,
                                         null=True, blank=True)

    # Subjective / AI evaluation
    ai_suggested_marks = models.DecimalField(max_digits=6, decimal_places=2,
                                             null=True, blank=True)
    ai_reasoning = models.TextField(blank=True)
    professor_feedback = models.TextField(blank=True)
    evaluated_by_user_id = models.IntegerField(null=True, blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "quiz_attempt_response"
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="response_unique_per_attempt_question",
            ),
        ]
        indexes = [
            models.Index(fields=["attempt", "question"],
                         name="response_attempt_question_idx"),
        ]

    def __str__(self) -> str:
        return f"Response#{self.pk} attempt={self.attempt_id} q={self.question_id}"


# ---------------------------------------------------------------------------
# QuizAuditLog
# ---------------------------------------------------------------------------

class QuizAuditLog(models.Model):
    """Append-only audit trail for quiz and attempt events (BR-QZ-022)."""

    quiz = models.ForeignKey(
        Quiz, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="audit_logs"
    )
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="audit_logs"
    )
    action = models.CharField(max_length=60, db_index=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    detail = models.JSONField(default=dict)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "quiz_audit_log"
        indexes = [
            models.Index(fields=["quiz", "at"], name="audit_quiz_at_idx"),
            models.Index(fields=["attempt", "at"], name="audit_attempt_at_idx"),
        ]

    def __str__(self) -> str:
        return f"Audit[{self.action}] quiz={self.quiz_id} at={self.at}"
