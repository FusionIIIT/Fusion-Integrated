from django.urls import path
from modules.leave.api import views

urlpatterns = [
    path("types", views.LeaveTypeListView.as_view(), name="leave-types"),
    path("balances", views.MyLeaveBalancesView.as_view(), name="leave-balances"),
    path("requests", views.MyLeaveRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/cancel", views.CancelLeaveRequestView.as_view(), name="leave-cancel"),
    path("approvals", views.PendingApprovalsView.as_view(), name="leave-pending-approvals"),
    path("requests/<int:pk>/decision", views.LeaveApprovalView.as_view(), name="leave-decision"),
]
