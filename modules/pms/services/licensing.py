"""Licensing and technology-transfer requests (UC-PMS-020, 021; BR-PMS-088, 091, 139)."""
from __future__ import annotations

from datetime import date

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.pms.domain import licensing as lic
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import LicenseAgreement, LicensingRequest, NegotiationNote
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors import scoping
from modules.pms.services import audit, notifications
from modules.pms.services.base import lock, move_record, now, owner_only, require, ruled, today

P_CREATE = "pms.licensing_request.create"
P_REVIEW = "pms.licensing_request.review"


def _route(req: LicensingRequest, actor, actor_kind: str, app) -> bool:
    target = lic.route_target(policy_selector.current().licensing_route)
    if target is None:
        return False
    req.route_kind, req.routed_at = target.kind, now()
    req.routed_director_user_id = target.director_user_id
    req.committee_name = target.committee_name
    move_record(sm.LICENSING, req, "route", actor_kind, actor, application=app,
                extra_fields=("route_kind", "routed_at", "routed_director_user_id",
                              "committee_name"))
    notifications.enqueue_many(
        topic="licensing.routed", key=f"licensing.routed:{req.pk}",
        recipients=[target.director_user_id, policy_selector.current().pcc_contact_user_id],
        subject=f"Licensing request on {app.reference}",
        body=f"A {req.kind.replace('_', ' ')} request on {app.reference} was routed to "
             + (target.committee_name or "you") + ".")
    return True


@ruled
def submit(*, actor, pk: int, kind: str, summary: str) -> LicensingRequest:
    require(actor, P_CREATE)
    text = lic.check_request(kind, summary)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        owner_only(actor, app)
        if app.status == sm.DRAFT:
            raise ConflictError("Submit the patent application before requesting a licence "
                                "for it.", code="application_draft")
        req = LicensingRequest(application=app, applicant_user_id=actor.user_id, kind=kind,
                               summary=text)
        req.save()
        audit.record(actor, "licensing_request.submitted", application=app, obj=req,
                     to=sm.LICENSING_SUBMITTED)
        _route(req, actor, sm.SYSTEM, app)
    return req


def _locked(actor, request_id: int):
    found = scoping.licensing_for(actor).filter(pk=request_id).first()
    if found is None:
        raise NotFoundError("No such licensing request.", code="not_found")
    return found.application, LicensingRequest.objects.select_for_update().get(pk=request_id)


def _kind(actor) -> str:
    return sm.PCC_ADMIN if scoping.lane(actor) == scoping.ADMIN else sm.DIRECTOR


@ruled
def route(*, actor, request_id: int) -> LicensingRequest:
    require(actor, P_REVIEW)
    with transaction.atomic():
        app, req = _locked(actor, request_id)
        sm.LICENSING.resolve(req.status, "route", _kind(actor))
        if not _route(req, actor, _kind(actor), app):
            raise ConflictError("No licensing route is configured. Set one under Settings "
                                "first.", code="licensing_route_missing")
    return req


@ruled
def add_note(*, actor, request_id: int, note: str) -> NegotiationNote:
    require(actor, P_REVIEW)
    text = (note or "").strip()
    if not text or len(text) > 5000:
        raise InvalidInput("Write the negotiation note (at most 5,000 characters).",
                           code="note_required")
    with transaction.atomic():
        app, req = _locked(actor, request_id)
        move_record(sm.LICENSING, req, "add_note", _kind(actor), actor, application=app)
        return NegotiationNote.objects.create(request=req, author_user_id=actor.user_id,
                                              note=text)


@ruled
def record_agreement(*, actor, request_id: int, counterparty: str, signed_on: date,
                     terms_summary: str, financial_terms: str = "") -> LicenseAgreement:
    """PMS-AFR-162; the finance system is not connected, which is recorded (PMS-AFR-163)."""
    require(actor, P_REVIEW)
    party, terms = (counterparty or "").strip(), (terms_summary or "").strip()
    if not party or len(party) > 200:
        raise InvalidInput("Name the other party to the agreement.", code="party_required")
    if not terms:
        raise InvalidInput("Summarise the agreed terms.", code="terms_required")
    if signed_on > today():
        raise InvalidInput("The signing date cannot be in the future.", code="date_in_future")
    with transaction.atomic():
        app, req = _locked(actor, request_id)
        move_record(sm.LICENSING, req, "record_agreement", _kind(actor), actor,
                    application=app)
        agreement = LicenseAgreement.objects.create(
            request=req, counterparty=party, signed_on=signed_on, terms_summary=terms[:20_000],
            financial_terms=(financial_terms or "").strip()[:20_000],
            financial_sync=lic.NOT_SHARED, recorded_by_user_id=actor.user_id)
        notifications.enqueue(
            topic="licensing.agreement", dedupe_key=f"licensing.agreement:{req.pk}",
            recipient_user_id=req.applicant_user_id,
            subject=f"Agreement recorded on {app.reference}",
            body=f"A {req.kind.replace('_', ' ')} agreement with {party} was recorded.")
    return agreement
