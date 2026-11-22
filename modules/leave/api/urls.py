"""Leave routes, mounted at /api/v1/leave/.

A viewset for the request resource, because its extra actions are part of the
same aggregate; plain views elsewhere, where a list path with no trailing slash
is the whole contract.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modules.leave.api import views as v

router = DefaultRouter()
router.register("requests", v.LeaveRequestViewSet, basename="leave-request")

urlpatterns = [
    path("", include(router.urls)),

    # the employee's own applications
    path("my-requests", v.MyRequestsView.as_view(), name="leave-my-requests"),
    path("my-requests/counts", v.RequestCountsView.as_view(),
         name="leave-request-counts"),
    path("drafts", v.DraftsView.as_view(), name="leave-drafts"),

    # substitutions
    path("substitutions", v.SubstitutionQueueView.as_view(),
         name="leave-substitutions"),
    path("substitutions/<int:pk>/respond", v.NominationResponseView.as_view(),
         name="leave-substitution-respond"),

    # approvals
    path("approvals", v.ApprovalsView.as_view(), name="leave-approvals"),
    path("approvals/<int:pk>/decision", v.TaskDecisionView.as_view(),
         name="leave-task-decision"),

    # lifecycle
    path("requests/<int:pk>/cancellation", v.CancellationView.as_view(),
         name="leave-cancellation"),
    path("requests/<int:pk>/extension", v.ExtensionView.as_view(),
         name="leave-extension"),
    path("requests/<int:pk>/resumption", v.ResumptionView.as_view(),
         name="leave-resumption"),
    path("lifecycle", v.LifecycleListView.as_view(), name="leave-lifecycle"),

    # accounts
    path("balances", v.BalancesView.as_view(), name="leave-balances"),
    path("balances/adjust", v.BalanceAdjustmentView.as_view(),
         name="leave-balance-adjust"),
    path("ledger", v.LedgerView.as_view(), name="leave-ledger"),
    path("ledger/reconcile", v.ReconciliationView.as_view(),
         name="leave-ledger-reconcile"),

    # administration
    path("admin/config", v.LeaveAdminConfigView.as_view(), name="leave-admin-config"),
    path("admin/policy", v.PolicyView.as_view(), name="leave-admin-policy"),
    path("admin/calendar/holidays", v.HolidayCalendarView.as_view(),
         name="leave-admin-holidays"),
    path("admin/calendar/holidays/<int:pk>/publish",
         v.HolidayCalendarPublishView.as_view(),
         name="leave-admin-calendar-publish"),
    path("admin/calendar/vacation-periods", v.VacationPeriodView.as_view(),
         name="leave-admin-vacation-periods"),
    path("admin/routes", v.RouteView.as_view(), name="leave-admin-routes"),
    path("admin/units", v.OrganizationalUnitView.as_view(),
         name="leave-admin-units"),
    path("admin/thresholds", v.ThresholdView.as_view(),
         name="leave-admin-thresholds"),
    path("admin/offline-leave", v.OfflineLeaveView.as_view(),
         name="leave-admin-offline-leave"),

    # exceptions and the year-end run
    path("exceptions/overview", v.ExceptionOverviewView.as_view(),
         name="leave-exceptions-overview"),
    path("exceptions/overdue-out-of-office", v.OverdueOutOfOfficeView.as_view(),
         name="leave-overdue-out-of-office"),
    path("admin/year-end/run", v.YearEndRunView.as_view(),
         name="leave-year-end-run"),
    path("admin/year-end/status", v.YearEndStatusView.as_view(),
         name="leave-year-end-status"),
]