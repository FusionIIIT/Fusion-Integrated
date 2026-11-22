"""URL routes for the SPACS API."""
from django.urls import path

from modules.spacs.api import views

app_name = "spacs"

urlpatterns = [
    # Catalogue
    path("catalogue/", views.CatalogueListView.as_view(), name="catalogue-list"),
    path("catalogue/manage/", views.CatalogueCreateView.as_view(), name="catalogue-create"),
    path("catalogue/<int:pk>/", views.CatalogueDetailView.as_view(), name="catalogue-detail"),
    path("catalogue/<int:pk>/versions/", views.CatalogueVersionCreateView.as_view(), name="catalogue-version-create"),
    path("catalogue/<int:pk>/versions/<int:version_id>/publish/", views.CataloguePublishView.as_view(), name="catalogue-publish"),
    path("catalogue/<int:pk>/retire/", views.CatalogueRetireView.as_view(), name="catalogue-retire"),

    # Applications
    path("applications/", views.ApplicationListView.as_view(), name="application-list"),
    path("applications/apply/", views.ApplicationCreateView.as_view(), name="application-create"),
    path("applications/renew/", views.RenewalApplicationView.as_view(), name="application-renew"),
    path("applications/<int:pk>/", views.ApplicationDetailView.as_view(), name="application-detail"),
    path("applications/<int:pk>/submit/", views.ApplicationSubmitView.as_view(), name="application-submit"),
    path("applications/<int:pk>/modify/", views.ApplicationModifyView.as_view(), name="application-modify"),
    path("applications/<int:pk>/withdraw/", views.ApplicationWithdrawView.as_view(), name="application-withdraw"),
    path("applications/<int:pk>/verify/", views.ApplicationVerifyView.as_view(), name="application-verify"),
    path("applications/<int:pk>/decide/", views.ApplicationDecideView.as_view(), name="application-decide"),
    path("applications/<int:pk>/export/", views.ApplicationExportView.as_view(), name="application-export"),
    path("applications/<int:pk>/documents/", views.DocumentUploadView.as_view(), name="document-upload"),
    path("applications/<int:pk>/documents/reuse/", views.DocumentReuseView.as_view(), name="document-reuse"),

    # Award cycles
    path("awards/cycles/", views.AwardCycleListView.as_view(), name="award-cycle-list"),
    path("awards/cycles/manage/", views.AwardCycleCreateView.as_view(), name="award-cycle-create"),
    path("awards/cycles/<int:pk>/", views.AwardCycleDetailView.as_view(), name="award-cycle-detail"),
    path("awards/cycles/<int:pk>/prepare-pool/", views.AwardCandidatePoolView.as_view(), name="award-prepare-pool"),
    path("awards/cycles/<int:pk>/evaluate/", views.AwardEvaluationView.as_view(), name="award-evaluate"),
    path("awards/cycles/<int:pk>/record-approval/", views.AwardApprovalView.as_view(), name="award-record-approval"),
    path("awards/cycles/<int:pk>/publish/", views.AwardPublishView.as_view(), name="award-publish"),

    # Audit & Notifications
    path("audit/", views.AuditLogListView.as_view(), name="audit-list"),
    path("notifications/", views.NotificationListView.as_view(), name="notifications-list"),
]
