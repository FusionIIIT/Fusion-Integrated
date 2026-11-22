"""Scoping and visibility selectors for Super Admin."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.superadmin.models import (
    AuditLogRecord,
    HistoricalArchiveRecord,
    RoleAssignmentRecord,
    SystemParameterPolicy,
    UserAccountRecord,
)


def _has_permission(principal, code: str) -> bool:
    checker = getattr(principal, "has_permission", None)
    return bool(checker and checker(code))


def is_superadmin(principal) -> bool:
    # Principal holds Super Admin permissions.
    return _has_permission(principal, "superadmin.user.view")


def visible_users(principal) -> QuerySet[UserAccountRecord]:
    # Scope user accounts. Out of scope returns empty queryset so detail is 404.
    if not principal:
        return UserAccountRecord.objects.none()
    if is_superadmin(principal):
        return UserAccountRecord.objects.all()
    user_id = getattr(principal, "user_id", None)
    if user_id is not None:
        return UserAccountRecord.objects.filter(user_id=user_id)
    return UserAccountRecord.objects.none()


def visible_roles(principal) -> QuerySet[RoleAssignmentRecord]:
    # Scope role assignments.
    if not principal:
        return RoleAssignmentRecord.objects.none()
    if is_superadmin(principal):
        return RoleAssignmentRecord.objects.all()
    user_id = getattr(principal, "user_id", None)
    if user_id is not None:
        return RoleAssignmentRecord.objects.filter(user_id=user_id)
    return RoleAssignmentRecord.objects.none()


def visible_archives(principal) -> QuerySet[HistoricalArchiveRecord]:
    # Archived records are strictly read-only and restricted to Super Admin.
    if is_superadmin(principal):
        return HistoricalArchiveRecord.objects.all()
    return HistoricalArchiveRecord.objects.none()


def visible_audit_logs(principal) -> QuerySet[AuditLogRecord]:
    # Audit log inspection is restricted to Super Admin and IT Head.
    if _has_permission(principal, "superadmin.audit_log.view"):
        return AuditLogRecord.objects.all()
    return AuditLogRecord.objects.none()


def visible_parameters(principal) -> QuerySet[SystemParameterPolicy]:
    # System parameters visible to authenticated Super Admin.
    if is_superadmin(principal):
        return SystemParameterPolicy.objects.filter(is_active=True)
    return SystemParameterPolicy.objects.none()


def get_scoped_or_404(model_class, **kwargs):
    from core.api.exceptions import NotFoundError

    obj = model_class.objects.filter(**kwargs).first()
    if not obj:
        raise NotFoundError(f"{model_class.__name__} not found.", code="not_found")
    return obj
