"""Server-filtered BADMS navigation and permission manifest."""

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError

MODULE = {
    "code": "badms",
    "label": "Backup and Archive Management",
    "icon": "Database",
    "base_path": "/badms",
    "nav_section": "Operations",
    "sort_order": 40,
    "status": "active",
}

PERMISSIONS = [
    ("badms.backup.run_manual", "Trigger a manual backup"),
    ("badms.backup.view", "View authorized backup status and history"),
    ("badms.backup.execute_scheduled", "Execute scheduled backups"),
    ("badms.notifications.deliver", "Deliver BADMS notifications"),
    ("badms.storage.monitor", "Monitor storage thresholds"),
    ("badms.retention.enforce", "Enforce configured retention policy"),
    ("badms.schedule_local.manage", "Manage local backup schedules"),
    ("badms.schedule_global.manage", "Manage global backup schedules and defaults"),
    ("badms.archive.create", "Submit archival requests"),
    ("badms.archive.view_self", "View own archival requests"),
    ("badms.archive.review_department", "Review department archival requests"),
    ("badms.archive.classify", "Assign authoritative archival classification"),
    ("badms.archive.encrypt", "Configure Sensitive archive encryption"),
    ("badms.archive.special", "Perform special archival operations"),
    ("badms.restore.create", "Request data restoration"),
    ("badms.restore.view_self", "View own restoration requests"),
    ("badms.restore.approve", "Approve Sensitive restoration"),
    ("badms.restore.execute", "Execute approved restoration"),
    ("badms.storage_extension.create", "Request storage extension"),
    ("badms.storage_extension.review_department", "Review department storage requests"),
    ("badms.audit.view", "View authorized audit history"),
    ("badms.security.audit", "Review security audit reports"),
    ("badms.security_policy.manage", "Manage BADMS security and retention policy"),
    ("badms.reports.department", "View department reports"),
]


def readiness():
    """Explain production prerequisites before BADMS is activated."""
    if settings.DEBUG:
        return []
    unmet = []
    if getattr(settings, "BADMS_STORAGE_BACKEND", "local") != "s3":
        unmet.append("Set BADMS_STORAGE_BACKEND=s3 for private recovery storage.")
    unmet.extend(
        f"Set {name}=true after enforcing the corresponding S3 policy."
        for name in ("BADMS_STORAGE_PRIVATE", "BADMS_STORAGE_AES256", "BADMS_STORAGE_TLS")
        if not getattr(settings, name, False)
    )
    unmet.extend(
        f"Configure {name} for the institute recovery bucket and KMS key."
        for name in ("BADMS_S3_BUCKET", "BADMS_S3_REGION", "BADMS_S3_KMS_KEY_ID")
        if not getattr(settings, name, "")
    )
    if getattr(settings, "BADMS_STORAGE_BACKEND", "local") == "s3":
        from django.core.files.storage import InvalidStorageError, storages

        try:
            from modules.badms.services.s3_storage import AES256S3Storage

            storage = storages["badms"]
            if (
                not isinstance(storage, AES256S3Storage)
                or not storage.use_ssl
                or storage.verify is False
                or storage.object_parameters.get("ServerSideEncryption") != "aws:kms"
                or not storage.object_parameters.get("SSEKMSKeyId")
            ):
                unmet.append(
                    "Configure the BADMS S3 alias for HTTPS, SSE-KMS, and the AES-256 TLS backend."
                )
        except InvalidStorageError:
            unmet.append("Configure the BADMS S3 storage alias.")
    retention = getattr(settings, "BADMS_RETENTION_DAYS", {})
    try:
        from modules.badms.models import SecurityPolicy

        configured = (
            SecurityPolicy.objects.filter(pk=1).values_list("retention_days", flat=True).first()
        )
        if configured is not None:
            retention = configured
    except (OperationalError, ProgrammingError):
        unmet.append("Run BADMS database migrations before checking retention configuration.")
    if not all(
        type(retention.get(kind)) is int and retention[kind] > 0
        for kind in ("Critical", "Sensitive", "Routine", "Archival")
    ):
        unmet.append("Set institute-approved positive retention days for all four classifications.")
    quota = getattr(settings, "BADMS_USER_QUOTA_BYTES", None)
    capacity = getattr(settings, "BADMS_AVAILABLE_STORAGE_BYTES", None)
    if not isinstance(quota, int) or quota < 1:
        unmet.append("Configure BADMS_USER_QUOTA_BYTES from institute policy.")
    if not isinstance(capacity, int) or capacity < 0:
        unmet.append("Configure BADMS_AVAILABLE_STORAGE_BYTES from infrastructure capacity.")
    if not getattr(settings, "BADMS_SYSADMIN_ALERT_EMAILS", []):
        unmet.append("Configure BADMS_SYSADMIN_ALERT_EMAILS for operational alerts.")
    if not getattr(settings, "BADMS_IT_SECURITY_EMAILS", []):
        unmet.append("Configure BADMS_IT_SECURITY_EMAILS for Sensitive archive routing.")
    if not getattr(settings, "BADMS_HOD_EMAILS", {}):
        unmet.append("Configure BADMS_HOD_EMAILS for department archival and storage routing.")
    return unmet


