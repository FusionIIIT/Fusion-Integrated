"""quizzes' tables. No foreign keys to other modules (ADR-0013).

People are referenced by IAM user id, and courses by code, as plain values.
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.quizzes.domain import scoring
from modules.quizzes.domain import state_machine as sm


def _choices(values):
    return [(v, v.replace("_", " ").title()) for v in values]


class Quiz(TimeStampedModel):
    owner_user_id = models.IntegerField(db_index=True)   # the professor (BR-QZ-002)
    course_code = models.CharField(max_length=32, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=_choices(sm.QUIZ_STATUSES),
                              default=sm.DRAFT, db_index=True)

    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    passing_marks = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    max_attempts = models.PositiveSmallIntegerField(default=1)      # BR-QZ-008

    # BR-QZ-009..013: applied while the student attempts.
    shuffle_questions = models.BooleanField(default=False)
    shuffle_options = models.BooleanField(default=False)
    allow_back_navigation = models.BooleanField(default=True)
    one_question_at_a_time = models.BooleanField(default=False)
    negative_marking = models.BooleanField(default=False)
    allow_unanswered = models.BooleanField(default=True)
    tab_block = models.BooleanField(default=False)
    show_answers_on_release = models.BooleanField(default=False)

    class Meta:
        ordering = ["-opens_at"]
        constraints = [
            models.CheckConstraint(condition=models.Q(closes_at__gt=models.F("opens_at")),
                                   name="quiz_closes_after_opening"),
        ]

    def __str__(self):
        return f"{self.course_code}: {self.title}"

    @property
    def max_marks(self):
        return sum((q.marks for q in self.questions.all()), scoring.ZERO)


class Question(TimeStampedModel):
    """A question in the professor's bank. `quiz` is null until it is used."""
    owner_user_id = models.IntegerField(db_index=True)
    quiz = models.ForeignKey(Quiz, null=True, blank=True, related_name="questions",
                             on_delete=models.CASCADE)
    question_type = models.CharField(max_length=16,
                                     choices=_choices(scoring.QUESTION_TYPES))
    text = models.TextField()
    image = models.CharField(max_length=255, blank=True)    # stored file key
    marks = models.DecimalField(max_digits=6, decimal_places=2)
    negative_marks = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    accepted_answers = models.JSONField(default=list, blank=True)   # fill-in-the-blank
    course_code = models.CharField(max_length=32, blank=True, db_index=True)
    topic = models.CharField(max_length=120, blank=True)
    difficulty = models.CharField(max_length=8, blank=True,
                                  choices=_choices(("easy", "medium", "hard")))
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    @property
    def is_objective(self) -> bool:
        return self.question_type in scoring.OBJECTIVE

    def key(self) -> scoring.QuestionKey:
        return scoring.QuestionKey(
            question_type=self.question_type, marks=self.marks,
            negative_marks=self.negative_marks,
            correct_option_ids=frozenset(
                o.id for o in self.options.all() if o.is_correct),
            accepted_answers=tuple(self.accepted_answers))


class Option(models.Model):
    question = models.ForeignKey(Question, related_name="options",
                                 on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]


class Attempt(TimeStampedModel):
    quiz = models.ForeignKey(Quiz, related_name="attempts", on_delete=models.PROTECT)
    student_user_id = models.IntegerField(db_index=True)
    number = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=_choices(sm.ATTEMPT_STATUSES),
                              default=sm.IN_PROGRESS, db_index=True)
    started_at = models.DateTimeField()
    deadline = models.DateTimeField()
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    question_order = models.JSONField(default=list)     # fixed at start (BR-QZ-009)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(fields=["quiz", "student_user_id", "number"],
                                    name="one_attempt_number_per_student"),
        ]


class Response(TimeStampedModel):
    attempt = models.ForeignKey(Attempt, related_name="responses",
                                on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
    selected_option_ids = models.JSONField(default=list, blank=True)
    text = models.TextField(blank=True)
    awarded_marks = models.DecimalField(max_digits=6, decimal_places=2,
                                        null=True, blank=True)
    feedback = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"],
                                    name="one_response_per_question"),
        ]

    def answer(self) -> scoring.Answer:
        return scoring.Answer(frozenset(self.selected_option_ids), self.text)
