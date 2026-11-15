"""Scoping and querying for BADMS models."""
from __future__ import annotations
from django.db.models import QuerySet
from modules.badms.models import (
    BackupOperation,
    BackupSchedule,
    SecureArchivalRequest,
    DataRestorationRequest,
    StorageExtensionRequest,
    BadmsAuditLog,
)


def visible_archival_requests(actor) -> QuerySet[SecureArchivalRequest]:
    """Scoping: SysAdmin/IT Security sees all; HoD sees department; User sees own."""
    qs = SecureArchivalRequest.objects.all()
    if actor.has_permission("badms.archival.classify_authoritative") or actor.has_permission("badms.security.manage"):
        return qs
    if actor.has_permission("badms.department.review"):
        dept = getattr(actor, "department", "")
        if dept:
            return qs.filter(department=dept)
        return qs
    return qs.filter(user_id=actor.user_id)


def visible_storage_extensions(actor) -> QuerySet[StorageExtensionRequest]:
    """Scoping for storage extensions."""
    qs = StorageExtensionRequest.objects.all()
    if actor.has_permission("badms.department.review"):
        dept = getattr(actor, "department", "")
        if dept:
            return qs.filter(department=dept)
        return qs
    return qs.filter(user_id=actor.user_id)


def visible_restorations(actor) -> QuerySet[DataRestorationRequest]:
    """Scoping for restoration requests."""
    qs = DataRestorationRequest.objects.all()
    if actor.has_permission("badms.restoration.approve_sensitive"):
        return qs
    return qs.filter(user_id=actor.user_id)
