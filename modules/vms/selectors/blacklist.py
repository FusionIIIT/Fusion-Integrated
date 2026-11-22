"""Read-only selectors for blacklist and safe-list entries."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.vms.domain.blacklist import BlacklistMatchCandidate
from modules.vms.models import BlacklistEntry


def list_blacklist_entries(status: str | None = None) -> QuerySet[BlacklistEntry]:
    qs = BlacklistEntry.objects.all()
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


def get_active_blacklist_candidates() -> list[BlacklistMatchCandidate]:
    """Load candidates for pure domain blacklist evaluation."""
    entries = BlacklistEntry.objects.exclude(status="INACTIVE")
    return [
        BlacklistMatchCandidate(
            id_document_type=e.id_document_type,
            id_document_number=e.id_document_number,
            name=e.name,
            phone=e.phone,
            status=e.status,
            safe_list_until=e.safe_list_until,
        )
        for e in entries
    ]
