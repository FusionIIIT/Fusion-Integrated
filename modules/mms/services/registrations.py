"""MMS registration services.

All writes go through here. No business logic in views or models.
Raises DomainError subclasses — never DRF exceptions — so the same
service can be called from management commands or Celery tasks.
"""
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.mms.models import RegistrationRequest, RegistrationWindow


def submit_registration(*, student_user_id: int, window_id: int,
                         remarks: str = "") -> RegistrationRequest:
    """UC-003 — Student submits a mess registration request.

    Business rules enforced:
      - BR-MMS-009: The registration window must be open.
      - BR-MMS-035: A student may not have more than one non-rejected
        request for the same window.
    """
    try:
        window = RegistrationWindow.objects.get(pk=window_id)
    except RegistrationWindow.DoesNotExist as exc:
        raise NotFoundError("Registration window not found.") from exc

    if not window.is_open:
        raise ConflictError(
            "Registration window is not open.",
            code="window_closed",
        )

    with transaction.atomic():
        # Check for an existing active request for this window.
        already = RegistrationRequest.objects.filter(
            student_user_id=student_user_id,
            window=window,
        ).exclude(status=RegistrationRequest.STATUS_REJECTED).first()
        if already:
            raise ConflictError(
                "You already have a registration request for this window.",
                code="duplicate_request",
            )

        return RegistrationRequest.objects.create(
            window=window,
            student_user_id=student_user_id,
            remarks=remarks,
            status=RegistrationRequest.STATUS_PENDING,
        )


def decide_registration(*, request_id: int, decision: str,
                          decided_by_user_id: int,
                          decision_note: str = "") -> RegistrationRequest:
    """UC-004 — Caretaker approves or rejects a pending registration request.

    Business rules enforced:
      - BR-MMS-010: Only a pending request can be decided.
      - The decision must be 'approved' or 'rejected'.
    """
    if decision not in (RegistrationRequest.STATUS_APPROVED,
                        RegistrationRequest.STATUS_REJECTED):
        raise BadRequestError(
            "Decision must be 'approved' or 'rejected'.",
            code="invalid_decision",
        )

    with transaction.atomic():
        try:
            req = RegistrationRequest.objects.select_for_update().get(pk=request_id)
        except RegistrationRequest.DoesNotExist as exc:
            raise NotFoundError("Registration request not found.") from exc

        if req.status != RegistrationRequest.STATUS_PENDING:
            raise ConflictError(
                "This request has already been decided.",
                code="already_decided",
            )

        req.status = decision
        req.decided_by_user_id = decided_by_user_id
        req.decision_note = decision_note
        req.decided_at = timezone.now()
        req.save(update_fields=[
            "status", "decided_by_user_id",
            "decision_note", "decided_at", "updated_at",
        ])

    return req
