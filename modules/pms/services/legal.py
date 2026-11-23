"""The assigned attorney's legal work (UC-PMS-012, 033; BR-PMS-046; PMS-AFR-082..089)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.pms.domain import state_machine as sm
from modules.pms.domain import validation
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import Assessment, LegalAdvice, LegalRequest
from modules.pms.selectors import scoping
from modules.pms.services import audit, notifications
from modules.pms.services.base import (
    accepted_attorney_only,
    lock,
    lock_application,
    now,
    require,
    ruled,
)

P_ASSESS = "pms.assessment.create"
P_REQUEST = "pms.legal_request.create"
P_ADVICE = "pms.legal_advice.create"
ACTIVE = frozenset({sm.ATTORNEY_ASSIGNED, sm.FILED, sm.GRANTED})
ASSESSMENT_FIELDS = ("analysis", "novelty", "non_obviousness", "utility", "recommendation")


def _case(actor, pk: int):
    app = lock(scoping.applications_for(actor), pk)
    accepted_attorney_only(actor, app)
    if app.status not in ACTIVE:
        raise ConflictError("Legal work is recorded while the case is active with you.",
                            code="case_not_active")
    return app


def _text(value, label: str, limit: int = 50_000) -> str:
    text = (value or "").strip()
    if len(text) > limit:
        raise InvalidInput(f"Keep the {label} under {limit:,} characters.", code="too_long")
    return text


@ruled
def save_assessment(*, actor, pk: int, fields: dict,
                    assessment_id: int | None = None) -> Assessment:
    """A draft may be saved incomplete; only finalizing enforces BR-PMS-046."""
    require(actor, P_ASSESS)
    clean = {k: _text(fields.get(k), k.replace("_", "-")) for k in ASSESSMENT_FIELDS[:-1]}
    rec = fields.get("recommendation") or ""
    if rec and rec not in validation.RECOMMENDATIONS:
        raise InvalidInput("Choose File Patent, Do Not File or Needs Amendment.",
                           code="recommendation_required")
    with transaction.atomic():
        app = _case(actor, pk)
        if assessment_id is None:
            row = Assessment(application=app, attorney_user_id=actor.user_id)
        else:
            row = (Assessment.objects.select_for_update()
                   .filter(pk=assessment_id, application=app).first())
            if row is None:
                raise NotFoundError("No such assessment.", code="not_found")
            if row.status == "final":
                raise ConflictError("A final opinion cannot be changed; record a new one.",
                                    code="assessment_final")
        for k, v in clean.items():
            setattr(row, k, v)
        row.recommendation = rec
        row.save()
        audit.record(actor, "assessment.saved", application=app, obj=row, to="draft")
    return row


@ruled
def finalize_assessment(*, actor, assessment_id: int) -> Assessment:
    require(actor, P_ASSESS)
    row = Assessment.objects.filter(pk=assessment_id,
                                    application__in=scoping.applications_for(actor)).first()
    if row is None:
        raise NotFoundError("No such assessment.", code="not_found")
    with transaction.atomic():
        app = lock_application(row.application_id)
        accepted_attorney_only(actor, app)
        row = Assessment.objects.select_for_update().get(pk=assessment_id)
        if row.status == "final":
            raise ConflictError("This opinion is already final.", code="assessment_final")
        validation.check_opinion(**{k: getattr(row, k) for k in ASSESSMENT_FIELDS})
        row.status, row.finalized_at = "final", now()
        row.save(update_fields=["status", "finalized_at", "updated_at"])
        audit.record(actor, "assessment.finalized", application=app, obj=row, frm="draft",
                     to="final", details={"recommendation": row.recommendation})
        latest = app.review_cycles.order_by("-cycle_no").first()
        notifications.enqueue_many(
            topic="assessment.final", key=f"assessment:{row.pk}",
            recipients=[app.applicant_user_id, getattr(latest, "director_user_id", None)],
            subject=f"Patentability opinion recorded: {app.reference}",
            body=f"The attorney recorded a patentability opinion on {app.reference} "
                 f"recommending: {row.recommendation.replace('_', ' ')}.")
    return row


@ruled
def request(*, actor, pk: int, kind: str, message: str) -> LegalRequest:
    """PMS-AFR-086 / 087: recorded and sent to the applicant."""
    require(actor, P_REQUEST)
    if kind not in ("information", "extension"):
        raise InvalidInput("Request either information or an extension.", code="invalid_kind")
    text = _text(message, "request", 5000)
    if not text:
        raise InvalidInput("Say what you need.", code="message_required")
    with transaction.atomic():
        app = _case(actor, pk)
        row = LegalRequest.objects.create(application=app, attorney_user_id=actor.user_id,
                                          kind=kind, message=text)
        audit.record(actor, f"legal_request.{kind}", application=app, obj=row)
        notifications.enqueue(
            topic="legal.request", dedupe_key=f"legal.request:{row.pk}",
            recipient_user_id=app.applicant_user_id,
            subject=f"Your attorney asks about {app.reference}",
            body=f"Request for {kind}:\n\n{text}")
    return row


@ruled
def record_advice(*, actor, pk: int, advice: str) -> LegalAdvice:
    require(actor, P_ADVICE)
    text = _text(advice, "advice", 20_000)
    if not text:
        raise InvalidInput("Write the advice to record.", code="advice_required")
    with transaction.atomic():
        app = _case(actor, pk)
        row = LegalAdvice.objects.create(application=app, attorney_user_id=actor.user_id,
                                         stage=app.status, advice=text)
        audit.record(actor, "legal_advice.recorded", application=app, obj=row)
    return row
