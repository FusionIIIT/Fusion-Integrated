"""URL routing for Employee Leave Management API."""
from django.urls import path

from modules.elm.api import views

urlpatterns = [
    path("types", views.LeaveTypeListView.as_view(), name="elm-leave-types"),
    path("balances", views.LeaveBalanceListView.as_view(), name="elm-balances"),
    path(
        "applications",
        views.LeaveApplicationListCreateView.as_view(),
        name="elm-applications",
    ),
    path(
        "applications/<int:pk>/withdraw",
        views.LeaveWithdrawView.as_view(),
        name="elm-application-withdraw",
    ),
    path(
        "applications/<int:pk>/substitute",
        views.SubstituteResponseView.as_view(),
        name="elm-substitute-respond",
    ),
    path(
        "applications/<int:pk>/replace-substitute",
        views.SubstituteReplacementView.as_view(),
        name="elm-substitute-replace",
    ),
    path(
        "applications/<int:pk>/cancel",
        views.LeaveCancellationRequestView.as_view(),
        name="elm-application-cancel",
    ),
    path(
        "applications/<int:pk>/cancel/decide",
        views.LeaveCancellationDecisionView.as_view(),
        name="elm-cancellation-decide",
    ),
    path(
        "applications/<int:pk>/extend",
        views.LeaveExtensionCreateView.as_view(),
        name="elm-application-extend",
    ),
    path(
        "applications/<int:pk>/resumption",
        views.DutyResumptionSubmitView.as_view(),
        name="elm-duty-resumption-submit",
    ),
    path(
        "applications/<int:pk>/resumption/decide",
        views.DutyResumptionReviewView.as_view(),
        name="elm-duty-resumption-decide",
    ),
    path(
        "approvals",
        views.LeaveApprovalQueueView.as_view(),
        name="elm-approvals",
    ),
    path(
        "approvals/<int:pk>/decide",
        views.LeaveApprovalDecisionView.as_view(),
        name="elm-approval-decide",
    ),
    path(
        "offline-leaves",
        views.OfflineLeaveCreateListView.as_view(),
        name="elm-offline-leaves",
    ),
    path(
        "rollover",
        views.LeaveRolloverExecuteView.as_view(),
        name="elm-rollover-execute",
    ),
    path(
        "calendar",
        views.HolidayCalendarListView.as_view(),
        name="elm-holiday-calendar",
    ),
]
