"""Estimate review and approval services across cost tiers (BR-IWD-004, 005, 006, 007)."""

from modules.iwd.domain.state_machine import get_next_state
from modules.iwd.models import Complaint, DecisionAuditTrail, Estimate


def review_low_cost(
    complaint_id: int, admin_user_id: int, approve: bool, reason: str = ""
) -> Estimate:
    """IWD Admin approves or rejects low-cost estimate under Rs.25,000 (BR-IWD-004)."""
    complaint = Complaint.objects.get(id=complaint_id)
    estimate = complaint.estimates.latest("created_at")

    action = "approve" if approve else "reject"
    prev = complaint.status
    complaint.status = get_next_state(prev, action, "iwd_admin")
    complaint.save()

    estimate.status = "Approved" if approve else "Rejected"
    if not approve:
        estimate.rejection_reason = reason
    estimate.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=admin_user_id,
        actor_role="iwd_admin",
        action="review_low_cost",
        previous_state=prev,
        new_state=complaint.status,
        remarks=f"Decision: {action}. {reason}".strip(),
    )
    return estimate


def record_committee_review(
    complaint_id: int, reviewer_user_id: int, outcome: str, approved: bool
) -> Estimate:
    """Record mid-range review committee necessity assessment (BR-IWD-005)."""
    complaint = Complaint.objects.get(id=complaint_id)
    estimate = complaint.estimates.latest("created_at")

    prev = complaint.status
    complaint.status = get_next_state(prev, "record_committee", "Review Committee")
    complaint.save()

    estimate.committee_outcome = outcome
    estimate.committee_approved = approved
    estimate.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=reviewer_user_id,
        actor_role="Review Committee",
        action="record_committee",
        previous_state=prev,
        new_state=complaint.status,
        remarks=outcome,
    )
    return estimate


def review_mid_range(
    complaint_id: int, dept_head_user_id: int, decision: str, remarks: str = ""
) -> Estimate:
    """Department Head decides mid-range estimate (UC-IWD-041, BR-IWD-006)."""
    complaint = Complaint.objects.get(id=complaint_id)
    estimate = complaint.estimates.latest("created_at")

    prev = complaint.status
    complaint.status = get_next_state(prev, decision, "iwd_department_head")
    complaint.save()

    estimate.dept_head_decision = decision.capitalize()
    estimate.dept_head_remarks = remarks
    if decision == "reject":
        estimate.rejection_reason = remarks
    elif decision == "approve":
        estimate.status = "Approved"
    estimate.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=dept_head_user_id,
        actor_role="iwd_department_head",
        action=f"mid_range_{decision}",
        previous_state=prev,
        new_state=complaint.status,
        remarks=remarks,
    )
    return estimate


def review_director(
    complaint_id: int, director_user_id: int, approve: bool, remarks: str = ""
) -> Estimate:
    """Director approves high-cost bidding or forwarded mid-range estimate (BR-IWD-007)."""
    complaint = Complaint.objects.get(id=complaint_id)
    estimate = complaint.estimates.latest("created_at")

    action = "approve" if approve else "reject"
    prev = complaint.status
    complaint.status = get_next_state(prev, action, "iwd_director")
    complaint.save()

    estimate.director_decision = "Approved" if approve else "Rejected"
    estimate.director_remarks = remarks
    if not approve:
        estimate.rejection_reason = remarks
    estimate.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=director_user_id,
        actor_role="iwd_director",
        action=f"director_{action}",
        previous_state=prev,
        new_state=complaint.status,
        remarks=remarks,
    )
    return estimate
