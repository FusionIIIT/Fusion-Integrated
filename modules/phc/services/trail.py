"""Audit trail (PHC-BR-09) and claimant/originator notifications (PHC-BR-11, PHC-BR-13)."""
from __future__ import annotations

from modules.phc.models import AuditRecord, Notification


def audit(*, actor_user_id: int, resource_type: str, resource_id: int, action: str,
          details: dict | None = None) -> AuditRecord:
    return AuditRecord.objects.create(actor_user_id=actor_user_id, resource_type=resource_type,
                                      resource_id=resource_id, action=action,
                                      details=details or {})


def notify(*, recipient_user_id: int, kind: str, message: str, resource_type: str,
           resource_id: int) -> Notification:
    return Notification.objects.create(recipient_user_id=recipient_user_id, kind=kind,
                                       message=message, resource_type=resource_type,
                                       resource_id=resource_id)
