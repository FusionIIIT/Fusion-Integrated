from django.urls import path

from .views import (
    ApprovalsQueueView,
    ApproverDecisionView,
    AuthorityApprovalsQueueView,
    AuthorityDecisionView,
    LeaveBalanceAdjustmentView,
    LeaveBalanceView,
    LeaveListCreateView,
    LeaveWithdrawView,
    ReplacementSubstituteView,
    SubstituteDecisionView,
    SubstituteQueueView,
)

urlpatterns = [
    path("leaves/", LeaveListCreateView.as_view(), name="leave_list_create"),
    path("balances/", LeaveBalanceView.as_view(), name="leave_balances"),
    path(
        "balances/admin/adjust/",
        LeaveBalanceAdjustmentView.as_view(),
        name="leave_balance_adjustment",
    ),
    path("substitute-queue/", SubstituteQueueView.as_view(), name="substitute_queue"),
    path(
        "substitute-queue/<uuid:pk>/decision/",
        SubstituteDecisionView.as_view(),
        name="substitute_decision",
    ),
    path(
        "leaves/<uuid:pk>/replacement-substitute/",
        ReplacementSubstituteView.as_view(),
        name="replacement_substitute",
    ),
    path("approvals/", ApprovalsQueueView.as_view(), name="approvals_queue"),
    path("approvals/<uuid:pk>/decision/", ApproverDecisionView.as_view(), name="approver_decision"),
    path(
        "authority-approvals/",
        AuthorityApprovalsQueueView.as_view(),
        name="authority_approvals_queue",
    ),
    path(
        "authority-approvals/<uuid:pk>/decision/",
        AuthorityDecisionView.as_view(),
        name="authority_decision",
    ),
    path("leaves/<uuid:pk>/withdraw/", LeaveWithdrawView.as_view(), name="leave_withdraw"),
]
