"""Applying for leave, and asking to cancel or extend it (EL-UC-001, EL-UC-008, EL-UC-009)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.directory import contracts as directory
from modules.leave.domain import categories as cat
from modules.leave.domain import policy as pol
from modules.leave.domain import routing
from modules.leave.domain import state_machine as sm
from modules.leave.domain import validation as v
from modules.leave.domain.overlap import Interval, first_collision
from modules.leave.models import LeaveRequest, Resumption, Substitution
from modules.leave.services import accounts, authz, configuration, workflow


class ValidationFailed(DomainError):
    """EL-UC-001 A1: name the condition that failed, every one of them."""

    code = "validation_failed"
    message = "The leave request was not submitted."


def _raise(problems: list[v.Problem]) -> None:
    if problems:
        raise ValidationFailed(problems[0].message, code=problems[0].code,
                               details=[{"code": p.code, "field": p.field, "message": p.message}
                                        for p in problems])


@dataclass(frozen=True)
class Applicant:
    user_id: int
    kind: str
    department: str
    roles: tuple[str, ...]


def applicant_for(actor) -> Applicant:
    """The person as the IAM projects them; department is read, never typed by the applicant."""
    authz.require_employee(actor)
    person = directory.get_users([actor.user_id]).get(actor.user_id)
    return Applicant(user_id=actor.user_id, kind=actor.kind,
                     department=getattr(person, "department", "") or "",
                     roles=tuple(sorted(set(getattr(actor, "roles", ()) or ()))))


def leave_intervals(user_ids, *, exclude_ids=()) -> dict[int, list[Interval]]:
    """Pending and approved leave as actually held, after extensions and early returns."""
    ids = [int(i) for i in user_ids]
    out: dict[int, list[Interval]] = {i: [] for i in ids}
    rows = (LeaveRequest.objects
            .filter(user_id__in=ids, kind__in=(sm.NEW, sm.EXTENSION),
                    status__in=(*sm.PENDING, sm.APPROVED))
            .exclude(pk__in=list(exclude_ids))
            .values_list("pk", "user_id", "start_date", "end_date", "half", "parent_id"))
    rows = list(rows)
    actual = dict(Resumption.objects.filter(
        leave_id__in=[r[0] for r in rows] + [r[5] for r in rows if r[5]],
        actual_end_date__isnull=False).values_list("leave_id", "actual_end_date"))
    for pk, uid, start, end, half, parent_id in rows:
        cut = actual.get(parent_id or pk)
        if cut is not None:
            if cut < start:
                continue
            end = min(end, cut)
        out[uid].append(Interval(start, end, half, pk))
    return out


def _context(app: Applicant, *, policy: pol.Policy, start: date, end: date, category: str,
             exclude_ids=()) -> v.Context:
    effective = configuration.calendar_for(start, end)
    return v.Context(
        applicant_id=app.user_id, applicant_kind=app.kind, today=workflow.today(),
        policy=policy, calendar=effective.view,
        available=(accounts.available(app.user_id, start.year, category)
                   if category in cat.CATEGORIES else Decimal(0)),
        existing=leave_intervals([app.user_id], exclude_ids=exclude_ids)[app.user_id],
        vacations=effective.vacations)


def _substitute_problems(app: Applicant, nominee_id: int | None, period: Interval,
                         rule: pol.CategoryRule) -> list[v.Problem]:
    if rule.substitute == pol.NONE:
        if nominee_id is not None:
            return [v.Problem("substitute_not_applicable",
                              "This category does not take a substitute.", "substitute_user_id")]
        return []
    if nominee_id is None and rule.substitute == pol.OPTIONAL:
        return []
    return nominee_problems(app.user_id, nominee_id, period)


def nominee_problems(applicant_id: int, nominee_id: int | None,
                     period: Interval) -> list[v.Problem]:
    nominee = directory.get_users([nominee_id]).get(nominee_id) if nominee_id else None
    return v.substitute_problems(
        applicant_id=applicant_id, nominee_id=nominee_id,
        nominee_kind=getattr(nominee, "kind", None), nominee_active=nominee is not None,
        nominee_leave=leave_intervals([nominee_id])[nominee_id] if nominee_id else [],
        period=period)


def _covering_problems(user_id: int, period: Interval) -> list[v.Problem]:
    """BR-EL-014 from the other side: nobody may leave a colleague uncovered after agreeing."""
    commitments = (Substitution.objects
                   .filter(substitute_user_id=user_id,
                           status__in=(Substitution.PENDING, Substitution.ACCEPTED),
                           request__status__in=(*sm.PENDING, sm.APPROVED))
                   .values_list("request__start_date", "request__end_date", "request__half"))
    clash = first_collision(period, [Interval(s, e, h) for s, e, h in commitments])
    if clash is None:
        return []
    return [v.Problem("covering_for_colleague",
                      f"You are a colleague's substitute from {clash.start} to {clash.end}. "
                      f"Decline or be released from that first.", "start")]


def _draft(data: dict) -> v.Draft:
    return v.Draft(
        category=data.get("category", ""), start=data["start_date"], end=data["end_date"],
        half=data.get("half", "") or "", purpose=data.get("purpose", "") or "",
        station_leave=bool(data.get("station_leave")), station_from=data.get("station_from"),
        station_to=data.get("station_to"), station_address=data.get("station_address", "") or "",
        evidence_reference=data.get("evidence_reference", "") or "",
        substitute_user_id=data.get("substitute_user_id"))


def _new_row(app: Applicant, draft: v.Draft, days, *, kind: str,
             parent: LeaveRequest | None = None) -> LeaveRequest:
    return LeaveRequest.objects.create(
        user_id=app.user_id, kind=kind, parent=parent, category=draft.category,
        start_date=draft.start, end_date=draft.end, half=draft.half, days=days,
        leave_year=draft.start.year, status=sm.DRAFT, purpose=draft.purpose.strip(),
        station_leave=draft.station_leave, station_from=draft.station_from,
        station_to=draft.station_to, station_address=draft.station_address.strip(),
        evidence_reference=draft.evidence_reference.strip(), applicant_kind=app.kind,
        applicant_department=app.department, applicant_roles=list(app.roles),
        is_director_applicant=routing.is_director(app.roles))


def _submit(req: LeaveRequest, actor, nominee_id: int | None) -> LeaveRequest:
    workflow.check_routable(req)
    if nominee_id is not None:
        Substitution.objects.create(request=req, substitute_user_id=nominee_id)
    return workflow.move(req, sm.SUBMIT, actor_lane=sm.EMPLOYEE, actor=actor,
                         needs_substitute=nominee_id is not None, substitute_id=nominee_id)


@transaction.atomic
def submit(*, actor, data: dict) -> LeaveRequest:
    """EL-UC-001: validated whole, under the applicant's account lock, then placed on its path."""
    authz.require(actor, "leave.request.create")
    app = applicant_for(actor)
    policy = configuration.current_policy()
    draft = _draft(data)
    accounts.lock(app.user_id, employee_kind=app.kind)
    if draft.category in cat.CATEGORIES:
        accounts.ensure_annual_credit(user_id=app.user_id, employee_kind=app.kind,
                                      year=draft.start.year, policy=policy)
    ctx = _context(app, policy=policy, start=draft.start, end=draft.end,
                   category=draft.category)
    problems = v.new_leave_problems(draft, ctx)
    _raise(problems)
    _raise(_covering_problems(app.user_id, Interval(draft.start, draft.end, draft.half)))
    _raise(_substitute_problems(app, draft.substitute_user_id,
                                Interval(draft.start, draft.end, draft.half),
                                policy.rule(draft.category)))
    req = _new_row(app, draft, v.chargeable(draft, ctx), kind=sm.NEW)
    return _submit(req, actor, draft.substitute_user_id)


