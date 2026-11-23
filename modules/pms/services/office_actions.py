"""Responding to an office action (UC-PMS-015, 029; BR-PMS-065, 066, 146)."""
from __future__ import annotations

from datetime import date

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.pms.domain import office_actions as oa
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import OfficeAction, OfficeActionExtension
from modules.pms.selectors import scoping
from modules.pms.services import audit, notifications
from modules.pms.services.base import (
    accepted_attorney_only,
    lock_application,
    move_record,
    now,
    owner_only,
    require,
    ruled,
    today,
)

P_PREPARE = "pms.office_action_response.create"
P_RECORD = "pms.office_action_response.update"
P_APPROVE = "pms.office_action_response.approve"


def _locked(actor, office_action_id: int):
    found = scoping.office_actions_for(actor).filter(pk=office_action_id).first()
    if found is None:
        raise NotFoundError("No such office action.", code="not_found")
    app = lock_application(found.application_id)
    return app, OfficeAction.objects.select_for_update().get(pk=office_action_id)


def _deadline(row: OfficeAction) -> date | None:
    return oa.current_deadline(row.response_due_on, [e.new_due_on for e in row.extensions.all()])


@ruled
def prepare_response(*, actor, office_action_id: int, draft: str) -> OfficeAction:
    require(actor, P_PREPARE)
    text = (draft or "").strip()
    if not text or len(text) > 100_000:
        raise InvalidInput("Write the draft response (at most 100,000 characters).",
                           code="draft_required")
    with transaction.atomic():
        app, row = _locked(actor, office_action_id)
        accepted_attorney_only(actor, app)
        event = "prepare_for_applicant" if row.requires_applicant_review else "prepare_ready"
        row.draft_response = text
        move_record(sm.OFFICE_ACTION, row, event, sm.ATTORNEY, actor, application=app,
                    extra_fields=("draft_response",))
        if row.requires_applicant_review:
            notifications.enqueue(
                topic="office_action.review", dedupe_key=f"oa.review:{row.pk}",
                recipient_user_id=app.applicant_user_id,
                subject=f"Approve the office-action response for {app.reference}",
                body="Your attorney prepared a response that needs your approval. Open "
                     "My Applications to review and approve it.")
    return row


@ruled
def approve_response(*, actor, office_action_id: int) -> OfficeAction:
    """UC-PMS-029: approval is the only outcome the spec defines for the applicant."""
    require(actor, P_APPROVE)
    with transaction.atomic():
        app, row = _locked(actor, office_action_id)
        owner_only(actor, app)
        row.approved_by_user_id, row.approved_at = actor.user_id, now()
        move_record(sm.OFFICE_ACTION, row, "applicant_approve", sm.APPLICANT, actor,
                    application=app, extra_fields=("approved_by_user_id", "approved_at"))
        attorney = app.attorney_assignments.filter(status=sm.ACCEPTED).first()
        notifications.enqueue_many(
            topic="office_action.approved", key=f"oa.approved:{row.pk}",
            recipients=[getattr(attorney, "attorney_user_id", None)],
            subject=f"Response approved: {app.reference}",
            body="The applicant approved the office-action response; you can submit it.")
    return row


@ruled
def record_submission(*, actor, office_action_id: int, submitted_on: date,
                      reference: str) -> OfficeAction:
    require(actor, P_RECORD)
    ref = (reference or "").strip()
    if not ref or len(ref) > 200:
        raise InvalidInput("Give the patent office's submission reference.",
                           code="reference_required")
    with transaction.atomic():
        app, row = _locked(actor, office_action_id)
        accepted_attorney_only(actor, app)
        sm.OFFICE_ACTION.resolve(row.status, "submit", sm.ATTORNEY)
        oa.check_submission(submitted_on, _deadline(row), today())
        row.submitted_on, row.submission_reference = submitted_on, ref
        move_record(sm.OFFICE_ACTION, row, "submit", sm.ATTORNEY, actor, application=app,
                    extra_fields=("submitted_on", "submission_reference"))
        notifications.enqueue(
            topic="office_action.submitted", dedupe_key=f"oa.submitted:{row.pk}",
            recipient_user_id=app.applicant_user_id,
            subject=f"Office-action response submitted: {app.reference}",
            body=f"The response was submitted on {submitted_on.isoformat()} ({ref}).")
    return row


@ruled
def record_extension(*, actor, office_action_id: int, new_due_on: date,
                     reason: str) -> OfficeAction:
    require(actor, P_RECORD)
    with transaction.atomic():
        app, row = _locked(actor, office_action_id)
        accepted_attorney_only(actor, app)
        if row.status == sm.RESPONSE_SUBMITTED:
            raise ConflictError("The response is already submitted.", code="already_submitted")
        current = _deadline(row)
        text = oa.check_extension(new_due_on, current, reason)
        ext = OfficeActionExtension.objects.create(office_action=row, previous_due_on=current,
                                                   new_due_on=new_due_on, reason=text,
                                                   recorded_by_user_id=actor.user_id)
        audit.record(actor, "office_action.extension", application=app, obj=row,
                     details={"extension_id": ext.pk, "new_due_on": new_due_on.isoformat()})
    return row
