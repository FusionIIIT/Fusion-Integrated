from django.urls import path

from modules.quizzes.api import views as v

urlpatterns = [
    # professor: authoring
    path("quizzes", v.QuizListView.as_view(), name="quizzes-list"),
    path("quizzes/<int:pk>", v.QuizDetailView.as_view(), name="quizzes-detail"),
    path("quizzes/<int:pk>/publish", v.QuizPublishView.as_view(),
         name="quizzes-publish"),
    path("quizzes/<int:pk>/close", v.QuizCloseView.as_view(), name="quizzes-close"),
    path("quizzes/<int:pk>/archive", v.QuizArchiveView.as_view(),
         name="quizzes-archive"),
    path("quizzes/<int:pk>/questions", v.QuizQuestionsView.as_view(),
         name="quizzes-questions"),
    path("quizzes/<int:pk>/questions/<int:question_id>",
         v.QuizQuestionDeleteView.as_view(), name="quizzes-question-delete"),
    path("quizzes/<int:pk>/questions/from-bank", v.QuizCopyFromBankView.as_view(),
         name="quizzes-copy-from-bank"),
    path("bank", v.QuestionBankView.as_view(), name="quizzes-bank"),

    # professor: evaluation
    path("quizzes/<int:pk>/attempts", v.QuizAttemptsView.as_view(),
         name="quizzes-attempts"),
    path("quizzes/<int:pk>/release", v.ReleaseResultsView.as_view(),
         name="quizzes-release"),
    path("attempts/<int:pk>/grade", v.GradeResponseView.as_view(),
         name="quizzes-grade"),

    # student
    path("available", v.AvailableQuizzesView.as_view(), name="quizzes-available"),
    path("available/<int:pk>/start", v.StartAttemptView.as_view(),
         name="quizzes-start"),
    path("my-attempts", v.MyAttemptsView.as_view(), name="quizzes-my-attempts"),
    path("my-attempts/<int:pk>", v.MyAttemptDetailView.as_view(),
         name="quizzes-my-attempt"),
    path("my-attempts/<int:pk>/responses", v.SaveResponseView.as_view(),
         name="quizzes-save-response"),
    path("my-attempts/<int:pk>/submit", v.SubmitAttemptView.as_view(),
         name="quizzes-submit"),
]
