from django.urls import path

from modules.badms.api import views

app_name = "badms"

urlpatterns = [
    # Backups
    path("backups/manual/", views.ManualBackupView.as_view(), name="manual_backup"),
    path("backups/", views.BackupRecordListView.as_view(), name="backup_list"),
    path("backups/<int:pk>/", views.BackupRecordDetailView.as_view(), name="backup_detail"),
    # Schedules
    path("schedules/", views.BackupScheduleListView.as_view(), name="schedule_list"),
    path("schedules/local/", views.CreateLocalScheduleView.as_view(), name="create_local_schedule"),
    path(
        "schedules/local/<int:pk>/",
        views.UpdateLocalScheduleView.as_view(),
        name="update_local_schedule",
    ),
    path(
        "schedules/global/", views.CreateGlobalScheduleView.as_view(), name="create_global_schedule"
    ),
    # Archival Requests
    path(
        "archival-requests/",
        views.ArchivalRequestListCreateView.as_view(),
        name="archival_list_create",
    ),
    path(
        "archival-requests/<int:pk>/",
        views.ArchivalRequestDetailView.as_view(),
        name="archival_detail",
    ),
    path(
        "archival-requests/<int:pk>/decide/",
        views.DecideArchivalRequestView.as_view(),
        name="archival_decide",
    ),
    path(
        "archival-requests/<int:pk>/classify/",
        views.ClassifyArchivalRequestView.as_view(),
        name="archival_classify",
    ),
    path(
        "archival-requests/<int:pk>/configure-encryption/",
        views.ConfigureEncryptionView.as_view(),
        name="archival_configure_encryption",
    ),
    path(
        "archival-requests/special/", views.SpecialArchivalView.as_view(), name="special_archival"
    ),
    # Storage Extensions
    path(
        "storage-extensions/",
        views.StorageExtensionListCreateView.as_view(),
        name="storage_extension_list_create",
    ),
    path(
        "storage-extensions/<int:pk>/decide/",
        views.DecideStorageExtensionView.as_view(),
        name="storage_extension_decide",
    ),
    # Restoration
    path(
        "restorations/", views.RestorationListCreateView.as_view(), name="restoration_list_create"
    ),
    path(
        "restorations/<int:pk>/approve/",
        views.ApproveSensitiveRestorationView.as_view(),
        name="restoration_approve_sensitive",
    ),
    path(
        "restorations/<int:pk>/execute/",
        views.ExecuteRestorationView.as_view(),
        name="restoration_execute",
    ),
    # Audits & Reports
    path("audit-logs/", views.AuditEventListView.as_view(), name="audit_log_list"),
    path(
        "audit-logs/security/",
        views.SecurityAuditEventListView.as_view(),
        name="security_audit_log_list",
    ),
    path("reports/department/", views.DepartmentReportView.as_view(), name="department_report"),
    # Security Policies
    path(
        "security-policies/",
        views.SecurityPolicyListCreateView.as_view(),
        name="security_policy_list_create",
    ),
]
