"""PMS Prior Art Search and Attachment service.

Enforces CFR-PMS-017, BR-PMS-141, and UC-PMS-004.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction

from modules.pms.domain.errors import PreconditionNotMetError
from modules.pms.models import PatentApplication, PriorArtReference
from modules.pms.services.audit import log_audit


def search_prior_art(
    *,
    query: str,
    domain: str = "",
    actor_user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Simulated external prior-art search across patent databases (BR-PMS-141)."""
    # Logs search session for audit trail (CFR-PMS-017)
    log_audit(
        actor_user_id=actor_user_id,
        action_type="prior_art_search_executed",
        details={"query": query, "domain": domain},
    )

    # Return search results with relevance ranking
    return [
        {
            "reference_id": f"PAT-REF-{abs(hash(query)) % 10000:04d}",
            "source": "Indian Patent Database",
            "title": f"Novel methods in {query}",
            "authors": "A. Kumar et al.",
            "relevance": "high",
            "url": "https://ipindia.gov.in/patents",
        },
        {
            "reference_id": f"PUB-REF-{(abs(hash(query)) + 1) % 10000:04d}",
            "source": "IEEE Xplore",
            "title": f"Recent advances in {domain or query}",
            "authors": "R. Sharma et al.",
            "relevance": "medium",
            "url": "https://ieeexplore.ieee.org",
        },
    ]


def attach_prior_art(
    *,
    application_id: int,
    user_id: int,
    source: str,
    reference_id: str,
    title: str,
    authors: str = "",
    relevance: str = "high",
    notes: str = "",
) -> PriorArtReference:
    """Attach a selected prior-art reference to an application (UC-PMS-004, CFR-PMS-017)."""
    if not reference_id or not reference_id.strip():
        raise PreconditionNotMetError("Reference ID is required.")
    if not title or not title.strip():
        raise PreconditionNotMetError("Reference title is required.")

    with transaction.atomic():
        app = PatentApplication.objects.get(pk=application_id)
        ref = PriorArtReference.objects.create(
            application=app,
            source=source.strip(),
            reference_id=reference_id.strip(),
            title=title.strip(),
            authors=authors.strip(),
            relevance=relevance,
            notes=notes.strip(),
            attached_by_user_id=user_id,
        )

        log_audit(
            application=app,
            actor_user_id=user_id,
            action_type="prior_art_reference_attached",
            details={"reference_id": reference_id, "title": title},
        )

    return ref
