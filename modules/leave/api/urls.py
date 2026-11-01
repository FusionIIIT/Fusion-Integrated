from django.urls import path

from modules.leave.api import views as v

urlpatterns = [
    # balances, history and the printable application
    path("balances", v.MyBalancesView.as_view(), name="leave-balances"),
    path("requests/<int:pk>/export", v.ApplicationExportView.as_view(),
         name="leave-application-export"),

    # requests
    path("requests", v.RequestListCreateView.as_view(), name="leave-requests"),
    path("requests/<int:pk>", v.RequestDetailView.as_view(), name="leave-request"),
    path("requests/<int:pk>/history", v.RequestHistoryView.as_view(),
         name="leave-request-history"),
    path("requests/<int:pk>/withdraw", v.WithdrawView.as_view(),
         name="leave-request-withdraw"),
    path("requests/<int:pk>/decision", v.DecisionView.as_view(),
         name="leave-request-decision"),
    path("requests/<int:pk>/cancellation", v.CancellationRequestView.as_view(),
         name="leave-cancellation"),
    path("requests/<int:pk>/extension", v.ExtensionRequestView.as_view(),
         name="leave-extension"),
    path("requests/<int:pk>/substitute", v.NominateReplacementView.as_view(),
         name="leave-substitute-replacement"),
    path("requests/<int:pk>/resumption", v.ResumptionSubmitView.as_view(),
         name="leave-resumption"),
    path("requests/<int:pk>/resumption/review", v.ResumptionReviewView.as_view(),
         name="leave-resumption-review"),

    # the office queue
    path("queue", v.QueueView.as_view(), name="leave-queue"),
    path("queue/count", v.MyQueueCountView.as_view(), name="leave-queue-count"),

    # responsibility requests
    path("substitute-requests", v.SubstituteRequestListView.as_view(),
         name="leave-substitute-requests"),
    path("substitute-requests/<int:request_id>/respond",
         v.SubstituteResponseView.as_view(),
         name="leave-substitute-response"),

    # configuration
    path("calendar", v.EffectiveCalendarView.as_view(), name="leave-calendar"),
    path("calendar/publish", v.PublishCalendarView.as_view(),
         name="leave-calendar-publish"),
    path("policy", v.PolicyView.as_view(), name="leave-policy"),
    path("policy/hierarchy", v.HierarchyView.as_view(), name="leave-hierarchy"),
    path("policy/vacation-periods", v.VacationPeriodView.as_view(),
         name="leave-vacation-periods"),
    path("sla-thresholds", v.ThresholdView.as_view(), name="leave-sla-thresholds"),

    # records
    path("records", v.RecordListView.as_view(), name="leave-records"),
    path("records/offline", v.OfflineRecordView.as_view(),
         name="leave-record-offline"),
    path("records/adjustment", v.BalanceAdjustmentView.as_view(),
         name="leave-record-adjustment"),
]
