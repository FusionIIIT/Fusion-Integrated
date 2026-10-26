from django.urls import path
from modules.elm.api.views import (
    CancelLeaveView,
    DecisionView,
    HolidayCalendarView,
    LeaveBalanceView,
    LeaveRequestDetailView,
    LeaveRequestListView,
    SubstituteRequestsView,
    SubstituteRespondView,
    WithdrawLeaveView,
)

app_name = "elm"

urlpatterns = [
    path("balances/", LeaveBalanceView.as_view(), name="leave-balances"),
    path("requests/", LeaveRequestListView.as_view(), name="leave-requests"),
    path("requests/<int:pk>/", LeaveRequestDetailView.as_view(), name="leave-request-detail"),
    path("requests/<int:pk>/decision/", DecisionView.as_view(), name="leave-decision"),
    path("requests/<int:pk>/withdraw/", WithdrawLeaveView.as_view(), name="leave-withdraw"),
    path("requests/<int:pk>/cancel/", CancelLeaveView.as_view(), name="leave-cancel"),
    path("substitute/requests/", SubstituteRequestsView.as_view(), name="substitute-requests"),
    path("substitute/requests/<int:pk>/respond/", SubstituteRespondView.as_view(), name="substitute-respond"),
    path("holidays/", HolidayCalendarView.as_view(), name="holiday-calendar"),
]
