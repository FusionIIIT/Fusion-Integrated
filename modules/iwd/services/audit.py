
from modules.iwd.models.audit import DecisionAuditTrail
from modules.iwd.models.complaint import Complaint
from modules.iwd.models.estimate import RepairEstimate


def record_audit_trail(
    complaint: Complaint,
    actor_user_id: int,
    acting_role: str,
    action: str,
    from_state: str,
    to_state: str,
    decision_reason: str = "",
    estimate: RepairEstimate | None = None,
) -> DecisionAuditTrail:
    """Records an immutable audit entry (BR-IWD-013)."""
    return DecisionAuditTrail.objects.create(
        complaint=complaint,
        estimate=estimate,
        actor_user_id=actor_user_id,
        acting_role=acting_role,
        action=action,
        from_state=from_state,
        to_state=to_state,
        decision_reason=decision_reason,
    )
