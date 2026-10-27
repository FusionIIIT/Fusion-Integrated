"""HTTP routes for Employee Leave Management."""
from django.urls import path

from modules.elm.api.views import (
    LeaveRequestDecisionView, LeaveRequestListCreateView, LeaveRequestWithdrawView,
    MyLeaveBalanceView, SubstituteConsentView, LeaveCancellationDecisionView, LeaveCancellationRequestView, LeaveRequestReviewListView,
)

app_name = "elm"

urlpatterns = [
    path("requests", LeaveRequestListCreateView.as_view(), name="leave-requests"),
    path("balances", MyLeaveBalanceView.as_view(), name="my-leave-balances"),
    path("requests/<int:request_id>/withdraw", LeaveRequestWithdrawView.as_view(), name="withdraw-leave-request"),
    path("requests/<int:request_id>/substitute-response", SubstituteConsentView.as_view(), name="substitute-consent"),
    path("requests/<int:request_id>/decision", LeaveRequestDecisionView.as_view(), name="leave-request-decision"),
    path("requests/review", LeaveRequestReviewListView.as_view(), name="leave-request-review-list"),
    path("requests/<int:request_id>/cancellation", LeaveCancellationRequestView.as_view(), name="leave-cancellation-request"),
    path("cancellations/<int:cancellation_id>/decision", LeaveCancellationDecisionView.as_view(), name="leave-cancellation-decision"),
]
