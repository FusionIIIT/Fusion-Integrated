from django.urls import path
from modules.elm.api.views import (
    HolidayCalendarListView,
    LeaveBalanceListView,
    LeaveCancellationView,
    LeaveDecisionView,
    LeaveDetailView,
    LeaveExtensionView,
    LeaveQueueView,
    LeaveRequestListView,
    LeaveResumptionView,
    LeaveWithdrawalView,
    OfflineLeaveEntryView,
    SubstituteQueueView,
    SubstituteResponseView,
    YearEndProcessingView,
)

urlpatterns = [
    path("requests", LeaveRequestListView.as_view(), name="elm-requests"),
    path("requests/<int:pk>", LeaveDetailView.as_view(), name="elm-detail"),
    path("requests/queue", LeaveQueueView.as_view(), name="elm-queue"),
    path("requests/<int:pk>/decision", LeaveDecisionView.as_view(), name="elm-decision"),
    path("requests/<int:pk>/withdraw", LeaveWithdrawalView.as_view(), name="elm-withdraw"),
    path("requests/<int:pk>/cancel", LeaveCancellationView.as_view(), name="elm-cancel"),
    path("requests/<int:pk>/extend", LeaveExtensionView.as_view(), name="elm-extend"),
    path("requests/<int:pk>/resume", LeaveResumptionView.as_view(), name="elm-resume"),
    path("substitute/queue", SubstituteQueueView.as_view(), name="elm-substitute-queue"),
    path("substitute/<int:pk>/respond", SubstituteResponseView.as_view(), name="elm-substitute-respond"),
    path("balances", LeaveBalanceListView.as_view(), name="elm-balances"),
    path("holidays", HolidayCalendarListView.as_view(), name="elm-holidays"),
    path("admin/yearend", YearEndProcessingView.as_view(), name="elm-yearend"),
    path("admin/offline-entry", OfflineLeaveEntryView.as_view(), name="elm-offline-entry"),
]
