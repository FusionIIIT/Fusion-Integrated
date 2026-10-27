from django.urls import path

from modules.leave.api.views import (
    LeaveRequestDetailView,
    LeaveRequestListView,
    LeaveRequestWithdrawView,
    LeaveTypeListView,
)

urlpatterns = [
    path("types", LeaveTypeListView.as_view(), name="leave-types"),
    path("requests", LeaveRequestListView.as_view(), name="leave-requests"),
    path(
        "requests/<int:pk>/withdraw",
        LeaveRequestWithdrawView.as_view(),
        name="leave-request-withdraw",
    ),
    path(
        "requests/<int:pk>",
        LeaveRequestDetailView.as_view(),
        name="leave-request-detail",
    ),
]
