from django.urls import path
from modules.badms.api import views as v

urlpatterns = [
    # Backup operations & schedules
    path("backups", v.BackupOperationListView.as_view(), name="badms-backups"),
    path("schedules", v.BackupScheduleListView.as_view(), name="badms-schedules"),

    # Secure archival
    path("archivals", v.SecureArchivalListView.as_view(), name="badms-archivals"),
    path("archivals/<int:pk>/hod-review", v.ArchivalHodReviewView.as_view(), name="badms-archival-hod-review"),
    path("archivals/<int:pk>/classify", v.ArchivalClassifyView.as_view(), name="badms-archival-classify"),
    path("archivals/<int:pk>/configure-encryption", v.ArchivalEncryptionView.as_view(), name="badms-archival-encrypt"),

    # Storage quota and extension
    path("storage/quota", v.StorageQuotaView.as_view(), name="badms-storage-quota"),
    path("storage-extensions", v.StorageExtensionListView.as_view(), name="badms-storage-extensions"),
    path("storage-extensions/<int:pk>/hod-review", v.StorageExtensionHodReviewView.as_view(), name="badms-storage-extension-hod-review"),

    # Data restoration
    path("restorations", v.RestorationListView.as_view(), name="badms-restorations"),
    path("restorations/<int:pk>/sysadmin-review", v.RestorationSysAdminReviewView.as_view(), name="badms-restoration-sysadmin-review"),

    # Audit logs
    path("audit-logs", v.AuditLogListView.as_view(), name="badms-audit-logs"),
]
