from decimal import Decimal
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.oap.domain import constants as c
from modules.oap.domain.state_machine import (
    InvalidStateTransitionError,
    NoDuesStateMachine,
)
from modules.oap.domain.validation import (
    DomainValidationError,
    validate_no_dues_clearance,
)
from modules.oap.models.no_dues import NoDuesAuthorityClearance, NoDuesRequest
from modules.oap.selectors.no_dues import get_no_dues_by_id
from modules.oap.services.notify import emit_notification


def initiate_no_dues_clearance(
    user_id: int,
    department: str,
    programme: str = "ug",
) -> NoDuesRequest:
    """Initiates no-dues clearance and creates parallel entries for all 7 mandatory authorities.
    
    (OA-UC-21, AFR-OAP-022, AFR-OAP-023, BW-OAP-05, BW-OAP-06).
    """
    # Prevent duplicate active requests
    existing_active = NoDuesRequest.objects.filter(
        user_id=user_id,
        status__in=[
            c.NODUES_VERIFICATION_IN_PROGRESS,
            c.NODUES_COMPLETE_ALL_CLEAR,
            c.NODUES_COMPLETE_DUES_OUTSTANDING,
        ],
    ).first()
    if existing_active:
        raise ConflictError(
            f"An active no-dues clearance request already exists (ID {existing_active.id}, status: {existing_active.status})."
        )

    req = NoDuesRequest.objects.create(
        user_id=user_id,
        department=department,
        programme=programme,
        status=NoDuesStateMachine.initial_state(),
    )

    # Route in parallel to all 7 mandatory authorities
    for domain in c.MANDATORY_NO_DUES_DOMAINS:
        NoDuesAuthorityClearance.objects.create(
            request=req,
            domain=domain,
            status=c.CLEARANCE_PENDING,
        )

    emit_notification(
        recipient_user_id=user_id,
        title="No-Dues Clearance Initiated",
        message="Your no-dues clearance request has been initiated and routed to all 7 mandatory authorities.",
        related_entity_type="no_dues",
        related_entity_id=req.id,
    )

    return req


def verify_authority_clearance(
    request_id: int,
    domain: str,
    status: str,
    verifier_user_id: int,
    dues_amount: Decimal | float = 0.00,
    remarks: str = "",
) -> NoDuesAuthorityClearance:
    """An authority records clearance result for its specific domain (OA-UC-22, OA-BR-31, OA-BR-32)."""
    try:
        validate_no_dues_clearance(domain, status, float(dues_amount))
    except DomainValidationError as exc:
        raise BadRequestError(str(exc)) from exc

    req = get_no_dues_by_id(request_id)
    if not req:
        raise NotFoundError(f"No-Dues request {request_id} not found.")

    if req.status == c.NODUES_FINALIZED:
        raise ConflictError("Cannot record clearance on an already finalized no-dues request.")

    clearance = NoDuesAuthorityClearance.objects.filter(request=req, domain=domain).first()
    if not clearance:
        raise NotFoundError(f"Clearance entry for domain '{domain}' not found in request {request_id}.")

    clearance.status = status
    clearance.verified_by_user_id = verifier_user_id
    clearance.dues_amount = Decimal(str(dues_amount))
    clearance.remarks = remarks
    clearance.verified_at = timezone.now()
    clearance.save(update_fields=["status", "verified_by_user_id", "dues_amount", "remarks", "verified_at", "updated_at"])

    # Re-evaluate overall request state across all 7 clearances (OA-BR-32, OA-BR-33)
    domain_statuses = {
        cl.domain: cl.status for cl in req.clearances.all()
    }
    # Update current in map
    domain_statuses[domain] = status
    new_request_state = NoDuesStateMachine.compute_request_state(domain_statuses)

    if new_request_state != req.status:
        req.status = new_request_state
        req.save(update_fields=["status", "updated_at"])

        if new_request_state in (c.NODUES_COMPLETE_ALL_CLEAR, c.NODUES_COMPLETE_DUES_OUTSTANDING):
            emit_notification(
                recipient_user_id=req.user_id,
                title="No-Dues Verifications Complete",
                message=(
                    "All 7 no-dues verifications have completed with all domains clear. Awaiting Academic Administrator finalization."
                    if new_request_state == c.NODUES_COMPLETE_ALL_CLEAR
                    else "All 7 no-dues verifications completed, but one or more domains reported outstanding dues."
                ),
                related_entity_type="no_dues",
                related_entity_id=req.id,
            )

    return clearance


def finalize_no_dues_clearance(
    request_id: int,
    admin_user_id: int,
) -> NoDuesRequest:
    """Academic Administrator finalizes no-dues clearance (OA-UC-23, OA-BR-33)."""
    req = get_no_dues_by_id(request_id)
    if not req:
        raise NotFoundError(f"No-Dues request {request_id} not found.")

    try:
        new_status = NoDuesStateMachine.finalize(req.status)
    except InvalidStateTransitionError as exc:
        raise ConflictError(str(exc)) from exc

    req.status = new_status
    req.finalized_by_user_id = admin_user_id
    req.finalized_at = timezone.now()
    req.certificate_number = f"NODUES-{timezone.now().year}-{req.id:05d}"
    req.save(update_fields=["status", "finalized_by_user_id", "finalized_at", "certificate_number", "updated_at"])

    emit_notification(
        recipient_user_id=req.user_id,
        title="No-Dues Clearance Finalized",
        message=f"Your no-dues clearance has been finalized! Certificate No: {req.certificate_number} is now available.",
        related_entity_type="no_dues",
        related_entity_id=req.id,
    )

    return req


def download_no_dues_certificate(request_id: int, requesting_user_id: int) -> dict:
    """Generates finalized no-dues certificate download payload (OA-UC-25, OA-BR-34)."""
    req = get_no_dues_by_id(request_id)
    if not req:
        raise NotFoundError(f"No-Dues request {request_id} not found.")

    if req.user_id != requesting_user_id:
        raise PermissionDeniedError("Cannot download no-dues certificate belonging to another student.")

    # OA-BR-34: Guard - download permitted only after Academic Administrator finalization
    if req.status != c.NODUES_FINALIZED:
        raise ConflictError(
            f"No-dues certificate cannot be downloaded in status '{req.status}' (OA-BR-34)."
        )

    clearance_details = [
        {"domain": cl.domain, "status": cl.status, "verified_at": cl.verified_at.isoformat() if cl.verified_at else None}
        for cl in req.clearances.all()
    ]

    return {
        "certificate_type": "No-Dues Clearance Certificate",
        "certificate_number": req.certificate_number,
        "student_user_id": req.user_id,
        "department": req.department,
        "programme": req.programme,
        "finalized_at": req.finalized_at.isoformat() if req.finalized_at else "",
        "clearance_records": clearance_details,
        "status": "FINALIZED",
    }
