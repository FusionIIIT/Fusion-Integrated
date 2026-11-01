"""Service functions for IWD complaint technical assessments.

Implements:
- UC-IWD-015: Assess Assigned Complaint
- BW-IWD-01: Step 3 (Assigned -> Assessed)
- BR-IWD-001: Active-role authorization & ownership isolation
- AFR-IWD-010: Assessment of assigned complaint and repairs required
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.iwd.domain.state_machine import IWDState, transition_complaint
from modules.iwd.models import Complaint, ComplaintTransition


def record_complaint_assessment(
    *,
    complaint_id: int,
    principal,
    assessment_details: str,
) -> Complaint:
    """Record technical assessment and repairs required for an assigned complaint.

    Enforces:
    1. Caller must have active role 'iwd_engineer'.
    2. Caller must have explicit permission 'iwd.complaint.assess'.
    3. Complaint must be assigned to the caller (user_id ownership).
    4. Complaint must be currently in 'Assigned' state.
    5. Assessment findings cannot be blank.
    6. Concurrency-safe row locking and atomic state transition with audit history.
    """
    if principal is None or getattr(principal, "active_role", None) != "iwd_engineer":
        raise PermissionDeniedError(
            "An active role of 'iwd_engineer' is required to record assessments.",
            code="active_role_required",
        )

    if not principal.has_permission("iwd.complaint.assess"):
        raise PermissionDeniedError(
            "Permission 'iwd.complaint.assess' is required.",
            code="permission_denied",
        )

    findings = assessment_details.strip() if assessment_details else ""
    if not findings:
        raise BadRequestError(
            "Assessment findings cannot be blank.",
            code="blank_assessment",
        )

    with transaction.atomic():
        try:
            complaint = Complaint.objects.select_for_update().get(pk=complaint_id)
        except Complaint.DoesNotExist:
            raise NotFoundError(f"Complaint #{complaint_id} not found.", code="complaint_not_found")

        if complaint.assigned_engineer_id != principal.user_id:
            raise PermissionDeniedError(
                "You can only assess complaints assigned to you.",
                code="complaint_not_assigned_to_caller",
            )

        if complaint.status != IWDState.ASSIGNED.value:
            raise ConflictError(
                f"Cannot assess complaint in status '{complaint.status}'. Complaint must be in '{IWDState.ASSIGNED.value}'.",
                code="invalid_state_transition",
            )

        new_state = transition_complaint(
            current_state=IWDState(complaint.status),
            action="record_assessment",
            actor_role="Engineer",
        )

        complaint.status = new_state.value
        complaint.assessment_details = findings
        complaint.assessed_at = timezone.now()
        complaint.save(update_fields=["status", "assessment_details", "assessed_at", "updated_at"])

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status=IWDState.ASSIGNED.value,
            to_status=new_state.value,
            actor_user_id=principal.user_id,
            actor_label="Engineer",
            reason="Technical assessment recorded",
        )

    return complaint

