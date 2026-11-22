from django.db.models import QuerySet

from modules.hr.models import AuditEvent


def audit_events() -> QuerySet[AuditEvent]:
    return AuditEvent.objects.all()
