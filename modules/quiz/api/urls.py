from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.quiz.api.views import (
    AttemptViewSet,
    EvaluationViewSet,
    QuestionBankViewSet,
    QuizViewSet,
)

router = DefaultRouter()
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"question-bank", QuestionBankViewSet, basename="question-bank")
router.register(r"attempts", AttemptViewSet, basename="attempt")
router.register(r"evaluations", EvaluationViewSet, basename="evaluation")

urlpatterns = [
    path("", include(router.urls)),
]
