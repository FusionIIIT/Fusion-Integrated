from django.urls import path

from modules.fts.api.views import (
    DraftListView,
    FileArchiveView,
    FileDetailView,
    FileDiscardView,
    FileForwardView,
    FileHistoryView,
    FileListCreateView,
    FileReturnView,
    GovernanceAuditLogsView,
    GovernanceUsageView,
    InboxListView,
    IntegrationCreateFileView,
    OutboxListView,
)

app_name = "fts"

urlpatterns = [
    path("files/", FileListCreateView.as_view(), name="file_list_create"),
    path("files/<int:pk>/", FileDetailView.as_view(), name="file_detail"),
    path("files/<int:pk>/discard/", FileDiscardView.as_view(), name="file_discard"),
    path("files/<int:pk>/forward/", FileForwardView.as_view(), name="file_forward"),
    path("files/<int:pk>/return/", FileReturnView.as_view(), name="file_return"),
    path("files/<int:pk>/archive/", FileArchiveView.as_view(), name="file_archive"),
    path("files/<int:pk>/history/", FileHistoryView.as_view(), name="file_history"),
    path("drafts/", DraftListView.as_view(), name="draft_list"),
    path("inbox/", InboxListView.as_view(), name="inbox_list"),
    path("outbox/", OutboxListView.as_view(), name="outbox_list"),
    path(
        "governance/audit-logs/",
        GovernanceAuditLogsView.as_view(),
        name="governance_audit_logs",
    ),
    path("governance/usage/", GovernanceUsageView.as_view(), name="governance_usage"),
    path(
        "integrations/requests/",
        IntegrationCreateFileView.as_view(),
        name="integration_create_file",
    ),
]
