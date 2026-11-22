from django.urls import path

from modules.badms.api.views import (
    ArchiveAttachmentView,
    ArchiveClassificationView,
    ArchiveDecisionView,
    ArchiveListCreateView,
    AuditListView,
    BackupDownloadView,
    BackupListView,
    BackupRunView,
    SensitiveArchiveCompleteView,
)

app_name = "badms"
urlpatterns = [
    path("backups/", BackupListView.as_view(), name="backups"),
    path("backups/run/", BackupRunView.as_view(), name="backup-run"),
    path("backups/<int:pk>/download/", BackupDownloadView.as_view(), name="backup-download"),
    path("archives/", ArchiveListCreateView.as_view(), name="archives"),
    path("archives/<int:pk>/decision/", ArchiveDecisionView.as_view(), name="archive-decision"),
    path("archives/<int:pk>/classification/", ArchiveClassificationView.as_view(), name="archive-classification"),
    path("archives/<int:pk>/complete-sensitive/", SensitiveArchiveCompleteView.as_view(), name="archive-complete-sensitive"),
    path("archives/<int:pk>/attachment/", ArchiveAttachmentView.as_view(), name="archive-attachment"),
    path("audit/", AuditListView.as_view(), name="audit"),
]
