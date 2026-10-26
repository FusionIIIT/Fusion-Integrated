"""URL configuration for ELM module."""
from django.urls import path

from modules.elm.views import (
    ApprovalQueueView,
    CancelLeaveView,
    HolidayCalendarView,
    LeaveBalancesView,
    MyLeavesView,
    RespondSubstituteView,
    ReviewLeaveView,
    SubstituteRequestsView,
)

urlpatterns = [
    path("balances/", LeaveBalancesView.as_view(), name="elm-balances"),
    path("applications/", MyLeavesView.as_view(), name="elm-applications"),
    path("applications/<int:pk>/cancel/", CancelLeaveView.as_view(), name="elm-cancel-application"),
    path("applications/<int:pk>/review/", ReviewLeaveView.as_view(), name="elm-review-application"),
    path("approvals/", ApprovalQueueView.as_view(), name="elm-approval-queue"),
    path("holidays/", HolidayCalendarView.as_view(), name="elm-holidays"),
    path("substitutes/", SubstituteRequestsView.as_view(), name="elm-substitutes"),
    path(
        "substitutes/<int:pk>/respond/",
        RespondSubstituteView.as_view(),
        name="elm-respond-substitute",
    ),
]
