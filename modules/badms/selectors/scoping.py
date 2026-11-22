from django.db.models import QuerySet

from modules.badms.domain.departments import department_code
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRun,
    RestoreRequest,
    StorageExtensionRequest,
)

SYSTEM_ROLES = {"SysAdmin", "Super Admin"}


def _role(actor) -> str:
    return getattr(actor, "active_role", None) or ""


def _department_role(actor) -> str:
    role = _role(actor)
    if role.startswith("HOD (") and role.endswith(")"):
        return department_code(role[5:-1])
    return ""


def _requester_or_department(queryset: QuerySet, actor) -> QuerySet:
    department = _department_role(actor)
    if _role(actor) in SYSTEM_ROLES:
        return queryset
    own_id = getattr(actor, "user_id", None)
    scoped = queryset.none()
    if own_id is not None:
        scoped = queryset.filter(requester_user_id=own_id)
    if department:
        scoped = scoped | queryset.filter(department_code__iexact=department)
    return scoped.distinct()


def archival_requests_for(actor) -> QuerySet[ArchivalRequest]:
    if _role(actor) == "IT Security Team":
        return ArchivalRequest.objects.filter(
            classification=ArchivalRequest.Classification.SENSITIVE,
        )
    return _requester_or_department(ArchivalRequest.objects.all(), actor)


def restoration_requests_for(actor) -> QuerySet[RestoreRequest]:
    qs = RestoreRequest.objects.select_related("archive")
    if _role(actor) in SYSTEM_ROLES:
        return qs
    own_id = getattr(actor, "user_id", None)
    return qs.filter(requester_user_id=own_id) if own_id is not None else qs.none()


def storage_extensions_for(actor) -> QuerySet[StorageExtensionRequest]:
    return _requester_or_department(StorageExtensionRequest.objects.all(), actor)


def backups_for(actor) -> QuerySet[BackupRun]:
    if _role(actor) in {"SysAdmin", "Super Admin"}:
        return BackupRun.objects.all()
    own_id = getattr(actor, "user_id", None)
    return (
        BackupRun.objects.filter(started_by_user_id=own_id)
        if own_id is not None
        else BackupRun.objects.none()
    )


def audit_events_for(actor) -> QuerySet[AuditEvent]:
    if _role(actor) in {"SysAdmin", "IT Security Team", "Super Admin"}:
        return AuditEvent.objects.all()
    department = _department_role(actor)
    if department:
        return AuditEvent.objects.filter(
            details__department_code__iexact=department,
        )
    return AuditEvent.objects.none()
