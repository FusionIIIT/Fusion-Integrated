import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


class QuestionType(models.TextChoices):
    MCQ_SINGLE = "MCQ_SINGLE", "Single Choice"
    MCQ_MULTI = "MCQ_MULTI", "Multiple Choice"
    TRUE_FALSE = "TRUE_FALSE", "True/False"
    SHORT_ANSWER = "SHORT_ANSWER", "Short Answer"
    SUBJECTIVE = "SUBJECTIVE", "Subjective"


class QuizStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    CLOSED = "CLOSED", "Closed"
    ARCHIVED = "ARCHIVED", "Archived"


class AttemptStatus(models.TextChoices):
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    SUBMITTED = "SUBMITTED", "Submitted"
    AUTOSUBMITTED = "AUTOSUBMITTED", "Auto-submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    EVALUATED = "EVALUATED", "Evaluated"


class NavigationMode(models.TextChoices):
    FREE = "FREE", "Free Navigation"
    LINEAR = "LINEAR", "Linear Restricted"


class QuestionBank(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_code = models.CharField(max_length=32, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_by = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "quizzing_question_bank"
        indexes = [
            models.Index(fields=["course_code", "created_at"], name="qz_bank_course_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.course_code} - {self.title}"


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=32,
        choices=QuestionType.choices,
        default=QuestionType.MCQ_SINGLE,
    )
    difficulty = models.CharField(max_length=16, default="MEDIUM")
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.JSONField(default=dict, blank=True)
    default_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("1.0"),
    )
    negative_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.0"),
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "quizzing_question"
        indexes = [
            models.Index(fields=["bank", "question_type"], name="qz_q_bank_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.question_type}: {self.question_text[:50]}"


class Quiz(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    course_code = models.CharField(max_length=32, db_index=True)
    created_by = models.CharField(max_length=64, db_index=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    status = models.CharField(
        max_length=16,
        choices=QuizStatus.choices,
        default=QuizStatus.DRAFT,
        db_index=True,
    )
    total_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.0"),
    )
    passing_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0.0"),
    )
    max_attempts = models.PositiveIntegerField(default=1)
    navigation_mode = models.CharField(
        max_length=16,
        choices=NavigationMode.choices,
        default=NavigationMode.FREE,
    )
    randomize_questions = models.BooleanField(default=False)
    allow_unanswered = models.BooleanField(default=True)
    negative_marking_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.0"),
    )
    answer_key_released = models.BooleanField(default=False)
    grades_released = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "quizzing_quiz"
        indexes = [
            models.Index(fields=["course_code", "status"], name="qz_quiz_course_st_idx"),
            models.Index(fields=["created_by", "created_at"], name="qz_quiz_creator_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.course_code}: {self.title} ({self.status})"


class QuizQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="quiz_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.0"))

    class Meta:
        db_table = "quizzing_quiz_question"
        unique_together = ("quiz", "question")
        indexes = [
            models.Index(fields=["quiz", "order"], name="qz_quiz_q_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.quiz_id} - Q{self.order}"


class QuizAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    student_user_id = models.CharField(max_length=64, db_index=True)
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=AttemptStatus.choices,
        default=AttemptStatus.IN_PROGRESS,
        db_index=True,
    )
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.0"))
    passed = models.BooleanField(default=False)
    flagged_for_integrity = models.BooleanField(default=False)
    last_answered_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "quizzing_attempt"
        indexes = [
            models.Index(fields=["quiz", "student_user_id"], name="qz_att_quiz_student_idx"),
            models.Index(fields=["status", "submitted_at"], name="qz_att_st_submitted_idx"),
        ]

    def __str__(self) -> str:
        return f"Attempt {self.id} by {self.student_user_id} ({self.status})"


class StudentAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    submitted_answer = models.JSONField(default=dict, blank=True)
    autograded_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    override_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    feedback = models.TextField(blank=True, default="")
    is_evaluated = models.BooleanField(default=False)

    class Meta:
        db_table = "quizzing_student_answer"
        unique_together = ("attempt", "question")
        indexes = [
            models.Index(fields=["attempt", "is_evaluated"], name="qz_ans_att_eval_idx"),
        ]

    def __str__(self) -> str:
        return f"Answer for Q{self.question_id} on Attempt {self.attempt_id}"

    @property
    def final_score(self) -> Decimal:
        if self.override_score is not None:
            return self.override_score
        return self.autograded_score if self.autograded_score is not None else Decimal("0.0")


class AttemptIntegrityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="integrity_logs",
    )
    event_type = models.CharField(max_length=64)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(blank=True, default="")

    class Meta:
        db_table = "quizzing_integrity_log"
        indexes = [
            models.Index(fields=["attempt", "timestamp"], name="qz_log_att_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} at {self.timestamp}"
