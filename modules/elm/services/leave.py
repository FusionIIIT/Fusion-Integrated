from django.db import transaction
from django.utils import timezone
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.models import LeaveType, LeaveBalance, LeaveApplication


ACTIVE = ("SUBMITTED", "APPROVED")


def require(actor, code):
    """Admit the actor, or raise PermissionDeniedError."""
    if actor is None or not actor.has_permission(code):
        raise PermissionDeniedError("This action needs " + code + ".", code="permission_denied")


def count_days(start, end):
    """BR-EL-011 continuous-day counting, inclusive (end - start).days + 1."""
    if end < start:
        raise BadRequestError("End date is before start date.", code="invalid_dates")
    return (end - start).days + 1


def get_balance(employee_id, leave_type, year):
    """BR-EL-001 get leave balance."""
    try:
        return LeaveBalance.objects.get(employee_id=employee_id, leave_type=leave_type, year=year)
    except LeaveBalance.DoesNotExist:
        raise NotFoundError("No leave balance for this leave type.", code="no_balance")


def apply(actor, leave_type_id, start_date, end_date, reason):
    """BR-EL-001 apply for leave."""
    require(actor, "leave_elm.application.apply")
    leave_type = LeaveType.objects.get(id=leave_type_id, is_active=True)
    days = count_days(start_date, end_date)
    if LeaveApplication.objects.filter(employee_id=actor.user_id, status__in=ACTIVE, start_date__lte=end_date, end_date__gte=start_date).exists():
        raise ConflictError(code="overlap")
    balance = get_balance(actor.user_id, leave_type, start_date.year)
    if balance.allotted - balance.used < days:
        raise ConflictError(code="insufficient_balance")
    with transaction.atomic():
        application = LeaveApplication.objects.create(
            employee_id=actor.user_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days=days,
            reason=reason,
            status="SUBMITTED"
        )
    return application


def decide(actor, application_id, approve: bool, remarks=""):
    """BR-EL-001 decide on leave application."""
    require(actor, "leave_elm.application.approve")
    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().get(id=application_id, status="SUBMITTED")
        if application.employee_id == actor.user_id:
            raise PermissionDeniedError("Cannot approve own application.", code="self_approval")
        if approve:
            balance = get_balance(application.employee_id, application.leave_type, application.start_date.year)
            balance.used += application.days
            balance.save(update_fields=["used", "updated_at"])
            application.status = "APPROVED"
        else:
            application.status = "REJECTED"
        application.approver_id = actor.user_id
        application.remarks = remarks
        application.decided_at = timezone.now()
        application.save()
    return application


def withdraw(actor, application_id):
    """BR-EL-022 withdraw leave application."""
    require(actor, "leave_elm.application.withdraw")
    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().get(id=application_id, status="SUBMITTED")
        if application.employee_id != actor.user_id:
            raise PermissionDeniedError("Cannot withdraw other's application.", code="permission_denied")
        application.status = "CANCELLED"
        application.save(update_fields=["status", "updated_at"])
    return application


def cancel_approved(actor, application_id):
    """BR-EL-023 cancel approved leave application."""
    require(actor, "leave_elm.application.cancel")
    with transaction.atomic():
        application = LeaveApplication.objects.select_for_update().get(id=application_id, status="APPROVED", start_date__gt=timezone.now().date())
        if application.employee_id != actor.user_id:
            raise PermissionDeniedError("Cannot cancel other's application.", code="permission_denied")
        balance = get_balance(application.employee_id, application.leave_type, application.start_date.year)
        balance.used -= application.days
        balance.save(update_fields=["used", "updated_at"])
        application.status = "CANCELLED"
        application.save(update_fields=["status", "updated_at"])
    return application
