from django.urls import path

from modules.leave_elm.api.views import (
    BalancesView,
    CalendarView,
    MyRequestsView,
    RequestActionView,
    RequestDetailView,
)

urlpatterns = [
    path("requests", MyRequestsView.as_view(), name="leave-elm-requests"),
    path("requests/<int:pk>", RequestDetailView.as_view(), name="leave-elm-request"),
    path("requests/<int:pk>/decision", RequestActionView.as_view(), name="leave-elm-decision"),
    path("balances", BalancesView.as_view(), name="leave-elm-balances"),
    path("calendar", CalendarView.as_view(), name="leave-elm-calendar"),
]
