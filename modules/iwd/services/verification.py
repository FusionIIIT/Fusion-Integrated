"""Department Head physical quality verification services (BR-IWD-014, BW-IWD-09, BW-IWD-10)."""

from django.utils import timezone

from modules.iwd.domain.state_machine import get_next_state
from modules.iwd.models import Complaint, DecisionAuditTrail, VerificationRecord


class MaxReworkExceededError(Exception):
    """Raised when an attempt is made to exceed the maximum permitted rework traversals."""


def verify_work(
    complaint_id: int, verifier_user_id: int, outcome: str, remarks: str = ""
) -> Complaint:
    """Verify completed repair quality; only verification resolves complaint (BR-IWD-014)."""
    complaint = Complaint.objects.get(id=complaint_id)
    prev = complaint.status

    if outcome == "Approved":
        action = "verify_approved"
        complaint.status = get_next_state(prev, action, "iwd_department_head")
        complaint.is_resolved = True
        complaint.resolved_at = timezone.now()
    else:
        if complaint.rework_count >= 1:
            raise MaxReworkExceededError("BW-IWD-10: Only one rework traversal is permitted.")
        action = "verify_rework"
        complaint.rework_count += 1
        complaint.status = get_next_state(
            prev, action, "iwd_department_head", {"rework_count": complaint.rework_count - 1}
        )

    complaint.save()

    VerificationRecord.objects.create(
        complaint=complaint,
        verifier_user_id=verifier_user_id,
        outcome=outcome,
        remarks=remarks,
        traversal_number=complaint.rework_count,
    )

    DecisionAuditTrail.objects.create(
        complaint=complaint,
        actor_user_id=verifier_user_id,
        actor_role="iwd_department_head",
        action=action,
        previous_state=prev,
        new_state=complaint.status,
        remarks=remarks,
    )
    return complaint
