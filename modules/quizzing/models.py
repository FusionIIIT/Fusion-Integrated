import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone


class QuestionType(models.TextChoices):
    MCQ_SINGLE = "MCQ_SINGLE", "Single Choice"
    MCQ_MULTI = "MCQ_MULTI", "Multiple Choice"
    TRUE_FALSE = "TRUE_FALSE", "True/False"
    SHORT_ANSWER = "SHORT_ANSWER", "Short Answer"


class QuizStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    CLOSED = "CLOSED", "Closed"


class AttemptStatus(models.TextChoices):
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    SUBMITTED = "SUBMITTED", "Submitted"
    AUTOSUBMITTED = "AUTOSUBMITTED", "Auto-submitted"
    EVALUATED = "EVALUATED", "Evaluated"


class QuestionBank(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_code = models.CharField(max_length=32, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    created_by = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "quizzing_question_bank"


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bank = models.ForeignKey(QuestionBank, on_delete=models.SET_NULL, null=True, blank=True, related_name="questions")
    question_text = models.TextField()
    question_type = models.CharField(max_length=32, choices=QuestionType.choices, default=QuestionType.MCQ_SINGLE)
    difficulty = models.CharField(max_length=16, default="MEDIUM")
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.JSONField(default=dict, blank=True)
    default_marks = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.0"))
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "quizzing_question"


class Quiz(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    course_code = models.CharField(max_length=32, db_index=True)
    created_by = models.CharField(max_length=64, db_index=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    status = models.CharField(max_length=16, choices=QuizStatus.choices, default=QuizStatus.DRAFT, db_index=True)
    total_marks = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.0"))
    answer_key_released = models.BooleanField(default=False)
    grades_released = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "quizzing_quiz"


class QuizQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="quiz_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    marks = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("1.0"))

    class Meta:
        db_table = "quizzing_quiz_question"


class QuizAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    student_user_id = models.CharField(max_length=64, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=AttemptStatus.choices, default=AttemptStatus.IN_PROGRESS, db_index=True)
    total_score = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.0"))

    class Meta:
        db_table = "quizzing_attempt"


class StudentAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    submitted_answer = models.JSONField(default=dict, blank=True)
    autograded_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    override_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True, default="")

    class Meta:
        db_table = "quizzing_student_answer"

    @property
    def final_score(self) -> Decimal:
        return self.override_score if self.override_score is not None else (self.autograded_score or Decimal("0.0"))


class AttemptIntegrityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="integrity_logs")
    event_type = models.CharField(max_length=64)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(blank=True, default="")

    class Meta:
        db_table = "quizzing_integrity_log"
