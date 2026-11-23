"""Reusable Question Bank entries and canonical answer options."""

from uuid import uuid4

from django.db import models

from core.db.mixins import TimeStampedModel


class Question(TimeStampedModel):
    """Reusable question content; answer keys remain server-side data."""

    QUESTION_TYPE = [
        ("multiple_choice", "Multiple choice"),
        ("multiple_select", "Multiple select"),
        ("true_false", "True / False"),
        ("fill_blank", "Fill in the blank"),
        ("short_answer", "Short answer"),
        ("long_answer", "Long answer"),
    ]

    public_id = models.UUIDField(default=uuid4, editable=False)
    created_by_user_id = models.PositiveBigIntegerField()
    subject_id = models.PositiveBigIntegerField(null=True, blank=True)
    question_type = models.CharField(max_length=24, choices=QUESTION_TYPE)
    prompt = models.TextField()
    marks = models.DecimalField(max_digits=9, decimal_places=2)
    negative_mark_value = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    topic = models.CharField(max_length=160, blank=True)
    difficulty = models.CharField(max_length=24, blank=True)
    answer_key = models.JSONField(default=dict, blank=True)
    reference_answer = models.TextField(blank=True)
    evaluation_criteria = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "quiz_question"
        constraints = [
            models.UniqueConstraint(fields=["public_id"], name="quiz_question_public_id_uniq"),
        ]
        indexes = [
            models.Index(fields=["subject_id", "question_type"], name="question_subject_type_idx"),
            models.Index(fields=["topic", "difficulty"], name="question_topic_diff_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.question_type} question#{self.pk}"


class QuestionOption(TimeStampedModel):
    """An option with a stable canonical UUID independent of display order."""

    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="options")
    option_key = models.UUIDField(default=uuid4, editable=False)
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField()

    class Meta:
        db_table = "quiz_question_option"
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"], name="question_option_position_uniq"
            ),
            models.UniqueConstraint(fields=["option_key"], name="question_option_key_uniq"),
        ]

    def __str__(self) -> str:
        return f"option {self.option_key} for question#{self.question_id}"
