from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from modules.iwd.domain.routing import classify_cost_band
from modules.iwd.domain.state_machine import transition
from modules.iwd.models.complaint import Complaint
from modules.iwd.models.estimate import RepairEstimate, ReviewCommitteeOutcome
from modules.iwd.services.audit import record_audit_trail


def create_estimate(
    complaint: Complaint,
    engineer_id: int,
    time_estimate_days: int,
    materials_cost: Decimal,
    labor_cost: Decimal,
    other_cost: Decimal = Decimal("0.00"),
) -> RepairEstimate:
    if complaint.assigned_engineer_id != engineer_id:
        raise ValidationError("Only the assigned engineer can prepare an estimate.")

    total_cost = materials_cost + labor_cost + other_cost
    band_info = classify_cost_band(total_cost)

    event_map = {
        "low": "submit_estimate_low",
        "mid": "submit_estimate_mid",
        "high": "submit_estimate_high",
    }
    event = event_map[band_info.band]

    with transaction.atomic():
        outcome = transition(complaint.status, event, "engineer")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        latest = complaint.estimates.order_by("-version").first()
        next_ver = (latest.version + 1) if latest else 1

        estimate = RepairEstimate.objects.create(
            complaint=complaint,
            version=next_ver,
            engineer_id=engineer_id,
            time_estimate_days=time_estimate_days,
            materials_cost=materials_cost,
            labor_cost=labor_cost,
            other_cost=other_cost,
            total_cost=total_cost,
            cost_band=band_info.band,
            status=outcome.next_state,
        )

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            estimate=estimate,
            actor_user_id=engineer_id,
            acting_role="engineer",
            action="submit_estimate",
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=f"Submitted estimate v{next_ver} for {total_cost} ({band_info.band})",
        )

        return estimate


def review_low_cost(
    estimate: RepairEstimate,
    admin_user_id: int,
    approve: bool,
    rejection_reason: str = "",
) -> RepairEstimate:
    complaint = estimate.complaint
    event = "approve_low_cost" if approve else "reject_low_cost"

    with transaction.atomic():
        outcome = transition(complaint.status, event, "iwd_admin")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        estimate.status = outcome.next_state
        if not approve:
            estimate.rejection_reason = rejection_reason
        estimate.save(update_fields=["status", "rejection_reason", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            estimate=estimate,
            actor_user_id=admin_user_id,
            acting_role="iwd_admin",
            action=event,
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=rejection_reason if not approve else "Approved low-cost estimate",
        )

        return estimate


def record_committee_review(
    estimate: RepairEstimate,
    reviewer_user_id: int,
    is_feasible: bool,
    is_necessary: bool,
    remarks: str,
) -> ReviewCommitteeOutcome:
    complaint = estimate.complaint

    with transaction.atomic():
        outcome = transition(
            complaint.status, "record_committee_review", "review_committee"
        )
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        review = ReviewCommitteeOutcome.objects.create(
            estimate=estimate,
            reviewer_user_id=reviewer_user_id,
            is_feasible=is_feasible,
            is_necessary=is_necessary,
            remarks=remarks,
        )

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        estimate.status = outcome.next_state
        estimate.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            estimate=estimate,
            actor_user_id=reviewer_user_id,
            acting_role="review_committee",
            action="record_committee_review",
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=remarks,
        )

        return review


def review_mid_range(
    estimate: RepairEstimate,
    dept_head_user_id: int,
    action: str,
    reason: str = "",
) -> RepairEstimate:
    complaint = estimate.complaint
    event_map = {
        "approve": "approve_dept_head",
        "reject": "reject_dept_head",
        "forward": "forward_to_director",
    }
    if action not in event_map:
        raise ValidationError(f"Invalid mid-range review action: {action}")
    event = event_map[action]

    with transaction.atomic():
        outcome = transition(complaint.status, event, "department_head")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        estimate.status = outcome.next_state
        if action == "reject":
            estimate.rejection_reason = reason
        estimate.save(update_fields=["status", "rejection_reason", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            estimate=estimate,
            actor_user_id=dept_head_user_id,
            acting_role="department_head",
            action=event,
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=reason,
        )

        return estimate


def review_director(
    estimate: RepairEstimate,
    director_user_id: int,
    action: str,
    reason: str = "",
) -> RepairEstimate:
    complaint = estimate.complaint
    event_map = {
        "approve_high": "authorize_bidding",
        "approve_mid": "approve_director_mid",
        "reject_high": "reject_director_high",
        "reject_mid": "reject_director_mid",
    }
    event = event_map.get(action)
    if not event:
        raise ValidationError(f"Invalid director action: {action}")

    with transaction.atomic():
        outcome = transition(complaint.status, event, "director")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        estimate.status = outcome.next_state
        if "reject" in action:
            estimate.rejection_reason = reason
        estimate.save(update_fields=["status", "rejection_reason", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            estimate=estimate,
            actor_user_id=director_user_id,
            acting_role="director",
            action=event,
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=reason,
        )

        return estimate
