"""FTS URL routing."""
from django.urls import path

from modules.fts.api import views

app_name = "fts"

urlpatterns = [
    path("inbox/", views.InboxListView.as_view(), name="inbox"),
    path("outbox/", views.OutboxListView.as_view(), name="outbox"),
    path("drafts/", views.DraftsListView.as_view(), name="drafts"),
    path("files/", views.FileCreateView.as_view(), name="file_create"),
    path(
        "files/<str:file_identifier>/",
        views.FileDetailView.as_view(),
        name="file_detail",
    ),
    path(
        "files/<str:file_identifier>/draft/",
        views.DraftActionView.as_view(),
        name="draft_action",
    ),
    path(
        "files/<str:file_identifier>/forward/",
        views.ForwardFileView.as_view(),
        name="forward_file",
    ),
    path(
        "files/<str:file_identifier>/return/",
        views.ReturnFileView.as_view(),
        name="return_file",
    ),
    path(
        "files/<str:file_identifier>/archive/",
        views.ArchiveFileView.as_view(),
        name="archive_file",
    ),
    path("users/search/", views.UserSearchView.as_view(), name="user_search"),
    path("audit-logs/", views.AuditLogListView.as_view(), name="audit_logs"),
]
