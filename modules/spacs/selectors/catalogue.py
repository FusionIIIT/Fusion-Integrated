"""Selectors for scholarship and award catalogue entries."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.spacs.models import SchemeCatalogue, SchemePolicyVersion


def visible_catalogue_entries(principal) -> QuerySet[SchemeCatalogue]:
    """Visible catalogue items.

    Staff with manage permission can see all items (draft, published, retired).
    Other authenticated users see only published entries.
    """
    qs = SchemeCatalogue.objects.prefetch_related("versions")
    if principal is not None and principal.has_permission("spacs.catalogue.manage"):
        return qs
    return qs.filter(status="published")


def get_catalogue_entry(scheme_id: int, principal) -> SchemeCatalogue | None:
    return visible_catalogue_entries(principal).filter(pk=scheme_id).first()


def visible_policy_versions(scheme_id: int, principal) -> QuerySet[SchemePolicyVersion]:
    qs = SchemePolicyVersion.objects.filter(scheme_id=scheme_id)
    if principal is not None and principal.has_permission("spacs.catalogue.manage"):
        return qs
    return qs.filter(status="published")
