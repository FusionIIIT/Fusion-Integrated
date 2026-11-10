"""Read queries for the admin area."""
from __future__ import annotations

from django.utils import timezone

from modules.vms.models import (
    AuditLog,
    BlacklistEntry,
    BlacklistVersion,
    Gate,
    SafeListEntry,
    Zone,
)


def blacklist_versions():
    return BlacklistVersion.objects.order_by("-version")


def blacklist_entries(version_id=None):
    qs = BlacklistEntry.objects.order_by("-id")
    return qs.filter(version_id=version_id) if version_id is not None else qs


def safelist(active_only: bool = False):
    qs = SafeListEntry.objects.order_by("-id")
    if active_only:
        qs = qs.filter(revoked_at__isnull=True, expires_at__gt=timezone.now())
    return qs


def zones():
    return Zone.objects.order_by("name")


def gates():
    return Gate.objects.select_related("zone").order_by("name")


def audit_rows(*, actor_user_id=None, action=None, entity_type=None, entity_id=None,
               date_from=None, date_to=None):
    """Filtered, newest first. `action` matches exactly or as a prefix ending in `.`."""
    qs = AuditLog.objects.order_by("-id")
    if actor_user_id is not None:
        qs = qs.filter(actor_user_id=actor_user_id)
    if action:
        qs = qs.filter(action__startswith=action) if action.endswith(".") \
            else qs.filter(action=action)
    if entity_type:
        qs = qs.filter(entity_type=entity_type.lower())
    if entity_id:
        qs = qs.filter(entity_id=str(entity_id))
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lt=date_to)
    return qs
