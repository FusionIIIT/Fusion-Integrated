from decimal import Decimal
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.oap.domain import constants as c
from modules.oap.domain.state_machine import (
    AssistantshipStateMachine,
    InvalidStateTransitionError,
)
from modules.oap.domain.validation import (
    DomainValidationError,
    validate_assistantship_claim,
)
from modules.oap.models.assistantship import (
    AssistantshipClaim,
    ClaimSupervisorVerification,
)
from modules.oap.selectors.assistantship import get_claim_by_id
from modules.oap.services.assignments import resolve_supervisors_for_student
from modules.oap.services.notify import emit_notification


def submit_assistantship_claim(
    user_id: int,
    month: int,
    year: int,
    department: str,
    stipend_amount: Decimal | float,
    work_summary: str,
    hours_worked: Decimal | float = 0.00,
    thesis_supervisor_user_id: int | None = None,
    ta_supervisor_user_id: int | None = None,
) -> AssistantshipClaim:
    """PG student submits an assistantship claim (OA-UC-31, OA-BR-41, OA-BR-42)."""
    try:
        validate_assistantship_claim(month, year, float(stipend_amount), work_summary)
    except DomainValidationError as exc:
        raise BadRequestError(str(exc)) from exc

    # If supervisor IDs are not explicitly provided, look them up from assignments (OA-BR-52)
    if not thesis_supervisor_user_id or not ta_supervisor_user_id:
        t_sup, ta_sup = resolve_supervisors_for_student(user_id)
        thesis_supervisor_user_id = thesis_supervisor_user_id or t_sup
        ta_supervisor_user_id = ta_supervisor_user_id or ta_sup

    if not thesis_supervisor_user_id or not ta_supervisor_user_id:
        raise ConflictError(
            "Cannot submit assistantship claim: both Thesis Supervisor and TA Supervisor must be assigned/identifiable (OA-BR-42, OA-BR-52)."
        )

    # Check for duplicate claim for the same month and year
    existing = AssistantshipClaim.objects.filter(
        user_id=user_id,
        month=month,
        year=year,
    ).exclude(status=c.ASSISTANTSHIP_REJECTED).first()
    if existing:
        raise ConflictError(
            f"An assistantship claim for {month}/{year} already exists (ID: {existing.id}, status: {existing.status})."
        )

    claim = AssistantshipClaim.objects.create(
        user_id=user_id,
        month=month,
        year=year,
        department=department,
        stipend_amount=Decimal(str(stipend_amount)),
        work_summary=work_summary,
        hours_worked=Decimal(str(hours_worked)),
        status=AssistantshipStateMachine.initial_state(),
        thesis_supervisor_user_id=thesis_supervisor_user_id,
        ta_supervisor_user_id=ta_supervisor_user_id,
    )

    emit_notification(
        recipient_user_id=user_id,
        title="Assistantship Claim Submitted",
        message=f"Your assistantship claim for {month}/{year} has been submitted for supervisor verification.",
        related_entity_type="assistantship",
        related_entity_id=claim.id,
    )

    return claim


def verify_assistantship_claim(
    claim_id: int,
    supervisor_user_id: int,
    role: str,
    remarks: str = "",
) -> AssistantshipClaim:
    """Assigned Thesis Supervisor or TA Supervisor records claim verification (OA-UC-33, OA-BR-42, OA-BR-52)."""
    claim = get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Assistantship claim {claim_id} not found.")

    if claim.status not in (
        c.ASSISTANTSHIP_AWAITING_DUAL_SUPERVISOR,
        c.ASSISTANTSHIP_AWAITING_OTHER_SUPERVISOR,
    ):
        raise ConflictError(
            f"Claim is not currently awaiting supervisor verification (current status: {claim.status})."
        )

    if role not in c.SUPERVISOR_ROLES:
        raise BadRequestError(f"Invalid supervisor verification role: '{role}'. Must be one of {c.SUPERVISOR_ROLES}.")

    # Role-specific verification check (OA-BR-52)
    if role == c.SUPERVISOR_ROLE_THESIS:
        if claim.thesis_supervisor_user_id != supervisor_user_id:
            raise PermissionDeniedError("You are not the assigned Thesis Supervisor for this claim.")
        if claim.thesis_verified:
            raise ConflictError("Thesis Supervisor verification has already been recorded for this claim.")
        claim.thesis_verified = True
        claim.thesis_verified_at = timezone.now()
    elif role == c.SUPERVISOR_ROLE_TA:
        if claim.ta_supervisor_user_id != supervisor_user_id:
            raise PermissionDeniedError("You are not the assigned TA Supervisor for this claim.")
        if claim.ta_verified:
            raise ConflictError("TA Supervisor verification has already been recorded for this claim.")
        claim.ta_verified = True
        claim.ta_verified_at = timezone.now()

    # Record the verification detail
    ClaimSupervisorVerification.objects.update_or_create(
        claim=claim,
        role=role,
        defaults={
            "supervisor_user_id": supervisor_user_id,
            "remarks": remarks,
        },
    )

    # Compute updated state (dual supervisor verification logic)
    new_status = AssistantshipStateMachine.compute_supervisor_verification_state(
        thesis_verified=claim.thesis_verified,
        ta_verified=claim.ta_verified,
    )
    claim.status = new_status
    claim.save(update_fields=[
        "status",
        "thesis_verified",
        "thesis_verified_at",
        "ta_verified",
        "ta_verified_at",
        "updated_at",
    ])

    emit_notification(
        recipient_user_id=claim.user_id,
        title="Assistantship Claim Supervisor Verification",
        message=f"Verification recorded by {role.replace('_', ' ').title()}. Current status: {new_status}.",
        related_entity_type="assistantship",
        related_entity_id=claim.id,
    )

    return claim


