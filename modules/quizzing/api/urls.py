"""URL routing for the Quizzing API."""

from django.urls import path

from .views import (
    AiEvaluationView,
    AttemptIntegrityLogsView,
    QuestionBankListCreateView,
    QuestionBankQuestionView,
    QuizActionView,
    QuizAnalyticsReportView,
    QuizAttemptDetailView,
    QuizDetailView,
    QuizGradingView,
    QuizListCreateView,
)

urlpatterns = [
    path("question-banks/", QuestionBankListCreateView.as_view(), name="question_bank_list_create"),
    path(
        "question-banks/<uuid:pk>/questions/",
        QuestionBankQuestionView.as_view(),
        name="question_bank_questions",
    ),
    path("quizzes/", QuizListCreateView.as_view(), name="quiz_list_create"),
    path("quizzes/<uuid:pk>/", QuizDetailView.as_view(), name="quiz_detail"),
    path("quizzes/<uuid:pk>/<str:action>/", QuizActionView.as_view(), name="quiz_action"),
    path("quizzes/<uuid:pk>/analytics/", QuizAnalyticsReportView.as_view(), name="quiz_analytics"),
    path("quizzes/<uuid:pk>/submissions/", QuizGradingView.as_view(), name="quiz_submissions"),
    path("attempts/<uuid:pk>/", QuizAttemptDetailView.as_view(), name="attempt_detail"),
    path(
        "attempts/<uuid:pk>/integrity-logs/",
        AttemptIntegrityLogsView.as_view(),
        name="attempt_integrity_logs",
    ),
    path("answers/<uuid:pk>/override/", QuizGradingView.as_view(), name="score_override"),
    path("answers/<uuid:pk>/ai-evaluate/", AiEvaluationView.as_view(), name="ai_evaluation"),
]
