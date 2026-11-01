from django.urls import path

from modules.quizzes.api import views as v

urlpatterns = [
    # professor
    path("quizzes", v.QuizListView.as_view(), name="quizzes-list"),
    path("quizzes/<int:pk>/publish", v.PublishView.as_view(), name="quizzes-publish"),

    # student
    path("available", v.AvailableQuizzesView.as_view(), name="quizzes-available"),
    path("available/<int:pk>/start", v.StartAttemptView.as_view(),
         name="quizzes-start"),
    path("my-attempts/<int:pk>/responses", v.SaveResponseView.as_view(),
         name="quizzes-save-response"),
    path("my-attempts/<int:pk>/submit", v.SubmitAttemptView.as_view(),
         name="quizzes-submit"),
]
