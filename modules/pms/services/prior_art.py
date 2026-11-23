"""PMS Prior Art Search and Attachment service.

Enforces CFR-PMS-017, BR-PMS-141, and UC-PMS-004.
"""

from __future__ import annotations

from django.db import transaction

from modules.pms.domain.errors import ExternalServiceUnavailableError, PreconditionNotMetError
from modules.pms.models import PatentApplication, PriorArtReference
from modules.pms.services.audit import log_audit
from modules.pms.services.authorization import require_assigned_attorney


def search_prior_art(
    *,
    query: str,
    domain: str = "",
    actor_user_id: int | None = None,
) -> None:
    """Refuse searches until a supported external source is configured (UC-PMS-004)."""
    del query, domain
    # No search session is logged as successful when no source was queried.
    log_audit(
        actor_user_id=actor_user_id,
        action_type="prior_art_search_unavailable",
        details={"result": "not_queried"},
    )
    raise ExternalServiceUnavailableError(
        "Prior-art search is unavailable because no external search source is configured."
    )


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
        if app.applicant_user_id != user_id:
            require_assigned_attorney(app, user_id, require_accepted_assignment=True)
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
