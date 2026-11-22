"""Quiz module URL configuration."""
from django.urls import path

from modules.quiz.api.views import (
    AddBankQuestionToQuizView,
    ArchiveQuizView,
    AttemptDetailView,
    AttemptEvaluationView,
    CloseQuizView,
    EligibleQuizDetailView,
    EligibleQuizzesView,
    MyResultDetailView,
    MyResultsView,
    PublishQuizView,
    QuestionBankListView,
    QuestionDetailView,
    QuestionListCreateView,
    QuizDetailView,
    QuizListCreateView,
    QuizReportView,
    QuizSubmissionsView,
    ReleaseAllResultsView,
    ReleaseAttemptResultView,
    SaveResponseView,
    StartAttemptView,
    SubmitAttemptView,
)

urlpatterns = [
    # -- Professor: quiz CRUD ------------------------------------------------
    path("quizzes/", QuizListCreateView.as_view(), name="quiz-list"),
    path("quizzes/<int:pk>/", QuizDetailView.as_view(), name="quiz-detail"),
    path("quizzes/<int:pk>/publish/", PublishQuizView.as_view(), name="quiz-publish"),
    path("quizzes/<int:pk>/close/", CloseQuizView.as_view(), name="quiz-close"),
    path("quizzes/<int:pk>/archive/", ArchiveQuizView.as_view(), name="quiz-archive"),

    # -- Professor: questions ------------------------------------------------
    path("quizzes/<int:quiz_pk>/questions/",
         QuestionListCreateView.as_view(), name="quiz-questions"),
    path("questions/<int:pk>/", QuestionDetailView.as_view(), name="question-detail"),

    # -- Professor: question bank --------------------------------------------
    path("bank/", QuestionBankListView.as_view(), name="question-bank"),
    path("bank/<int:pk>/add-to-quiz/",
         AddBankQuestionToQuizView.as_view(), name="bank-add-to-quiz"),

    # -- Professor: submissions / evaluation ---------------------------------
    path("quizzes/<int:quiz_pk>/submissions/",
         QuizSubmissionsView.as_view(), name="quiz-submissions"),
    path("attempts/<int:pk>/evaluate/",
         AttemptEvaluationView.as_view(), name="attempt-evaluate"),
    path("attempts/<int:pk>/release/",
         ReleaseAttemptResultView.as_view(), name="attempt-release"),
    path("quizzes/<int:quiz_pk>/release-all/",
         ReleaseAllResultsView.as_view(), name="quiz-release-all"),
    path("quizzes/<int:quiz_pk>/report/",
         QuizReportView.as_view(), name="quiz-report"),

    # -- Student: eligible quizzes ------------------------------------------
    path("eligible/", EligibleQuizzesView.as_view(), name="eligible-quizzes"),
    path("eligible/<int:pk>/", EligibleQuizDetailView.as_view(),
         name="eligible-quiz-detail"),
    path("eligible/<int:pk>/start/", StartAttemptView.as_view(),
         name="quiz-start"),

    # -- Student: active attempt --------------------------------------------
    path("attempts/<int:pk>/", AttemptDetailView.as_view(), name="attempt-detail"),
    path("attempts/<int:pk>/respond/", SaveResponseView.as_view(),
         name="attempt-respond"),
    path("attempts/<int:pk>/submit/", SubmitAttemptView.as_view(),
         name="attempt-submit"),

    # -- Student: results ----------------------------------------------------
    path("my-results/", MyResultsView.as_view(), name="my-results"),
    path("my-results/<int:pk>/", MyResultDetailView.as_view(),
         name="my-result-detail"),
]
