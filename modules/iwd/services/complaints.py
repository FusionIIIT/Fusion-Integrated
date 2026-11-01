"""Services for IWD complaints (intake and automatic assignment).

Enforces transactional integrity, deadlock-free row locking, and append-only audit trails.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.iwd.domain.state_machine import IWDState
from modules.iwd.domain.workload import (
    EngineerCandidate,
    NoEligibleEngineerError,
    select_engineer_for_assignment,
)
from modules.iwd.models import Complaint, ComplaintTransition, Engineer
from modules.iwd.selectors.complaints import get_active_workload


def submit_complaint(
    *,
    complainant_id: int,
    category: str,
    location: str,
    urgency: str = "low",
    remarks: str = "",
) -> Complaint:
    """Submit a maintenance complaint and attempt automatic engineer assignment.

    Implements:
    - UC-IWD-001 (Submit Maintenance Complaint)
    - BW-IWD-01 (Steps 1 & 2: No Complaint -> Submitted -> Assigned)
    - BR-IWD-001 (Authorization)
    - BR-IWD-002 (Workload-based automatic assignment)
    - Approach B: If no eligible engineer exists, the complaint remains in SUBMITTED
      for administrative assignment without failing the intake transaction.
    """
    category = category.lower().strip()
    urgency = urgency.lower().strip()
    location = location.strip()
    remarks = remarks.strip()

    if category not in ("civil", "electrical"):
        raise BadRequestError(
            f"Invalid category '{category}'. Must be 'civil' or 'electrical'.",
            code="invalid_category",
        )
    if urgency not in ("low", "medium", "high", "emergency"):
        raise BadRequestError(
            f"Invalid urgency '{urgency}'. Must be 'low', 'medium', 'high', or 'emergency'.",
            code="invalid_urgency",
        )
    if not location:
        raise BadRequestError("Location is required.", code="missing_location")

    with transaction.atomic():
        # Step 1: Create complaint in SUBMITTED state (BW-IWD-01 Step 1)
        complaint = Complaint.objects.create(
            user_id=complainant_id,
            category=category,
            location=location,
            urgency=urgency,
            remarks=remarks,
            status=IWDState.SUBMITTED.value,
            assigned_engineer_id=None,
        )

        ComplaintTransition.objects.create(
            complaint=complaint,
            from_status="None",
            to_status=IWDState.SUBMITTED.value,
            actor_user_id=complainant_id,
            actor_label="Institute Employee",
            reason="Complaint submitted",
        )

        # Step 2: Concurrency-safe automatic assignment (BW-IWD-01 Step 2)
        # Lock candidate engineer rows in deterministic user_id order to avoid deadlocks.
        candidate_engineers = list(
            Engineer.objects.filter(specialization=category, is_active=True)
            .select_for_update()
            .order_by("user_id")
        )

        if candidate_engineers:
            candidates = [
                EngineerCandidate(
                    user_id=eng.user_id,
                    active_complaint_count=get_active_workload(eng.user_id),
                    specialization=eng.specialization,
                    is_eligible=eng.is_active,
                )
                for eng in candidate_engineers
            ]
            try:
                chosen = select_engineer_for_assignment(candidates)
                complaint.assigned_engineer_id = chosen.user_id
                complaint.assigned_at = timezone.now()
                complaint.status = IWDState.ASSIGNED.value
                complaint.save(
                    update_fields=["assigned_engineer_id", "assigned_at", "status", "updated_at"]
                )

                ComplaintTransition.objects.create(
                    complaint=complaint,
                    from_status=IWDState.SUBMITTED.value,
                    to_status=IWDState.ASSIGNED.value,
                    actor_user_id=None,
                    actor_label="System",
                    reason=f"Auto-assigned to engineer u{chosen.user_id} (active workload: {chosen.active_complaint_count})",
                )
            except NoEligibleEngineerError:
                # Approach B: Remains in SUBMITTED state with assigned_engineer_id=None
                pass

    return complaint

