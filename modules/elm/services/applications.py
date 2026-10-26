"""Applying, modifying and withdrawing (WF-EL-01, WF-EL-02)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction

from modules.directory import contracts as directory
from modules.elm.domain import balances as balance_rules
from modules.elm.domain import calculation as calc
from modules.elm.domain import eligibility as elig
from modules.elm.domain import leave_types as lt
from modules.elm.domain import workflow as wf
from modules.elm.domain.errors import RuleViolation
from modules.elm.models import LeaveApplication
from modules.elm.selectors import applications as sel
from modules.elm.services import balances
from modules.elm.services.common import (
    PERMISSION_FOR_OWNER,
    announce_task,
    enforcing_rules,
    load,
    move,
    notify,
    require_owner,
    require_status,
)

P_SELF_SANCTION = "elm.leave.self_sanction"
EMPLOYEE_KINDS = (lt.FACULTY, lt.STAFF)


def _check_substitute(user_id: int, data: dict[str, Any]) -> None:
    substitute_id = data.get("substitute_user_id")
    if not substitute_id:
        return
    person = directory.get_users([substitute_id]).get(substitute_id)
    elig.check_substitute(
        user_id, substitute_id,
        substitute_is_employee=bool(person and person.kind in EMPLOYEE_KINDS),
        substitute_has_overlap=sel.has_overlap(
            substitute_id, data["start_date"], data["end_date"]))


def validate_request(*, user_id: int, kind: str, data: dict[str, Any],
                     exclude_id: int | None = None) -> Decimal:
    """Every rule that must hold before a request, or a changed request, is accepted."""
    leave_type, start, end = data["leave_type"], data["start_date"], data["end_date"]
    elig.check_category(kind, leave_type)
    days = calc.leave_days(leave_type, start, end, data.get("half_day", lt.NO_HALF),
                           sel.closed_days(start, end))
    if leave_type in (lt.CL, lt.SCL) and start.year != end.year:
        raise RuleViolation(f"{leave_type} cannot cross a calendar year; split the request.",
                            "BR-EL-002")
    if leave_type == lt.RH:
        elig.check_restricted_holiday(start, sel.published_restricted_holidays(start.year))
    if leave_type == lt.VL:
        elig.check_vacation_periods(start, end, sel.vacation_periods(start, end))
    elig.check_medical_evidence(leave_type, data.get("medical_reference", ""))
    if data.get("station_leave") and not data.get("station_address", "").strip():
        raise RuleViolation("Station leave needs the address you will stay at.", "BR-EL-013")
    clash = calc.find_overlap(calc.Period(start, end, data.get("half_day", lt.NO_HALF)),
                              sel.active_periods(user_id, exclude_id))
    if clash:
        raise RuleViolation(
            f"This overlaps your leave from {clash.start} to {clash.end}.", "BR-EL-012")
    if leave_type == lt.SCL:
        balance_rules.check_scl_ceiling(days, sel.scl_days_held(user_id, start.year, exclude_id))
    balances.ensure_balances(user_id, start.year, kind)
    balances.check_available(user_id, start.year, leave_type, days, exclude_id)
    _check_substitute(user_id, data)
    return days


def fields_of(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "leave_type": data["leave_type"], "start_date": data["start_date"],
        "end_date": data["end_date"], "half_day": data.get("half_day", lt.NO_HALF),
        "special_purpose": data.get("special_purpose", ""),
        "medical_reference": data.get("medical_reference", ""),
        "station_leave": bool(data.get("station_leave")),
        "station_address": data.get("station_address", ""),
        "substitute_user_id": data.get("substitute_user_id") or None,
    }


@transaction.atomic
def submit(principal, data: dict[str, Any], *,
           extends: LeaveApplication | None = None) -> LeaveApplication:
    with enforcing_rules():
        days = validate_request(user_id=principal.user_id, kind=principal.kind, data=data)
        is_director = principal.has_permission(P_SELF_SANCTION)
        first = wf.first_state(substitute_required=bool(data.get("substitute_user_id")),
                               is_director=is_director)
    application = LeaveApplication.objects.create(
        user_id=principal.user_id, applicant_kind=principal.kind, days=days,
        is_director=is_director, status=first, extends=extends, **fields_of(data))
    event = move(application, first, action="submitted", actor_id=principal.user_id,
                 first=True)
    application.save()
    announce_task(application, f"ev{event.pk}")
    return application


@transaction.atomic
def modify(principal, pk: int, data: dict[str, Any]) -> LeaveApplication:
    """BR-EL-021: revalidate, and supersede whatever the old data had set in motion."""
    application = load(pk)
    require_owner(principal, application)
    require_status(application, *wf.MODIFIABLE)
    with enforcing_rules():
        if application.pending_action:
            raise RuleViolation("A cancellation request cannot be modified.", "BR-EL-021")
        if application.extends_id and data["leave_type"] != application.leave_type:
            raise RuleViolation("An extension keeps the leave type it extends.", "BR-EL-025")
        days = validate_request(user_id=application.user_id, kind=principal.kind, data=data,
                                exclude_id=application.pk)
        first = wf.first_state(substitute_required=bool(data.get("substitute_user_id")),
                               is_director=application.is_director)
    for name, value in fields_of(data).items():
        setattr(application, name, value)
    application.days = days
    application.unit_head_recommendation = ""
    event = move(application, first, action="modified", actor_id=principal.user_id,
                 note="Revalidated; earlier tasks superseded.")
    application.save()
    announce_task(application, f"ev{event.pk}")
    return application


@transaction.atomic
def withdraw(principal, pk: int) -> LeaveApplication:
    """BR-EL-022: immediate, closes the open task, tells whoever was waiting."""
    application = load(pk)
    require_owner(principal, application)
    require_status(application, *wf.PENDING)
    waiting_on = wf.TASK_OWNER.get(application.status)
    cancelling = bool(application.pending_action)
    target = wf.APPROVED if cancelling else wf.WITHDRAWN
    event = move(application, target, action=(
        "cancellation_withdrawn" if cancelling else "withdrawn"), actor_id=principal.user_id,
        role=wf.EMPLOYEE)
    application.pending_action = ""
    application.save()
    label = f"{application.leave_type} {application.start_date}..{application.end_date}"
    if application.substitute_user_id:
        notify(application, "leave.withdrawn",
               f"A leave you were named for was withdrawn: {label}.",
               user_id=application.substitute_user_id, key=f"ev{event.pk}")
    if waiting_on in PERMISSION_FOR_OWNER:
        notify(application, "leave.withdrawn", f"A leave awaiting you was withdrawn: {label}.",
               permission=PERMISSION_FOR_OWNER[waiting_on], key=f"ev{event.pk}")
    return application
