"""Office actions and responses services (CW-PMS-03, BW-PMS-12, 13, BR-PMS-065, 066, 146)."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from modules.pms.domain.constants import (
    ACTOR_APPLICANT,
    ACTOR_ATTORNEY,
    STATUS_APPLICANT_APPROVED,
    STATUS_AWAITING_APPLICANT_APPROVAL,
    STATUS_OFFICE_ACTION_RECORDED,
    STATUS_RESPONSE_READY,
    STATUS_RESPONSE_SUBMITTED,
)
from modules.pms.domain.exceptions import DeadlineExpiredError, ValidationError
from modules.pms.domain.state_machine import validate_transition
from modules.pms.models import (
    DeadlineTracking,
    ExtensionRequest,
    OfficeAction,
    OfficeActionResponse,
    PatentApplication,
)
from modules.pms.services.audit import record_audit_event


@transaction.atomic
def record_office_action(
    application: PatentApplication,
    attorney_user_id: int,
    action_number: str,
    issue_date: datetime.date,
    response_deadline: datetime.date,
    action_type: str,
    description: str,
) -> OfficeAction:
    """Record an official communication from patent office (UC-PMS-014, BW-PMS-12, 13)."""
    validate_transition(application.status, STATUS_OFFICE_ACTION_RECORDED, ACTOR_ATTORNEY)

    prev_status = application.status
    application.status = STATUS_OFFICE_ACTION_RECORDED
    application.save()

    oa = OfficeAction.objects.create(
        application=application,
        action_number=action_number.strip(),
        issue_date=issue_date,
        response_deadline=response_deadline,
        action_type=action_type.strip(),
        description=description.strip(),
        recorded_by_user_id=attorney_user_id,
    )

    # Schedule deadline
    due_datetime = timezone.make_aware(
        datetime.datetime.combine(response_deadline, datetime.time(23, 59, 59))
    )
    DeadlineTracking.objects.create(
        application=application,
        deadline_type="office_action",
        due_date=due_datetime,
    )

    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="record_office_action",
        previous_state=prev_status,
        new_state=STATUS_OFFICE_ACTION_RECORDED,
        details={"action_number": action_number, "deadline": str(response_deadline)},
    )

    return oa


@transaction.atomic
def prepare_office_action_response(
    office_action: OfficeAction,
    attorney_user_id: int,
    draft_text: str,
    requires_applicant_approval: bool = True,
) -> OfficeActionResponse:
    """Attorney drafts office action response (UC-PMS-015, BW-PMS-12, 13, BR-PMS-146)."""
    application = office_action.application
    prev_status = application.status

    target_status = (
        STATUS_AWAITING_APPLICANT_APPROVAL if requires_applicant_approval else STATUS_RESPONSE_READY
    )

    validate_transition(application.status, target_status, ACTOR_ATTORNEY)
    application.status = target_status
    application.save()

    resp = OfficeActionResponse.objects.create(
        office_action=office_action,
        attorney_user_id=attorney_user_id,
        draft_text=draft_text.strip(),
        requires_applicant_approval=requires_applicant_approval,
    )

    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="prepare_office_action_response",
        previous_state=prev_status,
        new_state=target_status,
        details={"requires_applicant_approval": requires_applicant_approval},
    )

    return resp


@transaction.atomic
def approve_office_action_response(
    response: OfficeActionResponse,
    applicant_user_id: int,
) -> OfficeActionResponse:
    """Applicant approves draft response when review needed (UC-PMS-029, BW-PMS-12)."""
    application = response.office_action.application
    prev_status = application.status

    validate_transition(application.status, STATUS_APPLICANT_APPROVED, ACTOR_APPLICANT)
    application.status = STATUS_APPLICANT_APPROVED
    application.save()

    response.applicant_approved = True
    response.applicant_approved_at = timezone.now()
    response.save()

    record_audit_event(
        application=application,
        user_id=applicant_user_id,
        actor_role=ACTOR_APPLICANT,
        action_type="approve_office_action_response",
        previous_state=prev_status,
        new_state=STATUS_APPLICANT_APPROVED,
    )

    return response


@transaction.atomic
def submit_office_action_response(
    response: OfficeActionResponse,
    attorney_user_id: int,
    submission_details: str = "",
) -> OfficeActionResponse:
    """Attorney records submission of office-action response (UC-PMS-015, BW-PMS-12, 13)."""
    office_action = response.office_action
    application = office_action.application

    # Check deadline
    if timezone.now().date() > office_action.response_deadline:
        raise DeadlineExpiredError(
            f"Response deadline {office_action.response_deadline} has passed.",
            rule_id="BR-PMS-065",
        )

    # Check applicant approval if required
    if response.requires_applicant_approval and not response.applicant_approved:
        raise ValidationError(
            "Applicant review and approval is required before submitting response.",
            rule_id="BR-PMS-146",
        )

    prev_status = application.status
    validate_transition(application.status, STATUS_RESPONSE_SUBMITTED, ACTOR_ATTORNEY)

    application.status = STATUS_RESPONSE_SUBMITTED
    application.save()

    response.submitted_at = timezone.now()
    response.submission_details = submission_details.strip()
    response.save()

    office_action.status = "response_submitted"
    office_action.save()

    record_audit_event(
        application=application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="submit_office_action_response",
        previous_state=prev_status,
        new_state=STATUS_RESPONSE_SUBMITTED,
        details={"submission_details": submission_details.strip()},
    )

    return response


@transaction.atomic
def request_extension(
    office_action: OfficeAction,
    attorney_user_id: int,
    extension_days: int,
    reason: str,
) -> ExtensionRequest:
    """File extension request for an office action (UC-PMS-015 alternative flow)."""
    if extension_days <= 0:
        raise ValidationError("Extension days must be greater than zero.")

    new_deadline = office_action.response_deadline + datetime.timedelta(days=extension_days)
    ext = ExtensionRequest.objects.create(
        office_action=office_action,
        attorney_user_id=attorney_user_id,
        requested_days=extension_days,
        reason=reason.strip(),
        new_deadline=new_deadline,
        is_granted=True,
    )

    office_action.response_deadline = new_deadline
    office_action.save()

    record_audit_event(
        application=office_action.application,
        user_id=attorney_user_id,
        actor_role=ACTOR_ATTORNEY,
        action_type="request_extension",
        details={"extended_days": extension_days, "new_deadline": str(new_deadline)},
    )

    return ext
