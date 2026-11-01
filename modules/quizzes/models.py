"""quizzes' tables. No foreign keys to other modules (ADR-0013).

People are referenced by IAM user id, and courses by code, as plain values.
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.quizzes.domain import scoring
from modules.quizzes.domain import state_machine as sm


def _choices(values):
    return [(v, v.replace("_", " ").title()) for v in values]


# Named so the OpenAPI schema can tell the two `status` enums apart.
QUIZ_STATUS_CHOICES = _choices(sm.QUIZ_STATUSES)
ATTEMPT_STATUS_CHOICES = _choices(sm.ATTEMPT_STATUSES)


class Quiz(TimeStampedModel):
    owner_user_id = models.IntegerField(db_index=True)   # the professor (BR-QZ-002)
    course_code = models.CharField(max_length=32, db_index=True)
    title = models.CharField(max_length=200)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=QUIZ_STATUS_CHOICES,
                              default=sm.DRAFT, db_index=True)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    max_attempts = models.PositiveSmallIntegerField(default=1)      # BR-QZ-008
    shuffle_questions = models.BooleanField(default=False)          # BR-QZ-009
    negative_marking = models.BooleanField(default=False)           # BR-QZ-011

    class Meta:
        ordering = ["-opens_at"]

    def __str__(self):
        return f"{self.course_code}: {self.title}"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name="questions", on_delete=models.CASCADE)
    question_type = models.CharField(max_length=16,
                                     choices=_choices(scoring.QUESTION_TYPES))
    text = models.TextField()
    marks = models.DecimalField(max_digits=6, decimal_places=2)
    negative_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    accepted_answers = models.JSONField(default=list, blank=True)   # fill-in-the-blank
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.text

    def key(self) -> scoring.QuestionKey:
        return scoring.QuestionKey(
            self.question_type, self.marks, self.negative_marks,
            frozenset(o.id for o in self.options.all() if o.is_correct),
            tuple(self.accepted_answers))


class Option(models.Model):
    question = models.ForeignKey(Question, related_name="options",
                                 on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.text


class Attempt(TimeStampedModel):
    quiz = models.ForeignKey(Quiz, related_name="attempts", on_delete=models.PROTECT)
    student_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=16, choices=ATTEMPT_STATUS_CHOICES,
                              default=sm.IN_PROGRESS, db_index=True)
    deadline = models.DateTimeField()
    score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    question_order = models.JSONField(default=list)     # fixed at start (BR-QZ-009)
    #: {question_id: {"options": [option ids], "text": str}}, saved as the
    #: student goes so a dropped connection loses nothing (BR-QZ-015).
    answers = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]

    def answer(self, question_id: int) -> scoring.Answer | None:
        given = self.answers.get(str(question_id))
        if given is None:
            return None
        return scoring.Answer(frozenset(given["options"]), given["text"])
