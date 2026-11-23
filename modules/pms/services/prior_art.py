"""Prior-art search sessions and references (UC-PMS-004; PMS-AFR-141..149; BR-PMS-141)."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.pms.domain import documents as d
from modules.pms.domain import prior_art as pa
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import PriorArtReference, PriorArtSearch
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors import scoping
from modules.pms.services import audit
from modules.pms.services.base import lock, require, ruled

P_SEARCH = "pms.prior_art.create"
URLS = URLValidator(schemes=["http", "https"])


@ruled
def search(*, actor, query: str, application_id: int | None = None,
           classification_codes=None) -> dict:
    """Ranks only references the searcher may already see (blueprint S-2)."""
    require(actor, P_SEARCH)
    text = (query or "").strip()
    if not text or len(text) > 500:
        raise InvalidInput("Enter search terms (at most 500 characters).", code="query_required")
    codes = pa.check_classification(classification_codes or [])
    app = None
    if application_id is not None:
        app = scoping.applications_for(actor).filter(pk=application_id).first()
        if app is None:
            raise NotFoundError("No such application.", code="not_found")
    context = " ".join([app.title, app.abstract, app.claims]) if app else ""
    terms, suggestions = pa.optimise_keywords(text, context)
    domain = policy_selector.current().domain(app.domain_code) if app else None
    refs = list(scoping.prior_art_for(actor).order_by("-id")[:1000])
    ranked = pa.rank(terms, [pa.ReferenceText(r.pk, r.title, r.notes, r.identifier)
                             for r in refs])[:50]
    by_id = {r.pk: r for r in refs}
    session = PriorArtSearch.objects.create(
        actor_user_id=actor.user_id, application=app, query=text, keywords=terms,
        classification_codes=codes, result_reference_ids=[i for i, _ in ranked])
    audit.record(actor, "prior_art.searched", application=app, obj=session,
                 details={"results": len(ranked)})
    return {"search_id": session.pk, "terms": terms, "suggested_keywords": suggestions,
            "classification_codes": codes,
            "suggested_classifications": list(domain.ipc_classes) if domain else [],
            "sources": [{"code": c, "label": label, "status": pa.NOT_CONNECTED}
                        for c, label in pa.SOURCES],
            "results": [{"reference": by_id[i], "score": s} for i, s in ranked]}


@ruled
def attach(*, actor, pk: int, kind: str, title: str, identifier: str = "", url: str = "",
           source_name: str = "", notes: str = "",
           search_id: int | None = None) -> PriorArtReference:
    require(actor, P_SEARCH)
    if kind not in ("patent", "publication"):
        raise InvalidInput("Say whether the reference is a patent or a publication.",
                           code="invalid_kind")
    clean_title = (title or "").strip()
    if not clean_title or len(clean_title) > 500:
        raise InvalidInput("Give the reference's title.", code="title_required")
    link = (url or "").strip()
    if link:
        try:
            URLS(link)
        except ValidationError as exc:
            raise InvalidInput("The link must be a full http or https address.",
                               code="invalid_url") from exc
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        rel = scoping.relations(actor, app)
        if not rel & {d.APPLICANT, d.ATTORNEY} or app.status in sm.TERMINAL:
            raise PermissionDeniedError("Only the applicant or the assigned attorney can attach "
                                        "prior art to an active application.",
                                        code="attach_not_allowed")
        session = None
        if search_id is not None:
            session = PriorArtSearch.objects.filter(pk=search_id,
                                                    actor_user_id=actor.user_id).first()
            if session is None:
                raise NotFoundError("No such search.", code="not_found")
        try:
            with transaction.atomic():
                ref = PriorArtReference.objects.create(
                    application=app, kind=kind, title=clean_title,
                    identifier=(identifier or "").strip()[:120], url=link[:500],
                    source_name=(source_name or "").strip()[:120],
                    notes=(notes or "").strip()[:10_000], added_by_user_id=actor.user_id,
                    search=session)
        except IntegrityError as exc:
            raise ConflictError("That reference is already attached to this application.",
                                code="reference_exists") from exc
        audit.record(actor, "prior_art.attached", application=app, obj=ref)
    return ref
