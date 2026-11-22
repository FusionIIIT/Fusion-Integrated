from django.db.models import QuerySet

from modules.iaa.models import AuditLogEntry, AuditObservation
from modules.iaa.selectors.scoping import scope_audit_observations


def get_audit_observations(principal, status: str | None = None) -> QuerySet[AuditObservation]:
    qs = scope_audit_observations(AuditObservation.objects.all(), principal)
    if status:
        qs = qs.filter(status=status)
    return qs


def get_audit_observation_by_id(principal, observation_id: int) -> AuditObservation | None:
    return get_audit_observations(principal).filter(id=observation_id).first()


def get_audit_logs(
    target_type: str | None = None, target_id: int | None = None
) -> QuerySet[AuditLogEntry]:
    qs = AuditLogEntry.objects.all()
    if target_type:
        qs = qs.filter(target_type=target_type)
    if target_id is not None:
        qs = qs.filter(target_id=target_id)
    return qs
