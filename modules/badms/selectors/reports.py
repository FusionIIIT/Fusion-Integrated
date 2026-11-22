"""Read-only operational and compliance reports for BADMS."""

from __future__ import annotations

from typing import Any

from django.db.models import Count, Sum

from modules.badms.models import ArchivalRequest, BackupRecord, StorageExtensionRequest


def get_departmental_report(department_id: int) -> dict[str, Any]:
    archival_stats = (
        ArchivalRequest.objects.filter(department_id=department_id)
        .values("status")
        .annotate(total=Count("id"), total_bytes=Sum("file_size_bytes"))
    )
    extension_stats = (
        StorageExtensionRequest.objects.filter(department_id=department_id)
        .values("status")
        .annotate(total=Count("id"), total_requested_bytes=Sum("requested_bytes"))
    )
    return {
        "department_id": department_id,
        "archival_summary": list(archival_stats),
        "extension_summary": list(extension_stats),
    }


def get_backup_compliance_report() -> dict[str, Any]:
    total_backups = BackupRecord.objects.count()
    success_count = BackupRecord.objects.filter(status="success").count()
    failure_count = BackupRecord.objects.filter(status="failure").count()
    return {
        "total_backups": total_backups,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate_percent": round((success_count / total_backups * 100), 2)
        if total_backups > 0
        else 100.0,
    }


def get_security_audit_report() -> dict[str, Any]:
    """AFR-BA-061: Security audit report including unauthorized access attempts."""
    from modules.badms.models import AuditLog

    total_events = AuditLog.objects.count()
    failed_attempts = AuditLog.objects.filter(outcome="failure").count()
    return {
        "total_security_events": total_events,
        "unauthorized_access_attempts": failed_attempts,
    }
