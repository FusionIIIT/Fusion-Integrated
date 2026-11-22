"""Cross-module public contracts for BADMS (Backup and Database Archive Management System).

Adheres strictly to Fusion Architectural Decision Records:
- Plural getters only (accepts list[str] of user_ids or entity_ids)
- Safe, read-only dictionary structures returned
- No leaky ORM model objects exposed across module boundaries
"""

from typing import Any, Dict, List, Optional
from django.utils import timezone


def get_user_storage_quotas(user_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Return storage quota and current usage status for a list of user IDs.
    
    Ref: CFR-BA-012, AFR-BA-045.
    """
    from .models import StorageQuota
    
    records = StorageQuota.objects.filter(user_id__in=user_ids)
    quota_map = {}
    for q in records:
        quota_map[q.user_id] = {
            "user_id": q.user_id,
            "department_id": q.department_id,
            "allocated_mb": float(q.allocated_storage_mb),
            "used_mb": float(q.used_storage_mb),
            "usage_percent": q.usage_percentage,
            "threshold_percent": float(q.threshold_percent),
            "is_alerted": q.is_alerted,
        }
    
    # Fill in default fallback for users not yet seeded
    for uid in user_ids:
        if uid not in quota_map:
            quota_map[uid] = {
                "user_id": uid,
                "department_id": "DEFAULT",
                "allocated_mb": 1024.0,
                "used_mb": 0.0,
                "usage_percent": 0.0,
                "threshold_percent": 80.0,
                "is_alerted": False,
            }
    return quota_map


def get_archival_status_summary(user_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Return active and completed secure archival requests for a list of user IDs.
    
    Ref: CFR-BA-009, AFR-BA-035.
    """
    from .models import ArchivalRequest
    
    requests = ArchivalRequest.objects.filter(requester_user_id__in=user_ids).order_by("-created_at")
    summary: Dict[str, List[Dict[str, Any]]] = {uid: [] for uid in user_ids}
    
    for req in requests:
        summary[req.requester_user_id].append({
            "request_number": req.request_number,
            "file_name": req.file_name,
            "file_size_mb": float(req.file_size_mb),
            "initial_classification": req.initial_classification,
            "authoritative_classification": req.authoritative_classification or "PENDING",
            "status": req.status,
            "created_at": req.created_at.isoformat(),
        })
    return summary


def get_latest_backup_status() -> Dict[str, Any]:
    """Return the most recent database backup status and operational health summary.
    
    Ref: CFR-BA-004, AFR-BA-017, AFR-BA-018.
    """
    from .models import BackupRecord
    
    last_backup = BackupRecord.objects.order_by("-started_at").first()
    if not last_backup:
        return {
            "has_backups": False,
            "status": "NONE",
            "last_backup_time": None,
            "checksum": None,
            "consecutive_failures": 0,
        }
    
    recent_backups = list(BackupRecord.objects.order_by("-started_at")[:5])
    consecutive_failures = 0
    for b in recent_backups:
        if b.status == "FAILED":
            consecutive_failures += 1
        else:
            break
            
    return {
        "has_backups": True,
        "backup_type": last_backup.backup_type,
        "dataset_name": last_backup.dataset_name,
        "status": last_backup.status,
        "started_at": last_backup.started_at.isoformat(),
        "completed_at": last_backup.completed_at.isoformat() if last_backup.completed_at else None,
        "checksum_sha256": last_backup.checksum_sha256,
        "file_size_bytes": last_backup.file_size_bytes,
        "consecutive_failures": consecutive_failures,
        "escalated_to_director": last_backup.escalated_to_director,
    }
