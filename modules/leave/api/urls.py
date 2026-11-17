from django.urls import path
from modules.leave.api import views

urlpatterns = [
    path("types", views.LeaveTypeListView.as_view(), name="leave-types"),
    path("balances", views.MyLeaveBalancesView.as_view(), name="leave-balances"),
    path("requests", views.MyLeaveRequestsView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/cancel", views.CancelLeaveRequestView.as_view(), name="leave-cancel"),
    path("requests/<int:pk>/recommend", views.RecommendLeaveRequestView.as_view(), name="leave-recommend"),
    path("requests/<int:pk>/decision", views.LeaveApprovalView.as_view(), name="leave-decision"),
    path("approvals", views.PendingApprovalsView.as_view(), name="leave-pending-approvals"),
    path("ledger", views.LeaveLedgerListView.as_view(), name="leave-ledger"),
]
