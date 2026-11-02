"""PMS Office Action and Response Workflow service.

Enforces business rules BR-PMS-065, BR-PMS-066, BR-PMS-146, and Workflows BW-PMS-12, 13, CW-PMS-03.
"""

from __future__ import annotations

import datetime
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.errors import PreconditionNotMetError
from modules.pms.domain.state_machine import (
    PatentApplicationStatus,
    validate_transition,
)
from modules.pms.models import OfficeAction, PatentApplication
from modules.pms.services.audit import log_audit
from modules.pms.services.notifications import enqueue_notification


def record_office_action(
    *,
    application_id: int,
    attorney_user_id: int,
    action_type: str,
    issue_date: datetime.date,
    due_date: datetime.date,
    details: str,
    requires_applicant_review: bool = True,
) -> OfficeAction:
    """Record an official office action received from the patent office (UC-PMS-014, CFR-PMS-014)."""
    with transaction.atomic():
        app = PatentApplication.objects.select_for_update().get(pk=application_id)

        allowed_statuses = (
            PatentApplicationStatus.FILED.value,
            PatentApplicationStatus.RESPONSE_SUBMITTED.value,
        )
        if app.status not in allowed_statuses:
            raise PreconditionNotMetError(
                f"Office action can only be recorded for filed applications, not '{app.status}'."
            )

        validate_transition(
            app.status, PatentApplicationStatus.OFFICE_ACTION_RECORDED, actor_role="Attorney"
        )
        prev_status = app.status

        app.status = PatentApplicationStatus.OFFICE_ACTION_RECORDED.value
        app.save(update_fields=["status", "updated_at"])

        oa = OfficeAction.objects.create(
            application=app,
            action_type=action_type.strip(),
            issue_date=issue_date,
            due_date=due_date,
            details=details.strip(),
            status="recorded",
            requires_applicant_review=requires_applicant_review,
        )

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="office_action_recorded",
            from_state=prev_status,
            to_state=app.status,
            details={"oa_id": oa.id, "action_type": action_type, "due_date": str(due_date)},
        )

        enqueue_notification(
            topic="office_action.recorded",
            dedupe_key=f"pms:oa:rec:{oa.id}",
            subject=f"PMS: Office Action Received ({app.application_no})",
            body=f"Patent Office issued an office action ({action_type}) for '{app.title}'. Due Date: {due_date}.",
            recipient_user_id=app.applicant_user_id,
        )

    return oa


def draft_office_action_response(
    *,
    office_action_id: int,
    attorney_user_id: int,
    draft_response: str,
) -> OfficeAction:
    """Prepare a draft response to an office action (UC-PMS-015, CFR-PMS-014)."""
    if not draft_response or not draft_response.strip():
        raise PreconditionNotMetError("Draft response text is required.")

    with transaction.atomic():
        oa = OfficeAction.objects.select_for_update().get(pk=office_action_id)
        app = oa.application

        target_status = (
            PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL
            if oa.requires_applicant_review
            else PatentApplicationStatus.RESPONSE_READY
        )
        validate_transition(app.status, target_status, actor_role="Attorney")
        prev_status = app.status

        oa.draft_response = draft_response.strip()
        oa.status = (
            "awaiting_applicant_approval" if oa.requires_applicant_review else "response_ready"
        )
        oa.save()

        app.status = target_status.value
        app.save(update_fields=["status", "updated_at"])

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="office_action_response_drafted",
            from_state=prev_status,
            to_state=app.status,
            details={"oa_id": oa.id, "requires_review": oa.requires_applicant_review},
        )

        if oa.requires_applicant_review:
            enqueue_notification(
                topic="office_action.response_ready",
                dedupe_key=f"pms:oa:await_review:{oa.id}",
                subject=f"PMS: Review Required for Office Action Response ({app.application_no})",
                body=f"Draft response for office action on '{app.title}' is ready for your review and approval.",
                recipient_user_id=app.applicant_user_id,
            )

    return oa


