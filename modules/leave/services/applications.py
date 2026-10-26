"""All write operations and state transitions for leave applications (CW-EL-01 to CW-EL-05).

Raises DomainError subclasses, never raw DRF exceptions, ensuring service calls
remain safe, transactional, and decoupled from HTTP layers.
"""
from __future__ import annotations

import logging
from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain.rules import is_substitute_valid
from modules.leave.models import LeaveApplication, LeaveApplicationAudit

log = logging.getLogger("fusion.leave.applications")


def apply_leave(
    *,
    actor,
    category: str,
    start_date: date,
    end_date: date,
    reason: str = "",
    half_day_cl: bool = False,
    station_leave_details: dict | None = None,
    substitute_id: int | None = None,
) -> LeaveApplication:
    """Create and submit a new leave application (EL-UC-001, CW-EL-01).

    If a substitute is nominated, application enters 'awaiting_substitute' state (BR-EL-014/015).
    Otherwise, application is directly 'submitted'.
    """
    if actor is None or not getattr(actor, "user_id", None):
        raise PermissionDeniedError("Authenticated user required to apply for leave.")

    user_id = actor.user_id

    # Validate substitute self-nomination
    if substitute_id is not None and not is_substitute_valid(user_id, substitute_id):
        raise BadRequestError(
            "Substitute cannot be the applicant themselves.",
            code="invalid_substitute",
        )

    # Initial state based on substitute requirement
    initial_status = "awaiting_substitute" if substitute_id else "submitted"

    app = LeaveApplication(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        reason=reason or "",
        half_day_cl=half_day_cl,
        station_leave_details=station_leave_details or {},
        substitute_id=substitute_id,
        status=initial_status,
    )

    try:
        app.clean()
    except DjangoValidationError as exc:
        details = [
            {"field": field, "message": str(m)}
            for field, messages in getattr(exc, "message_dict", {}).items()
            for m in messages
        ]
        raise BadRequestError(
            message=str(exc.messages[0])
            if hasattr(exc, "messages") and exc.messages
            else "Invalid leave data.",
            code="validation_error",
            details=details,
        ) from exc

    with transaction.atomic():
        app.save()
        LeaveApplicationAudit.objects.create(
            application=app,
            status=app.status,
            reason="Application created and submitted.",
        )

    log.info(
        "Leave application #%s created by user %s in status '%s'",
        app.pk,
        user_id,
        app.status,
    )
    return app


def respond_substitute(
    *,
    actor,
    application_id: int,
    action: str,
    reason: str = "",
) -> LeaveApplication:
    """Substitute accepts or declines responsibility (EL-UC-002, BR-EL-015)."""
    if actor is None or not getattr(actor, "user_id", None):
        raise PermissionDeniedError("Authentication required.")

    try:
        app = LeaveApplication.objects.get(pk=application_id)
    except LeaveApplication.DoesNotExist as exc:
        raise NotFoundError(f"Leave application #{application_id} not found.") from exc

    if app.substitute_id != actor.user_id:
        raise PermissionDeniedError("You are not the nominated substitute for this application.")

    if app.status != "awaiting_substitute":
        raise ConflictError(
            f"Cannot respond: application #{app.pk} is in status '{app.status}', "
            "not awaiting substitute response."
        )

    if action not in ("accept", "decline"):
        raise BadRequestError("Action must be 'accept' or 'decline'.", code="invalid_action")

    with transaction.atomic():
        if action == "accept":
            app.status = "under_review"
            audit_msg = f"Substitute accepted responsibility: {reason}".strip()
        else:
            # Per BR-EL-015: decline returns to draft so applicant can re-nominate
            app.status = "draft"
            audit_msg = f"Substitute declined responsibility: {reason}".strip()

        app.save(update_fields=["status", "updated_at"])
        LeaveApplicationAudit.objects.create(
            application=app,
            status=app.status,
            reason=audit_msg,
        )

    log.info(
        "Leave application #%s substitute response '%s' by user %s",
        app.pk,
        action,
        actor.user_id,
    )
    return app


