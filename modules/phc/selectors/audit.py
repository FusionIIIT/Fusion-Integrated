"""Audit trail selectors (CFR-PHC-012, AFR-PHC-037; PHC-BR-09)."""
from modules.phc.models.audit import PHCAuditTrail


def list_audit_trail_events(
    target_type: str | None = None,
    limit: int = 100,
) -> list[PHCAuditTrail]:
    qs = PHCAuditTrail.objects.all()
    if target_type:
        qs = qs.filter(target_type=target_type)
    return list(qs.order_by("-created_at")[:limit])
