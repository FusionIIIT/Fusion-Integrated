from django.urls import path

from modules.iaa.api import views

app_name = "iaa"

urlpatterns = [
    path("expenses", views.ExpenseListView.as_view(), name="expenses"),
    path("expenses/<int:pk>", views.ExpenseDetailView.as_view(), name="expense"),
    path("expenses/<int:pk>/submit", views.ExpenseSubmitView.as_view(), name="expense-submit"),
    path(
        "expenses/<int:pk>/finance-review",
        views.ExpenseFinanceReviewView.as_view(),
        name="expense-review",
    ),
    path(
        "financial-records/<str:record_type>/<int:pk>/record",
        views.FinancialRecordView.as_view(),
        name="record-financial-item",
    ),
    path(
        "expenses/<int:pk>/clarification-response",
        views.ClarificationResponseView.as_view(),
        {"record_type": "expense"},
        name="expense-clarification",
    ),
    path("ta-claims", views.TravelClaimListView.as_view(), name="ta-claims"),
    path("ta-claims/<int:pk>", views.TravelClaimDetailView.as_view(), name="ta-claim"),
    path(
        "ta-claims/<int:pk>/finance-review",
        views.TravelClaimFinanceReviewView.as_view(),
        name="ta-review",
    ),
    path("documents", views.SupportingDocumentView.as_view(), name="documents"),
    path(
        "ta-claims/<int:pk>/clarification-response",
        views.ClarificationResponseView.as_view(),
        {"record_type": "ta"},
        name="ta-clarification",
    ),
    path("approvals", views.ApprovalQueueView.as_view(), name="approvals"),
    path(
        "approvals/<int:pk>/decision",
        views.ApprovalDecisionView.as_view(),
        name="approval-decision",
    ),
    path("anomalies", views.AnomalyListCreateView.as_view(), name="anomalies"),
    path(
        "anomalies/<int:pk>/resolution",
        views.AnomalyResolveView.as_view(),
        name="anomaly-resolution",
    ),
    path("observations", views.ObservationListView.as_view(), name="observations"),
    path("observations/raise", views.ObservationCreateView.as_view(), name="observation-raise"),
    path(
        "observations/<int:pk>/responses",
        views.ObservationResponseView.as_view(),
        name="observation-response",
    ),
    path(
        "observations/<int:pk>/responses/<int:response_id>/review",
        views.ObservationReviewView.as_view(),
        name="observation-review",
    ),
    path("audit/records", views.AuditRecordsView.as_view(), name="audit-records"),
    path(
        "<str:record_type>/<int:pk>/history",
        views.RecordHistoryView.as_view(),
        name="record-history",
    ),
    path("notifications", views.NotificationListView.as_view(), name="notifications"),
    path(
        "finance/recovery-issues",
        views.ProcessingIssuesView.as_view(),
        name="finance-recovery-issues",
    ),
    path("reports/summary", views.ReportSummaryView.as_view(), name="report-summary"),
    path("reports/export", views.ReportExportView.as_view(), name="report-export"),
    path("configuration/policy", views.IaaPolicyView.as_view(), name="policy"),
    path(
        "configuration/approval-routes",
        views.ApprovalRouteListCreateView.as_view(),
        name="approval-routes",
    ),
    path(
        "configuration/approval-routes/<int:pk>",
        views.ApprovalRouteDetailView.as_view(),
        name="approval-route",
    ),
    path("configuration/budgets", views.BudgetAllocationListCreateView.as_view(), name="budgets"),
    path(
        "configuration/budgets/<int:pk>", views.BudgetAllocationDetailView.as_view(), name="budget"
    ),
]
