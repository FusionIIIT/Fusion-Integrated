"""Quiz Management API routes; identifiers are never treated as scope facts."""

from django.urls import path

from modules.quiz.api import views

urlpatterns = [
    path("quizzes", views.QuizListCreateView.as_view(), name="quiz-list-create"),
    path(
        "quizzes/<uuid:public_id>",
        views.QuizDetailUpdateView.as_view(),
        name="quiz-detail-update",
    ),
    path(
        "quizzes/<uuid:public_id>/publish",
        views.QuizPublishView.as_view(),
        name="quiz-publish",
    ),
    path("questions", views.QuestionBankListView.as_view(), name="quiz-question-bank"),
    path(
        "questions/<uuid:public_id>",
        views.QuestionBankDetailView.as_view(),
        name="quiz-question-bank-detail",
    ),
    path(
        "eligible-quizzes",
        views.EligibleQuizListView.as_view(),
        name="quiz-eligible-list",
    ),
    path(
        "eligible-quizzes/<uuid:public_id>",
        views.EligibleQuizDetailView.as_view(),
        name="quiz-eligible-detail",
    ),
    path(
        "attempts/<int:attempt_id>", views.StudentAttemptDetailView.as_view(), name="quiz-attempt"
    ),
    path(
        "attempts/<int:attempt_id>/responses/<int:attempt_question_id>",
        views.StudentResponseView.as_view(),
        name="quiz-attempt-response",
    ),
    path(
        "attempts/<int:attempt_id>/submit",
        views.StudentAttemptSubmitView.as_view(),
        name="quiz-attempt-submit",
    ),
    path("results", views.StudentReleasedResultListView.as_view(), name="quiz-result-list"),
    path(
        "results/<int:result_id>",
        views.StudentReleasedResultDetailView.as_view(),
        name="quiz-result-detail",
    ),
]
