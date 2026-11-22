"""URL routes for BADMS REST API."""

from django.urls import path

from modules.badms.api import views as v

urlpatterns = [
    # Backups
    path("backups", v.BackupListView.as_view(), name="badms-backups"),
    path("backups/manual", v.ManualBackupTriggerView.as_view(), name="badms-backup-manual"),
    path("backups/<int:pk>", v.BackupDetailView.as_view(), name="badms-backup-detail"),
    # Schedules
    path("schedules", v.BackupScheduleListView.as_view(), name="badms-schedules"),
    # Archival Requests
    path("archival-requests", v.ArchivalRequestListView.as_view(), name="badms-archival-requests"),
    path(
        "archival-requests/<int:pk>",
        v.ArchivalRequestDetailView.as_view(),
        name="badms-archival-detail",
    ),
    path(
        "archival-requests/<int:pk>/hod-decision",
        v.HoDArchivalDecisionView.as_view(),
        name="badms-archival-hod-decision",
    ),
    path(
        "archival-requests/<int:pk>/classify",
        v.SysAdminClassifyView.as_view(),
        name="badms-archival-classify",
    ),
    path(
        "archival-requests/<int:pk>/configure-encryption",
        v.ITSecurityEncryptionView.as_view(),
        name="badms-archival-encrypt",
    ),
    path("special-archival", v.SpecialArchivalView.as_view(), name="badms-special-archival"),
    # Storage & Extensions
    path("storage/quota", v.UserStorageQuotaView.as_view(), name="badms-storage-quota"),
    path(
        "storage/extensions", v.StorageExtensionListView.as_view(), name="badms-storage-extensions"
    ),
    path(
        "storage/extensions/<int:pk>/hod-decision",
        v.StorageExtensionDecisionView.as_view(),
        name="badms-storage-extension-hod-decision",
    ),
    # Restorations
    path("restorations", v.RestorationListView.as_view(), name="badms-restorations"),
    path(
        "restorations/<int:pk>/sysadmin-decision",
        v.SysAdminRestorationDecisionView.as_view(),
        name="badms-restoration-sysadmin-decision",
    ),
    path(
        "restorations/<int:pk>/execute",
        v.RestorationExecuteView.as_view(),
        name="badms-restoration-execute",
    ),
    # Audit & Reports
    path("audit-logs", v.AuditLogListView.as_view(), name="badms-audit-logs"),
    path(
        "reports/departmental", v.DepartmentalReportView.as_view(), name="badms-report-departmental"
    ),
    path("reports/compliance", v.ComplianceReportView.as_view(), name="badms-report-compliance"),
    path("reports/security", v.SecurityAuditReportView.as_view(), name="badms-report-security"),
    # Security Policies
    path("security/policies", v.SecurityPolicyListView.as_view(), name="badms-security-policies"),
]
