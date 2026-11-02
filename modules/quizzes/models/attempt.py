from django.db import models
from core.db.mixins import TimeStampedModel
from modules.quizzes.domain.state_machine import AttemptStatus, ResultStatus
from modules.quizzes.models.quiz import Quiz, QuizQuestion


class QuizAttempt(TimeStampedModel):
    """Student quiz attempt model (CW-QZ-02)."""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    student_id = models.IntegerField(db_index=True)  # IAM Student User ID
    attempt_number = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=64,
        choices=[(s.value, s.value) for s in AttemptStatus],
        default=AttemptStatus.IN_PROGRESS.value,
        db_index=True,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_auto_submitted = models.BooleanField(default=False)

    class Meta:
        db_table = "qz_quiz_attempt"
        indexes = [
            models.Index(fields=["student_id", "quiz", "-started_at"], name="qz_student_quiz_idx"),
            models.Index(fields=["status", "-started_at"], name="qz_attempt_status_idx"),
        ]

    def __str__(self):
        return f"Attempt {self.attempt_number} by Student {self.student_id} on Quiz {self.quiz_id} ({self.status})"


class QuizResponse(TimeStampedModel):
    """Student response to an individual question."""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="responses")
    answer_text = models.TextField(blank=True)

    # Evaluation state
    is_evaluated = models.BooleanField(default=False)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    negative_marks = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    # Subjective evaluation details (BR-QZ-019)
    ai_suggested_marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_feedback = models.TextField(blank=True)
    professor_feedback = models.TextField(blank=True)

    class Meta:
        db_table = "qz_quiz_response"
        unique_together = ("attempt", "question")

    def __str__(self):
        return f"Response for Question {self.question_id} in Attempt {self.attempt_id}"


class QuizResult(TimeStampedModel):
    """Evaluated result for a completed quiz attempt (CW-QZ-03)."""
    attempt = models.OneToOneField(QuizAttempt, on_delete=models.CASCADE, related_name="result")
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    marks_obtained = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    negative_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    is_passed = models.BooleanField(default=False)

    correct_count = models.PositiveIntegerField(default=0)
    incorrect_count = models.PositiveIntegerField(default=0)
    unanswered_count = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=64,
        choices=[(s.value, s.value) for s in ResultStatus],
        default=ResultStatus.NOT_EVALUATED.value,
        db_index=True,
    )

    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "qz_quiz_result"
        indexes = [
            models.Index(fields=["status", "-created_at"], name="qz_result_status_idx"),
        ]

    def __str__(self):
        return f"Result for Attempt {self.attempt_id}: {self.marks_obtained}/{self.total_marks} ({self.status})"
