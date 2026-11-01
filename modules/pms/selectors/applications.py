"""Application queries, filtering and detail selectors."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from modules.pms.models import PatentApplication
from modules.pms.selectors.scoping import scoped_applications


def get_application_or_404(actor, application_id: int) -> PatentApplication:
    """Fetch an application within the actor's authorized scope, or raise 404."""
    qs = scoped_applications(actor).select_related("budget", "filing_record", "post_grant")
    return get_object_or_404(qs, id=application_id)


def list_applications_for_actor(
    actor,
    filters: dict[str, Any] | None = None,
    status: str | None = None,
    domain: str | None = None,
    search: str | None = None,
) -> QuerySet[PatentApplication]:
    """List applications for the current actor, applying optional status and domain filters."""
    qs = scoped_applications(actor)
    f = filters or {}
    st = status or f.get("status")
    dom = domain or f.get("domain")
    q_search = search or f.get("search")

    if st:
        qs = qs.filter(status=st)
    if dom:
        qs = qs.filter(domain__icontains=dom)
    if q_search:
        qs = qs.filter(title__icontains=q_search) | qs.filter(application_no__icontains=q_search)

    return qs.distinct()
