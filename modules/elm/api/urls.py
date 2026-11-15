from django.urls import path
from .views import (
    LeaveListCreateView, LeaveBalanceView, SubstituteQueueView,
    SubstituteDecisionView, ApprovalsQueueView, ApproverDecisionView, LeaveWithdrawView
)

urlpatterns = [
    path("leaves/", LeaveListCreateView.as_view(), name="leave_list_create"),
    path("balances/", LeaveBalanceView.as_view(), name="leave_balances"),
    path("substitute-queue/", SubstituteQueueView.as_view(), name="substitute_queue"),
    path("substitute-queue/<uuid:pk>/decision/", SubstituteDecisionView.as_view(), name="substitute_decision"),
    path("approvals/", ApprovalsQueueView.as_view(), name="approvals_queue"),
    path("approvals/<uuid:pk>/decision/", ApproverDecisionView.as_view(), name="approver_decision"),
    path("leaves/<uuid:pk>/withdraw/", LeaveWithdrawView.as_view(), name="leave_withdraw"),
]
