import logging

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

log = logging.getLogger("fusion.badms.scoping")


def resolve_actor_department(actor, default: str = "") -> str:
    """Resolve an actor's department from actor attributes, active role, or directory profile."""
    dept = getattr(actor, "department", "") or ""
    if dept:
        return dept
    active_role = getattr(actor, "active_role", "") or ""
    if active_role.startswith("HOD (") and active_role.endswith(")"):
        return active_role[5:-1]
    user_id = getattr(actor, "user_id", None)
    if user_id:
        try:
            from modules.directory import contracts as directory

            user_dto = directory.get_users([user_id]).get(user_id)
            if user_dto and user_dto.department:
                return user_dto.department
        except (AttributeError, KeyError, LookupError, ValueError, OSError) as exc:
            log.warning("badms.resolve_department_failed user=%s err=%s", user_id, exc)
    return default


def _is_admin(active_role: str, roles: tuple[str, ...] = ()) -> bool:
    admin_roles = {"SysAdmin", "acadadmin", "Super Admin", "Director"}
    return active_role in admin_roles or any(r in admin_roles for r in roles)


def _is_hod(active_role: str, roles: tuple[str, ...] = ()) -> bool:
    return (
        active_role == "HOD"
        or active_role.startswith("HOD (")
        or any(r == "HOD" or r.startswith("HOD (") for r in roles)
    )


def _get_actor_info(actor) -> tuple[int, str, str]:
    user_id = getattr(actor, "user_id", None) or 0
    active_role = getattr(actor, "active_role", "") or ""
    roles = tuple(getattr(actor, "roles", ()) or ())
    department = getattr(actor, "department", "") or ""

    if not department:
        if active_role.startswith("HOD (") and active_role.endswith(")"):
            department = active_role[5:-1]
        else:
            for r in roles:
                if r.startswith("HOD (") and r.endswith(")"):
                    department = r[5:-1]
                    break

    if not department and _is_hod(active_role, roles):
        department = resolve_actor_department(actor, default="")
    return user_id, active_role, department


def scope_backup_records(actor) -> QuerySet[BackupRecord]:
    user_id, active_role, _ = _get_actor_info(actor)
    roles = tuple(getattr(actor, "roles", ()) or ())
    if not user_id:
        return BackupRecord.objects.none()
    if _is_admin(active_role, roles) or active_role == "IT Security" or "IT Security" in roles:
        return BackupRecord.objects.all().order_by("-created_at")
    return BackupRecord.objects.filter(triggered_by_user_id=user_id).order_by("-created_at")


def scope_backup_schedules(actor) -> QuerySet[BackupSchedule]:
    user_id, _active_role, _ = _get_actor_info(actor)
    if not user_id:
        return BackupSchedule.objects.none()
    return BackupSchedule.objects.filter(is_active=True).order_by("-created_at")


def scope_archival_requests(actor) -> QuerySet[ArchivalRequest]:
    user_id, active_role, department = _get_actor_info(actor)
    roles = tuple(getattr(actor, "roles", ()) or ())
    if not user_id:
        return ArchivalRequest.objects.none()
    if _is_admin(active_role, roles) or active_role == "IT Security" or "IT Security" in roles:
        return ArchivalRequest.objects.all().order_by("-created_at")
    if _is_hod(active_role, roles):
        return ArchivalRequest.objects.filter(department=department).order_by("-created_at")
    return ArchivalRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def scope_storage_extensions(actor) -> QuerySet[StorageExtensionRequest]:
    user_id, active_role, department = _get_actor_info(actor)
    roles = tuple(getattr(actor, "roles", ()) or ())
    if not user_id:
        return StorageExtensionRequest.objects.none()
    if _is_admin(active_role, roles):
        return StorageExtensionRequest.objects.all().order_by("-created_at")
    if _is_hod(active_role, roles):
        return StorageExtensionRequest.objects.filter(department=department).order_by("-created_at")
    return StorageExtensionRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def scope_restoration_requests(actor) -> QuerySet[RestorationRequest]:
    user_id, active_role, _ = _get_actor_info(actor)
    roles = tuple(getattr(actor, "roles", ()) or ())
    if not user_id:
        return RestorationRequest.objects.none()
    if _is_admin(active_role, roles):
        return RestorationRequest.objects.all().order_by("-created_at")
    return RestorationRequest.objects.filter(requester_user_id=user_id).order_by("-created_at")


def scope_audit_events(actor) -> QuerySet[AuditEvent]:
    user_id, active_role, department = _get_actor_info(actor)
    roles = tuple(getattr(actor, "roles", ()) or ())
    if not user_id:
        return AuditEvent.objects.none()
    if _is_admin(active_role, roles) or active_role == "IT Security" or "IT Security" in roles:
        return AuditEvent.objects.all().order_by("-timestamp")
    if _is_hod(active_role, roles):
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
