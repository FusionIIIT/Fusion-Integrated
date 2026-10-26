"""URL patterns for Employee Leave Management."""

from django.urls import path

from modules.elm.api.views import (
    DecideLeaveApplicationView,
    LeaveLifecycleView,
    MyLeaveApplicationsView,
    SubmitLeaveApplicationView,
)

app_name = "elm"

urlpatterns = [
    path(
        "my-leaves/",
        MyLeaveApplicationsView.as_view(),
        name="my-leaves",
    ),
    path(
        "apply/",
        SubmitLeaveApplicationView.as_view(),
        name="apply",
    ),
    path(
        "applications/<uuid:application_id>/lifecycle/",
        LeaveLifecycleView.as_view(),
        name="leave-lifecycle",
    ),
    path(
        "applications/<uuid:application_id>/decision/",
        DecideLeaveApplicationView.as_view(),
        name="decide-application",
    ),
]
