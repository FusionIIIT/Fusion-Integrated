"""Service functions for IWD estimate preparation and submission.

Implements:
- UC-IWD-021: Prepare and Submit Estimate
- BW-IWD-02 Step 1, BW-IWD-03 Step 1, BW-IWD-05 Step 1; CW-IWD-01
- BR-IWD-001: Active-role authorization & ownership isolation
- BR-IWD-003: Cost-band routing
- AFR-IWD-011: Estimated repair time
- AFR-IWD-012: Required materials and quantities
- AFR-IWD-013: Estimated cost and estimate submission
- AFR-IWD-014, AFR-IWD-015, AFR-IWD-018, AFR-IWD-021
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.iwd.domain.cost_bands import classify_cost_band
from modules.iwd.domain.state_machine import IWDState, route_initial_estimate, transition_resubmission
from modules.iwd.models import Complaint, ComplaintTransition, Estimate


def submit_complaint_estimate(
    *,
    complaint_id: int,
    principal,
    estimated_cost: Decimal | str | int,
    estimated_time: str,
    materials_summary: str,
    supporting_details: str = "",
) -> tuple[Complaint, Estimate]:
    """Submit a repair estimate for an assessed complaint and route by cost band.

    Enforces:
    1. Caller must have active role 'iwd_engineer'.
    2. Caller must have explicit permission 'iwd.complaint.assess'.
    3. Complaint must be assigned to the caller (user_id ownership).
    4. Complaint must be currently in 'Assessed' state (BW-IWD-02/03/05 STTs).
    5. Cost must be positive Decimal without floating-point conversion.
    6. Estimated time and materials summary must not be blank.
    7. Concurrency-safe row locking and atomic state transition with audit history.
    """
    if principal is None or getattr(principal, "active_role", None) != "iwd_engineer":
        raise PermissionDeniedError(
            "An active role of 'iwd_engineer' is required to submit estimates.",
            code="active_role_required",
        )

    if not principal.has_permission("iwd.complaint.assess"):
        raise PermissionDeniedError(
            "Permission 'iwd.complaint.assess' is required.",
            code="permission_denied",
        )

    # Validate cost without float conversion
    try:
        dec_cost = Decimal(str(estimated_cost))
    except (InvalidOperation, TypeError):
        raise BadRequestError(
            f"Invalid estimated cost: {estimated_cost!r}",
            code="invalid_cost",
        )

    if dec_cost <= Decimal("0.00"):
        raise BadRequestError(
            "Estimated cost must be greater than zero.",
            code="non_positive_cost",
        )

    time_str = estimated_time.strip() if estimated_time else ""
    if not time_str:
        raise BadRequestError(
            "Estimated repair time is required.",
            code="missing_estimated_time",
        )

    mat_str = materials_summary.strip() if materials_summary else ""
    if not mat_str:
        raise BadRequestError(
            "Materials summary is required.",
            code="missing_materials_summary",
        )

    details_str = supporting_details.strip() if supporting_details else ""

    # Determine cost band and target state via pure domain functions
    cost_band = classify_cost_band(dec_cost)
    next_state = route_initial_estimate(dec_cost)

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.assigned_engineer_id != principal.user_id:
            raise PermissionDeniedError(
                "You can only submit estimates for complaints assigned to you.",
                code="complaint_not_assigned_to_caller",
            )

        if complaint.status != IWDState.ASSESSED.value:
            raise ConflictError(
                f"Cannot submit estimate for complaint in status '{complaint.status}'. Complaint must be in '{IWDState.ASSESSED.value}'.",
                code="invalid_state_transition",
            )

        estimate = Estimate.objects.create(
            complaint=complaint,
            engineer_id=principal.user_id,
            cost_band=cost_band.value,
            estimated_cost=dec_cost,
            estimated_time=time_str,
            materials_summary=mat_str,
            supporting_details=details_str,
        )

        from_status = complaint.status
        complaint.status = next_state.value
        complaint.save(update_fields=["status", "updated_at"])

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=next_state.value,
            actor_user_id=principal.user_id,
            actor_label="Engineer",
            reason=f"Estimate submitted: ₹{dec_cost} ({cost_band.value})",
        )

    return complaint, estimate

def resubmit_complaint_estimate(
    *,
    complaint_id: int,
    principal,
    estimated_cost: Decimal | str | int,
    estimated_time: str,
    materials_summary: str,
    supporting_details: str = "",
) -> tuple[Complaint, Estimate]:
    """Modify and resubmit a rejected repair estimate (BW-IWD-12..14 / UC-IWD-151 / BR-IWD-009).

    Enforces:
    1. Caller must have active role 'iwd_engineer'.
    2. Caller must have explicit permission 'iwd.complaint.assess'.
    3. Complaint must be assigned to caller (user_id ownership).
    4. Complaint must be currently in an allowed rejected state (REJECTED_LOW, REJECTED_MID, REJECTED_DIRECTOR).
    5. Cost must be positive Decimal without floating-point conversion.
    6. Estimated time and materials summary must not be blank.
    7. Atomically locks complaint row, evaluates dynamic cost-band routing, creates a new Estimate version,
       transitions complaint status, and appends audit record in ComplaintTransition.
    """
    if principal is None or getattr(principal, "active_role", None) != "iwd_engineer":
        raise PermissionDeniedError(
            "An active role of 'iwd_engineer' is required to resubmit estimates.",
            code="active_role_required",
        )

    if not principal.has_permission("iwd.complaint.assess"):
        raise PermissionDeniedError(
            "Permission 'iwd.complaint.assess' is required.",
            code="permission_denied",
        )

    try:
        dec_cost = Decimal(str(estimated_cost))
    except (InvalidOperation, TypeError):
        raise BadRequestError(
            f"Invalid estimated cost: {estimated_cost!r}",
            code="invalid_cost",
        )

    if dec_cost <= Decimal("0.00"):
        raise BadRequestError(
            "Estimated cost must be greater than zero.",
            code="non_positive_cost",
        )

    time_str = estimated_time.strip() if estimated_time else ""
    if not time_str:
        raise BadRequestError(
            "Estimated repair time is required.",
            code="missing_estimated_time",
        )

    mat_str = materials_summary.strip() if materials_summary else ""
    if not mat_str:
        raise BadRequestError(
            "Materials summary is required.",
            code="missing_materials_summary",
        )

    details_str = supporting_details.strip() if supporting_details else ""

    allowed_rejected_states = (
        IWDState.REJECTED_LOW.value,
        IWDState.REJECTED_MID.value,
        IWDState.REJECTED_DIRECTOR.value,
    )

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.assigned_engineer_id != principal.user_id:
            raise PermissionDeniedError(
                "You can only resubmit estimates for complaints assigned to you.",
                code="complaint_not_assigned_to_caller",
            )

        if complaint.status not in allowed_rejected_states:
            raise ConflictError(
                f"Cannot resubmit estimate for complaint in status '{complaint.status}'. "
                f"Complaint must be in one of {allowed_rejected_states} (BR-IWD-009, UC-IWD-151).",
                code="not_in_rejected_state",
            )

        # Dynamic routing via pure domain function
        next_state = transition_resubmission(
            current_state=IWDState(complaint.status),
            new_amount=dec_cost,
            actor_role="Engineer",
        )
        cost_band = classify_cost_band(dec_cost)

        # Append new Estimate version (preserving previous rejected Estimate)
        estimate = Estimate.objects.create(
            complaint=complaint,
            engineer_id=principal.user_id,
            cost_band=cost_band.value,
            estimated_cost=dec_cost,
            estimated_time=time_str,
            materials_summary=mat_str,
            supporting_details=details_str,
        )

        from_status = complaint.status
        complaint.status = next_state.value
        complaint.save(update_fields=["status", "updated_at"])

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=from_status,
            to_status=next_state.value,
            actor_user_id=principal.user_id,
            actor_label="Engineer",
            reason=f"Estimate resubmitted: ₹{dec_cost} ({cost_band.value})",
        )

    return complaint, estimate

