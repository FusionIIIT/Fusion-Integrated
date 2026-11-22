from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Quiz(TimeStampedModel):
    STATUS = [
        ("DRAFT", "Draft"),
        ("DRAFT_CONFIGURED", "Draft configured"),
        ("READY_TO_PUBLISH", "Ready to publish"),
        ("SCHEDULED", "Scheduled"),
        ("AVAILABLE", "Available"),
        ("CLOSED", "Closed"),
        ("ARCHIVED", "Archived"),
    ]
    course_id = models.IntegerField()
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="DRAFT")
    created_by_user_id = models.IntegerField()
    start_at = models.DateTimeField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    max_attempts = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "quiz_quiz"
        constraints = [
            models.CheckConstraint(
                condition=Q(duration_minutes__gt=0), name="quiz_duration_positive"
            ),
            models.CheckConstraint(condition=Q(max_attempts__gt=0), name="quiz_attempts_positive"),
            models.CheckConstraint(
                condition=Q(close_at__isnull=True)
                | Q(start_at__isnull=True)
                | Q(close_at__gt=models.F("start_at")),
                name="quiz_window_valid",
            ),
        ]


class QuizSettings(models.Model):
    quiz = models.OneToOneField(Quiz, on_delete=models.CASCADE, related_name="settings")
    allow_unanswered = models.BooleanField(default=True)
    back_navigation = models.BooleanField(default=True)
    tab_violation_limit = models.PositiveSmallIntegerField(default=3)
    negative_marking_enabled = models.BooleanField(default=False)
    result_visibility = models.CharField(max_length=16, default="FULL")

    def __str__(self):
        return f"Settings for quiz#{self.quiz_id}"


class QuestionBankItem(TimeStampedModel):
    QUESTION_TYPES = [
        ("MCQ", "MCQ"),
        ("TF", "True/False"),
        ("MSQ", "MSQ"),
        ("FIB", "Fill in the blank"),
        ("SHORT", "Short answer"),
        ("LONG", "Long answer"),
    ]
    owner_user_id = models.IntegerField()
    question_text = models.TextField()
    question_type = models.CharField(max_length=8, choices=QUESTION_TYPES)
    topic = models.CharField(max_length=100, blank=True)
    difficulty = models.CharField(max_length=20, blank=True)
    marks = models.DecimalField(max_digits=8, decimal_places=2)
    negative_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    image = models.ImageField(upload_to="quiz/question-bank/", blank=True)


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    question_type = models.CharField(max_length=8)
    marks = models.DecimalField(max_digits=8, decimal_places=2)
    negative_marks = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    correct = models.JSONField(default=list)
    position = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "position"], name="quiz_question_position_unique"
            ),
        ]

    def __str__(self):
        return f"Question #{self.position} for quiz#{self.quiz_id}"


class QuizOption(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="options")
    option_id = models.CharField(max_length=20)
    option_text = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["question", "option_id"], name="quiz_option_id_unique"),
        ]

    def __str__(self):
        return f"{self.question_id}:{self.option_id}"


class QuizAttempt(TimeStampedModel):
    STATUS = [("STARTED", "Started"), ("SUBMITTED", "Submitted")]
    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="attempts")
    student_id = models.IntegerField()
    status = models.CharField(max_length=16, choices=STATUS, default="STARTED")
    deadline_at = models.DateTimeField()
    seed = models.CharField(max_length=64)
    question_order = models.JSONField(default=list)
    tab_violations = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "student_id", "status"], name="quiz_attempt_status_unique"
            ),
            models.UniqueConstraint(
                fields=["quiz", "student_id"],
                condition=Q(status="STARTED"),
                name="quiz_one_active_attempt",
            ),
        ]


class AttemptResponse(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(QuizQuestion, on_delete=models.PROTECT)
    answer = models.JSONField(null=True, blank=True)
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="attempt_question_unique"),
        ]

    def __str__(self):
        return f"Response #{self.pk} for attempt#{self.attempt_id}"


class ResponseEvaluation(models.Model):
    STATUS = [("PENDING", "Pending"), ("AI_SUGGESTED", "AI suggested"), ("FINAL", "Final")]
    response = models.OneToOneField(
        AttemptResponse, on_delete=models.CASCADE, related_name="evaluation"
    )
    status = models.CharField(max_length=16, choices=STATUS, default="PENDING")
    auto_marks = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    final_marks = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    finalized_by = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Evaluation for response#{self.response_id}"


class QuizResult(models.Model):
    STATUS = [
        ("NOT_EVALUATED", "Not evaluated"),
        ("PARTIALLY_EVALUATED", "Partially evaluated"),
        ("EVALUATED", "Evaluated"),
        ("RELEASED", "Released"),
    ]
    attempt = models.OneToOneField(QuizAttempt, on_delete=models.CASCADE, related_name="result")
    status = models.CharField(max_length=24, choices=STATUS, default="NOT_EVALUATED")
    marks_obtained = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    percentage = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)

    def __str__(self):
        return f"Result for attempt#{self.attempt_id}: {self.status}"


class AuditLogEntry(models.Model):
    quiz_id = models.IntegerField()
    event = models.CharField(max_length=80)
    actor_user_id = models.IntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event} for quiz#{self.quiz_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Audit log entries are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Audit log entries are append-only.")


class Notification(models.Model):
    recipient_user_id = models.IntegerField()
    event = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    delivery_status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event} for user#{self.recipient_user_id}"
