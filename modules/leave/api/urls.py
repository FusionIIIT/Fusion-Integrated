from django.urls import path

from modules.leave.api.views import (
    LeaveApplicationListCreateView,
    LeaveApplicationReviewView,
    LeaveBalanceListView,
)

urlpatterns = [
    path("balances", LeaveBalanceListView.as_view(), name="leave_balance_list"),
    path("applications", LeaveApplicationListCreateView.as_view(), name="leave_application_list_create"),
    path("applications/<int:pk>/review", LeaveApplicationReviewView.as_view(), name="leave_application_review"),
]
