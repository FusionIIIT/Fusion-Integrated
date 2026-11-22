"""Blacklist and safe-list management services."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.vms.models import BlacklistEntry


@transaction.atomic
def add_to_blacklist(
    name: str,
    id_document_type: str,
    id_document_number: str,
    phone: str,
    reason: str,
) -> BlacklistEntry:
    """Admin adds an individual to the blacklist (UC-006, BR-051)."""
    return BlacklistEntry.objects.create(
        name=name.strip(),
        id_document_type=id_document_type.strip(),
        id_document_number=id_document_number.strip().upper(),
        phone=phone.strip(),
        reason=reason.strip(),
        status="ACTIVE",
    )


@transaction.atomic
def safe_list_entry(
    entry_id: int,
    hours: int,
    admin_id: int,
    reason: str,
) -> BlacklistEntry:
    """Admin grants a temporary safe-list exemption (UC-006, BR-118, BR-119)."""
    if hours <= 0 or hours > 72:
        raise ValueError("Safe-list duration must be between 1 and 72 hours.")

    now = timezone.now()
    entry = BlacklistEntry.objects.select_for_update().get(pk=entry_id)
    entry.status = "SAFE_LISTED"
    entry.safe_list_until = now + timezone.timedelta(hours=hours)
    entry.safe_list_reason = reason.strip()
    entry.safe_listed_by_id = admin_id
    fields = ["status", "safe_list_until", "safe_list_reason", "safe_listed_by_id", "updated_at"]
    entry.save(update_fields=fields)
    return entry


@transaction.atomic
def deactivate_blacklist_entry(entry_id: int) -> BlacklistEntry:
    """Deactivate a blacklist entry."""
    entry = BlacklistEntry.objects.select_for_update().get(pk=entry_id)
    entry.status = "INACTIVE"
    entry.save(update_fields=["status", "updated_at"])
    return entry
