"""Drafting and submitting an application (UC-PMS-001; BR-PMS-014..017; PMS-AFR-044, 045)."""
from __future__ import annotations

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError
from modules.pms.domain import state_machine as sm
from modules.pms.domain import validation
from modules.pms.domain.errors import InvalidInput, RuleViolation
from modules.pms.models import (
    Application,
    ApplicationVersion,
    DocumentVersion,
    PanelAttorney,
    ReferenceCounter,
)
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors import scoping
from modules.pms.services import audit, notifications
from modules.pms.services.base import (
    lock,
    move,
    now,
    owner_only,
    require,
    ruled,
)

P_CREATE = "pms.application.create"
P_UPDATE = "pms.application.update"
CONTENT = ("title", "abstract", "description", "claims", "domain_code")
EDITABLE = (*CONTENT, "preferred_attorney_user_id")


def _clean(fields: dict) -> dict:
    out = {k: fields[k] for k in EDITABLE if k in fields}
    for k in CONTENT:
        if k in out:
            out[k] = (out[k] or "").strip()
    validation.check_lengths(out)
    preferred = out.get("preferred_attorney_user_id")
    if preferred is not None and not PanelAttorney.objects.filter(
            user_id=preferred, valid_to__isnull=True).exists():
        raise RuleViolation("A preferred attorney must be on the approved panel "
                            "(BR-PMS-045). Choose one from the list.",
                            code="preference_not_on_panel")
    return out


@ruled
def create_draft(*, actor, fields: dict) -> Application:
    require(actor, P_CREATE)
    clean = _clean(fields)
    with transaction.atomic():
        app = Application.objects.create(applicant_user_id=actor.user_id, **clean)
        audit.record(actor, "application.created", application=app, obj=app, to=sm.DRAFT)
    return app


@ruled
def update(*, actor, pk: int, fields: dict) -> Application:
    """Edit a draft, or an application being revised (BR-PMS-087 as ruled: B6)."""
    require(actor, P_UPDATE)
    clean = _clean(fields)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        owner_only(actor, app)
        if app.status not in sm.APPLICANT_EDITABLE:
            raise ConflictError(f"An application that is {app.status.replace('_', ' ')} "
                                f"cannot be edited.", code="not_editable")
        changed = [k for k, v in clean.items() if getattr(app, k) != v]
        for k in changed:
            setattr(app, k, clean[k])
        if changed:
            app.save(update_fields=[*changed, "updated_at"])
            audit.record(actor, "application.edited", application=app, obj=app,
                         details={"fields": sorted(changed)})
    return app


def current_document_count(app: Application) -> int:
    return DocumentVersion.objects.filter(document__application=app, is_current=True).count()


def require_complete(app: Application) -> None:
    """BR-PMS-017: every required field, an inventor and a document, or a list of what is not."""
    spec = policy_selector.current()
    missing = validation.missing_fields(
        {k: getattr(app, k) for k in CONTENT}, inventors=app.inventors.count(),
        documents=current_document_count(app), domain_codes=spec.domain_codes)
    if missing:
        raise InvalidInput("Before submitting, add: " + ", ".join(missing) + ".",
                           code="incomplete")


def next_reference(year: int) -> str:
    """PMS-AFR-044: PMS-<year>-<number>, numbered under a lock so two submissions never share."""
    try:
        with transaction.atomic():
            ReferenceCounter.objects.create(year=year)
    except IntegrityError:
        pass
    counter = ReferenceCounter.objects.select_for_update().get(year=year)
    counter.last += 1
    counter.save(update_fields=["last"])
    return f"PMS-{year}-{counter.last:05d}"


def snapshot(app: Application, actor) -> None:
    """PMS-AFR-071: the content exactly as submitted, kept for every version."""
    ApplicationVersion.objects.create(
        application=app, version=app.version, title=app.title, abstract=app.abstract,
        description=app.description, claims=app.claims, domain_code=app.domain_code,
        created_by_user_id=actor.user_id)


def notify_office(spec, topic: str, key: str, subject: str, body: str) -> None:
    notifications.enqueue_many(topic=topic, key=key, recipients=[spec.pcc_contact_user_id],
                               subject=subject, body=body)


@ruled
def submit(*, actor, pk: int) -> Application:
    require(actor, P_CREATE)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        owner_only(actor, app)
        sm.APPLICATION.resolve(app.status, "submit", sm.APPLICANT)
        require_complete(app)
        stamp = now()
        app.reference = next_reference(stamp.year)
        app.version, app.submitted_at = 1, stamp
        move(app, "submit", sm.APPLICANT, actor,
             extra_fields=("reference", "version", "submitted_at"))
        snapshot(app, actor)
        notifications.enqueue(
            topic="application.submitted", dedupe_key=f"submitted:{app.pk}:1",
            recipient_user_id=app.applicant_user_id,
            subject=f"Application {app.reference} submitted",
            body=f"Your patent application '{app.title}' was submitted as {app.reference}. "
                 f"PCC_ADMIN will assign it to a Director for review.")
        notify_office(policy_selector.current(), "application.submitted",
                      f"submitted-office:{app.pk}:1",
                      f"New application {app.reference}",
                      f"Application {app.reference} is waiting for a Director to be assigned.")
    return app
