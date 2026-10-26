"""URL routes for the Leave module."""

from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    # Applications
    path("applications", v.LeaveApplicationListCreateView.as_view(), name="leave-applications"),
    path(
        "applications/<int:pk>",
        v.LeaveApplicationDetailView.as_view(),
        name="leave-application-detail",
    ),
    path(
        "applications/<int:pk>/withdraw",
        v.LeaveApplicationWithdrawView.as_view(),
        name="leave-application-withdraw",
    ),
    path(
        "applications/<int:pk>/cancel",
        v.LeaveApplicationCancelView.as_view(),
        name="leave-application-cancel",
    ),
    path(
        "applications/<int:pk>/cancellation-review",
        v.LeaveApplicationCancellationReviewView.as_view(),
        name="leave-application-cancellation-review",
    ),
    path(
        "applications/<int:pk>/extend",
        v.LeaveApplicationExtendView.as_view(),
        name="leave-application-extend",
    ),
    path(
        "applications/<int:pk>/resumption",
        v.LeaveApplicationResumptionView.as_view(),
        name="leave-application-resumption",
    ),
    path(
        "applications/<int:pk>/resumption-review",
        v.LeaveApplicationResumptionReviewView.as_view(),
        name="leave-application-resumption-review",
    ),
    # Substitute flow
    path(
        "substitute/pending", v.SubstitutePendingListView.as_view(), name="leave-substitute-pending"
    ),
    path(
        "substitute/<int:pk>/respond",
        v.SubstituteRespondView.as_view(),
        name="leave-substitute-respond",
    ),
    path(
        "substitute/<int:pk>/replace",
        v.SubstituteReplaceView.as_view(),
        name="leave-substitute-replace",
    ),
    # Approval workflows
    path("approvals/pending", v.ApprovalsPendingListView.as_view(), name="leave-approvals-pending"),
    path(
        "approvals/<int:pk>/unit-head",
        v.UnitHeadReviewView.as_view(),
        name="leave-unit-head-review",
    ),
    path(
        "approvals/<int:pk>/establishment",
        v.EstablishmentRouteView.as_view(),
        name="leave-establishment-route",
    ),
    path(
        "approvals/<int:pk>/sanction",
        v.SanctionDecisionView.as_view(),
        name="leave-sanction-decision",
    ),
    # Balances
    path("balances", v.LeaveBalanceListView.as_view(), name="leave-balances"),
    path("balances/adjust", v.LeaveBalanceAdjustView.as_view(), name="leave-balance-adjust"),
    # Calendar
    path("calendar/holidays", v.HolidayCalendarListView.as_view(), name="leave-calendar-holidays"),
    path("calendar/vacations", v.VacationPeriodListView.as_view(), name="leave-calendar-vacations"),
    # Admin & event triggers
    path("offline/record", v.OfflineLeaveCreateView.as_view(), name="leave-offline-record"),
    path("admin/yearend", v.YearEndProcessingView.as_view(), name="leave-admin-yearend"),
    path("admin/sla", v.SLAProcessingView.as_view(), name="leave-admin-sla"),
]
