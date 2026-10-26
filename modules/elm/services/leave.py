from datetime import datetime
from django.db import transaction
from django.utils import timezone
from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.models import LeaveType, LeaveBalance, LeaveApplication
from modules.elm import application as leave_elm_application


def require(actor, code):
    if actor is None or not actor.has_permission(code):
        raise PermissionDeniedError(f"This action needs {code}.", code="permission_denied")


def count_days(start, end):
    if end < start:
        raise BadRequestError("End date is before start date.", code="invalid_dates")
    return (end - start).days + 1


def get_balance(employee_id, leave_type, year):
    try:
        return LeaveBalance.objects.get(employee_id=employee_id, leave_type=leave_type, year=year)
    except LeaveBalance.DoesNotExist:
        raise NotFoundError("No leave balance for this leave type.", code="no_balance")


@transaction.atomic
def apply(actor, leave_type_id, start_date, end_date, reason):
    require(actor, "leave_elm.application.apply")
    leave_type = LeaveType.objects.get(id=leave_type_id)
    if not leave_type.is_active:
        raise BadRequestError("Leave type is not active.", code="inactive_leave_type")
    days = count_days(start_date, end_date)
    balance = get_balance(actor.user_id, leave_type, start_date.year)
    if balance.allotted - balance.used < days:
        raise ConflictError("Insufficient leave balance.", code="insufficient_balance")
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


@transaction.atomic
def decide(actor, application_id, approve: bool, remarks=""):
    require(actor, "leave_elm.application.approve")
    application = LeaveApplication.objects.select_for_update().get(id=application_id)
    if application.status not in ("SUBMITTED",):
        raise ConflictError("Application is not pending.", code="not_pending")
    if application.employee_id == actor.user_id:
        raise PermissionDeniedError("Cannot approve own application.", code="self_approval")
    if approve:
        balance = get_balance(application.employee_id, application.leave_type, application.start_date.year)
        with transaction.atomic():
            balance.used += application.days
            balance.save()
        application.status = "APPROVED"
    else:
        application.status = "REJECTED"
    application.approver_id = actor.user_id
    application.remarks = remarks
    application.decided_at = timezone.now()
    application.save()
    return application


@transaction.atomic
def withdraw(actor, application_id):
    require(actor, "leave_elm.application.withdraw")
    application = LeaveApplication.objects.select_for_update().get(id=application_id)
    if application.status != "SUBMITTED":
        raise ConflictError("Application is not pending.", code="not_pending")
    if application.employee_id != actor.user_id:
        raise PermissionDeniedError("Cannot withdraw other's application.", code="permission_denied")
    application.status = "CANCELLED"
    application.save()


@transaction.atomic
def cancel_approved(actor, application_id):
    require(actor, "leave_elm.application.cancel_approved")
    application = LeaveApplication.objects.select_for_update().get(id=application_id)
    if application.status != "APPROVED":
        raise ConflictError("Application is not approved.", code="not_approved")
    if application.start_date < timezone.now().date():
        raise ConflictError("Cannot cancel approved leave before start date.", code="invalid_date")
    balance = get_balance(application.employee_id, application.leave_type, application.start_date.year)
    with transaction.atomic():
        balance.used -= application.days
        balance.save()
    application.status = "CANCELLED"
    application.save()
