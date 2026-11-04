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


def get_all_catalogue_entries() -> QuerySet[CatalogueEntry]:
    """Convener view: all entries regardless of status (UC-SPACS-010, UC-SPACS-014)."""
    return CatalogueEntry.objects.all().prefetch_related("versions")


def get_catalogue_entry_by_code(code: str) -> CatalogueEntry | None:
    return (
        CatalogueEntry.objects.filter(code=code)
        .prefetch_related("versions")
        .first()
    )


def get_catalogue_entry_by_pk(pk: int) -> CatalogueEntry | None:
    """Look up a catalogue entry by primary key (used by detail/version/retire views)."""
    return (
        CatalogueEntry.objects.filter(pk=pk)
        .prefetch_related("versions")
        .first()
    )


def get_policy_version_by_pk(version_pk: int) -> CataloguePolicyVersion | None:
    """Look up a policy version by primary key."""
    return CataloguePolicyVersion.objects.filter(pk=version_pk).first()


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
