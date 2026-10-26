"""Leave Admin maintenance. BR-EL-037: maintenance is not sanctioning; nothing here approves."""

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.elm.models import LeaveBalance, LeaveType
from modules.elm.services.leave import require


def create_leave_type(actor, code, name, max_days_per_year, requires_document=False):
    require(actor, "leave_elm.policy.manage")
    if LeaveType.objects.filter(code=code).exists():
        raise ConflictError("A leave type with this code already exists.", code="duplicate_code")
    return LeaveType.objects.create(
        code=code,
        name=name,
        max_days_per_year=max_days_per_year,
        requires_document=requires_document,
    )


def allot_balance(actor, employee_id, leave_type_id, year, allotted):
    require(actor, "leave_elm.policy.manage")
    with transaction.atomic():
        try:
            leave_type = LeaveType.objects.select_for_update().get(id=leave_type_id)
        except LeaveType.DoesNotExist:
            raise NotFoundError("Leave type not found.", code="not_found") from None
        if allotted > leave_type.max_days_per_year:
            raise BadRequestError(
                "Allotment exceeds the leave type's maximum days per year.", code="above_max"
            )
        balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
            employee_id=employee_id,
            leave_type=leave_type,
            year=year,
            defaults={"allotted": allotted, "used": 0},
        )
        if allotted < balance.used:
            raise ConflictError("Allotment cannot be below days already used.", code="below_used")
        balance.allotted = allotted
        balance.save()
        return balance
