from django.db.models import QuerySet

from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    RestorationRequest,
    SecurityPolicy,
    StorageExtensionRequest,
    UserStorageQuota,
)


def _get_actor_info(actor) -> tuple[int, str, str]:
    user_id = getattr(actor, "user_id", None) or 0
    active_role = getattr(actor, "active_role", "") or ""
    department = getattr(actor, "department", "") or ""
    if not department and active_role.startswith("HOD (") and active_role.endswith(")"):
        department = active_role[5:-1]
    return user_id, active_role, department


def _is_admin(active_role: str) -> bool:
    return active_role in {"SysAdmin", "acadadmin", "Super Admin", "Director"}


def _is_hod(active_role: str) -> bool:
    return active_role == "HOD" or active_role.startswith("HOD (")


def scope_backup_records(actor) -> QuerySet[BackupRecord]:
    user_id, active_role, _ = _get_actor_info(actor)
    if not user_id:
        return BackupRecord.objects.none()
    if _is_admin(active_role) or active_role == "IT Security":
        return BackupRecord.objects.all().order_by("-created_at")
    return BackupRecord.objects.filter(triggered_by_user_id=user_id).order_by("-created_at")


def scope_backup_schedules(actor) -> QuerySet[BackupSchedule]:
    user_id, _active_role, _ = _get_actor_info(actor)
    if not user_id:
        return BackupSchedule.objects.none()
    return BackupSchedule.objects.filter(is_active=True).order_by("-created_at")


def scope_archival_requests(actor) -> QuerySet[ArchivalRequest]:
    user_id, active_role, department = _get_actor_info(actor)
    if not user_id:
        return ArchivalRequest.objects.none()
    if _is_admin(active_role) or active_role == "IT Security":
        return ArchivalRequest.objects.all().order_by("-created_at")
    if _is_hod(active_role):
        return ArchivalRequest.objects.filter(department=department).order_by("-created_at")
    return ArchivalRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def scope_storage_extensions(actor) -> QuerySet[StorageExtensionRequest]:
    user_id, active_role, department = _get_actor_info(actor)
    if not user_id:
        return StorageExtensionRequest.objects.none()
    if _is_admin(active_role):
        return StorageExtensionRequest.objects.all().order_by("-created_at")
    if _is_hod(active_role):
        return StorageExtensionRequest.objects.filter(department=department).order_by("-created_at")
    return StorageExtensionRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def scope_restoration_requests(actor) -> QuerySet[RestorationRequest]:
    user_id, active_role, _ = _get_actor_info(actor)
    if not user_id:
        return RestorationRequest.objects.none()
    if _is_admin(active_role):
        return RestorationRequest.objects.all().order_by("-created_at")
    return RestorationRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def scope_audit_events(actor) -> QuerySet[AuditEvent]:
    user_id, active_role, department = _get_actor_info(actor)
    if not user_id:
        return AuditEvent.objects.none()
    if _is_admin(active_role) or active_role == "IT Security":
        return AuditEvent.objects.all().order_by("-timestamp")
    if _is_hod(active_role):
        return AuditEvent.objects.filter(department=department).order_by("-timestamp")
    return AuditEvent.objects.filter(actor_user_id=user_id).order_by("-timestamp")


def scope_security_policies(actor) -> QuerySet[SecurityPolicy]:
    user_id, _active_role, _ = _get_actor_info(actor)
    if not user_id:
        return SecurityPolicy.objects.none()
    return SecurityPolicy.objects.filter(is_active=True).order_by("-created_at")


def scope_user_storage_quotas(actor) -> QuerySet[UserStorageQuota]:
    user_id, active_role, _ = _get_actor_info(actor)
    if not user_id:
        return UserStorageQuota.objects.none()
    if _is_admin(active_role):
        return UserStorageQuota.objects.all().order_by("-last_calculated_at")
    return UserStorageQuota.objects.filter(user_id=user_id).order_by("-last_calculated_at")
