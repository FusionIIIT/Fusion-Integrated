from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.oap.domain import constants as c
from modules.oap.domain.state_machine import (
    BonafideStateMachine,
    InvalidStateTransitionError,
)
from modules.oap.domain.validation import (
    DomainValidationError,
    validate_bonafide_request,
)
from modules.oap.models.bonafide import BonafideRequest
from modules.oap.selectors.bonafide import get_bonafide_by_id
from modules.oap.services.notify import emit_notification


def request_bonafide_certificate(
    user_id: int,
    purpose: str,
    details: str = "",
) -> BonafideRequest:
    """Submits a bonafide certificate request for Academic Administrator verification (OA-UC-11)."""
    try:
        validate_bonafide_request(purpose)
    except DomainValidationError as exc:
        raise BadRequestError(str(exc)) from exc

    request = BonafideRequest.objects.create(
        user_id=user_id,
        purpose=purpose,
        details=details,
        status=BonafideStateMachine.initial_state(),
    )

    emit_notification(
        recipient_user_id=user_id,
        title="Bonafide Certificate Requested",
        message=f"Your bonafide request for '{purpose}' has been submitted to the Academic Administrator.",
        related_entity_type="bonafide",
        related_entity_id=request.id,
    )

    return request


def decide_bonafide_request(
    request_id: int,
    admin_user_id: int,
    decision: str,
    remarks: str = "",
) -> BonafideRequest:
    """Academic Administrator verifies and approves/rejects bonafide request (OA-UC-12, OA-BR-21)."""
    req = get_bonafide_by_id(request_id)
    if not req:
        raise NotFoundError(f"Bonafide request {request_id} not found.")

    try:
        new_status = BonafideStateMachine.transition_decision(req.status, decision)
    except InvalidStateTransitionError as exc:
        raise ConflictError(str(exc)) from exc

    req.status = new_status
    req.decision_by_user_id = admin_user_id
    req.decision_remarks = remarks
    req.decided_at = timezone.now()

    if new_status == c.BONAFIDE_APPROVED:
        req.certificate_number = f"BON-{timezone.now().year}-{req.id:05d}"

    req.save(update_fields=[
        "status",
        "decision_by_user_id",
        "decision_remarks",
        "decided_at",
        "certificate_number",
        "updated_at",
    ])

    emit_notification(
        recipient_user_id=req.user_id,
        title=f"Bonafide Request {new_status.title()}",
        message=(
            f"Your bonafide request has been {new_status}. "
            + (f"Certificate No: {req.certificate_number} is now available for download." if new_status == c.BONAFIDE_APPROVED else f"Remarks: {remarks}")
        ),
        related_entity_type="bonafide",
        related_entity_id=req.id,
    )

    return req


def download_bonafide_certificate(request_id: int, requesting_user_id: int) -> dict:
    """Generates bonafide certificate download payload (OA-UC-13, OA-BR-22)."""
    req = get_bonafide_by_id(request_id)
    if not req:
        raise NotFoundError(f"Bonafide request {request_id} not found.")

    if req.user_id != requesting_user_id:
        raise PermissionDeniedError("Cannot download bonafide certificate belonging to another student.")

    # OA-BR-22: Guard - download permitted only if approved
    if req.status != c.BONAFIDE_APPROVED:
        raise ConflictError(
            f"Bonafide certificate is not available for download in state '{req.status}' (OA-BR-22)."
        )

    return {
        "certificate_type": "Bonafide Certificate",
        "certificate_number": req.certificate_number,
        "student_user_id": req.user_id,
        "purpose": req.purpose,
        "issued_at": req.decided_at.isoformat() if req.decided_at else "",
        "status": "APPROVED",
    }
