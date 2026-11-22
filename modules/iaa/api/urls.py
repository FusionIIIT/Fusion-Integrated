from django.urls import path

from modules.iaa.api import views

app_name = "iaa"

urlpatterns = [
    # Requests (Expense / Voucher)
    path("requests/", views.RequestListCreateView.as_view(), name="request-list-create"),
    path("requests/<int:pk>/", views.RequestDetailView.as_view(), name="request-detail"),
    path("requests/<int:pk>/submit/", views.RequestSubmitView.as_view(), name="request-submit"),
    path(
        "requests/<int:pk>/validate/", views.RequestValidateView.as_view(), name="request-validate"
    ),
    path("requests/<int:pk>/query/", views.RequestQueryView.as_view(), name="request-query"),
    path(
        "requests/queries/<int:query_id>/respond/",
        views.RequestRespondQueryView.as_view(),
        name="request-respond-query",
    ),
    path("requests/<int:pk>/decide/", views.RequestDecideView.as_view(), name="request-decide"),
    path("requests/<int:pk>/record/", views.RequestRecordView.as_view(), name="request-record"),
    # Travel Claims
    path("travel/", views.TravelClaimListCreateView.as_view(), name="travel-list-create"),
    path("travel/<int:pk>/", views.TravelClaimDetailView.as_view(), name="travel-detail"),
    path("travel/<int:pk>/verify/", views.TravelClaimVerifyView.as_view(), name="travel-verify"),
    path("travel/<int:pk>/decide/", views.TravelClaimDecideView.as_view(), name="travel-decide"),
    path("travel/<int:pk>/record/", views.TravelClaimRecordView.as_view(), name="travel-record"),
    # Anomalies
    path("anomalies/", views.AnomalyListCreateView.as_view(), name="anomaly-list-create"),
    path("anomalies/<int:pk>/resolve/", views.AnomalyResolveView.as_view(), name="anomaly-resolve"),
    # Audit
    path("audit/", views.AuditObservationListCreateView.as_view(), name="audit-list-create"),
    path(
        "audit/<int:pk>/respond/", views.AuditObservationRespondView.as_view(), name="audit-respond"
    ),
    path("audit/<int:pk>/close/", views.AuditObservationCloseView.as_view(), name="audit-close"),
    # Reports
    path("reports/", views.ReportSummaryView.as_view(), name="report-summary"),
    path("reports/export/", views.ReportExportView.as_view(), name="report-export"),
    # Configuration
    path("config/", views.ConfigurationView.as_view(), name="configuration"),
    path("config/budgets/", views.DepartmentBudgetView.as_view(), name="department-budgets"),
]
