from django.urls import path

from modules.iaa.api import views

urlpatterns = [
    path("expenses", views.ExpenseRequestsView.as_view(), name="iaa-expenses"),
    path("expenses/<int:pk>/submit", views.ExpenseSubmitView.as_view(), name="iaa-expense-submit"),
    path("expenses/<int:pk>/finance-review", views.ExpenseFinanceReviewView.as_view(),
         name="iaa-expense-finance-review"),
    path("expenses/<int:pk>/respond-query", views.ExpenseQueryRespondView.as_view(),
         name="iaa-expense-respond-query"),
    path("expenses/<int:pk>/decide", views.ExpenseDecideView.as_view(), name="iaa-expense-decide"),
    path("expenses/<int:pk>/escalate", views.ExpenseEscalateView.as_view(),
         name="iaa-expense-escalate"),
    path("expenses/<int:pk>/record", views.ExpenseRecordView.as_view(), name="iaa-expense-record"),

    path("ta-claims", views.TAClaimsView.as_view(), name="iaa-ta-claims"),
    path("ta-claims/<int:pk>/verify", views.TAVerifyView.as_view(), name="iaa-ta-verify"),
    path("ta-claims/<int:pk>/decide", views.TADecideView.as_view(), name="iaa-ta-decide"),
    path("ta-claims/<int:pk>/record", views.TARecordView.as_view(), name="iaa-ta-record"),

    path("anomalies", views.AnomaliesView.as_view(), name="iaa-anomalies"),
    path("anomalies/<int:pk>/resolve", views.AnomalyResolveView.as_view(),
         name="iaa-anomaly-resolve"),

    path("audit-observations", views.AuditObservationsView.as_view(), name="iaa-audit-observations"),
    path("audit-observations/<int:pk>/respond", views.AuditRespondView.as_view(),
         name="iaa-audit-respond"),
    path("audit-observations/<int:pk>/review-close", views.AuditReviewCloseView.as_view(),
         name="iaa-audit-review-close"),
]
