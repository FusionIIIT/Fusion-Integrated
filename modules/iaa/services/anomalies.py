"""Material anomaly service enforcing IAA-BR-103, IAA-UC-302, IAA-UC-303, IAA-UC-304."""

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.iaa.domain.state_machine import transition_anomaly
from modules.iaa.models import Anomaly, AnomalyStatus
from modules.iaa.services.audit_trail import record_audit_log


def create_anomaly(
    category: str,
    description: str,
    reference_type: str,
    reference_id: int,
    flagged_by_id: int | None = None,
    flagged_by_role: str = "system",
    resolver_role: str = "finance_staff",
) -> Anomaly:
    with transaction.atomic():
        anomaly = Anomaly.objects.create(
            category=category,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            status=AnomalyStatus.OPEN,
            flagged_by_id=flagged_by_id,
            flagged_by_role=flagged_by_role,
            resolver_role=resolver_role,
        )
        record_audit_log(
            user_id=flagged_by_id or 0,
            acting_role=flagged_by_role,
            action="flag_anomaly",
            target_type="anomaly",
            target_id=anomaly.id,
            resulting_status=AnomalyStatus.OPEN,
            details={"category": category, "ref_type": reference_type, "ref_id": reference_id},
        )
        return anomaly


def resolve_or_escalate_anomaly(
    anomaly_id: int,
    actor_id: int,
    actor_role: str,
    action: str,  # "resolve" or "escalate"
    remarks: str,
) -> Anomaly:
    with transaction.atomic():
        anomaly = Anomaly.objects.select_for_update().filter(id=anomaly_id).first()
        if not anomaly:
            raise NotFoundError("Anomaly not found.")

        new_status = transition_anomaly(anomaly.status, action, "resolver")
        anomaly.status = new_status
        anomaly.resolution_remarks = remarks
        if new_status == AnomalyStatus.RESOLVED:
            anomaly.resolved_by_id = actor_id
            anomaly.resolved_at = timezone.now()
        anomaly.save()

        record_audit_log(
            user_id=actor_id,
            acting_role=actor_role,
            action=f"anomaly_{action}",
            target_type="anomaly",
            target_id=anomaly.id,
            resulting_status=new_status,
            details={"remarks": remarks},
        )
        return anomaly
