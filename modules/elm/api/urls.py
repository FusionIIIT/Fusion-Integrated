from django.urls import path

from .views import (
    LeaveBalanceListView,
    LeaveRequestDetailView,
    LeaveRequestListView,
    LeaveTypeListView,
    SubstituteResponseListView,
)

urlpatterns = [
    path("leave-types/", LeaveTypeListView.as_view(), name="leave-type-list"),
    path("leave-requests/", LeaveRequestListView.as_view(), name="leave-request-list"),
    path("leave-requests/<int:pk>/", LeaveRequestDetailView.as_view(), name="leave-request-detail"),
    path("leave-balances/", LeaveBalanceListView.as_view(), name="leave-balance-list"),
    path(
        "substitute-responses/",
        SubstituteResponseListView.as_view(),
        name="substitute-response-list",
    ),
]
