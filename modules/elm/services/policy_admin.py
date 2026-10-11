"""Leave setup: type versions and the holiday calendar (BR-12)."""
from __future__ import annotations

import logging
from datetime import date

from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.models import Holiday, LeaveType
from modules.elm.services import authz

log = logging.getLogger("fusion.elm.policy")
CODE_MAX = 12


def create_leave_type(*, actor, code: str, name: str, annual_entitlement_days,
                      counts_calendar_days: bool = False,
                      allows_half_day: bool = False,
                      requires_reason: bool = False,
                      effective_from: date | None = None) -> LeaveType:
    """A changed entitlement is a new version, never an edit of the old one."""
    authz.require(actor, "elm.policy.manage")
    code = (code or "").strip().upper()
    name = (name or "").strip()
    if not code or len(code) > CODE_MAX or not code.isalnum():
        raise ConflictError("A leave type code is 1-12 letters or digits, like CL.",
                            code="invalid_type_code")
    if not name:
        raise ConflictError("A leave type needs a name.", code="type_name_required")
    effective = effective_from or timezone.localdate()
    if LeaveType.objects.filter(code=code, effective_from=effective).exists():
        raise ConflictError(
            f"{code} already has a version effective {effective}; give the new"
            " version a later date.", code="type_version_exists")

    leave_type = LeaveType.objects.create(
        code=code, name=name, annual_entitlement_days=annual_entitlement_days,
        counts_calendar_days=counts_calendar_days,
        allows_half_day=allows_half_day, requires_reason=requires_reason,
        effective_from=effective,
        created_by_user_id=getattr(actor, "user_id", None))
    log.info("leave type %s v%s created by u%s", code, effective,
             getattr(actor, "user_id", None))
    return leave_type


def set_leave_type_active(*, actor, leave_type_id: int, is_active: bool) -> LeaveType:
    """Retiring a version stops offering it; history still resolves through it."""
    authz.require(actor, "elm.policy.manage")
    leave_type = LeaveType.objects.filter(pk=leave_type_id).first()
    if leave_type is None:
        raise NotFoundError("That leave type does not exist.",
                            code="leave_type_not_found")
    leave_type.is_active = bool(is_active)
    leave_type.save(update_fields=["is_active", "updated_at"])
    log.info("leave type %s v%s active=%s by u%s", leave_type.code,
             leave_type.effective_from, leave_type.is_active,
             getattr(actor, "user_id", None))
    return leave_type


def create_holiday(*, actor, on_date: date, name: str) -> Holiday:
    authz.require(actor, "elm.policy.manage")
    name = (name or "").strip()
    if not name:
        raise ConflictError("A holiday needs a name.", code="holiday_name_required")
    if Holiday.objects.filter(date=on_date).exists():
        raise ConflictError(f"{on_date} is already a holiday.", code="holiday_exists")
    holiday = Holiday.objects.create(
        date=on_date, name=name,
        created_by_user_id=getattr(actor, "user_id", None))
    log.info("holiday %s added by u%s", on_date, getattr(actor, "user_id", None))
    return holiday


def delete_holiday(*, actor, holiday_id: int) -> None:
    authz.require(actor, "elm.policy.manage")
    holiday = Holiday.objects.filter(pk=holiday_id).first()
    if holiday is None:
        raise NotFoundError("That holiday does not exist.", code="holiday_not_found")
    removed = holiday.date
    holiday.delete()
    log.info("holiday %s removed by u%s", removed, getattr(actor, "user_id", None))
