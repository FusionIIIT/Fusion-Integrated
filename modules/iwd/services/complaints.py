"""Complaint intake, automatic assignment, assessment, and urgency escalation services."""

from django.db.models import Count
from django.utils import timezone

from modules.iwd.domain.assignment import select_best_engineer
from modules.iwd.domain.state_machine import IWDState, get_next_state
from modules.iwd.models import Complaint, DecisionAuditTrail


def submit_complaint(
    requester_user_id: int,
    category: str,
    location: str,
    urgency: str = "Low",
    remarks: str = "",
    eligible_engineer_ids: list[int] | None = None,
) -> Complaint:
    """Create a complaint and assign an engineer by workload (UC-IWD-001, BR-IWD-002)."""
    complaint = Complaint.objects.create(
        requester_user_id=requester_user_id,
        category=category,
        location=location,
        urgency=urgency,
        remarks=remarks,
        status=IWDState.SUBMITTED,
    )

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=requester_user_id,
        actor_role="Institute Employee",
        action="submit_complaint",
        previous_state="No Complaint",
        new_state=IWDState.SUBMITTED,
        remarks=remarks,
    )

    # Automatic assignment (BR-IWD-002)
    engineers = eligible_engineer_ids or [201, 202]
    workloads = (
        Complaint.objects.filter(
            assigned_engineer_id__in=engineers,
            is_resolved=False,
        )
        .values("assigned_engineer_id")
        .annotate(active_count=Count("id"))
    )
    workload_map = {row["assigned_engineer_id"]: row["active_count"] for row in workloads}

    best_engineer = select_best_engineer(engineers, workload_map)
    if best_engineer:
        complaint.assigned_engineer_id = best_engineer
        prev = complaint.status
        complaint.status = get_next_state(prev, "assign", "System")
        complaint.save()

        DecisionAuditTrail.objects.create(
            complaint=complaint,
            actor_user_id=None,
            actor_role="System",
            action="auto_assign_engineer",
            previous_state=prev,
            new_state=complaint.status,
            remarks=f"Assigned to engineer {best_engineer}",
        )

    return complaint


def assess_complaint(
    complaint_id: int, engineer_user_id: int, assessment_details: str
) -> Complaint:
    """Record repair assessment by the assigned engineer (UC-IWD-015)."""
    complaint = Complaint.objects.get(id=complaint_id)
    prev = complaint.status
    complaint.status = get_next_state(prev, "assess", "iwd_engineer")
    complaint.assessment_details = assessment_details
    complaint.assessment_date = timezone.now()
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=engineer_user_id,
        actor_role="iwd_engineer",
        action="assess_complaint",
        previous_state=prev,
        new_state=complaint.status,
        remarks=assessment_details,
    )
    return complaint


def flag_urgent(complaint_id: int, engineer_user_id: int, remarks: str) -> Complaint:
    """Flag an active complaint for urgent fast-track review (UC-IWD-025, BR-IWD-012)."""
    complaint = Complaint.objects.get(id=complaint_id)
    prev = complaint.status
    complaint.status = get_next_state(prev, "flag_urgent", "iwd_engineer")
    complaint.is_urgent_escalated = True
    complaint.urgent_remarks = remarks
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=engineer_user_id,
        actor_role="iwd_engineer",
        action="flag_urgent",
        previous_state=prev,
        new_state=complaint.status,
        remarks=remarks,
    )
    return complaint


def review_urgent(complaint_id: int, reviewer_user_id: int, role: str, accept: bool) -> Complaint:
    """Review urgent escalation without bypassing cost controls (UC-IWD-055, BR-IWD-012)."""
    complaint = Complaint.objects.get(id=complaint_id)
    action = "accept_fast_track" if accept else "decline_fast_track"
    prev = complaint.status
    complaint.status = get_next_state(prev, action, role)
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=reviewer_user_id,
        actor_role=role,
        action="review_urgent",
        previous_state=prev,
        new_state=complaint.status,
        remarks=f"Urgent decision: {'Accepted' if accept else 'Declined'}",
    )
    return complaint
