"""URL routes for Patent Management System API."""

from __future__ import annotations

from django.urls import path

from modules.pms.api import views as v

urlpatterns = [
    # Applications
    path("applications", v.ApplicationListView.as_view(), name="pms-applications"),
    path(
        "applications/<int:pk>",
        v.ApplicationDetailView.as_view(),
        name="pms-application-detail",
    ),
    path(
        "applications/<int:pk>/resubmit",
        v.ApplicationResubmitView.as_view(),
        name="pms-application-resubmit",
    ),
    path(
        "applications/<int:pk>/withdraw",
        v.ApplicationWithdrawView.as_view(),
        name="pms-application-withdraw",
    ),
    path(
        "applications/<int:pk>/history",
        v.ApplicationHistoryView.as_view(),
        name="pms-application-history",
    ),
    # Reviews & Assignments
    path(
        "applications/<int:pk>/assign-director",
        v.AssignDirectorView.as_view(),
        name="pms-assign-director",
    ),
    path(
        "applications/<int:pk>/review",
        v.DirectorReviewView.as_view(),
        name="pms-director-review",
    ),
    # Documents
    path(
        "applications/<int:pk>/documents",
        v.ApplicationDocumentListView.as_view(),
        name="pms-application-documents",
    ),
    path(
        "documents/<int:pk>/download",
        v.DocumentDownloadView.as_view(),
        name="pms-document-download",
    ),
    # Attorney Panel & Prosecution
    path("attorney-panel", v.AttorneyPanelView.as_view(), name="pms-attorney-panel"),
    path(
        "applications/<int:pk>/assign-attorney",
        v.AssignAttorneyView.as_view(),
        name="pms-assign-attorney",
    ),
    path(
        "attorney/assignments",
        v.AttorneyAssignmentListView.as_view(),
        name="pms-attorney-assignments",
    ),
    path(
        "attorney/assignments/<int:pk>/respond",
        v.AttorneyAssignmentRespondView.as_view(),
        name="pms-attorney-respond",
    ),
    path(
        "applications/<int:pk>/assessment",
        v.PatentabilityAssessmentView.as_view(),
        name="pms-patentability-assessment",
    ),
    path(
        "applications/<int:pk>/legal-advice",
        v.PatentLegalAdviceView.as_view(),
        name="pms-legal-advice",
    ),
    # Budget
    path("applications/<int:pk>/budget", v.BudgetView.as_view(), name="pms-budget"),
    path(
        "applications/<int:pk>/budget/decide",
        v.BudgetDecideView.as_view(),
        name="pms-budget-decide",
    ),
    # Filing & Office Actions
    path(
        "applications/<int:pk>/filing",
        v.ExternalFilingView.as_view(),
        name="pms-external-filing",
    ),
    path("office-actions", v.OfficeActionListView.as_view(), name="pms-office-actions"),
    path(
        "applications/<int:pk>/office-actions",
        v.OfficeActionListView.as_view(),
        name="pms-application-office-action-create",
    ),
    path(
        "office-actions/<int:pk>/response",
        v.OfficeActionResponseView.as_view(),
        name="pms-office-action-response",
    ),
    path(
        "office-actions/responses/<int:pk>/approve",
        v.OfficeActionApproveView.as_view(),
        name="pms-office-action-approve",
    ),
    path(
        "office-actions/responses/<int:pk>/submit",
        v.OfficeActionSubmitView.as_view(),
        name="pms-office-action-submit",
    ),
    path(
        "office-actions/<int:pk>/extension",
        v.OfficeActionExtensionView.as_view(),
        name="pms-office-action-extension",
    ),
    # Post-Grant & Licensing
    path(
        "applications/<int:pk>/grant",
        v.PostGrantInitView.as_view(),
        name="pms-post-grant-init",
    ),
    path("maintenance", v.MaintenanceScheduleListView.as_view(), name="pms-maintenance"),
    path(
        "maintenance/<int:pk>/request-decision",
        v.MaintenanceRequestDecisionView.as_view(),
        name="pms-maintenance-request-decision",
    ),
    path(
        "maintenance/<int:pk>/decide",
        v.MaintenanceDecideView.as_view(),
        name="pms-maintenance-decide",
    ),
    path(
        "maintenance/<int:pk>/pay",
        v.MaintenancePaymentView.as_view(),
        name="pms-maintenance-pay",
    ),
    path("licensing", v.LicensingRequestListView.as_view(), name="pms-licensing"),
    path(
        "applications/<int:pk>/licensing",
        v.LicensingRequestListView.as_view(),
        name="pms-application-licensing-create",
    ),
    path(
        "licensing/<int:pk>/review",
        v.LicensingReviewView.as_view(),
        name="pms-licensing-review",
    ),
    # Appeals & Prior Art
    path("applications/<int:pk>/appeal", v.PatentAppealView.as_view(), name="pms-appeal"),
    path("appeals/<int:pk>/review", v.AppealReviewView.as_view(), name="pms-appeal-review"),
    path("prior-art", v.PriorArtSearchListView.as_view(), name="pms-prior-art"),
    path(
        "prior-art/<int:pk>/attach",
        v.PriorArtAttachView.as_view(),
        name="pms-prior-art-attach",
    ),
    # Reports & Audit
    path(
        "reports/summary",
        v.PortfolioSummaryView.as_view(),
        name="pms-reports-summary",
    ),
    path("audit-logs", v.AuditLogListView.as_view(), name="pms-audit-logs"),
]
