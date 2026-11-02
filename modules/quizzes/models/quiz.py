from django.db import models
from core.db.mixins import TimeStampedModel
from modules.quizzes.domain.state_machine import QuizStatus, Status


class Quiz(TimeStampedModel):
    """Quiz model representing an academic quiz lifecycle (CW-QZ-01)."""
    course_id = models.CharField(max_length=64, db_index=True)
    created_by_id = models.IntegerField(db_index=True)  # IAM Professor User ID
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    max_marks = models.DecimalField(max_digits=6, decimal_places=2, default=100.0)
    passing_marks = models.DecimalField(max_digits=6, decimal_places=2, default=40.0)
    permitted_attempts = models.PositiveIntegerField(default=1)

    start_time = models.DateTimeField(null=True, blank=True)
    closing_time = models.DateTimeField(null=True, blank=True)

    # Configuration flags (BR-QZ-009 - BR-QZ-013)
    randomize_questions = models.BooleanField(default=False)
    randomize_options = models.BooleanField(default=False)
    allow_back_navigation = models.BooleanField(default=True)
    negative_marking_enabled = models.BooleanField(default=False)
    allow_unanswered = models.BooleanField(default=True)
    one_question_at_a_time = models.BooleanField(default=False)
    tab_blocking_enabled = models.BooleanField(default=False)

    status = models.CharField(
        max_length=64,
        choices=[(s.value, s.value) for s in QuizStatus],
        default=QuizStatus.DRAFT.value,
        db_index=True,
    )

    class Meta:
        db_table = "qz_quiz"
        indexes = [
            models.Index(fields=["course_id", "-created_at"], name="qz_quiz_course_idx"),
            models.Index(fields=["status", "-created_at"], name="qz_quiz_status_idx"),
        ]

    def __str__(self):
        return f"Quiz: {self.title} ({self.status})"


class QuizQuestion(TimeStampedModel):
    """Question item inside a quiz."""
    QUESTION_TYPES = [
        ("MCQ", "Multiple Choice"),
        ("MSQ", "Multiple Select"),
        ("TF", "True / False"),
        ("FITB", "Fill In The Blank"),
        ("SUBJECTIVE", "Subjective / Short Answer"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    question_type = models.CharField(max_length=32, choices=QUESTION_TYPES, default="MCQ")
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.TextField(blank=True)
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    topic = models.CharField(max_length=100, blank=True)
    difficulty = models.CharField(max_length=32, blank=True)
    reference_answer = models.TextField(blank=True)
    evaluation_criteria = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "qz_quiz_question"
        ordering = ["order", "id"]

    def __str__(self):
        return f"Question {self.id} for Quiz {self.quiz_id} ({self.question_type})"


class QuizTransition(models.Model):
    """Audit log of status transitions for quizzes and attempts."""
    quiz = models.ForeignKey(Quiz, null=True, blank=True, on_delete=models.CASCADE, related_name="transitions")
    attempt_id = models.IntegerField(null=True, blank=True)
    from_status = models.CharField(max_length=64)
    to_status = models.CharField(max_length=64)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=32, blank=True)
    workflow_id = models.CharField(max_length=32, blank=True)
    use_case_id = models.CharField(max_length=32, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "qz_quiz_transition"
        indexes = [
            models.Index(fields=["quiz", "-at"], name="qz_quiz_desc_at_idx"),
            models.Index(fields=["attempt_id", "-at"], name="qz_attempt_desc_at_idx"),
        ]

    def __str__(self):
        return f"Transition {self.from_status} -> {self.to_status} at {self.at}"
