"""Repair work execution, completion, and rework management services (UC-IWD-091)."""

from modules.iwd.domain.state_machine import get_next_state
from modules.iwd.models import Complaint, DecisionAuditTrail


def start_work(complaint_id: int, engineer_user_id: int) -> Complaint:
    """Transition from materials issued to ready for execution."""
    complaint = Complaint.objects.get(id=complaint_id)
    prev = complaint.status
    complaint.status = get_next_state(prev, "start_execution", "iwd_engineer")
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=engineer_user_id,
        actor_role="iwd_engineer",
        action="start_execution",
        previous_state=prev,
        new_state=complaint.status,
        remarks="Execution initiated after materials issued",
    )
    return complaint


def mark_work_complete(complaint_id: int, engineer_user_id: int) -> Complaint:
    """Mark repair work completed and await Department Head physical verification (UC-IWD-091)."""
    complaint = Complaint.objects.get(id=complaint_id)
    prev = complaint.status
    complaint.status = get_next_state(prev, "work_complete", "iwd_engineer")
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=engineer_user_id,
        actor_role="iwd_engineer",
        action="work_complete",
        previous_state=prev,
        new_state=complaint.status,
        remarks="Work marked complete, ready for physical verification",
    )
    return complaint


def execute_rework(complaint_id: int, engineer_user_id: int) -> Complaint:
    """Execute assigned rework and return complaint for re-verification (BW-IWD-10)."""
    complaint = Complaint.objects.get(id=complaint_id)
    prev = complaint.status
    complaint.status = get_next_state(prev, "rework_complete", "iwd_engineer")
    complaint.save()

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=engineer_user_id,
        actor_role="iwd_engineer",
        action="rework_complete",
        previous_state=prev,
        new_state=complaint.status,
        remarks="Rework completed, returned for verification",
    )
    return complaint
