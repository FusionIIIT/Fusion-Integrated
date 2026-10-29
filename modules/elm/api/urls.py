"""URL configuration for ELM API endpoints."""
from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    # Leaves application & listing
    path("leaves", v.LeaveRequestListView.as_view(), name="elm-leaves"),
    path("leaves/<int:pk>", v.LeaveRequestDetailView.as_view(), name="elm-leave-detail"),
    path("leaves/<int:pk>/history", v.LeaveRequestHistoryView.as_view(), name="elm-leave-history"),

    # Substitute flow
    path("substitute/requests", v.SubstituteRequestsListView.as_view(), name="elm-substitute-requests"),
    path("leaves/<int:pk>/substitute", v.SubstituteResponseView.as_view(), name="elm-substitute-respond"),

    # Approval & sanction flow
    path("approvals/pending", v.PendingApprovalsListView.as_view(), name="elm-pending-approvals"),
    path("leaves/<int:pk>/review", v.UnitHeadReviewView.as_view(), name="elm-unit-head-review"),
    path("leaves/<int:pk>/sanction", v.SanctionDecisionView.as_view(), name="elm-sanction-decision"),

    # Cancellation flow (CW-EL-02)
    path("leaves/<int:pk>/cancel", v.CancelRequestView.as_view(), name="elm-cancel-request"),
    path("leaves/<int:pk>/cancel/decide", v.CancelDecisionView.as_view(), name="elm-cancel-decide"),

    # Extension flow (CW-EL-03)
    path("leaves/<int:pk>/extend", v.ExtensionRequestView.as_view(), name="elm-extend-request"),
    path("leaves/<int:pk>/extend/decide", v.ExtensionDecisionView.as_view(), name="elm-extend-decide"),

    # Resumption flow (CW-EL-04)
    path("leaves/<int:pk>/resume", v.ResumptionRequestView.as_view(), name="elm-resume-request"),
    path("leaves/<int:pk>/resume/review", v.ResumptionReviewView.as_view(), name="elm-resume-review"),

    # Balances
    path("balances/my", v.MyBalancesView.as_view(), name="elm-my-balances"),
    path("balances/<int:user_id>", v.UserBalancesView.as_view(), name="elm-user-balances"),

    # Holiday calendar
    path("calendar", v.HolidayCalendarListView.as_view(), name="elm-calendar"),

    # Admin actions
    path("offline", v.OfflineLeaveView.as_view(), name="elm-offline-record"),
]
