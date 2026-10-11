"""Every route the leave module exposes, under /api/v1/leave/.

The module is mounted by one line in config/urls.py; removing the directory
plus that line removes the API entirely, which is what "independent module"
means here.
"""
from django.urls import path

from modules.leave.api import admin as a
from modules.leave.api import approvals as ap
from modules.leave.api import requests as r

urlpatterns = [
    # -- employee self-service -------------------------------------------------
    path("requests/validate", r.LeaveValidateView.as_view(),
         name="leave-validate"),
    path("requests", r.LeaveApplyView.as_view(), name="leave-apply"),
    path("requests/mine", r.MyLeaveRequestsView.as_view(), name="leave-mine"),
    path("requests/<int:pk>", r.LeaveRequestDetailView.as_view(),
         name="leave-request"),
    path("requests/<int:pk>/withdraw", r.LeaveWithdrawView.as_view(),
         name="leave-withdraw"),
    path("requests/<int:pk>/cancellation", r.LeaveCancellationView.as_view(),
         name="leave-cancellation"),
    path("requests/<int:pk>/extension", r.LeaveExtensionView.as_view(),
         name="leave-extension"),
    path("requests/<int:pk>/resumption", r.LeaveResumptionView.as_view(),
         name="leave-resumption"),
    path("requests/<int:pk>/print", r.LeaveApplicationPrintView.as_view(),
         name="leave-print"),
    path("requests/<int:pk>/substitute", r.NominateReplacementView.as_view(),
         name="leave-nominate-replacement"),
    path("summary", r.MyLeaveSummaryView.as_view(), name="leave-summary"),
    path("balances", r.MyLeaveBalancesView.as_view(), name="leave-balances"),
    path("ledger", r.MyLeaveLedgerView.as_view(), name="leave-ledger"),
    path("substitutions", r.MySubstitutionsView.as_view(),
         name="leave-substitutions"),
    path("substitutions/<int:pk>/respond", r.SubstituteRespondView.as_view(),
         name="leave-substitute-respond"),

    # -- approval worklist -----------------------------------------------------
    path("tasks", ap.TaskListView.as_view(), name="leave-tasks"),
    path("tasks/<int:pk>/decision", ap.TaskDecisionView.as_view(),
         name="leave-task-decision"),
    path("resumptions", ap.ResumptionQueueView.as_view(),
         name="leave-resumptions"),
    path("resumptions/<int:pk>", ap.ResumptionDetailView.as_view(),
         name="leave-resumption-detail"),
    path("resumptions/<int:pk>/review", ap.ResumptionReviewView.as_view(),
         name="leave-resumption-review"),

    # -- records (view / balance.update) --------------------------------------
    path("records", a.LeaveRecordsView.as_view(), name="leave-records"),
    path("records/offline", a.OfflineRecordView.as_view(),
         name="leave-offline-record"),
    path("records/<int:pk>/adjustments", a.RecordAdjustmentsView.as_view(),
         name="leave-record-adjustments"),
    path("records/<int:pk>/correct", a.RecordCorrectionView.as_view(),
         name="leave-record-correct"),
    path("accounts/<int:user_id>", a.LeaveBalanceDetailView.as_view(),
         name="leave-account"),
    path("accounts/<int:user_id>/ledger", a.LeaveLedgerView.as_view(),
         name="leave-account-ledger"),
    path("accounts/adjust", a.BalanceAdjustmentView.as_view(),
         name="leave-balance-adjust"),

    # -- configuration (type.manage) ------------------------------------------
    path("config/policy", a.PolicyView.as_view(), name="leave-config-policy"),
    path("config/hierarchy", a.HierarchyView.as_view(),
         name="leave-config-hierarchy"),
    path("config/calendar", a.CalendarView.as_view(),
         name="leave-config-calendar"),
    path("config/calendar/<int:pk>/publish", a.CalendarPublishView.as_view(),
         name="leave-config-calendar-publish"),
    path("config/sla", a.SlaThresholdView.as_view(), name="leave-config-sla"),
]
