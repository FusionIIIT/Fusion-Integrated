"""Office action services: tracking, drafting responses, applicant approvals.

Enforces BW-PMS-12..13, BR-PMS-065..066, BR-PMS-138, BR-PMS-142, BR-PMS-146.
"""
from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.patents.models import OfficeActionRecord
from modules.patents.selectors import scoping


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
        return OfficeActionRecord.objects.create(
            application=app,
            action_code=action_code,
            issuing_authority=issuing_authority,
            issued_date=issued_date,
            response_deadline=response_deadline,
            requires_applicant_review=requires_applicant_review,
            status="RECORDED",
        )


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

        oa.response_summary = response_summary
        if oa.requires_applicant_review:
            oa.status = "AWAITING_APPLICANT"
        else:
            oa.status = "RESPONSE_READY"
        oa.save()
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

        oa.status = "RESPONSE_READY"
        oa.save()
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

        if oa.status != "RESPONSE_READY":
            raise ConflictError("Office action response is not ready for submission.")

        oa.status = "SUBMITTED"
        oa.submitted_at = timezone.now()
        oa.save()
    return oa
