from django.db.models import Q

from modules.hreis.models import AuditEvent, EmployeeServiceRecord, HRRequest, NotificationRecord


def employee_record_for(actor):
    if actor is None:
        return EmployeeServiceRecord.objects.none()
    if actor.has_permission("hreis.employee.manage"):
        return EmployeeServiceRecord.objects.all()
    return EmployeeServiceRecord.objects.filter(user_id=actor.user_id)


def requests_for(actor):
    if actor is None:
        return HRRequest.objects.none()
    if actor.has_permission("hreis.request.manage"):
        return HRRequest.objects.all()
    visible = Q(owner_user_id=actor.user_id)
    if actor.active_role:
        visible |= Q(current_authority_designation=actor.active_role)
    return HRRequest.objects.filter(visible).prefetch_related("decisions").distinct()


def notifications_for(actor):
    if actor is None:
        return NotificationRecord.objects.none()
    return NotificationRecord.objects.filter(user_id=actor.user_id)


def audit_events_for(actor):
    if actor is None or not actor.has_permission("hreis.audit.view"):
        return AuditEvent.objects.none()
    return AuditEvent.objects.all()
