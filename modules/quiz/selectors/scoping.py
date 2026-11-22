from django.http import Http404

from modules.quiz.models import Quiz, QuizAttempt, QuizResult


def scope_quizzes_for_user(user_id, role, course_id=None):
    qs = Quiz.objects.all().order_by("-created_at")
    if role == "faculty":
        qs = qs.filter(created_by_user_id=user_id)
    else:
        qs = qs.filter(status__in=["AVAILABLE", "CLOSED", "ARCHIVED"])
    if course_id:
        qs = qs.filter(course_id=course_id)
    return qs


def get_scoped_quiz(quiz_id, user_id, role):
    try:
        quiz = (
            Quiz.objects.select_related("settings")
            .prefetch_related("questions__options")
            .get(pk=quiz_id)
        )
    except Quiz.DoesNotExist:
        raise Http404("Quiz not found.") from None

    if role == "faculty":
        if quiz.created_by_user_id != user_id:
            raise Http404("Quiz not found.")
    else:
        if quiz.status not in ["AVAILABLE", "CLOSED", "ARCHIVED"]:
            raise Http404("Quiz not found.")
    return quiz


def get_scoped_attempt(attempt_id, user_id, role):
    try:
        attempt = (
            QuizAttempt.objects.select_related("quiz")
            .prefetch_related("responses__question__options")
            .get(pk=attempt_id)
        )
    except QuizAttempt.DoesNotExist:
        raise Http404("Attempt not found.") from None

    if role == "faculty":
        if attempt.quiz.created_by_user_id != user_id:
            raise Http404("Attempt not found.")
    else:
        if attempt.student_id != user_id:
            raise Http404("Attempt not found.")
    return attempt


def get_scoped_result(result_id, user_id, role):
    try:
        result = QuizResult.objects.select_related("attempt__quiz").get(pk=result_id)
    except QuizResult.DoesNotExist:
        raise Http404("Result not found.") from None

    if role == "faculty":
        if result.attempt.quiz.created_by_user_id != user_id:
            raise Http404("Result not found.")
    else:
        if result.attempt.student_id != user_id or result.status != "RELEASED":
            raise Http404("Result not found.")
    return result
