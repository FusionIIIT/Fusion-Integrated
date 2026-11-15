"""All writes to a patent application. Every move goes through one checker,
records an audit event, and raises domain errors (never DRF errors)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.patents import models as m
from modules.patents.domain import workflow as wf
from modules.patents.selectors import visible


def _event(app: m.Application, action: str, actor: int | None, frm: str, to: str, detail: str = ""):
    m.ApplicationEvent.objects.create(application=app, action=action, actor_user_id=actor,
                                      from_state=frm, to_state=to, detail=detail)


def _notify(app: m.Application, actor: int | None, kind: str, message: str) -> None:
    """Tell every party on the file except whoever just acted."""
    parties = {app.applicant_user_id, app.director_user_id, app.attorney_user_id}
    for user_id in parties - {None, actor}:
        m.Notification.objects.create(recipient_user_id=user_id, application=app,
                                      kind=kind, message=message)


def _move(app: m.Application, actor: int | None, action: str, to: str, detail: str = "") -> None:
    frm = app.status
    app.status = to
    app.save(update_fields=["status"])
    _event(app, action, actor, frm, to, detail)
    _notify(app, actor, "status", f"{app.application_no}: now {wf.LABELS.get(to, to)}.")


def _add_business_days(start: date, days: int) -> date:
    d = start
    while days:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days -= 1
    return d


def _need_status(app: m.Application, allowed, action: str) -> None:
    if app.status not in allowed:
        raise ConflictError(f"'{action}' is not allowed while the application is "
                            f"{wf.LABELS.get(app.status, app.status)}.", code="invalid_state")


def _owner(principal, app: m.Application) -> None:
    if principal.user_id != app.applicant_user_id:
        raise PermissionDeniedError("Only the applicant may do this.", code="forbidden")


def _director(principal, app: m.Application) -> None:
    if principal.user_id != app.director_user_id:
        raise PermissionDeniedError("Only the assigned Director may do this.", code="forbidden")


def _attorney(principal, app: m.Application) -> None:
    if principal.user_id != app.attorney_user_id or app.attorney_status != "accepted":
        raise PermissionDeniedError("Only the accepting Attorney may do this.", code="forbidden")


def _text(data: dict, name: str, required: bool = False) -> str:
    value = str(data.get(name) or "").strip()
    if required and not value:
        raise BadRequestError(f"{name} is required.", code="validation",
                              details=[{"field": name, "message": "This field is required."}])
    return value


# -- applicant ----------------------------------------------------------------
@transaction.atomic
def create_draft(principal, data: dict) -> m.Application:
    app = m.Application(
        application_no=f"PMS-{timezone.now():%Y}-{uuid.uuid4().hex[:8].upper()}",
        title=_text(data, "title", required=True),
        domain=_text(data, "domain"), abstract=_text(data, "abstract"),
        description=_text(data, "description"), claims=_text(data, "claims"),
        applicant_user_id=principal.user_id,
    )
    app.save()
    _event(app, "draft.create", principal.user_id, "", wf.DRAFT)
    set_inventors(principal, app, data.get("inventors") or [])
    return app


@transaction.atomic
def set_inventors(principal, app: m.Application, rows: list[dict]) -> m.Application:
    """Replace the inventor list. The applicant is the default sole inventor."""
    _owner(principal, app)
    _need_status(app, {wf.DRAFT, wf.NEEDS_REVISION, wf.REMANDED}, "inventors")
    if not rows:
        rows = [{"user_id": app.applicant_user_id, "name": "Applicant", "ownership_pct": 100,
                 "consent_given": True}]
    shares = []
    for row in rows:
        try:
            shares.append(float(row.get("ownership_pct", 0)))
        except (TypeError, ValueError):
            raise BadRequestError("Ownership must be a number.", code="validation") from None
    message = wf.validate_ownership(shares)
    if message:
        raise BadRequestError(message, code="validation")
    app.inventors.all().delete()
    for row in rows:
        m.Inventor.objects.create(
            application=app, user_id=row.get("user_id"), name=str(row.get("name", "")).strip(),
            email=str(row.get("email", "")).strip(),
            ownership_pct=Decimal(str(row.get("ownership_pct", 0))),
            consent_given=bool(row.get("consent_given", False)),
        )
    return app


@transaction.atomic
def upload_document(principal, app: m.Application, kind: str, upload, sensitivity: str):
    """Add a new version of a document (or start one). Content is hashed, never trusted."""
    _owner(principal, app)
    if sensitivity not in wf.SENSITIVITY_LEVELS:
        raise BadRequestError("Unknown sensitivity level.", code="validation")
    data = upload.read()
    message = wf.validate_document(getattr(upload, "content_type", ""), len(data))
    if message:
        raise BadRequestError(message, code="validation")
    if not data.startswith(b"%PDF"):
        raise BadRequestError("The file is not a valid PDF.", code="validation")
    doc, _ = m.Document.objects.get_or_create(
        application=app, kind=kind, defaults={"sensitivity": sensitivity})
    latest = doc.versions.order_by("-version_no").first()
    version = m.DocumentVersion.objects.create(
        document=doc, version_no=(latest.version_no + 1 if latest else 1),
        file_name=upload.name[:255], size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(), uploaded_by_user_id=principal.user_id,
    )
    _event(app, "document.upload", principal.user_id, app.status, app.status,
           f"{kind} v{version.version_no}")
    return version


def sweep_expired() -> int:
    """Expire rejected or revision-pending files past the 60-day window (BR-038)."""
    cutoff = timezone.now() - timedelta(days=wf.RESUBMISSION_DAYS)
    stale = m.Application.objects.filter(
        status__in=[wf.NEEDS_REVISION, wf.REJECTED], decision_at__lt=cutoff)
    count = 0
    for app in stale:
        _move(app, None, "expire", wf.EXPIRED, "Resubmission window closed.")
        count += 1
    return count


def summary(principal) -> dict:
    """Counts by status over what the caller may see (PS 2.3.18)."""
    from collections import Counter

    rows = Counter(visible(principal).values_list("status", flat=True))
    return {
        "total": sum(rows.values()),
        "by_status": {wf.LABELS.get(k, k): v for k, v in sorted(rows.items())},
        "approved_budget": str(
            visible(principal).filter(budget_status="approved")
            .aggregate(t=Sum("budget_total"))["t"] or 0),
    }


@transaction.atomic
def submit(principal, app: m.Application) -> m.Application:
    _owner(principal, app)
    _need_status(app, {wf.DRAFT}, "submit")
    for field in ("title", "abstract", "description", "claims"):
        if not getattr(app, field):
            raise BadRequestError(f"{field} is required before submission.", code="validation",
                                  details=[{"field": field, "message": "Required."}])
    app.submitted_at = timezone.now()
    app.save(update_fields=["submitted_at"])
    _move(app, principal.user_id, "submit", wf.SUBMITTED)
    return app


@transaction.atomic
def revise(principal, app: m.Application, response: str) -> m.Application:
    _owner(principal, app)
    _need_status(app, wf.REVISABLE, "revise")
    if app.decision_at and timezone.now() > app.decision_at + timedelta(days=wf.RESUBMISSION_DAYS):
        raise ConflictError("The resubmission period has passed.", code="expired")
    if not response.strip():
        raise BadRequestError("Describe how the revision addresses the feedback.",
                              code="validation")
    app.revision_count += 1
    app.save(update_fields=["revision_count"])
    _move(app, principal.user_id, "revise", wf.RESUBMITTED, response.strip())
    return app


@transaction.atomic
def withdraw(principal, app: m.Application, reason: str) -> m.Application:
    _owner(principal, app)
    _need_status(app, wf.WITHDRAWABLE, "withdraw")
    if not reason.strip():
        raise BadRequestError("A withdrawal reason is required.", code="validation")
    _move(app, principal.user_id, "withdraw", wf.WITHDRAWN, reason.strip())
    return app


@transaction.atomic
def appeal(principal, app: m.Application, grounds: str) -> m.Application:
    _owner(principal, app)
    _need_status(app, {wf.REJECTED}, "appeal")
    if app.decision_at and timezone.now() > app.decision_at + timedelta(days=wf.APPEAL_DAYS):
        raise ConflictError("The appeal period has passed.", code="expired")
    if not grounds.strip():
        raise BadRequestError("Grounds for appeal are required.", code="validation")
    _move(app, principal.user_id, "appeal", wf.APPEAL_SUBMITTED, grounds.strip())
    return app


# -- placement cell (PCC_ADMIN) ------------------------------------------------
@transaction.atomic
def assign_director(
    principal, app: m.Application, director_user_id: int | None
) -> m.Application:
    _need_status(app, {wf.SUBMITTED, wf.RESUBMITTED}, "assign-director")
    if not director_user_id:
        raise BadRequestError("A Director is required.", code="validation")
    if director_user_id == app.applicant_user_id:
        raise ConflictError("A Director may not review their own application.", code="conflict")
    app.director_user_id = director_user_id
    app.review_due_on = _add_business_days(timezone.now().date(), wf.REVIEW_BUSINESS_DAYS)
    app.save(update_fields=["director_user_id", "review_due_on"])
    _move(app, principal.user_id, "assign-director", wf.UNDER_REVIEW)
    return app


@transaction.atomic
def assign_attorney(
    principal, app: m.Application, attorney_user_id: int | None
) -> m.Application:
    _need_status(app, {wf.APPROVED}, "assign-attorney")
    if not attorney_user_id:
        raise BadRequestError("An Attorney is required.", code="validation")
    app.attorney_user_id = attorney_user_id
    app.attorney_status = "offered"
    app.save(update_fields=["attorney_user_id", "attorney_status"])
    _event(app, "assign-attorney", principal.user_id, app.status, app.status, "offered")
    return app


# -- director -----------------------------------------------------------------
@transaction.atomic
def decide_review(
    principal, app: m.Application, decision: str, justification: str
) -> m.Application:
    _director(principal, app)
    _need_status(app, {wf.UNDER_REVIEW}, "review")
    if decision not in wf.REVIEW_DECISIONS:
        raise BadRequestError(
            "Decision must be approve, reject or needs_revision.", code="validation"
        )
    if len(justification.strip()) < wf.JUSTIFICATION_MIN:
        raise BadRequestError(f"Justification must be at least {wf.JUSTIFICATION_MIN} characters.",
                              code="validation")
    app.decision_justification = justification.strip()
    app.decision_at = timezone.now()
    app.save(update_fields=["decision_justification", "decision_at"])
    _move(app, principal.user_id, f"review.{decision}", wf.REVIEW_DECISIONS[decision])
    return app


@transaction.atomic
def decide_appeal(principal, app: m.Application, outcome: str, reasoning: str) -> m.Application:
    _director(principal, app)
    _need_status(app, {wf.APPEAL_SUBMITTED}, "appeal-decision")
    if outcome not in wf.APPEAL_OUTCOMES:
        raise BadRequestError("Outcome must be uphold, remand or modify.", code="validation")
    _move(
        app, principal.user_id, f"appeal.{outcome}",
        wf.APPEAL_OUTCOMES[outcome], reasoning.strip(),
    )
    return app


# -- attorney -----------------------------------------------------------------
@transaction.atomic
def respond_assignment(principal, app: m.Application, accept: bool) -> m.Application:
    if principal.user_id != app.attorney_user_id or app.attorney_status != "offered":
        raise PermissionDeniedError("No pending assignment for you.", code="forbidden")
    if accept:
        app.attorney_status = "accepted"
        app.save(update_fields=["attorney_status"])
        _event(app, "attorney.accept", principal.user_id, app.status, app.status)
    else:
        app.attorney_user_id = None
        app.attorney_status = ""
        app.save(update_fields=["attorney_user_id", "attorney_status"])
        _event(app, "attorney.decline", principal.user_id, app.status, app.status)
    return app


@transaction.atomic
def record_opinion(principal, app: m.Application, recommendation: str, text: str) -> m.Application:
    _attorney(principal, app)
    if recommendation not in wf.RECOMMENDATIONS:
        raise BadRequestError("Choose a valid recommendation.", code="validation")
    app.opinion_recommendation, app.opinion_text = recommendation, text.strip()
    app.save(update_fields=["opinion_recommendation", "opinion_text"])
    _event(app, "opinion", principal.user_id, app.status, app.status, recommendation)
    return app


@transaction.atomic
def record_budget(
    principal, app: m.Application, filing: str, attorney: str, admin: str
) -> m.Application:
    _attorney(principal, app)
    _need_status(app, {wf.APPROVED}, "budget")
    try:
        total = sum(Decimal(str(v or 0)) for v in (filing, attorney, admin))
    except ArithmeticError:
        raise BadRequestError("Fees must be numbers.", code="validation") from None
    app.budget_total = total
    app.budget_status = "pending"
    app.save(update_fields=["budget_total", "budget_status"])
    _event(app, "budget.record", principal.user_id, app.status, app.status, str(total))
    return app


@transaction.atomic
def decide_budget(principal, app: m.Application, decision: str) -> m.Application:
    _director(principal, app)
    if app.status != wf.APPROVED or app.budget_status != "pending":
        raise ConflictError("No budget is waiting for a decision.", code="invalid_state")
    if decision not in ("approve", "reject"):
        raise BadRequestError("Decision must be approve or reject.", code="validation")
    app.budget_status = "approved" if decision == "approve" else "rejected"
    app.save(update_fields=["budget_status"])
    _event(app, f"budget.{decision}", principal.user_id, app.status, app.status)
    return app


@transaction.atomic
def record_filing(
    principal, app: m.Application, external_id: str, filing_date: date
) -> m.Application:
    _attorney(principal, app)
    _need_status(app, {wf.APPROVED}, "filing")
    if app.budget_status != "approved":
        raise ConflictError("The budget must be approved before filing.", code="invalid_state")
    app.external_filing_id, app.filing_date = external_id.strip(), filing_date
    app.save(update_fields=["external_filing_id", "filing_date"])
    _move(app, principal.user_id, "filing", wf.FILED, external_id.strip())
    return app
