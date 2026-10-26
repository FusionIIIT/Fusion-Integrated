from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    path("requests", v.MyLeaveRequestsView.as_view(), name="elm-my-requests"),
    path("balances", v.LeaveBalanceSummaryView.as_view(), name="elm-balances"),
    path("balances/history", v.LeaveBalanceHistoryView.as_view(), name="elm-balance-history"),
    path(
        "requests/submit",
        v.LeaveRequestSubmitView.as_view(),
        name="elm-request-submit",
    ),
    path(
        "requests/<int:request_id>/withdraw",
        v.LeaveRequestWithdrawView.as_view(),
        name="elm-request-withdraw",
    ),
    path(
        "requests/<int:request_id>/history",
        v.LeaveRequestHistoryView.as_view(),
        name="elm-request-history",
    ),
    path(
        "requests/<int:request_id>/substitute-response",
        v.LeaveSubstituteResponseView.as_view(),
        name="elm-substitute-response",
    ),
    path(
        "requests/<int:request_id>/substitute",
        v.LeaveSubstituteReplacementView.as_view(),
        name="elm-substitute-replacement",
    ),
    path("approvals", v.LeaveApprovalsView.as_view(), name="elm-approvals"),
    path("substitutions", v.LeaveSubstituteTasksView.as_view(), name="elm-substitutions"),
    path(
        "requests/<int:request_id>/decision",
        v.LeaveRequestDecisionView.as_view(),
        name="elm-request-decision",
    ),
]
