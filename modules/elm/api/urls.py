from django.urls import path

from modules.elm.api.views import (
    LeaveRequestCreateView,
    LeaveRequestListView,
)

urlpatterns = [
    path("applications", LeaveRequestListView.as_view(), name="elm-applications"),
    path(
        "applications/create",
        LeaveRequestCreateView.as_view(),
        name="elm-application-create",
    ),
]
