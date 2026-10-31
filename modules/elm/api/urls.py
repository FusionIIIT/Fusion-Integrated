from django.urls import path

from modules.elm.api import views as v

urlpatterns = [
    # Leave categories
    path("categories", v.LeaveCategoryViewSet.as_view({"get": "list"}), name="elm-categories"),
    # Leave application
    path("apply", v.LeaveApplicationCreateView.as_view(), name="elm-apply"),
    path("my-applications", v.EmployeeLeaveApplicationsView.as_view(), name="elm-my-applications"),
    path(
        "applications/<int:pk>",
        v.LeaveApplicationDetailView.as_view(),
        name="elm-application-detail",
    ),
    # Leave balances and history
    path("balances", v.EmployeeLeaveBalancesView.as_view(), name="elm-balances"),
    path("history", v.EmployeeLeaveHistoryView.as_view(), name="elm-history"),
    # Approval workflow and configurable routing
    path("workflow/queue", v.LeaveApprovalQueueView.as_view(), name="elm-approval-queue"),
    path(
        "workflow/decision/<int:pk>",
        v.LeaveApprovalDecisionView.as_view(),
        name="elm-approval-decision",
    ),
    path(
        "workflow/routing",
        v.ApprovalRoutingConfigurationView.as_view(),
        name="elm-approval-routing",
    ),
    # Withdrawal
    path("withdraw/<int:pk>", v.LeaveApplicationWithdrawView.as_view(), name="elm-withdraw"),
    # Cancellation
    path(
        "cancel-request/<int:pk>",
        v.LeaveCancellationRequestView.as_view(),
        name="elm-cancel-request",
    ),
    # Extension
    path("extension-request", v.LeaveExtensionRequestView.as_view(), name="elm-extension-request"),
    # Resumption
    path("resumption-submit", v.ResumptionSubmitView.as_view(), name="elm-resumption-submit"),
    path(
        "resumption-review/<int:pk>", v.ResumptionReviewView.as_view(), name="elm-resumption-review"
    ),
    # Printable export
    path(
        "application/<int:pk>/print",
        v.LeaveApplicationPrintView.as_view(),
        name="elm-application-print",
    ),
    # Policy and configuration
    path("policy", v.LeavePolicyConfigView.as_view(), name="elm-policy-config"),
    path("holiday-calendar", v.HolidayCalendarView.as_view(), name="elm-holiday-calendar"),
    # Offline synchronization
    path("offline-sync", v.OfflineLeaveSyncView.as_view(), name="elm-offline-sync"),
    # Record maintenance
    path("records", v.AuthorizedLeaveRecordsView.as_view(), name="elm-records"),
    # SLA thresholds
    path("sla/thresholds", v.SLATrendsConfigView.as_view(), name="elm-sla-thresholds"),
    # Substitute replacement
    path(
        "substitute/replacement",
        v.SubstituteReplacementView.as_view(),
        name="elm-substitute-replacement",
    ),
    # Year-end processing
    path("year-end", v.YearEndLeaveProcessingView.as_view(), name="elm-year-end"),
    # SLA threshold event processing
    path("sla/process", v.SLAThresholdEventView.as_view(), name="elm-sla-process"),
]
