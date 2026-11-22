"""Policy services: changes supersede the active row, so the history is kept (R1-08)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.patents.models import PatentPolicy


def supersede_policy(**fields) -> PatentPolicy:
    """Insert a new active policy and end the current one. Existing content is never edited."""
    with transaction.atomic():
        current = PatentPolicy.objects.select_for_update().filter(is_active=True).first()
        new = PatentPolicy.objects.create(is_active=True, **fields)
        if current is not None:
            current.effective_to = timezone.now()
            current.is_active = False
            current.superseded_by = new
            current.save(update_fields=["effective_to", "is_active", "superseded_by", "updated_at"])
        return new
