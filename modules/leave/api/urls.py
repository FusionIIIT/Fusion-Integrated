"""Leave module URL routes."""
from django.urls import path

from modules.leave.api.views import (
    ApplyLeaveView,
    LeaveTypeListView,
    MyBalanceListView,
    MyLeaveListView,
    PendingLeaveListView,
    TransitionLeaveView,
)

urlpatterns = [
    path("types/",       LeaveTypeListView.as_view(),    name="leave-types"),
    path("balances/me/", MyBalanceListView.as_view(),    name="leave-balances-me"),
    path("requests/me/", MyLeaveListView.as_view(),      name="leave-requests-me"),
    path("requests/queue/", PendingLeaveListView.as_view(), name="leave-requests-queue"),
    path("apply/",       ApplyLeaveView.as_view(),       name="leave-apply"),
    path("requests/<int:request_id>/transition/", TransitionLeaveView.as_view(), name="leave-transition"),
]
