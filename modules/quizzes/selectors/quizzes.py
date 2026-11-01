"""Read-side scoping. Anything out of scope is simply absent, so it 404s."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.quizzes.domain import state_machine as sm
from modules.quizzes.models import Attempt, Quiz


def quizzes_owned_by(user_id: int) -> QuerySet[Quiz]:
    """A professor manages only their own quizzes (BR-QZ-002)."""
    return Quiz.objects.filter(owner_user_id=user_id).prefetch_related("questions")


def quizzes_for_student() -> QuerySet[Quiz]:
    """BR-QZ-003. Course enrolment is not checked yet: that needs an academics
    contract, which does not exist. Until then every published quiz is listed."""
    return Quiz.objects.exclude(status=sm.DRAFT).prefetch_related("questions")


def attempts_of(student_user_id: int) -> QuerySet[Attempt]:
    """A student sees only their own attempts (BR-QZ-004)."""
    return Attempt.objects.filter(student_user_id=student_user_id) \
        .select_related("quiz")

