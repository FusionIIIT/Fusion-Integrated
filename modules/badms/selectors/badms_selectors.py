"""Selectors (read queries) for BADMS.

Enforces scope and visibility constraints per BR-BA-020:
- Users only see their own requests and status.
- HoD access is strictly scoped to requests in the HoD's department.
- Administrators view records within their authorized operational domains.
"""

from typing import List, Optional
from django.db.models import QuerySet
from ..models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    EncryptedArchive,
    RestorationRequest,
    StorageExtensionRequest,
    StorageQuota,
)


def list_archival_requests_for_user(
    user_id: str,
    role: str,
    department_id: Optional[str] = None
) -> QuerySet[ArchivalRequest]:
    """Retrieve archival requests visible to the requesting actor.
    
    Ref: BR-BA-020, AFR-BA-035.
    """
    role_norm = role.strip().lower() if role else "student"
    
    if role_norm in {"sysadmin", "system_admin", "superadmin", "super_admin", "it_security"}:
        return ArchivalRequest.objects.all().order_by("-created_at")
    
    if "hod" in role_norm:
        if department_id:
            return ArchivalRequest.objects.filter(department_id=department_id).order_by("-created_at")
        return ArchivalRequest.objects.none()
        
    return ArchivalRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def get_archival_request_by_id(request_id: str) -> Optional[ArchivalRequest]:
    """Fetch archival request by ID."""
    try:
        return ArchivalRequest.objects.get(id=request_id)
    except (ArchivalRequest.DoesNotExist, ValueError):
        return None


def list_backup_history(limit: int = 50) -> QuerySet[BackupRecord]:
    """Retrieve backup records sorted by execution time.
    
    Ref: BR-BA-020, AFR-BA-017.
    """
    return BackupRecord.objects.all().order_by("-started_at")[:limit]


def get_consecutive_backup_failures() -> int:
    """Calculate the number of consecutive failed backups up to the latest one."""
    records = BackupRecord.objects.order_by("-started_at")[:10]
    failures = 0
    for r in records:
        if r.status == "FAILED":
            failures += 1
        else:
            break
    return failures


def list_backup_schedules(scope: Optional[str] = None) -> QuerySet[BackupSchedule]:
    """Retrieve configured backup schedules."""
    qs = BackupSchedule.objects.all().order_by("scope", "dataset_name")
    if scope:
        qs = qs.filter(scope=scope.upper())
    return qs


def get_user_storage_quota(user_id: str, department_id: str = "DEFAULT") -> StorageQuota:
    """Get or initialize user's storage quota record."""
    quota, _ = StorageQuota.objects.get_or_create(
        user_id=user_id,
        defaults={
            "department_id": department_id,
            "allocated_storage_mb": 1024.0,
            "used_storage_mb": 0.0,
            "threshold_percent": 80.0,
        }
    )
    return quota


def list_storage_extensions(
    user_id: str,
    role: str,
    department_id: Optional[str] = None
) -> QuerySet[StorageExtensionRequest]:
    """Retrieve storage extension requests visible to the actor."""
    role_norm = role.strip().lower() if role else "student"
    
    if role_norm in {"sysadmin", "superadmin"}:
        return StorageExtensionRequest.objects.all().order_by("-created_at")
    
    if "hod" in role_norm:
        if department_id:
            return StorageExtensionRequest.objects.filter(department_id=department_id).order_by("-created_at")
        return StorageExtensionRequest.objects.none()
        
    return StorageExtensionRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def list_restoration_requests(
    user_id: str,
    role: str,
    department_id: Optional[str] = None
) -> QuerySet[RestorationRequest]:
    """Retrieve data restoration requests visible to the actor."""
    role_norm = role.strip().lower() if role else "student"
    
    if role_norm in {"sysadmin", "superadmin"}:
        return RestorationRequest.objects.all().order_by("-created_at")
        
    if "hod" in role_norm:
        if department_id:
            return RestorationRequest.objects.filter(department_id=department_id).order_by("-created_at")
        return RestorationRequest.objects.none()
        
    return RestorationRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def list_audit_events(
    actor_role: str,
    department_id: Optional[str] = None,
    limit: int = 100
) -> QuerySet[AuditEvent]:
    """Retrieve audit events scoped by role authority (BR-BA-020)."""
    role_norm = actor_role.strip().lower() if actor_role else "student"
    
    if role_norm in {"sysadmin", "superadmin", "it_security"}:
        return AuditEvent.objects.all().order_by("-timestamp")[:limit]
        
    if "hod" in role_norm and department_id:
        return AuditEvent.objects.filter(department_id=department_id).order_by("-timestamp")[:limit]
        
    return AuditEvent.objects.none()
