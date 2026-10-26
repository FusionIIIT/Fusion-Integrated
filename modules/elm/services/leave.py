"""Leave application lifecycle. BR-EL-034: there is deliberately no edit function."""

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType

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


def _load_for_update(application_id):
    try:
        return LeaveApplication.objects.select_for_update().get(id=application_id)
    except LeaveApplication.DoesNotExist:
        raise NotFoundError("Leave application not found.", code="not_found") from None


def get_balance(employee_id, leave_type, year, for_update=False):
    """BR-EL-001 get leave balance."""
    rows = LeaveBalance.objects.select_for_update() if for_update else LeaveBalance.objects
    try:
        return rows.get(employee_id=employee_id, leave_type=leave_type, year=year)
    except LeaveBalance.DoesNotExist:
        raise NotFoundError("No leave balance for this leave type.", code="no_balance") from None


def _balance_of(application):
    """The locked balance row an application draws from."""
    return get_balance(
        application.employee_id, application.leave_type, application.start_date.year,
        for_update=True,
    )


def apply(actor, leave_type_id, start_date, end_date, reason):
    """BR-EL-011 apply for leave."""
    require(actor, "leave_elm.application.apply")
    with transaction.atomic():
        try:
            leave_type = LeaveType.objects.get(id=leave_type_id, is_active=True)
        except LeaveType.DoesNotExist:
            raise NotFoundError("Leave type not found.", code="not_found") from None
        days = count_days(start_date, end_date)
        overlapping = LeaveApplication.objects.filter(
            employee_id=actor.user_id,
            status__in=ACTIVE,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if overlapping.exists():
            raise ConflictError("These dates overlap another leave application.", code="overlap")
        balance = get_balance(actor.user_id, leave_type, start_date.year, for_update=True)
        if balance.allotted - balance.used < days:
            raise ConflictError("Not enough leave balance.", code="insufficient_balance")
        return LeaveApplication.objects.create(
            employee_id=actor.user_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days=days,
            reason=reason,
            status="SUBMITTED",
        )


def decide(actor, application_id, approve: bool, remarks=""):
    """BR-EL-036 decide on leave application."""
    require(actor, "leave_elm.application.approve")
    with transaction.atomic():
        application = _load_for_update(application_id)
        if application.status != "SUBMITTED":
            raise ConflictError("Only a pending application can be decided.", code="not_pending")
        if application.employee_id == actor.user_id:
            raise PermissionDeniedError("Cannot approve own application.", code="self_approval")
        if approve:
            balance = _balance_of(application)
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


def withdraw(actor, application_id):
    """BR-EL-022 withdraw leave application."""
    require(actor, "leave_elm.application.apply")
    with transaction.atomic():
        application = _load_for_update(application_id)
        if application.status != "SUBMITTED":
            raise ConflictError("Only a pending application can be withdrawn.", code="not_pending")
        if application.employee_id != actor.user_id:
            raise PermissionDeniedError(
                "Cannot withdraw other's application.", code="permission_denied"
            )
        application.status = "CANCELLED"
        application.save()
    return application


def cancel_approved(actor, application_id):
    """BR-EL-023 cancel approved leave application."""
    require(actor, "leave_elm.application.apply")
    with transaction.atomic():
        application = _load_for_update(application_id)
        if application.status != "APPROVED" or application.start_date <= timezone.now().date():
            raise ConflictError(
                "Only approved leave that has not started can be cancelled.", code="not_cancellable"
            )
        if application.employee_id != actor.user_id:
            raise PermissionDeniedError(
                "Cannot cancel other's application.", code="permission_denied"
            )
        balance = _balance_of(application)
        balance.used -= application.days
        balance.save()
        application.status = "CANCELLED"
        application.save()
    return application
