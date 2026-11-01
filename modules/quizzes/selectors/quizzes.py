"""Read-side scoping. Anything out of scope is simply absent, so it 404s."""
from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from modules.quizzes.domain import state_machine as sm
from modules.quizzes.models import Attempt, Option, Question, Quiz

#: What a student may ever see of a quiz. Drafts and archives stay hidden.
_VISIBLE_TO_STUDENTS = (sm.SCHEDULED, sm.AVAILABLE, sm.CLOSED)


def _with_questions(qs: QuerySet) -> QuerySet:
    return qs.prefetch_related(
        Prefetch("questions", queryset=Question.objects.prefetch_related(
            Prefetch("options", queryset=Option.objects.order_by("position", "id")))))


def quizzes_owned_by(user_id: int) -> QuerySet[Quiz]:
    """A professor manages only their own quizzes (BR-QZ-002)."""
    return _with_questions(Quiz.objects.filter(owner_user_id=user_id))


def quizzes_for_student() -> QuerySet[Quiz]:
    """BR-QZ-003. Course enrolment is not yet checked: that needs an academics
    contract, which does not exist. Until then every published quiz is listed."""
    return _with_questions(Quiz.objects.filter(status__in=_VISIBLE_TO_STUDENTS))


def bank_for(user_id: int, *, course_code: str = "", topic: str = "",
             difficulty: str = "", question_type: str = "",
             search: str = "") -> QuerySet[Question]:
    """The professor's reusable questions, filtered as UC-QZ-003 asks."""
    qs = Question.objects.filter(owner_user_id=user_id, quiz__isnull=True)
    for field, value in (("course_code", course_code), ("topic", topic),
                         ("difficulty", difficulty), ("question_type", question_type)):
        if value:
            qs = qs.filter(**{field: value})
    if search:
        qs = qs.filter(text__icontains=search)
    return qs.prefetch_related("options")


def attempts_of(student_user_id: int) -> QuerySet[Attempt]:
    """A student sees only their own attempts (BR-QZ-004)."""
    return (Attempt.objects.filter(student_user_id=student_user_id)
            .select_related("quiz").prefetch_related("responses"))


def attempts_on_quizzes_of(owner_user_id: int) -> QuerySet[Attempt]:
    return (Attempt.objects.filter(quiz__owner_user_id=owner_user_id)
            .select_related("quiz").prefetch_related("responses__question"))


def expired_attempts(now) -> QuerySet[Attempt]:
    return Attempt.objects.filter(status=sm.IN_PROGRESS, deadline__lte=now)
