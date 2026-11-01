from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import AuditEvent, Notification, WorkflowRoute


def require(principal, permission):
    if (
        not principal
        or not principal.has_module("hreis")
        or not principal.has_permission(permission)
    ):
        raise PermissionDenied


def emit(principal, action, employee, request=None, details=None):
    audit = AuditEvent.objects.create(
        actor_id=principal.user_id,
        action=action,
        employee=employee,
        request=request,
        details=details or {},
    )
    Notification.objects.create(
        recipient_id=employee.user_id,
        request=request,
        event=action,
        payload={"details": details or {}},
    )
    return audit


def route_for(employee, kind):
    route = WorkflowRoute.objects.filter(
        employee_category=employee.category,
        request_kind=kind,
        department=employee.department,
        active=True,
    ).first()
    if not route:
        route = WorkflowRoute.objects.filter(
            employee_category=employee.category, request_kind=kind, department="", active=True
        ).first()
    if (
        not route
        or not isinstance(route.steps, list)
        or not route.steps
        or not all(type(s) is int and s > 0 for s in route.steps)
        or len(set(route.steps)) != len(route.steps)
    ):
        raise ValidationError("Invalid route configuration")
    return list(route.steps)
