"""URL routing for the Quizzing API."""

from django.urls import path

from .views import (
    AttemptIntegrityLogsView,
    QuizActionView,
    QuizAttemptDetailView,
    QuizDetailView,
    QuizGradingView,
    QuizListCreateView,
)

urlpatterns = [
    path("quizzes/", QuizListCreateView.as_view(), name="quiz_list_create"),
    path("quizzes/<uuid:pk>/", QuizDetailView.as_view(), name="quiz_detail"),
    path("quizzes/<uuid:pk>/<str:action>/", QuizActionView.as_view(), name="quiz_action"),
    path("attempts/<uuid:pk>/", QuizAttemptDetailView.as_view(), name="attempt_detail"),
    path(
        "attempts/<uuid:pk>/integrity-logs/",
        AttemptIntegrityLogsView.as_view(),
        name="attempt_integrity_logs",
    ),
    path("quizzes/<uuid:pk>/submissions/", QuizGradingView.as_view(), name="quiz_submissions"),
    path("answers/<uuid:pk>/override/", QuizGradingView.as_view(), name="score_override"),
]
