"""Seeding the venue list (BR-GYM-020): a new version each time, never an edit."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError
from modules.gymkhana.models import Venue, VenueList

MAX_NAME = 120


@transaction.atomic
def seed_venue_list(*, names: Sequence[str], effective_from: datetime | None = None,
                    created_by_label: str = "operator") -> VenueList:
    cleaned = []
    seen: set[str] = set()
    for raw in names:
        name = " ".join((raw or "").split())
        if not name:
            continue
        if len(name) > MAX_NAME:
            raise DomainError(f"Venue names can be at most {MAX_NAME} characters.",
                              code="venue_name_too_long")
        if name.casefold() not in seen:
            seen.add(name.casefold())
            cleaned.append(name)
    if not cleaned:
        raise DomainError("Give at least one venue name.", code="no_venues")
    effective_from = effective_from or timezone.now()
    if VenueList.objects.filter(effective_from=effective_from).exists():
        raise ConflictError("A venue list already takes effect at that moment.",
                            code="venue_list_exists")
    venue_list = VenueList.objects.create(effective_from=effective_from,
                                          created_by_label=created_by_label[:120])
    Venue.objects.bulk_create([Venue(venue_list=venue_list, name=n) for n in cleaned])
    return venue_list
