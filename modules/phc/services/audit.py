"""Audit trail service (PHC-BR-09, CFR-PHC-012, AFR-PHC-037)."""
import json
from typing import Any

from modules.phc.models.audit import PHCAuditTrail


def record_audit_event(
    target_type: str,
    target_id: str | int,
    action: str,
    details: dict[str, Any] | str,
    actor_user_id: int,
    actor_username: str,
) -> PHCAuditTrail:
    """Appends an immutable audit record for sensitive operations.

    Covered:
    - PATIENT_RECORD
    - INVENTORY_LEVEL
    - REIMBURSEMENT_CLAIM
    """
    detail_str = json.dumps(details) if isinstance(details, dict) else str(details)
    return PHCAuditTrail.objects.create(
        target_type=target_type,
        target_id=str(target_id),
        action=action,
        details=detail_str,
        actor_user_id=actor_user_id,
        actor_username=actor_username or f"user_{actor_user_id}",
    )