def approve_office_action_response(
    *,
    office_action_id: int,
    applicant_user_id: int,
) -> OfficeAction:
    """Applicant approves the draft office action response (UC-PMS-029, BR-PMS-146)."""
    with transaction.atomic():
        oa = OfficeAction.objects.select_for_update().get(pk=office_action_id)
        app = oa.application

        if app.applicant_user_id != applicant_user_id:
            raise PreconditionNotMetError(
                "Only the applicant can review and approve this response."
            )

        if app.status != PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL.value:
            raise PreconditionNotMetError("Response is not awaiting applicant approval.")

        validate_transition(
            app.status, PatentApplicationStatus.APPLICANT_APPROVED, actor_role="Applicant"
        )
        prev_status = app.status

        oa.applicant_approved = True
        oa.status = "applicant_approved"
        oa.save(update_fields=["applicant_approved", "status", "updated_at"])

        app.status = PatentApplicationStatus.APPLICANT_APPROVED.value
        app.save(update_fields=["status", "updated_at"])

        log_audit(
            application=app,
            actor_user_id=applicant_user_id,
            action_type="office_action_applicant_approved",
            from_state=prev_status,
            to_state=app.status,
            details={"oa_id": oa.id},
        )

        enqueue_notification(
            topic="office_action.applicant_approved",
            dedupe_key=f"pms:oa:approved:{oa.id}",
            subject=f"PMS: Office Action Response Approved ({app.application_no})",
            body=f"Applicant has approved the draft response for '{app.title}'. Ready for submission.",
            recipient_user_id=app.assigned_attorney_user_id,
        )

    return oa


def submit_office_action_response(
    *,
    office_action_id: int,
    attorney_user_id: int,
    submission_details: str,
) -> OfficeAction:
    """Finalize and submit response externally, recording status in PMS (UC-PMS-015, BR-PMS-065)."""
    with transaction.atomic():
        oa = OfficeAction.objects.select_for_update().get(pk=office_action_id)
        app = oa.application

        allowed_statuses = (
            PatentApplicationStatus.APPLICANT_APPROVED.value,
            PatentApplicationStatus.RESPONSE_READY.value,
        )
        if app.status not in allowed_statuses:
            raise PreconditionNotMetError(
                f"Cannot submit response in status '{app.status}'. Must be Applicant Approved or Response Ready."
            )

        validate_transition(
            app.status, PatentApplicationStatus.RESPONSE_SUBMITTED, actor_role="Attorney"
        )
        prev_status = app.status

        now = timezone.now()
        oa.status = "response_submitted"
        oa.response_submitted_date = now.date()
        oa.submission_details = submission_details.strip()
        oa.save()

        app.status = PatentApplicationStatus.RESPONSE_SUBMITTED.value
        app.save(update_fields=["status", "updated_at"])

        log_audit(
            application=app,
            actor_user_id=attorney_user_id,
            action_type="office_action_response_submitted",
            from_state=prev_status,
            to_state=app.status,
            details={"oa_id": oa.id, "submission_details": submission_details},
        )

        enqueue_notification(
            topic="office_action.response_submitted",
            dedupe_key=f"pms:oa:sub:{oa.id}",
            subject=f"PMS: Office Action Response Submitted ({app.application_no})",
            body=f"Response for office action on '{app.title}' has been officially submitted.",
            recipient_user_id=app.applicant_user_id,
        )

    return oa


def request_office_action_extension(
    *,
    office_action_id: int,
    attorney_user_id: int,
    extension_months: int = 1,
) -> OfficeAction:
    """File extension request for additional time to respond (UC-PMS-015)."""
    with transaction.atomic():
        oa = OfficeAction.objects.select_for_update().get(pk=office_action_id)
        oa.extension_months += extension_months
        oa.due_date = oa.due_date + timedelta(days=30 * extension_months)
        oa.save(update_fields=["extension_months", "due_date", "updated_at"])

        log_audit(
            application=oa.application,
            actor_user_id=attorney_user_id,
            action_type="office_action_extension_requested",
            details={
                "oa_id": oa.id,
                "extension_months": extension_months,
                "new_due_date": str(oa.due_date),
            },
        )

    return oa
