"""Transactional year-end leave conversion services."""

from decimal import Decimal

from django.db import IntegrityError, transaction

from modules.elm.domain.leave_rules import (
    LeaveRuleError,
    convert_unused_vl_to_el,
)
from modules.elm.models import (
    LeaveBalance,
    LeaveType,
    YearEndConversion,
)


@transaction.atomic
def convert_vl_to_el(*, user_id: int, source_year: int) -> YearEndConversion:
    """Convert unused VL into next year's EL exactly once.

    The source year's VL balance is set to zero. Converted EL is credited
    to the next year's EL balance. Any failure rolls back all database
    changes.
    """
    if source_year < 1:
        raise LeaveRuleError("Source year must be a positive year.")

    # Lock an existing source balance while conversion is performed.
    try:
        vl_balance = LeaveBalance.objects.select_for_update().get(
            user_id=user_id,
            leave_type=LeaveType.VL,
            leave_year=source_year,
        )
    except LeaveBalance.DoesNotExist as exc:
        raise LeaveRuleError("No VL balance exists for this employee and source year.") from exc

    # A unique database constraint also prevents duplicate conversion rows.
    if YearEndConversion.objects.filter(
        user_id=user_id,
        source_year=source_year,
    ).exists():
        raise LeaveRuleError("VL conversion has already been recorded for this year.")

    unused_vl = vl_balance.available_balance
    converted_el = convert_unused_vl_to_el(unused_vl)

    # Find or create the next year's EL balance.
    el_balance, _ = LeaveBalance.objects.get_or_create(
        user_id=user_id,
        leave_type=LeaveType.EL,
        leave_year=source_year + 1,
        defaults={
            "entitlement": Decimal("0"),
            "available_balance": Decimal("0"),
        },
    )

    el_balance = LeaveBalance.objects.select_for_update().get(pk=el_balance.pk)

    el_balance.available_balance += converted_el
    el_balance.save(update_fields=["available_balance", "updated_at"])

    # VL itself does not carry forward after conversion.
    vl_balance.available_balance = Decimal("0")
    vl_balance.save(update_fields=["available_balance", "updated_at"])

    try:
        conversion = YearEndConversion.objects.create(
            user_id=user_id,
            source_year=source_year,
            unused_vl=unused_vl,
            converted_el=converted_el,
        )
    except IntegrityError as exc:
        # The atomic transaction rolls back the balance changes too.
        raise LeaveRuleError("VL conversion has already been recorded for this year.") from exc

    return conversion
