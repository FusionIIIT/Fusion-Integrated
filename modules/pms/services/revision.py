"""Revise and resubmit (UC-PMS-005; BR-PMS-033..036, 038; PMS-AFR-070, 071)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.pms.domain import state_machine as sm
from modules.pms.domain import validation
from modules.pms.models import Application, DocumentVersion, RevisionResponse
from modules.pms.selectors import applications as app_selector
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors import scoping
from modules.pms.services import applications as drafting
from modules.pms.services import audit, notifications
from modules.pms.services.base import lock, move, owner_only, require, ruled, today

P_UPDATE = "pms.application.update"


def changed_since_last_submission(app: Application) -> bool:
    last = app.versions.order_by("-version").first()
    if last is None:
        return True
    if any(getattr(app, k) != getattr(last, k) for k in drafting.CONTENT):
        return True
    return DocumentVersion.objects.filter(document__application=app,
                                          uploaded_at__gt=last.created_at).exists()


def expire(app: Application, actor=None) -> None:
    """BR-PMS-038: the caller holds the lock and has seen the period end."""
    move(app, "expire", sm.SYSTEM, actor, details={"revision_due_on": str(app.revision_due_on)})
    notifications.enqueue(
        topic="application.expired", dedupe_key=f"expired:{app.pk}",
        recipient_user_id=app.applicant_user_id, subject=f"{app.reference} has expired",
        body=f"The 60-day period to resubmit {app.reference} ended on "
             f"{app.revision_due_on.isoformat()}, so the application has expired.")


@ruled
def resubmit(*, actor, pk: int, responses: dict) -> Application:
    require(actor, P_UPDATE)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        owner_only(actor, app)
        sm.APPLICATION.resolve(app.status, "resubmit", sm.APPLICANT)
        overdue = app.revision_due_on is not None and today() > app.revision_due_on
        if overdue:
            # UC-PMS-005 exception flow: the late attempt itself expires the application.
            expire(app, actor)
    if overdue:
        raise ConflictError("The 60-day period to resubmit has ended, so the application "
                            "has expired and the resubmission was not accepted.",
                            code="revision_period_over")
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        sm.APPLICATION.resolve(app.status, "resubmit", sm.APPLICANT)
        cleaned = validation.check_revision_responses(
            app_selector.feedback_keys(app), responses,
            changed=changed_since_last_submission(app))
        drafting.require_complete(app)
        app.version += 1
        app.revision_due_on = app.appeal_due_on = None
        move(app, "resubmit", sm.APPLICANT, actor, details={"version": app.version},
             extra_fields=("version", "revision_due_on", "appeal_due_on"))
        drafting.snapshot(app, actor)
        RevisionResponse.objects.bulk_create(
            RevisionResponse(application=app, version=app.version, feedback_key=k, response=v)
            for k, v in cleaned.items())
        audit.record(actor, "revision.responses", application=app, obj=app,
                     details={"keys": sorted(cleaned)})
        drafting.notify_office(policy_selector.current(), "application.resubmitted",
                               f"resubmitted:{app.pk}:{app.version}",
                               f"{app.reference} resubmitted",
                               f"Application {app.reference} was revised and resubmitted; "
                               f"assign a Director for a new review cycle.")
    return app
