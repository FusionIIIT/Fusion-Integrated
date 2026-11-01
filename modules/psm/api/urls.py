from django.urls import path

from .attachments import AttachmentDownloadView, AttachmentView
from .views import ActionView, CollectionView, ReportView, WorkspaceView

urlpatterns = [
    path("attachments/upload", AttachmentView.as_view(), name="psm-attachment-upload"),
    path(
        "attachments/<uuid:pk>/download",
        AttachmentDownloadView.as_view(),
        name="psm-attachment-download",
    ),
    path("workspace", WorkspaceView.as_view(), name="psm-workspace"),
    path("report", ReportView.as_view(), name="psm-report"),
    path("<str:resource>", CollectionView.as_view(), name="psm-collection"),
    path("<str:resource>/<uuid:pk>/actions", ActionView.as_view(), name="psm-action"),
]
