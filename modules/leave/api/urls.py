from django.urls import path

from modules.leave.api import views

urlpatterns = [
    path("", views.LeaveDashboardView.as_view(), name="leave-dashboard"),
    path("requests", views.LeaveRequestListView.as_view(), name="leave-requests"),
    path("review", views.LeaveReviewView.as_view(), name="leave-review"),
    path("balances", views.LeaveBalanceManagementView.as_view(), name="leave-balances"),
    path("types", views.LeaveTypeManagementView.as_view(), name="leave-types"),
]
