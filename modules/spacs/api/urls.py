"""URL routing for the SPACS API."""

from django.urls import path

from modules.spacs.api import views as v

urlpatterns = [
    # Catalogue
    path("catalogue", v.CatalogueListView.as_view(), name="spacs-catalogue-list"),
    path("catalogue/<int:pk>", v.CatalogueDetailView.as_view(), name="spacs-catalogue-detail"),
    path("catalogue/<int:pk>/versions", v.CatalogueVersionCreateView.as_view(), name="spacs-catalogue-version-create"),
    path("catalogue/versions/<int:version_id>/publish", v.CataloguePublishView.as_view(), name="spacs-catalogue-publish"),
    path("catalogue/<int:pk>/retire", v.CatalogueRetireView.as_view(), name="spacs-catalogue-retire"),

    # Applications
    path("applications/mine", v.MyApplicationsView.as_view(), name="spacs-my-applications"),
    path("applications/draft", v.ApplicationDraftSaveView.as_view(), name="spacs-application-draft-save"),
    path("applications/<int:pk>", v.ApplicationDetailView.as_view(), name="spacs-application-detail"),
    path("applications/<int:pk>/submit", v.ApplicationSubmitView.as_view(), name="spacs-application-submit"),
    path("applications/<int:pk>/withdraw", v.ApplicationWithdrawView.as_view(), name="spacs-application-withdraw"),
    path("applications/<int:pk>/timeline", v.ApplicationTimelineView.as_view(), name="spacs-application-timeline"),
    path("applications/<int:pk>/export", v.ApplicationExportView.as_view(), name="spacs-application-export"),
    path("applications/<int:pk>/renew", v.RenewalInitiateView.as_view(), name="spacs-application-renew"),

    # Verification
    path("verification/queue", v.VerificationQueueView.as_view(), name="spacs-verification-queue"),
    path("verification/<int:application_id>/action", v.VerificationActionView.as_view(), name="spacs-verification-action"),
    path("verification/documents/<int:doc_id>", v.DocumentVerifyView.as_view(), name="spacs-document-verify"),

    # Decisions
    path("decisions/queue", v.DecisionQueueView.as_view(), name="spacs-decision-queue"),
    path("decisions/<int:application_id>/action", v.DecisionActionView.as_view(), name="spacs-decision-action"),

    # Awards
    path("awards/cycles", v.AwardCycleListView.as_view(), name="spacs-award-cycles"),
    path("awards/cycles/<int:pk>/pool", v.AwardCyclePoolView.as_view(), name="spacs-award-cycle-pool"),
    path("awards/cycles/<int:pk>/evaluations", v.AwardEvaluationView.as_view(), name="spacs-award-evaluations"),
    path("awards/cycles/<int:pk>/approve", v.AwardApprovalView.as_view(), name="spacs-award-approve"),
    path("awards/cycles/<int:pk>/publish", v.AwardPublishView.as_view(), name="spacs-award-publish"),
    path("awards/public", v.PublishedAwardsPublicView.as_view(), name="spacs-awards-public"),

    # Audit
    path("audit/trail", v.AuditTrailView.as_view(), name="spacs-audit-trail"),
]
