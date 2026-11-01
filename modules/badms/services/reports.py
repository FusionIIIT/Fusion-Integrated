"""Compliance and retention reporting service for BADMS."""
from __future__ import annotations

from django.db.models import Count, Sum
from modules.badms.models import (
    ArchivalRequest,
    ArchiveClassification,
    ArchiveStatus,
    BackupExecution,
    BackupStatus,
    BadmsAuditLog,
    RestorationRequest,
    SpecialArchivalRecord,
    UserStorageQuota,
)


def get_retention_compliance_summary() -> dict:
    """Generate summary report for retention compliance and system health."""
    total_archives = ArchivalRequest.objects.count()

    classification_counts = {
        c[0]: ArchivalRequest.objects.filter(authoritative_classification=c[0]).count()
        for c in ArchiveClassification.choices
    }

    status_counts = {
        s[0]: ArchivalRequest.objects.filter(status=s[0]).count()
        for s in ArchiveStatus.choices
    }

    # Compliance calculation: items with policy applied or encrypted
    compliant_count = ArchivalRequest.objects.filter(
        status__in=[ArchiveStatus.POLICY_APPLIED, ArchiveStatus.ENCRYPTED_ARCHIVE_CREATED]
    ).count()

    compliance_rate = (
        round((compliant_count / total_archives) * 100, 1) if total_archives > 0 else 100.0
    )

    # Backups
    total_backups = BackupExecution.objects.count()
    successful_backups = BackupExecution.objects.filter(status=BackupStatus.COMPLETED).count()
    failed_backups = BackupExecution.objects.filter(status=BackupStatus.FAILED).count()
    last_backup = BackupExecution.objects.order_by("-started_at").first()
    consecutive_failures = last_backup.consecutive_failure_count if last_backup else 0

    # Restorations
    total_restorations = RestorationRequest.objects.count()
    completed_restorations = RestorationRequest.objects.filter(status="completed").count()
    pending_restorations = RestorationRequest.objects.filter(status="pending_approval").count()

    # Special Archival
    special_archives_count = SpecialArchivalRecord.objects.count()

    # Storage Quota Aggregation
    quota_aggs = UserStorageQuota.objects.aggregate(
        total_allocated=Sum("allocated_bytes"),
        total_used=Sum("used_bytes"),
    )
    total_allocated = quota_aggs["total_allocated"] or 0
    total_used = quota_aggs["total_used"] or 0
    total_remaining = max(0, total_allocated - total_used)

    return {
        "archives": {
            "total": total_archives,
            "compliant_count": compliant_count,
            "compliance_rate_percent": compliance_rate,
            "by_classification": classification_counts,
            "by_status": status_counts,
        },
        "backups": {
            "total": total_backups,
            "successful": successful_backups,
            "failed": failed_backups,
            "consecutive_failures": consecutive_failures,
            "last_backup_status": last_backup.status if last_backup else "none",
            "last_backup_at": last_backup.started_at.isoformat() if last_backup else None,
        },
        "restorations": {
            "total": total_restorations,
            "completed": completed_restorations,
            "pending": pending_restorations,
        },
        "special_archives": {
            "total": special_archives_count,
        },
        "storage": {
            "total_allocated_bytes": total_allocated,
            "total_used_bytes": total_used,
            "total_remaining_bytes": total_remaining,
            "utilization_percent": (
                round((total_used / total_allocated) * 100, 1) if total_allocated > 0 else 0.0
            ),
        },
        "audit_logs_count": BadmsAuditLog.objects.count(),
    }
