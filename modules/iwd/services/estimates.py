"""Estimate preparation, cost-band routing, and rejection resubmission services."""

from decimal import Decimal

from modules.iwd.domain.cost_bands import BAND_HIGH, BAND_LOW, BAND_MID, classify_band
from modules.iwd.domain.state_machine import get_next_state
from modules.iwd.models import Complaint, DecisionAuditTrail, Estimate


def submit_estimate(
    complaint_id: int,
    engineer_user_id: int,
    estimated_time_days: int,
    materials_details: str,
    total_cost: Decimal | float | int | str,
) -> Estimate:
    """Submit a repair estimate and route by cost band (UC-IWD-021, BR-IWD-003)."""
    complaint = Complaint.objects.get(id=complaint_id)
    cost = Decimal(str(total_cost))
    band = classify_band(cost)

    estimate = Estimate.objects.create(
        complaint=complaint,
        engineer_user_id=engineer_user_id,
        estimated_time_days=estimated_time_days,
        materials_details=materials_details,
        total_cost=cost,
        cost_band=band,
        status="Pending",
    )

    action_map = {
        BAND_LOW: "submit_low",
        BAND_MID: "submit_mid",
        BAND_HIGH: "submit_high",
    }
    action = action_map[band]
    prev = complaint.status
    complaint.status = get_next_state(prev, action, "iwd_engineer")
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=engineer_user_id,
        actor_role="iwd_engineer",
        action="submit_estimate",
        previous_state=prev,
        new_state=complaint.status,
        remarks=f"Estimate submitted: Rs.{cost} ({band} band)",
    )
    return estimate


def resubmit_estimate(
    complaint_id: int,
    engineer_user_id: int,
    estimated_time_days: int | None = None,
    materials_details: str | None = None,
    total_cost: Decimal | float | int | str | None = None,
) -> Estimate:
    """Modify and resubmit a rejected request to approval route (UC-IWD-151, BR-IWD-009)."""
    complaint = Complaint.objects.get(id=complaint_id)
    estimate = complaint.estimates.latest("created_at")

    if total_cost is not None:
        estimate.total_cost = Decimal(str(total_cost))
        estimate.cost_band = classify_band(estimate.total_cost)
    if estimated_time_days is not None:
        estimate.estimated_time_days = estimated_time_days
    if materials_details is not None:
        estimate.materials_details = materials_details

    estimate.resubmission_count += 1
    estimate.status = "Resubmitted"
    estimate.save()

    prev = complaint.status
    complaint.status = get_next_state(prev, "modify_resubmit", "iwd_engineer")
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=engineer_user_id,
        actor_role="iwd_engineer",
        action="modify_resubmit",
        previous_state=prev,
        new_state=complaint.status,
        remarks=f"Resubmission #{estimate.resubmission_count}: Rs.{estimate.total_cost}",
    )
    return estimate