ROLE_GRANTS = {
    "student": [
        "badms.archive.create",
        "badms.archive.view_self",
        "badms.restore.create",
        "badms.restore.view_self",
        "badms.storage_extension.create",
        "badms.backup.view",
    ],
    "faculty": [
        "badms.archive.create",
        "badms.archive.view_self",
        "badms.restore.create",
        "badms.restore.view_self",
        "badms.storage_extension.create",
        "badms.backup.view",
    ],
    "staff": [
        "badms.archive.create",
        "badms.archive.view_self",
        "badms.restore.create",
        "badms.restore.view_self",
        "badms.storage_extension.create",
        "badms.backup.view",
    ],
    "Department Head (HoD)": [
        "badms.archive.review_department",
        "badms.storage_extension.review_department",
        "badms.reports.department",
    ],
    "System Administrator (SysAdmin)": [
        "badms.backup.run_manual",
        "badms.backup.view",
        "badms.schedule_local.manage",
        "badms.archive.classify",
        "badms.restore.approve",
        "badms.restore.execute",
        "badms.audit.view",
    ],
    "Super Admin": [
        "badms.backup.run_manual",
        "badms.backup.view",
        "badms.schedule_global.manage",
        "badms.archive.special",
    ],
    "IT Security Team": [
        "badms.archive.encrypt",
        "badms.security.audit",
        "badms.security_policy.manage",
    ],
}

SYSTEM_PERMISSIONS = [
    "badms.backup.execute_scheduled",
    "badms.notifications.deliver",
    "badms.storage.monitor",
    "badms.retention.enforce",
]

NAV_ITEMS = [
    {
        "code": "badms.home",
        "label": "Overview",
        "icon": "Database",
        "to": "/badms",
        "required_permission": "badms.backup.view",
        "sort_order": 10,
    },
    {
        "code": "badms.archives",
        "label": "Archives",
        "icon": "ArchiveBox",
        "to": "/badms/archives",
        "required_permission": "badms.archive.view_self",
        "sort_order": 20,
    },
    {
        "code": "badms.archive.review",
        "label": "Review Archives",
        "icon": "ShieldCheck",
        "to": "/badms/archives",
        "required_permission": "badms.archive.review_department",
        "sort_order": 30,
    },
    {
        "code": "badms.operations",
        "label": "Recovery & Reports",
        "icon": "Database",
        "to": "/badms/operations",
        "required_permission": "badms.restore.view_self",
        "sort_order": 40,
    },
    {
        "code": "badms.schedule.manage",
        "label": "Backup Schedules",
        "icon": "Database",
        "to": "/badms/operations",
        "required_permission": "badms.schedule_local.manage",
        "sort_order": 50,
    },
    {
        "code": "badms.schedule.global",
        "label": "Global Backup Schedules",
        "icon": "Database",
        "to": "/badms/operations",
        "required_permission": "badms.schedule_global.manage",
        "sort_order": 55,
    },
    {
        "code": "badms.security.audit",
        "label": "Security Audit",
        "icon": "ShieldCheck",
        "to": "/badms/operations",
        "required_permission": "badms.security.audit",
        "sort_order": 60,
    },
    {
        "code": "badms.department.report",
        "label": "Department Reports",
        "icon": "Database",
        "to": "/badms/operations",
        "required_permission": "badms.reports.department",
        "sort_order": 70,
    },
    {
        "code": "badms.special.archive",
        "label": "Special Archive",
        "icon": "ArchiveBox",
        "to": "/badms/operations",
        "required_permission": "badms.archive.special",
        "sort_order": 80,
    },
    {
        "code": "badms.audit",
        "label": "Audit History",
        "icon": "ShieldCheck",
        "to": "/badms/operations",
        "required_permission": "badms.audit.view",
        "sort_order": 90,
    },
    {
        "code": "badms.storage.review",
        "label": "Review Storage Requests",
        "icon": "Database",
        "to": "/badms/operations",
        "required_permission": "badms.storage_extension.review_department",
        "sort_order": 100,
    },
]
