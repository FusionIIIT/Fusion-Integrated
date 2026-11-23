from django.db.models import Count

from modules.badms.selectors.scoping import (
    can_access_department,
    get_authorized_departments_for_actor,
    resolve_actor_department,
    scope_archival_requests,
    scope_audit_events,
    scope_backup_records,
    scope_backup_schedules,
    scope_restoration_requests,
    scope_security_policies,
    scope_storage_extensions,
    scope_user_storage_quotas,
    validate_department_scope,
)


def get_department_report(actor, department: str) -> dict:
    validate_department_scope(actor, department)
    archival_qs = scope_archival_requests(actor).filter(department=department)
    storage_qs = scope_storage_extensions(actor).filter(department=department)
    return {
        "department": department,
        "total_archival_requests": archival_qs.count(),
        "archival_by_status": dict(archival_qs.values_list("status").annotate(c=Count("id"))),
        "total_storage_extensions": storage_qs.count(),
        "storage_by_status": dict(storage_qs.values_list("status").annotate(c=Count("id"))),
    }


__all__ = [
    "can_access_department",
    "get_authorized_departments_for_actor",
    "get_department_report",
    "resolve_actor_department",
    "scope_archival_requests",
    "scope_audit_events",
    "scope_backup_records",
    "scope_backup_schedules",
    "scope_restoration_requests",
    "scope_security_policies",
    "scope_storage_extensions",
    "scope_user_storage_quotas",
    "validate_department_scope",
]
