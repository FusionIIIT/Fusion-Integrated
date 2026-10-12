from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    path("requests", v.LeaveListView.as_view(), name="elm-requests"),
    path("requests/apply", v.LeaveApplyView.as_view(), name="elm-apply"),
    path("requests/<int:pk>/transition", v.LeaveTransitionView.as_view(),
         name="elm-transition"),
]
