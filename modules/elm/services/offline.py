"""Offline (paper) leave recorded after the fact, EL-UC-018 / BR-EL-029."""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.directory import contracts as directory
from modules.elm.domain import counting
from modules.elm.domain import enums as e
from modules.elm.models import LeaveRequest, LeaveRequestEvent
from modules.elm.services import accounts, calendars, config, notifications


def _fail(code: str, message: str):
    raise ConflictError(message, code=code)


@transaction.atomic
def record(*, actor, employee_user_id: int, category: str, start_date: date,
           end_date: date, half_day: str = "", sanction_reference: str = "",
           purpose: str = "") -> LeaveRequest:
    dto = directory.get_users([employee_user_id]).get(employee_user_id)
    if dto is None:
        _fail("bad_employee", "Unknown employee.")
    if category not in e.CATEGORIES:
        _fail("unknown_category", f"{category!r} is not a leave category.")
    if not config.type_config(category).active:
        _fail("category_inactive", f"{category} leave is not currently offered.")
    if not sanction_reference:
        _fail("reference_required",
              "Record the sanction reference of the paper approval.")

    cal = calendars.effective_calendar()
    try:
        days = counting.chargeable_days(
            category=category, start=start_date, end=end_date, half_day=half_day,
            closed_dates=calendars.closed_dates(cal))
    except counting.CountingError as exc:
        _fail("counting", str(exc))
    if days <= 0:
        _fail("no_days", "The period contains no chargeable leave days.")

    request = LeaveRequest.objects.create(
        user_id=employee_user_id, kind=e.NEW, category=category,
        start_date=start_date, end_date=end_date, half_day=half_day or "",
        days=days, purpose=purpose or "Recorded offline", department=dto.department,
        status=e.APPROVED, final_decision=e.APPROVE, is_offline=True,
        sanction_reference=sanction_reference, recorded_by_user_id=actor.user_id,
        decided_by_user_id=actor.user_id, decided_at=timezone.now(),
        route={"applicant_is_director": False, "establishment_required": False,
               "final_authority": "offline"})
    LeaveRequestEvent.objects.create(
        request=request, from_status=e.DRAFT, to_status=e.APPROVED,
        actor_user_id=actor.user_id, actor_role=e.SYSTEM,
        note=f"Offline record {sanction_reference}")

    account = accounts.ensure_account(employee_user_id, category, start_date.year)
    accounts.deduct(account=account, days=days, request=request,
                    actor_user_id=actor.user_id,
                    note=f"Offline sanction {sanction_reference}")
    notifications.enqueue(
        topic="record.offline", dedupe_key=f"offline:req{request.pk}",
        subject=f"Leave recorded offline for you (#{request.pk})",
        body=f"{category} leave {start_date}..{end_date} was recorded offline.",
        recipient_user_id=employee_user_id,
        payload={"request_id": request.pk})
    return request
