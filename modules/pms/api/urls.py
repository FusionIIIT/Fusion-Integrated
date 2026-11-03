from django.urls import path

from modules.pms.api import views as v

urlpatterns = [
    path("applications", v.ApplicationListCreateView.as_view(), name="pms-applications"),
    path(
        "applications/<uuid:app_id>",
        v.ApplicationDetailView.as_view(),
        name="pms-application-detail",
    ),
    path(
        "applications/<uuid:app_id>/history",
        v.ApplicationHistoryView.as_view(),
        name="pms-application-history",
    ),
    path(
        "applications/<uuid:app_id>/submit",
        v.ApplicationSubmitView.as_view(),
        name="pms-application-submit",
    ),
    path(
        "applications/<uuid:app_id>/assign-director",
        v.DirectorAssignmentView.as_view(),
        name="pms-assign-director",
    ),
    path("applications/<uuid:app_id>/review", v.ReviewDecisionView.as_view(), name="pms-review"),
    path(
        "applications/<uuid:app_id>/resubmit",
        v.RevisionResubmissionView.as_view(),
        name="pms-resubmit",
    ),
    path(
        "applications/<uuid:app_id>/withdraw",
        v.ApplicationWithdrawalView.as_view(),
        name="pms-withdraw",
    ),
    path(
        "applications/<uuid:app_id>/inventors",
        v.InventorListCreateView.as_view(),
        name="pms-inventors",
    ),
    path(
        "inventor-agreements/<int:agreement_id>/consent",
        v.InventorConsentView.as_view(),
        name="pms-inventor-consent",
    ),
    path(
        "applications/<uuid:app_id>/documents", v.DocumentUploadView.as_view(), name="pms-documents"
    ),
    path(
        "applications/<uuid:app_id>/documents/<int:document_id>/download",
        v.DocumentDownloadView.as_view(),
        name="pms-document-download",
    ),
    path(
        "applications/<uuid:app_id>/assign-attorney",
        v.AttorneyAssignmentView.as_view(),
        name="pms-assign-attorney",
    ),
    path(
        "attorney-assignments/<int:assignment_id>/respond",
        v.AttorneyAssignmentResponseView.as_view(),
        name="pms-attorney-assignment-response",
    ),
    path(
        "applications/<uuid:app_id>/budgets", v.BudgetListCreateView.as_view(), name="pms-budgets"
    ),
    path(
        "budgets/<int:budget_id>/decision",
        v.BudgetDecisionView.as_view(),
        name="pms-budget-decision",
    ),
    path(
        "applications/<uuid:app_id>/opinion",
        v.PatentabilityOpinionView.as_view(),
        name="pms-opinion",
    ),
    path("applications/<uuid:app_id>/filing", v.FilingRecordView.as_view(), name="pms-filing"),
    path(
        "applications/<uuid:app_id>/appeals", v.AppealListCreateView.as_view(), name="pms-appeals"
    ),
    path(
        "appeals/<int:appeal_id>/decision",
        v.AppealDecisionView.as_view(),
        name="pms-appeal-decision",
    ),
    path(
        "applications/<uuid:app_id>/office-actions",
        v.OfficeActionListCreateView.as_view(),
        name="pms-office-actions",
    ),
    path(
        "office-actions/<int:communication_id>/responses",
        v.OfficeActionResponseView.as_view(),
        name="pms-office-action-response",
    ),
    path(
        "office-action-responses/<int:response_id>/approval",
        v.OfficeActionApprovalView.as_view(),
        name="pms-office-action-approval",
    ),
    path(
        "office-action-responses/<int:response_id>/submission",
        v.OfficeActionSubmissionView.as_view(),
        name="pms-office-action-submission",
    ),
    path("configuration", v.PmsConfigurationView.as_view(), name="pms-configuration"),
    path("panel", v.PanelProfilesView.as_view(), name="pms-panel"),
    path("audit", v.AuditTrailView.as_view(), name="pms-audit"),
    path(
        "applications/<uuid:app_id>/audit", v.AuditTrailView.as_view(), name="pms-application-audit"
    ),
    path("reports", v.ReportsView.as_view(), name="pms-reports"),
    path("deadlines", v.DeadlineListView.as_view(), name="pms-deadlines"),
    path(
        "applications/<uuid:app_id>/legal-advice",
        v.LegalAdviceView.as_view(),
        name="pms-legal-advice",
    ),
    path("prior-art/search", v.PriorArtSearchView.as_view(), name="pms-prior-art-search"),
    path(
        "prior-art/references/<int:reference_id>/attach",
        v.PriorArtReferenceAttachView.as_view(),
        name="pms-prior-art-attach",
    ),
    path(
        "applications/<uuid:app_id>/licensing",
        v.LicensingRequestListCreateView.as_view(),
        name="pms-licensing-requests",
    ),
    path(
        "licensing/<int:request_id>",
        v.LicensingRequestReviewView.as_view(),
        name="pms-licensing-review",
    ),
    path(
        "applications/<uuid:app_id>/maintenance-cycles",
        v.MaintenanceCycleListCreateView.as_view(),
        name="pms-maintenance-cycles",
    ),
    path(
        "maintenance-cycles/<int:cycle_id>/request-decision",
        v.MaintenanceDecisionRequestView.as_view(),
        name="pms-maintenance-request",
    ),
    path(
        "maintenance-cycles/<int:cycle_id>/decision",
        v.MaintenanceDecisionView.as_view(),
        name="pms-maintenance-decision",
    ),
    path(
        "maintenance-cycles/<int:cycle_id>/record-action",
        v.MaintenanceActionRecordView.as_view(),
        name="pms-maintenance-record",
    ),
]
