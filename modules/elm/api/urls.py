from django.urls import path
from modules.elm.api.views import (
    LeaveRequestListView, LeaveWithdrawView, LeaveCancellationRequestView,
    SubstituteQueueView, SubstituteConsentView,
    UnitHeadQueueView, UnitHeadReviewView,
    HigherSanctionQueueView, HigherSanctionDecisionView,
    CancellationReviewView, DutyResumptionView, DutyResumptionReviewView,
    LeaveBalanceListView, HolidayCalendarListView
)

urlpatterns = [
    path("requests", LeaveRequestListView.as_view(), name="elm-requests"),
    path("requests/<int:pk>/withdraw", LeaveWithdrawView.as_view(), name="elm-withdraw"),
    path("requests/<int:pk>/cancel", LeaveCancellationRequestView.as_view(), name="elm-cancel-request"),
    path("requests/substitute-queue", SubstituteQueueView.as_view(), name="elm-substitute-queue"),
    path("requests/<int:pk>/substitute-consent", SubstituteConsentView.as_view(), name="elm-substitute-consent"),
    path("requests/unit-head-queue", UnitHeadQueueView.as_view(), name="elm-unit-head-queue"),
    path("requests/<int:pk>/unit-head-review", UnitHeadReviewView.as_view(), name="elm-unit-head-review"),
    path("requests/sanction-queue", HigherSanctionQueueView.as_view(), name="elm-sanction-queue"),
    path("requests/<int:pk>/sanction", HigherSanctionDecisionView.as_view(), name="elm-sanction-decision"),
    path("requests/<int:pk>/cancellation-review", CancellationReviewView.as_view(), name="elm-cancellation-review"),
    path("requests/<int:pk>/resume", DutyResumptionView.as_view(), name="elm-resumption"),
    path("resumptions/<int:pk>/review", DutyResumptionReviewView.as_view(), name="elm-resumption-review"),
    path("balances", LeaveBalanceListView.as_view(), name="elm-balances"),
    path("calendar/holidays", HolidayCalendarListView.as_view(), name="elm-holidays")
]
