# API URL routes for ELM module
from django.urls import path

from modules.leave.api.views import (
    LeaveApplicationCancelView,
    LeaveApplicationListCreateView,
    LeaveApplicationReviewView,
    LeaveApplicationWithdrawView,
    LeaveBalanceListView,
)

urlpatterns = [
    path("balances", LeaveBalanceListView.as_view(), name="leave_balance_list"),
    path(
        "applications",
        LeaveApplicationListCreateView.as_view(),
        name="leave_application_list_create",
    ),
    path(
        "applications/<int:pk>/review",
        LeaveApplicationReviewView.as_view(),
        name="leave_application_review",
    ),
    path(
        "applications/<int:pk>/withdraw",
        LeaveApplicationWithdrawView.as_view(),
        name="leave_application_withdraw",
    ),
    path(
        "applications/<int:pk>/cancel",
        LeaveApplicationCancelView.as_view(),
        name="leave_application_cancel",
    ),
]
