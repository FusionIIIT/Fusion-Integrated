from django.urls import path

from modules.elm.api.views import MyLeaveApplicationsView

urlpatterns = [
    path(
        "applications",
        MyLeaveApplicationsView.as_view(),
        name="elm-my-applications",
    ),
]