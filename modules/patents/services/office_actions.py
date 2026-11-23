"""Office action services: tracking, drafting responses, applicant approvals."""
from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.patents.models import OfficeActionRecord
from modules.patents.selectors import scoping
from modules.patents.services import audit, notifications


def log_office_action(
    actor,
    application_id: int,
    action_code: str,
    issuing_authority: str,
    issued_date: datetime.date,
    response_deadline: datetime.date,
    requires_applicant_review: bool = False,
) -> OfficeActionRecord:
    """Log official office action received from external patent office."""
    scope = scoping.applications_for(actor)
    app = scope.filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Patent application not found.")

    with transaction.atomic():
        oa = OfficeActionRecord.objects.create(
            application=app,
            action_code=action_code,
            issuing_authority=issuing_authority,
            issued_date=issued_date,
            response_deadline=response_deadline,
            requires_applicant_review=requires_applicant_review,
            status="RECORDED",
        )
        audit.record(
            actor, "office_action_recorded", app, new_state=oa.status,
            action_code=action_code, issuing_authority=issuing_authority,
            response_deadline=response_deadline.isoformat(),
        )
    notifications.notify(
        [app.user_id, app.assigned_attorney_id], app, "Office action received",
        f"{issuing_authority} issued {action_code}; respond by {response_deadline.isoformat()}.",
    )
    return oa


def draft_response(
    actor,
    office_action_id: int,
    response_summary: str,
) -> OfficeActionRecord:
    """Attorney drafts response summary to an office action."""
    if not scoping.is_attorney(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Attorney authority required to draft response.")

    with transaction.atomic():
        oa = OfficeActionRecord.objects.select_for_update().filter(pk=office_action_id).first()
        if oa is None:
            raise NotFoundError("Office action not found.")

        previous = oa.status
        oa.response_summary = response_summary
        if oa.requires_applicant_review:
            oa.status = "AWAITING_APPLICANT"
        else:
            oa.status = "RESPONSE_READY"
        oa.save()
        audit.record(
            actor, "office_action_response_drafted", oa.application, previous, oa.status,
            office_action_id=oa.id,
        )
    if oa.status == "AWAITING_APPLICANT":
        notifications.notify(
            [oa.application.user_id], oa.application, "Response awaiting your approval",
            "Review and approve the drafted office-action response.",
        )
    return oa


def applicant_approve_response(
    actor,
    office_action_id: int,
) -> OfficeActionRecord:
    """Applicant approves drafted office action response (BR-PMS-146)."""
    with transaction.atomic():
        oa = OfficeActionRecord.objects.select_for_update().filter(pk=office_action_id).first()
        if oa is None:
            raise NotFoundError("Office action not found.")

        # Ensure actor is applicant on this application
        user_id = getattr(actor, "user_id", None)
        if user_id != oa.application.user_id and not scoping.is_pcc_admin(actor):
            raise PermissionDeniedError("Only the applicant may approve response.")

        if oa.status != "AWAITING_APPLICANT":
            raise ConflictError("Office action is not awaiting applicant approval.")

        oa.status = "APPLICANT_APPROVED"
        oa.save()
        audit.record(
            actor, "office_action_response_approved", oa.application,
            "AWAITING_APPLICANT", oa.status, office_action_id=oa.id,
        )
    return oa


def submit_response(
    actor,
    office_action_id: int,
) -> OfficeActionRecord:
    """Attorney submits response to patent office."""
    if not scoping.is_attorney(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Attorney authority required to submit response.")

    with transaction.atomic():
        oa = OfficeActionRecord.objects.select_for_update().filter(pk=office_action_id).first()
        if oa is None:
            raise NotFoundError("Office action not found.")

        if oa.status not in ("RESPONSE_READY", "APPLICANT_APPROVED"):
            raise ConflictError("Office action response is not ready for submission.")

        previous = oa.status
        oa.status = "SUBMITTED"
        oa.submitted_at = timezone.now()
        oa.save()
        audit.record(
            actor, "office_action_response_submitted", oa.application, previous, oa.status,
            office_action_id=oa.id,
        )
    return oa
