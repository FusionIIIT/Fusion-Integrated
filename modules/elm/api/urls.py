from django.urls import path
from modules.elm.api.views import LeaveBalanceListView, LeaveDecisionView, LeaveQueueView, LeaveRequestListView

urlpatterns = [
    path("requests", LeaveRequestListView.as_view(), name="elm-requests"),
    path("requests/queue", LeaveQueueView.as_view(), name="elm-queue"),
    path("requests/<int:pk>/decision", LeaveDecisionView.as_view(), name="elm-decision"),
    path("balances", LeaveBalanceListView.as_view(), name="elm-balances"),
]
