"""Selectors for audit logs and notifications."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.spacs.models import SpacsAuditLog, SpacsNotification


def visible_audit_logs(principal) -> QuerySet[SpacsAuditLog]:
    """Visible audit trail (CFR-SPACS-016, BR-SPACS-021). Restricted to authorized personnel."""
    if principal is None or not principal.has_permission("spacs.audit.view"):
        return SpacsAuditLog.objects.none()
    return SpacsAuditLog.objects.all()


def visible_notifications(principal) -> QuerySet[SpacsNotification]:
    """Visible notifications for caller (BR-SPACS-008)."""
    if principal is None:
        return SpacsNotification.objects.none()
    return SpacsNotification.objects.filter(recipient_user_id=principal.user_id)
