"""URL routing for File Tracking System API."""

from django.urls import path

from modules.filetracking.api.views import (
    ArchivedView,
    DraftsView,
    FileArchiveView,
    FileCreateView,
    FileDetailView,
    FileDraftDiscardView,
    FileDraftUpdateView,
    FileForwardView,
    FileHistoryView,
    FileReturnView,
    GovernanceAuditView,
    InboxView,
    IntegrationInitiateView,
    OutboxView,
)

app_name = "filetracking"

urlpatterns = [
    # Collections
    path("files/inbox/", InboxView.as_view(), name="files-inbox"),
    path("files/outbox/", OutboxView.as_view(), name="files-outbox"),
    path("files/drafts/", DraftsView.as_view(), name="files-drafts"),
    path("files/archived/", ArchivedView.as_view(), name="files-archived"),
    path("files/", FileCreateView.as_view(), name="files-create"),
    # Detail and Actions
    path("files/<int:file_id>/", FileDetailView.as_view(), name="files-detail"),
    path(
        "files/<int:file_id>/draft/",
        FileDraftUpdateView.as_view(),
        name="files-draft-update",
    ),
    path(
        "files/<int:file_id>/draft/discard/",
        FileDraftDiscardView.as_view(),
        name="files-draft-discard",
    ),
    path("files/<int:file_id>/forward/", FileForwardView.as_view(), name="files-forward"),
    path("files/<int:file_id>/return/", FileReturnView.as_view(), name="files-return"),
    path("files/<int:file_id>/archive/", FileArchiveView.as_view(), name="files-archive"),
    path("files/<int:file_id>/history/", FileHistoryView.as_view(), name="files-history"),
    # Governance & Inter-module
    path("governance/audit/", GovernanceAuditView.as_view(), name="governance-audit"),
    path("integration/initiate/", IntegrationInitiateView.as_view(), name="integration-initiate"),
]
