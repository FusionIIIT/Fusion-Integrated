"""Apply, modify, withdraw, cancel and extend (EL-UC-001, 006..009)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from fusion_auth.client import IamUnavailable
from modules.directory import contracts as directory
from modules.elm.domain import categories as c
from modules.elm.domain import counting, overlap, routing
from modules.elm.domain import permissions as p
from modules.elm.domain import policy as policy_domain
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, PolicyVersion
from modules.elm.selectors import config as config_sel
from modules.elm.selectors import ledger as ledger_sel
from modules.elm.services import ledger, notify
from modules.elm.services.authz import DirectoryUnavailable, require
from modules.elm.services.transitions import enter_stage, move


class LeaveInvalid(DomainError):
    code = "leave_invalid"


@dataclass
class LeaveInput:
    category: str
    start_date: date
    end_date: date
    purpose: str
    half: str = ""
    medical_evidence: str = ""
    station_leave: bool = False
    station_from: date | None = None
    station_to: date | None = None
    station_address: str = ""
    substitute_user_id: int | None = None
    responsibility: str = ""


def _policy() -> tuple[PolicyVersion, policy_domain.Policy, dict]:
    pv = config_sel.effective_policy()
    if pv is None:
        raise ConflictError(
            "No leave policy has been published yet. Ask the Leave Administrator to "
            "publish one before applying.", code="no_policy")
    return pv, policy_domain.parse(pv.params), routing.parse_hierarchy(pv.hierarchy)


def _employee(user_ids):
    try:
        return directory.get_users(user_ids)
    except IamUnavailable as exc:
        raise DirectoryUnavailable() from exc


def _interval(r: LeaveRequest) -> overlap.Interval:
    end = r.end_date
    if r.status == sm.CLOSED and r.actual_return_date:
        end = min(end, date.fromordinal(r.actual_return_date.toordinal() - 1))
    return overlap.Interval(r.start_date, end, r.half or None)


def _active_overlap(user_id: int, want: overlap.Interval,
                    exclude: set[int]) -> LeaveRequest | None:
    qs = (LeaveRequest.objects
          .filter(user_id=user_id, status__in=sm.ACTIVE,
                  start_date__lte=want.end, end_date__gte=want.start)
          .exclude(pk__in=exclude))
    for r in qs:
        i = _interval(r)
        if i.end >= i.start and overlap.overlaps(i, want):
            return r
    return None


def _validate(actor, data: LeaveInput, *, kind: str, exclude: set[int],
              policy: policy_domain.Policy) -> Decimal:
    if kind not in c.EMPLOYEE_KINDS:
        raise PermissionDeniedError("Only faculty and staff can apply for leave.",
                                    code="not_employee")
    if data.category not in c.ALL:
        raise BadRequestError("Choose a valid leave category.", code="invalid_category")
    if not (data.purpose or "").strip():
        raise LeaveInvalid("Give the purpose or reason for the leave.")
    try:
        policy.check_eligible(kind, data.category)
    except policy_domain.NotEligible as exc:
        raise LeaveInvalid(str(exc), code="not_eligible") from exc

    cal = config_sel.calendar_for(config_sel.effective_calendar_version())
    try:
        days = counting.chargeable_days(data.category, data.start_date, data.end_date,
                                        data.half or None, cal)
        if data.category == c.RH:
            counting.validate_rh_dates(data.start_date, data.end_date, cal)
        if data.category == c.VL:
            counting.validate_vacation(data.start_date, data.end_date, cal)
    except counting.InvalidPeriod as exc:
        raise LeaveInvalid(str(exc), code="invalid_period") from exc

    if (data.category == c.COL and policy.col_requires_medical_evidence
            and not data.medical_evidence.strip()):
        raise LeaveInvalid("Commuted Leave needs a medical certificate reference.",
                           code="medical_evidence_required")
    if data.station_leave:
        if not (data.station_from and data.station_to and data.station_address.strip()):
            raise LeaveInvalid("Station Leave needs the dates away and an address.",
                               code="station_leave_incomplete")
        if data.station_to < data.station_from:
            raise LeaveInvalid("Station Leave cannot end before it starts.",
                               code="station_leave_incomplete")

    clash = _active_overlap(actor.user_id, overlap.Interval(
        data.start_date, data.end_date, data.half or None), exclude)
    if clash is not None:
        raise LeaveInvalid(
            f"These dates overlap your leave #{clash.pk} "
            f"({clash.start_date} to {clash.end_date}).", code="overlap")

    ledger.ensure_annual_credits(actor.user_id, kind, data.start_date.year, policy)
    available = (ledger_sel.balances(actor.user_id)[data.category]
                 - ledger_sel.pending_days(actor.user_id, None)[data.category])
    for pk in exclude:
        r = LeaveRequest.objects.filter(pk=pk, status__in=sm.PENDING,
                                        category=data.category).first()
        if r is not None:
            available += r.days
    if days > available:
        raise LeaveInvalid(
            f"You have {available} day(s) of {c.LABELS[data.category]} available; "
            f"this request needs {days}.", code="insufficient_balance")

    if data.substitute_user_id is not None:
        _validate_substitute(actor.user_id, data.substitute_user_id,
                             data.start_date, data.end_date)
    return days


def _validate_substitute(applicant_id: int, nominee_id: int, start: date,
                         end: date) -> None:
    if nominee_id == applicant_id:
        raise LeaveInvalid("You cannot nominate yourself as substitute.",
                           code="invalid_substitute")
    nominee = _employee([nominee_id]).get(nominee_id)
    if nominee is None or nominee.kind not in c.EMPLOYEE_KINDS:
        raise LeaveInvalid("The substitute must be another faculty or staff member.",
                           code="invalid_substitute")
    if _active_overlap(nominee_id, overlap.Interval(start, end), set()) is not None:
        raise LeaveInvalid("The nominated substitute has leave during this period.",
                           code="substitute_unavailable")


def _route(actor, data: LeaveInput, kind: str, unit: str, hierarchy: dict) -> list[dict]:
    try:
        steps = routing.resolve_route(category=data.category, kind=kind, unit=unit,
                                      applicant_roles=getattr(actor, "roles", ()),
                                      hierarchy=hierarchy)
    except routing.RouteUnresolved as exc:
        raise LeaveInvalid(str(exc), code="route_unresolved") from exc
    return [s.as_dict() for s in steps]


def _fill(req: LeaveRequest, data: LeaveInput) -> None:
    for f in ("category", "start_date", "end_date", "purpose", "medical_evidence",
              "station_leave", "station_from", "station_to", "station_address",
              "substitute_user_id", "responsibility"):
        setattr(req, f, getattr(data, f))
    req.half = data.half or ""
    if not data.station_leave:
        req.station_from = req.station_to = None
        req.station_address = ""


def _enter_routing(req: LeaveRequest, *, keep_consent: bool) -> str:
    req.recommendation = ""
    if req.substitute_user_id is not None and not keep_consent:
        req.substitute_status = "requested"
        req.stage, req.current_role = 0, ""
        req.stage_entered_at = timezone.now()
        return sm.AWAITING_SUBSTITUTE
    if req.substitute_user_id is None:
        req.substitute_status = ""
    return enter_stage(req, 0)


def _announce(req: LeaveRequest) -> None:
    if req.status == sm.AWAITING_SUBSTITUTE:
        notify.to_user(req.substitute_user_id, req,
                       f"You have been nominated as substitute for leave #{req.pk}.")
    elif req.current_role:
        notify.to_role(req.current_role, req, f"Leave #{req.pk} awaits your action.")


def apply(actor, data: LeaveInput) -> LeaveRequest:
    require(actor, p.P_CREATE)
    pv, policy, hierarchy = _policy()
    kind = getattr(actor, "kind", "")
    unit = (_employee([actor.user_id]).get(actor.user_id) or None)
    unit = unit.department if unit else ""
    with transaction.atomic():
        ledger.lock_employee(actor.user_id)
        days = _validate(actor, data, kind=kind, exclude=set(), policy=policy)
        req = LeaveRequest(user_id=actor.user_id, kind=LeaveRequest.LEAVE,
                           applicant_kind=kind, applicant_unit=unit, days=days,
                           policy_version_id=pv.pk, status=sm.NEW)
        _fill(req, data)
        req.route = _route(actor, data, kind, unit, hierarchy)
        to = _enter_routing(req, keep_consent=False)
        req.pk = None
        req.status = sm.NEW
        move(req, event=sm.SUBMIT, actor_kind=sm.EMPLOYEE, to=to, actor=actor)
        _announce(req)
        return req


def _own_locked(actor, pk: int) -> LeaveRequest:
    req = (LeaveRequest.objects.select_for_update()
           .filter(pk=pk, user_id=actor.user_id).first())
    if req is None:
        raise NotFoundError("No such leave request.")
    return req


def modify(actor, pk: int, data: LeaveInput) -> LeaveRequest:
    require(actor, p.P_UPDATE)
    pv, policy, hierarchy = _policy()
    with transaction.atomic():
        ledger.lock_employee(actor.user_id)
        req = _own_locked(actor, pk)
        if req.status not in sm.PENDING:
            raise ConflictError("Only a pending request can be modified. After approval, "
                                "request a cancellation instead.", code="not_modifiable")
        if req.kind != LeaveRequest.LEAVE:
            raise ConflictError("An extension cannot be modified; withdraw it and submit "
                                "a new one.", code="not_modifiable")
        keep = (req.substitute_status == "accepted"
                and data.substitute_user_id == req.substitute_user_id
                and data.start_date == req.start_date and data.end_date == req.end_date)
        days = _validate(actor, data, kind=req.applicant_kind, exclude={req.pk},
                         policy=policy)
        old = req.status
        _fill(req, data)
        req.days, req.policy_version_id = days, pv.pk
        req.route = _route(actor, data, req.applicant_kind, req.applicant_unit, hierarchy)
        to = _enter_routing(req, keep_consent=keep)
        req.status = old
        move(req, event=sm.MODIFY, actor_kind=sm.EMPLOYEE, to=to, actor=actor,
             note="Modified; earlier substitute/review/sanction tasks superseded.")
        _announce(req)
        return req


def renominate(actor, pk: int, substitute_user_id: int, responsibility: str = "") -> LeaveRequest:
    require(actor, p.P_UPDATE)
    with transaction.atomic():
        req = _own_locked(actor, pk)
        if req.status != sm.SUBSTITUTE_DECLINED:
            raise ConflictError("A new substitute can only be nominated after the "
                                "previous one declined.", code="not_declined")
        _validate_substitute(actor.user_id, substitute_user_id, req.start_date,
                             req.end_date)
        req.substitute_user_id = substitute_user_id
        req.substitute_status = "requested"
        req.responsibility = responsibility or req.responsibility
        req.stage_entered_at = timezone.now()
        move(req, event=sm.RENOMINATE, actor_kind=sm.EMPLOYEE,
             to=sm.AWAITING_SUBSTITUTE, actor=actor)
        _announce(req)
        return req


def withdraw(actor, pk: int, reason: str = "") -> LeaveRequest:
    require(actor, p.P_WITHDRAW)
    with transaction.atomic():
        req = _own_locked(actor, pk)
        if req.status not in sm.PENDING:
            raise ConflictError(
                "Only a pending request can be withdrawn. An approved leave needs a "
                "cancellation request.", code="not_withdrawable")
        role, sub = req.current_role, req.substitute_user_id
        was_awaiting_sub = req.status == sm.AWAITING_SUBSTITUTE
        req.current_role = ""
        move(req, event=sm.WITHDRAW, actor_kind=sm.EMPLOYEE, to=sm.WITHDRAWN,
             actor=actor, note=reason)
        notify.to_role(role, req, f"Leave #{req.pk} was withdrawn by the applicant.")
        if was_awaiting_sub:
            notify.to_user(sub, req, f"Leave #{req.pk} was withdrawn; no response needed.")
        return req


def request_cancellation(actor, pk: int, reason: str = "") -> LeaveRequest:
    require(actor, p.P_UPDATE)
    with transaction.atomic():
        req = _own_locked(actor, pk)
        if req.status != sm.APPROVED:
            raise ConflictError("Only an approved leave can be cancelled.",
                                code="not_cancellable")
        if req.kind == LeaveRequest.OFFLINE or not req.route:
            raise ConflictError("An offline-sanctioned record cannot be cancelled here; "
                                "contact the Leave Administrator.", code="not_cancellable")
        if timezone.localdate() >= req.start_date:
            raise ConflictError(
                "This leave has already begun. Use an extension or submit resumption "
                "of duty instead.", code="leave_started")
        to = sm.CANCELLATION_PENDING
        enter_stage(req, 0)
        move(req, event=sm.REQUEST_CANCELLATION, actor_kind=sm.EMPLOYEE, to=to,
             actor=actor, note=reason)
        notify.to_role(req.current_role, req,
                       f"Cancellation of approved leave #{req.pk} awaits your action.")
        return req


def apply_extension(actor, pk: int, *, end_date: date, purpose: str,
                    substitute_user_id: int | None = None,
                    responsibility: str = "") -> LeaveRequest:
    require(actor, p.P_CREATE)
    pv, policy, hierarchy = _policy()
    with transaction.atomic():
        ledger.lock_employee(actor.user_id)
        parent = _own_locked(actor, pk)
        today = timezone.localdate()
        if parent.kind != LeaveRequest.LEAVE or parent.category not in c.EXTENDABLE:
            raise ConflictError("Only Earned, Commuted or Vacation Leave can be extended.",
                                code="not_extendable")
        current_end = effective_end(parent)
        if parent.status != sm.APPROVED or not (parent.start_date <= today <= current_end):
            raise ConflictError("Only leave that is currently ongoing can be extended.",
                                code="not_ongoing")
        start = date.fromordinal(current_end.toordinal() + 1)
        if end_date < start:
            raise LeaveInvalid(f"The extension must end on or after {start}.",
                               code="invalid_period")
        data = LeaveInput(category=parent.category, start_date=start, end_date=end_date,
                          purpose=purpose, medical_evidence=parent.medical_evidence,
                          substitute_user_id=substitute_user_id,
                          responsibility=responsibility)
        days = _validate(actor, data, kind=parent.applicant_kind, exclude=set(),
                         policy=policy)
        req = LeaveRequest(user_id=actor.user_id, kind=LeaveRequest.EXTENSION,
                           parent=parent, applicant_kind=parent.applicant_kind,
                           applicant_unit=parent.applicant_unit, days=days,
                           policy_version_id=pv.pk)
        _fill(req, data)
        req.route = _route(actor, data, parent.applicant_kind, parent.applicant_unit,
                           hierarchy)
        to = _enter_routing(req, keep_consent=False)
        req.status = sm.NEW
        move(req, event=sm.SUBMIT, actor_kind=sm.EMPLOYEE, to=to, actor=actor)
        _announce(req)
        return req


def effective_end(parent: LeaveRequest) -> date:
    ends = list(LeaveRequest.objects
                .filter(parent=parent, kind=LeaveRequest.EXTENSION, status=sm.APPROVED)
                .values_list("end_date", flat=True))
    return max([parent.end_date, *ends])
