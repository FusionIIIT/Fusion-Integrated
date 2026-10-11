from django.urls import path

from modules.leave_elm.api.views import (
    LeaveApplicationDetailView,
    LeaveApplicationListCreateView,
)

urlpatterns = [
    path(
        "applications",
        LeaveApplicationListCreateView.as_view(),
        name="leave-elm-applications",
    ),
    path(
        "applications/<int:pk>",
        LeaveApplicationDetailView.as_view(),
        name="leave-elm-application-detail",
    ),
]
