"""PMS API URLs."""

from django.urls import path

from modules.pms.api import views

urlpatterns = [
    # Applications core lifecycle
    path(
        "applications/",
        views.PatentApplicationListCreateView.as_view(),
        name="pms-application-list-create",
    ),
    path(
        "applications/<int:pk>/",
        views.PatentApplicationDetailView.as_view(),
        name="pms-application-detail",
    ),
    path(
        "applications/<int:pk>/revise/",
        views.PatentApplicationReviseView.as_view(),
        name="pms-application-revise",
    ),
    path(
        "applications/<int:pk>/withdraw/",
        views.PatentApplicationWithdrawView.as_view(),
        name="pms-application-withdraw",
    ),
    path(
        "applications/<int:pk>/assign-director/",
        views.PatentApplicationAssignDirectorView.as_view(),
        name="pms-application-assign-director",
    ),
    path(
        "applications/<int:pk>/review/",
        views.PatentApplicationReviewView.as_view(),
        name="pms-application-review",
    ),
    path(
        "applications/<int:pk>/appeal/",
        views.PatentApplicationAppealView.as_view(),
        name="pms-application-appeal",
    ),
    path(
        "appeals/<int:appeal_id>/review/",
        views.PatentAppealReviewView.as_view(),
        name="pms-appeal-review",
    ),
    # Budget & Financial
    path(
        "applications/<int:pk>/budget/",
        views.PatentBudgetView.as_view(),
        name="pms-application-budget",
    ),
    # Attorney assignment & assessment
    path(
        "applications/<int:pk>/assign-attorney/",
        views.PatentApplicationAssignAttorneyView.as_view(),
        name="pms-application-assign-attorney",
    ),
    path(
        "attorney-assignments/<int:assignment_id>/respond/",
        views.AttorneyAssignmentRespondView.as_view(),
        name="pms-attorney-assignment-respond",
    ),
    path(
        "applications/<int:pk>/patentability/",
        views.PatentabilityAssessmentView.as_view(),
        name="pms-application-patentability",
    ),
    path(
        "applications/<int:pk>/legal-advice/",
        views.LegalAdviceListCreateView.as_view(),
        name="pms-application-legal-advice",
    ),
    # Filing & Office actions
    path(
        "applications/<int:pk>/filing/",
        views.PatentFilingView.as_view(),
        name="pms-application-filing",
    ),
    path(
        "applications/<int:pk>/grant/",
        views.PatentGrantView.as_view(),
        name="pms-application-grant",
    ),
    path(
        "applications/<int:pk>/office-actions/",
        views.OfficeActionListCreateView.as_view(),
        name="pms-office-actions",
    ),
    path(
        "office-actions/<int:oa_id>/draft-response/",
        views.OfficeActionDraftResponseView.as_view(),
        name="pms-oa-draft-response",
    ),
    path(
        "office-actions/<int:oa_id>/approve-response/",
        views.OfficeActionApproveResponseView.as_view(),
        name="pms-oa-approve-response",
    ),
    path(
        "office-actions/<int:oa_id>/submit-response/",
        views.OfficeActionSubmitResponseView.as_view(),
        name="pms-oa-submit-response",
    ),
    path(
        "office-actions/<int:oa_id>/extension/",
        views.OfficeActionExtensionView.as_view(),
        name="pms-oa-extension",
    ),
    # Post-grant maintenance
    path(
        "maintenance/<int:maintenance_id>/request-renewal/",
        views.MaintenanceRequestRenewalView.as_view(),
        name="pms-maintenance-request-renewal",
    ),
    path(
        "maintenance/<int:maintenance_id>/decide-renewal/",
        views.MaintenanceDecideRenewalView.as_view(),
        name="pms-maintenance-decide-renewal",
    ),
    path(
        "maintenance/<int:maintenance_id>/record-action/",
        views.MaintenanceRecordActionView.as_view(),
        name="pms-maintenance-record-action",
    ),
    # Prior art & documents
    path("prior-art/search/", views.PriorArtSearchView.as_view(), name="pms-prior-art-search"),
    path(
        "applications/<int:pk>/prior-art/",
        views.PriorArtAttachView.as_view(),
        name="pms-prior-art-attach",
    ),
    path(
        "applications/<int:pk>/documents/",
        views.DocumentUploadView.as_view(),
        name="pms-document-upload",
    ),
    # Licensing & Agreements
    path(
        "applications/<int:pk>/licensing/",
        views.LicensingRequestListCreateView.as_view(),
        name="pms-licensing-list-create",
    ),
    path(
        "licensing/<int:request_id>/review/",
        views.LicensingRequestReviewView.as_view(),
        name="pms-licensing-review",
    ),
    path(
        "coinventors/<int:coinventor_id>/consent/",
        views.CoInventorConsentView.as_view(),
        name="pms-coinventor-consent",
    ),
    path(
        "coinventors/<int:coinventor_id>/withdrawal-consent/",
        views.CoInventorWithdrawalConsentView.as_view(),
        name="pms-coinventor-withdrawal-consent",
    ),
    # Oversight, panel, audit & reports
    path("attorney-panel/", views.AttorneyPanelListView.as_view(), name="pms-attorney-panel"),
    path("audit-trail/", views.AuditTrailListView.as_view(), name="pms-audit-trail"),
    path("reports/", views.ReportsView.as_view(), name="pms-reports"),
]
