"""Catalogue and policy selectors for SPACS.

Enforces:
- CFR-SPACS-001 (Published Catalogue Access)
- BR-SPACS-014 (Published catalogue version is source of truth)
"""
from __future__ import annotations

from datetime import date
from django.db.models import QuerySet
from modules.spacs.models import CatalogueEntry, CataloguePolicyVersion


def get_published_catalogue() -> QuerySet[CatalogueEntry]:
    """Returns all active catalogue entries that have a published policy version."""
    return (
        CatalogueEntry.objects.filter(status="active", versions__is_published=True)
        .prefetch_related("versions")
        .distinct()
    )


def get_catalogue_entry_by_code(code: str) -> CatalogueEntry | None:
    return (
        CatalogueEntry.objects.filter(code=code)
        .prefetch_related("versions")
        .first()
    )


def get_effective_policy_version(
    catalogue_entry_id: int, as_of_date: date | None = None
) -> CataloguePolicyVersion | None:
    """Finds the published policy version effective on the specified date."""
    if as_of_date is None:
        as_of_date = date.today()

    return (
        CataloguePolicyVersion.objects.filter(
            catalogue_entry_id=catalogue_entry_id,
            is_published=True,
            effective_from__lte=as_of_date,
        )
        .filter(models_Q_effective_to(as_of_date))
        .order_by("-effective_from", "-id")
        .first()
    )


def models_Q_effective_to(as_of_date: date):
    from django.db.models import Q
    return Q(effective_to__isnull=True) | Q(effective_to__gte=as_of_date)
