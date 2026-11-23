"""URL routing for patents module API."""
from django.urls import path

from modules.patents.api import views as v

urlpatterns = [
    # Applications CRUD
    path("applications", v.ApplicationListView.as_view(), name="patents-applications"),
    path(
        "applications/<int:pk>",
        v.ApplicationDetailView.as_view(),
        name="patents-application-detail",
    ),
    path(
        "applications/<int:pk>/withdraw",
        v.ApplicationWithdrawView.as_view(),
        name="patents-application-withdraw",
    ),
    path(
        "applications/<int:pk>/documents",
        v.ApplicationDocumentUploadView.as_view(),
        name="patents-application-documents",
    ),
    path(
        "applications/<int:pk>/consent",
        v.ApplicationConsentView.as_view(),
        name="patents-application-consent",
    ),
    path(
        "applications/<int:pk>/co-inventors/<int:ci_pk>/consent-token",
        v.CoInventorConsentTokenView.as_view(),
        name="patents-coinventor-consent-token",
    ),
    path(
        "consent/confirm",
        v.ConsentConfirmView.as_view(),
        name="patents-consent-confirm",
    ),

    # Director actions
    path(
        "applications/<int:pk>/assign-director",
        v.ApplicationAssignDirectorView.as_view(),
        name="patents-application-assign-director",
    ),
    path(
        "applications/<int:pk>/review-decision",
        v.ApplicationReviewDecisionView.as_view(),
        name="patents-application-review-decision",
    ),
    path(
        "applications/<int:pk>/budget-decision",
        v.ApplicationBudgetDecisionView.as_view(),
        name="patents-application-budget-decision",
    ),
    path(
        "applications/<int:pk>/renewal-decision",
        v.ApplicationRenewalDecisionView.as_view(),
        name="patents-application-renewal-decision",
    ),
    path(
        "applications/<int:pk>/renewal-request",
        v.ApplicationRenewalRequestView.as_view(),
        name="patents-application-renewal-request",
    ),
    path(
        "applications/<int:pk>/maintenance-action",
        v.ApplicationMaintenanceActionView.as_view(),
        name="patents-application-maintenance-action",
    ),
    path(
        "applications/<int:pk>/budget-escalation",
        v.ApplicationBudgetEscalationView.as_view(),
        name="patents-application-budget-escalation",
    ),

    # Appeals
    path(
        "applications/<int:pk>/appeal",
        v.ApplicationAppealView.as_view(),
        name="patents-application-appeal",
    ),
    path(
        "applications/<int:pk>/appeal-decision",
        v.ApplicationAppealDecisionView.as_view(),
        name="patents-application-appeal-decision",
    ),

    # Attorney actions
    path(
        "applications/<int:pk>/assign-attorney",
        v.ApplicationAssignAttorneyView.as_view(),
        name="patents-application-assign-attorney",
    ),
    path(
        "applications/<int:pk>/respond-assignment",
        v.ApplicationRespondAssignmentView.as_view(),
        name="patents-application-respond-assignment",
    ),
    path(
        "applications/<int:pk>/assessment",
        v.ApplicationAssessmentView.as_view(),
        name="patents-application-assessment",
    ),
    path(
        "applications/<int:pk>/filing",
        v.ApplicationFilingView.as_view(),
        name="patents-application-filing",
    ),

    # Office Actions
    path(
        "applications/<int:pk>/office-actions",
        v.ApplicationOfficeActionsView.as_view(),
        name="patents-application-office-actions",
    ),
    path(
        "office-actions/<int:pk>/response",
        v.OfficeActionResponseView.as_view(),
        name="patents-office-action-response",
    ),
    path(
        "office-actions/<int:pk>/approve",
        v.OfficeActionApproveView.as_view(),
        name="patents-office-action-approve",
    ),

    # Supporting collections
    path("attorney-panel", v.AttorneyPanelListView.as_view(), name="patents-attorney-panel"),
    path("tech-transfer", v.TechTransferCreateView.as_view(), name="patents-tech-transfer"),
    path("prior-art/search", v.PriorArtSearchView.as_view(), name="patents-prior-art-search"),
    path("reports", v.ReportsView.as_view(), name="patents-reports"),
    path("audit-logs", v.AuditLogsView.as_view(), name="patents-audit-logs"),
]
