"""URLs for the File Tracking System (FTS) API."""
from django.urls import path

from modules.filetracking.api import views

app_name = "filetracking"

urlpatterns = [
    path("files/", views.FileListView.as_view(), name="file-list"),
    path("files/<int:pk>/", views.FileDetailView.as_view(), name="file-detail"),
    path("files/<int:pk>/draft/", views.DraftActionView.as_view(), name="file-draft-action"),
    path("files/<int:pk>/forward/", views.FileForwardView.as_view(), name="file-forward"),
    path("files/<int:pk>/return/", views.FileReturnView.as_view(), name="file-return"),
    path("files/<int:pk>/archive/", views.FileArchiveView.as_view(), name="file-archive"),
    path("files/<int:pk>/history/", views.FileHistoryView.as_view(), name="file-history"),
    path(
        "admin/audit-logs/",
        views.GovernanceAuditLogsView.as_view(),
        name="governance-audit-logs",
    ),
]
