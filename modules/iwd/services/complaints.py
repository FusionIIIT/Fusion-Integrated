import uuid
from typing import Sequence
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.iwd.domain.assignment import EngineerCandidate, select_best_engineer
from modules.iwd.domain.state_machine import transition
from modules.iwd.models.complaint import Complaint, RepairAssessment
from modules.iwd.services.audit import record_audit_trail


def create_complaint(
    complainant_user_id: int,
    category: str,
    location: str,
    urgency: str,
    remarks: str = "",
    available_engineers: Sequence[EngineerCandidate] = (),
) -> Complaint:
    """Creates a maintenance complaint and assigns engineer automatically (BR-IWD-001, BR-IWD-002)."""
    with transaction.atomic():
        cid = f"CMP-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        assigned_id = None
        status = "submitted"

        if available_engineers:
            assigned_id = select_best_engineer(category, available_engineers)
            outcome = transition("submitted", "assign_engineer", "system")
            if outcome.allowed:
                status = outcome.next_state

        complaint = Complaint.objects.create(
            complaint_id=cid,
            complainant_user_id=complainant_user_id,
            category=category,
            location=location,
            urgency=urgency,
            remarks=remarks,
            status=status,
            assigned_engineer_id=assigned_id,
        )

        record_audit_trail(
            complaint=complaint,
            actor_user_id=complainant_user_id,
            acting_role="employee",
            action="submit_complaint",
            from_state="none",
            to_state=status,
            decision_reason=remarks,
        )

        return complaint


def record_assessment(
    complaint: Complaint,
    engineer_id: int,
    assessment_details: str,
    is_site_visit_complete: bool = True,
) -> RepairAssessment:
    """Records engineer repair assessment."""
    if complaint.assigned_engineer_id != engineer_id:
        raise ValidationError("Only the assigned engineer can assess this complaint.")

    with transaction.atomic():
        outcome = transition(complaint.status, "record_assessment", "engineer")
        if not outcome.allowed:
            raise ValidationError(outcome.reason)

        assessment, _ = RepairAssessment.objects.update_or_create(
            complaint=complaint,
            defaults={
                "engineer_id": engineer_id,
                "assessment_details": assessment_details,
                "is_site_visit_complete": is_site_visit_complete,
            },
        )

        old_state = complaint.status
        complaint.status = outcome.next_state
        complaint.save(update_fields=["status", "updated_at"])

        record_audit_trail(
            complaint=complaint,
            actor_user_id=engineer_id,
            acting_role="engineer",
            action="record_assessment",
            from_state=old_state,
            to_state=complaint.status,
            decision_reason=assessment_details,
        )

        return assessment


def flag_urgent(
    complaint: Complaint,
    engineer_id: int,
    escalated_to: str,
) -> Complaint:
    """Flags urgent repair for fast-track attention (BR-IWD-012)."""
    if complaint.assigned_engineer_id != engineer_id:
        raise ValidationError("Only the assigned engineer can flag urgent escalation.")

    complaint.is_urgent_escalated = True
    complaint.urgent_escalated_at = timezone.now()
    complaint.urgent_escalated_to = escalated_to
    complaint.save(update_fields=["is_urgent_escalated", "urgent_escalated_at", "urgent_escalated_to", "updated_at"])

    record_audit_trail(
        complaint=complaint,
        actor_user_id=engineer_id,
        acting_role="engineer",
        action="flag_urgent",
        from_state=complaint.status,
        to_state=complaint.status,
        decision_reason=f"Flagged urgent to {escalated_to}",
    )
    return complaint
