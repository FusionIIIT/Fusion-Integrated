"""The venue list in effect now (BR-GYM-020)."""
from __future__ import annotations

from django.utils import timezone

from modules.gymkhana.models import Venue, VenueList


def current_venue_list(now=None) -> VenueList | None:
    now = now or timezone.now()
    return (VenueList.objects.filter(effective_from__lte=now)
            .order_by("-effective_from").first())


def current_venue_names(now=None) -> list[str]:
    current = current_venue_list(now)
    if current is None:
        return []
    return list(Venue.objects.filter(venue_list=current)
                .order_by("name").values_list("name", flat=True))
