from django.urls import path

from modules.elm.api.views import (
    LeaveApplicationCancelView,
    LeaveApplicationDetailView,
    LeaveApplicationListCreateView,
    LeaveApplicationReviewView,
)

urlpatterns = [
    path(
        "leave-applications",
        LeaveApplicationListCreateView.as_view(),
        name="elm-leave-applications",
    ),
    path(
        "leave-applications/<int:pk>",
        LeaveApplicationDetailView.as_view(),
        name="elm-leave-application-detail",
    ),
    path(
        "leave-applications/<int:pk>/review",
        LeaveApplicationReviewView.as_view(),
        name="elm-leave-application-review",
    ),
    path(
        "leave-applications/<int:pk>/cancel",
        LeaveApplicationCancelView.as_view(),
        name="elm-leave-application-cancel",
    ),
]