def review_application(
    *,
    actor,
    application_id: int,
    action: str,
    reason: str = "",
) -> LeaveApplication:
    """Recommending authority (Unit Head) reviews leave application (EL-UC-003, CW-EL-01)."""
    if actor is None:
        raise PermissionDeniedError("Authentication required.")

    if not actor.has_permission("leave.application.review"):
        raise PermissionDeniedError("Permission 'leave.application.review' required.")

    try:
        app = LeaveApplication.objects.get(pk=application_id)
    except LeaveApplication.DoesNotExist as exc:
        raise NotFoundError(f"Leave application #{application_id} not found.") from exc

    valid_statuses = ("submitted", "under_review", "awaiting_unit_head")
    if app.status not in valid_statuses:
        raise ConflictError(
            f"Cannot review application #{app.pk} in state '{app.status}'."
        )

    if action not in ("recommend", "reject"):
        raise BadRequestError("Action must be 'recommend' or 'reject'.", code="invalid_action")

    with transaction.atomic():
        if action == "recommend":
            app.status = "awaiting_sanction"
            audit_msg = f"Recommended by reviewer: {reason}".strip()
        else:
            app.status = "rejected"
            audit_msg = f"Rejected by reviewer: {reason}".strip()

        app.save(update_fields=["status", "updated_at"])
        LeaveApplicationAudit.objects.create(
            application=app,
            status=app.status,
            reason=audit_msg,
        )

    log.info(
        "Leave application #%s reviewed ('%s') by user %s",
        app.pk,
        action,
        getattr(actor, "user_id", None),
    )
    return app


def sanction_application(
    *,
    actor,
    application_id: int,
    action: str,
    reason: str = "",
) -> LeaveApplication:
    """Sanctioning authority grants final approval or rejection (EL-UC-004, CW-EL-01, CW-EL-04)."""
    if actor is None:
        raise PermissionDeniedError("Authentication required.")

    if not actor.has_permission("leave.application.approve"):
        raise PermissionDeniedError("Permission 'leave.application.approve' required.")

    try:
        app = LeaveApplication.objects.get(pk=application_id)
    except LeaveApplication.DoesNotExist as exc:
        raise NotFoundError(f"Leave application #{application_id} not found.") from exc

    valid_statuses = ("awaiting_sanction", "awaiting_unit_head", "under_review", "submitted")
    if app.status not in valid_statuses:
        raise ConflictError(
            f"Cannot sanction application #{app.pk} in state '{app.status}'."
        )

    if action not in ("approve", "reject"):
        raise BadRequestError("Action must be 'approve' or 'reject'.", code="invalid_action")

    with transaction.atomic():
        if action == "approve":
            app.status = "approved"
            audit_msg = f"Sanction approved: {reason}".strip()
        else:
            app.status = "rejected"
            audit_msg = f"Sanction rejected: {reason}".strip()

        app.save(update_fields=["status", "updated_at"])
        LeaveApplicationAudit.objects.create(
            application=app,
            status=app.status,
            reason=audit_msg,
        )

    log.info(
        "Leave application #%s sanctioned ('%s') by user %s",
        app.pk,
        action,
        getattr(actor, "user_id", None),
    )
    return app


def withdraw_application(
    *,
    actor,
    application_id: int,
    reason: str = "",
) -> LeaveApplication:
    """Applicant withdraws their own leave application (EL-UC-005, CFR-EL-021)."""
    if actor is None or not getattr(actor, "user_id", None):
        raise PermissionDeniedError("Authentication required.")

    try:
        app = LeaveApplication.objects.get(pk=application_id)
    except LeaveApplication.DoesNotExist as exc:
        raise NotFoundError(f"Leave application #{application_id} not found.") from exc

    if app.user_id != actor.user_id:
        raise PermissionDeniedError("You can only withdraw your own leave applications.")

    disallowed_statuses = ("withdrawn", "rejected", "cancelled", "auto_withdrawn", "closed")
    if app.status in disallowed_statuses:
        raise ConflictError(
            f"Cannot withdraw application #{app.pk} in terminal status '{app.status}'."
        )

    # BR-EL-021: withdrawal must precede start date
    if app.start_date and app.start_date < date.today():
        raise ConflictError("Cannot withdraw leave that has already commenced.")

    with transaction.atomic():
        app.status = "withdrawn"
        app.save(update_fields=["status", "updated_at"])
        LeaveApplicationAudit.objects.create(
            application=app,
            status=app.status,
            reason=f"Withdrawn by applicant: {reason}".strip(),
        )

    log.info("Leave application #%s withdrawn by user %s", app.pk, actor.user_id)
    return app
