"""URL routing for BADMS API endpoints."""

from django.urls import path
from .views import (
    ArchivalDetailView,
    ArchivalEncryptionConfigureView,
    ArchivalHodDecisionView,
    ArchivalRequestListView,
    ArchivalSysAdminClassifyView,
    AuditListView,
    BackupListView,
    BackupScheduleListView,
    RestorationExecuteView,
    RestorationListView,
    RestorationSysAdminDecisionView,
    SpecialArchivalView,
    StorageExtensionHodDecisionView,
    StorageExtensionListView,
    StorageQuotaView,
)

app_name = "badms"

urlpatterns = [
    # Backups
    path("backups/", BackupListView.as_view(), name="backup_list"),
    path("schedules/", BackupScheduleListView.as_view(), name="schedule_list"),
    
    # Archival Workflow (CW-BA-01)
    path("archival/", ArchivalRequestListView.as_view(), name="archival_list"),
    path("archival/special/", SpecialArchivalView.as_view(), name="archival_special"),
    path("archival/<uuid:pk>/", ArchivalDetailView.as_view(), name="archival_detail"),
    path("archival/<uuid:pk>/hod-decision/", ArchivalHodDecisionView.as_view(), name="archival_hod_decision"),
    path("archival/<uuid:pk>/classify/", ArchivalSysAdminClassifyView.as_view(), name="archival_classify"),
    path("archival/<uuid:pk>/configure-encryption/", ArchivalEncryptionConfigureView.as_view(), name="archival_encrypt"),
    
    # Storage Extension Workflow (CW-BA-02)
    path("storage/quota/", StorageQuotaView.as_view(), name="storage_quota"),
    path("storage/extensions/", StorageExtensionListView.as_view(), name="storage_extension_list"),
    path("storage/extensions/<uuid:pk>/hod-decision/", StorageExtensionHodDecisionView.as_view(), name="storage_extension_hod"),
    
    # Restoration Workflow (CW-BA-03)
    path("restoration/", RestorationListView.as_view(), name="restoration_list"),
    path("restoration/<uuid:pk>/sysadmin-decision/", RestorationSysAdminDecisionView.as_view(), name="restoration_sysadmin_decision"),
    path("restoration/<uuid:pk>/execute/", RestorationExecuteView.as_view(), name="restoration_execute"),
    
    # Audit & Monitoring
    path("audit/", AuditListView.as_view(), name="audit_list"),
]