def _own_approved_leave(actor, leave_id: int) -> LeaveRequest:
    leave = workflow.lock_request(leave_id, LeaveRequest.objects.filter(
        user_id=actor.user_id, kind=sm.NEW))
    if leave.status != sm.APPROVED:
        raise ConflictError("Only an approved leave can be changed this way.",
                            code="not_approved")
    return leave


@transaction.atomic
def request_cancellation(*, actor, leave_id: int, reason: str) -> LeaveRequest:
    """EL-UC-008: pre-start only; the leave is untouched, a revision is fresh (BR-EL-024)."""
    authz.require(actor, "leave.request.create")
    app = applicant_for(actor)
    leave = _own_approved_leave(actor, leave_id)
    if leave.start_date <= workflow.today():
        raise ConflictError("This leave has already begun, so it cannot be cancelled. Use an "
                            "extension or your resumption instead.", code="leave_already_started")
    if not reason.strip():
        raise ConflictError("Give the reason for cancelling.", code="reason_required")
    if LeaveRequest.objects.filter(parent=leave, kind=sm.CANCELLATION,
                                   status__in=sm.PENDING).exists():
        raise ConflictError("A cancellation for this leave is already being processed.",
                            code="cancellation_pending")
    req = LeaveRequest.objects.create(
        user_id=app.user_id, kind=sm.CANCELLATION, parent=leave, category=leave.category,
        start_date=leave.start_date, end_date=leave.end_date, half=leave.half, days=leave.days,
        leave_year=leave.leave_year, status=sm.DRAFT, purpose=reason.strip(),
        applicant_kind=leave.applicant_kind, applicant_department=leave.applicant_department,
        applicant_roles=leave.applicant_roles,
        is_director_applicant=leave.is_director_applicant)
    return _submit(req, actor, None)


@transaction.atomic
def request_extension(*, actor, leave_id: int, data: dict) -> LeaveRequest:
    """EL-UC-009: a separate request for the extra days only."""
    authz.require(actor, "leave.request.create")
    app = applicant_for(actor)
    leave = _own_approved_leave(actor, leave_id)
    if LeaveRequest.objects.filter(parent=leave, kind=sm.EXTENSION,
                                   status__in=sm.PENDING).exists():
        raise ConflictError("An extension for this leave is already being processed.",
                            code="extension_pending")
    if Resumption.objects.filter(leave=leave).exists():
        raise ConflictError("You have already resumed duty from this leave.",
                            code="already_resumed")
    end = workflow.effective_end(leave)
    policy = configuration.current_policy()
    draft = _draft({**data, "category": leave.category,
                    "start_date": data.get("start_date") or _day_after(end)})
    accounts.lock(app.user_id, employee_kind=app.kind)
    accounts.ensure_annual_credit(user_id=app.user_id, employee_kind=app.kind,
                                  year=draft.start.year, policy=policy)
    ctx = _context(app, policy=policy, start=draft.start, end=draft.end, category=leave.category)
    _raise(v.extension_problems(base_category=leave.category, base_start=leave.start_date,
                                base_effective_end=end, draft=draft, ctx=ctx))
    _raise(_substitute_problems(app, draft.substitute_user_id, Interval(draft.start, draft.end),
                                policy.rule(leave.category)))
    req = _new_row(app, draft, v.chargeable(draft, ctx), kind=sm.EXTENSION, parent=leave)
    return _submit(req, actor, draft.substitute_user_id)


def _day_after(d: date) -> date:
    return d + timedelta(days=1)


def get_own(actor, request_id: int) -> LeaveRequest:
    req = LeaveRequest.objects.filter(pk=request_id, user_id=actor.user_id).first()
    if req is None:
        raise NotFoundError("No such leave request.")
    return req