def review_and_forward_claim(
    claim_id: int,
    dept_admin_user_id: int,
) -> AssistantshipClaim:
    """Department Administrator reviews claim after dual verification and forwards to HoD (OA-UC-34, OA-BR-43)."""
    claim = get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Assistantship claim {claim_id} not found.")

    try:
        new_status = AssistantshipStateMachine.forward_to_hod(claim.status)
    except InvalidStateTransitionError as exc:
        raise ConflictError(str(exc)) from exc

    claim.status = new_status
    claim.dept_reviewed_by_user_id = dept_admin_user_id
    claim.dept_reviewed_at = timezone.now()
    claim.save(update_fields=["status", "dept_reviewed_by_user_id", "dept_reviewed_at", "updated_at"])

    return claim


def decide_assistantship_claim(
    claim_id: int,
    hod_user_id: int,
    decision: str,
    remarks: str = "",
) -> AssistantshipClaim:
    """HoD approves or rejects the assistantship claim (OA-UC-35, OA-BR-44)."""
    claim = get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Assistantship claim {claim_id} not found.")

    try:
        new_status = AssistantshipStateMachine.decide_hod(claim.status, decision)
    except InvalidStateTransitionError as exc:
        raise ConflictError(str(exc)) from exc

    claim.status = new_status
    claim.hod_decided_by_user_id = hod_user_id
    claim.hod_decision_remarks = remarks
    claim.hod_decided_at = timezone.now()
    claim.save(update_fields=["status", "hod_decided_by_user_id", "hod_decision_remarks", "hod_decided_at", "updated_at"])

    emit_notification(
        recipient_user_id=claim.user_id,
        title=f"Assistantship Claim {new_status.title()}",
        message=f"Your claim for {claim.month}/{claim.year} has been {new_status} by the HoD. Remarks: {remarks or 'None'}",
        related_entity_type="assistantship",
        related_entity_id=claim.id,
    )

    return claim


def disburse_stipend(
    claim_id: int,
    admin_user_id: int,
    disbursement_reference: str = "",
) -> AssistantshipClaim:
    """Academic Administrator processes stipend disbursement (OA-UC-36, OA-BR-45)."""
    claim = get_claim_by_id(claim_id)
    if not claim:
        raise NotFoundError(f"Assistantship claim {claim_id} not found.")

    try:
        new_status = AssistantshipStateMachine.process_stipend(claim.status)
    except InvalidStateTransitionError as exc:
        raise ConflictError(str(exc)) from exc

    claim.status = new_status
    claim.disbursed_by_user_id = admin_user_id
    claim.disbursed_at = timezone.now()
    claim.disbursement_reference = disbursement_reference or f"DISB-{timezone.now().strftime('%Y%m')}-{claim.id:05d}"
    claim.save(update_fields=["status", "disbursed_by_user_id", "disbursed_at", "disbursement_reference", "updated_at"])

    emit_notification(
        recipient_user_id=claim.user_id,
        title="Stipend Disbursed",
        message=f"Stipend disbursement processed for {claim.month}/{claim.year}. Ref: {claim.disbursement_reference}.",
        related_entity_type="assistantship",
        related_entity_id=claim.id,
    )

    return claim
