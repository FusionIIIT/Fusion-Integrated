from django.urls import path

from modules.elm.api.views import (
    LeaveApprovalDecisionView,
    LeaveBalanceListView,
    LeaveRequestListCreateView,
    LeaveRequestWithdrawView,
    RestrictedHolidayListView,
)

urlpatterns = [
    path("requests", LeaveRequestListCreateView.as_view(), name="elm-requests"),
    path(
        "requests/<int:request_id>/decision",
        LeaveApprovalDecisionView.as_view(),
        name="elm-request-decision",
    ),
    path(
        "requests/<int:request_id>/withdraw",
        LeaveRequestWithdrawView.as_view(),
        name="elm-request-withdraw",
    ),
    path("balances", LeaveBalanceListView.as_view(), name="elm-balances"),
    path(
        "restricted-holidays",
        RestrictedHolidayListView.as_view(),
        name="elm-restricted-holidays",
    ),
]
