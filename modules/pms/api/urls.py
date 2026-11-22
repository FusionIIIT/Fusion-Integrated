from django.urls import path

from modules.pms.api.views import (
    AppealView,
    ApplicationDetailView,
    ApplicationListCreateView,
    ApplicationSubmitView,
    ApplicationWithdrawView,
    AssignAttorneyView,
    AssignDirectorView,
    BudgetReviewView,
    FinancialTransactionListView,
    OfficeActionListCreateView,
    RecordFilingView,
    RecordGrantView,
    RespondAttorneyView,
    ReviewSubmitView,
    SystemSummaryReportView,
)

app_name = "pms"

urlpatterns = [
    path("applications/", ApplicationListCreateView.as_view(), name="application-list-create"),
    path("applications/<int:pk>/", ApplicationDetailView.as_view(), name="application-detail"),
    path("applications/<int:pk>/submit/", ApplicationSubmitView.as_view(), name="application-submit"),
    path("applications/<int:pk>/withdraw/", ApplicationWithdrawView.as_view(), name="application-withdraw"),
    path("applications/<int:pk>/assign-director/", AssignDirectorView.as_view(), name="assign-director"),
    path("applications/<int:pk>/review/", ReviewSubmitView.as_view(), name="review-submit"),
    path("applications/<int:pk>/appeal/", AppealView.as_view(), name="application-appeal"),
    path("applications/<int:pk>/budget/", BudgetReviewView.as_view(), name="budget-review"),
    path("applications/<int:pk>/assign-attorney/", AssignAttorneyView.as_view(), name="assign-attorney"),
    path("applications/<int:pk>/respond-attorney/", RespondAttorneyView.as_view(), name="respond-attorney"),
    path("applications/<int:pk>/record-filing/", RecordFilingView.as_view(), name="record-filing"),
    path("applications/<int:pk>/record-grant/", RecordGrantView.as_view(), name="record-grant"),
    path("applications/<int:pk>/office-actions/", OfficeActionListCreateView.as_view(), name="office-actions"),
    path("applications/<int:pk>/transactions/", FinancialTransactionListView.as_view(), name="transactions"),
    path("reports/summary/", SystemSummaryReportView.as_view(), name="report-summary"),
]
