"""Submitting, withdrawing, cancelling and extending leave (EL-UC-001/007/008/009).

The service owns the transaction: it validates against the current policy and
calendar, freezes the routing facts, advances the state machine and writes the
audit trail and notifications together.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.directory import contracts as directory
from modules.elm.domain import counting, overlap, routing
from modules.elm.domain import enums as e
from modules.elm.domain import state_machine as sm
from modules.elm.domain.errors import ActorNotAllowed, InvalidTransition
from modules.elm.models import (
    LeaveRequest,
    LeaveRequestEvent,
    SubstituteAssignment,
    WorkflowTask,
)
from modules.elm.services import accounts, calendars, config, notifications

#: Roles that identify the Director, who self-sanctions (BR-EL-020).
_DIRECTOR_ROLES = {"director"}


def is_director(actor) -> bool:
    roles = {str(r).lower() for r in getattr(actor, "roles", ())}
    return bool(roles & _DIRECTOR_ROLES)


def _fail(code: str, message: str):
    raise ConflictError(message, code=code)


def _year_for(day: date) -> int:
    return day.year


def _employee_kind(user_id: int) -> str:
    dto = directory.get_users([user_id]).get(user_id)
    return dto.kind if dto else ""


def _department(user_id: int) -> str:
    dto = directory.get_users([user_id]).get(user_id)
    return dto.department if dto else ""


def _active_intervals(user_id: int, *, exclude=()):
    qs = (LeaveRequest.objects
          .filter(user_id=user_id, kind=e.NEW,
                  status__in=[*e.PENDING_APPROVAL, e.APPROVED])
          .exclude(pk__in=[p for p in exclude if p]))
    return [{"start": r.start_date, "end": r.end_date, "half": r.half_day,
             "id": r.pk} for r in qs]


# -- validation ----------------------------------------------------------------
def _validate_new(*, user_id: int, category: str, start: date, end: date,
                  half_day: str, kind: str = e.NEW, exclude=()) -> Decimal:
    if category not in e.CATEGORIES:
        _fail("unknown_category", f"{category!r} is not a leave category.")
    cfg = config.type_config(category)
    if not cfg.active:
        _fail("category_inactive", f"{category} leave is not currently offered.")

    kind_of = _employee_kind(user_id)
    if cfg.employee_kind == "faculty" and kind_of != "faculty":
        _fail("faculty_only", f"{category} leave is available to faculty only.")

    if end < start:
        _fail("bad_period", "The end date is before the start date.")
    if half_day and (not cfg.half_day or start != end):
        _fail("bad_half_day",
              "A half day must be a single day in a half-day category.")

    cal = calendars.effective_calendar()
    if cal is None and category in (e.RH,):
        _fail("no_calendar", "No published holiday calendar is in effect.")

    if category == e.RH:
        restricted = calendars.restricted_dates(cal)
        d = start
        while d <= end:
            if d.weekday() < 5 and d not in restricted:
                _fail("rh_not_restricted",
                      f"{d.isoformat()} is not a published restricted holiday.")
            d = date.fromordinal(d.toordinal() + 1)

    if category == e.VL and not calendars.within_vacation(start, end):
        _fail("not_vacation",
              "Vacation leave may only be taken within an academic vacation period.")

    try:
        days = counting.chargeable_days(
            category=category, start=start, end=end, half_day=half_day,
            closed_dates=calendars.closed_dates(cal))
    except counting.CountingError as exc:
        _fail("counting", str(exc))

    if days <= 0:
        _fail("no_days", "The period contains no chargeable leave days.")

    year = _year_for(start)
    available = accounts.available(user_id, category, year)
    if days > available:
        _fail("insufficient_balance",
              f"Only {available} {category} day(s) available, {days} requested.")

    conflict = overlap.first_conflict(
        candidate={"start": start, "end": end, "half": half_day},
        existing=_active_intervals(user_id, exclude=exclude))
    if conflict is not None:
        _fail("overlap",
              f"This period overlaps an existing leave (request #{conflict['id']}).")

    return days


def _validate_substitute(*, user_id: int, substitute_user_id: int,
                         start: date, end: date) -> None:
    if substitute_user_id in (None, user_id):
        _fail("bad_substitute", "A substitute must be another employee.")
    if not _employee_kind(substitute_user_id):
        _fail("bad_substitute", "The nominated substitute is not a known employee.")
    conflict = overlap.first_conflict(
        candidate={"start": start, "end": end, "half": ""},
        existing=_active_intervals(substitute_user_id))
    if conflict is not None:
        _fail("substitute_unavailable",
              "The nominated substitute has leave during this period.")


# -- transition plumbing -------------------------------------------------------
def _role_for_status(status: str) -> str:
    return {
        e.AWAITING_SUBSTITUTE: e.SUBSTITUTE,
        e.AWAITING_UNIT_HEAD: e.UNIT_HEAD,
        e.AWAITING_ESTABLISHMENT: e.ESTABLISHMENT,
        e.AWAITING_FINAL_SANCTION: e.SANCTION,
        e.AWAITING_DIRECTOR_SANCTION: e.DIRECTOR,
    }.get(status, "")


def _assignee_for(request: LeaveRequest, status: str) -> int | None:
    if status == e.AWAITING_SUBSTITUTE:
        return request.substitute_user_id
    if status == e.AWAITING_UNIT_HEAD:
        return config.unit_head_for(request.department)
    return None                        # establishment / sanction pools by role


def _open_task(request: LeaveRequest, status: str) -> WorkflowTask | None:
    task_type = routing.task_type_for(status)
    if status not in (e.AWAITING_SUBSTITUTE, e.AWAITING_UNIT_HEAD,
                      e.AWAITING_ESTABLISHMENT, e.AWAITING_FINAL_SANCTION,
                      e.AWAITING_DIRECTOR_SANCTION):
        return None
    task = WorkflowTask.objects.create(
        request=request, task_type=task_type, role=_role_for_status(status),
        assigned_to_user_id=_assignee_for(request, status))
    if task.assigned_to_user_id:
        notifications.enqueue(
            topic="request.task_assigned",
            dedupe_key=f"task:{task.pk}:assigned",
            subject=f"Leave request #{request.pk} needs your action",
            body=(f"A {request.category} leave request from applicant "
                  f"u{request.user_id} is awaiting your action."),
            recipient_user_id=task.assigned_to_user_id,
            payload={"request_id": request.pk, "task_id": task.pk})
    return task


def _close_tasks(request: LeaveRequest, *, decision: str,
                 actor_user_id: int | None, note: str = "") -> None:
    request.tasks.filter(status="pending").update(
        status="done", decision=decision, acted_by_user_id=actor_user_id,
        acted_at=timezone.now(), note=note)


def advance(*, request: LeaveRequest, to_status: str, actor_user_id: int | None,
            actor_role: str, note: str = "", decision: str = "") -> LeaveRequest:
    """Move the request through one legal edge, writing history and the next
    task."""
    try:
        sm.resolve(request.status, to_status, actor_role)
    except (InvalidTransition, ActorNotAllowed) as exc:
        raise ConflictError(str(exc), code="illegal_transition") from exc
    frm = request.status
    request.status = to_status
    request.save(update_fields=["status", "updated_at"])
    LeaveRequestEvent.objects.create(
        request=request, from_status=frm, to_status=to_status,
        actor_user_id=actor_user_id, actor_role=actor_role, note=note)
    _close_tasks(request, decision=decision or to_status,
                 actor_user_id=actor_user_id, note=note)
    if to_status not in e.TERMINAL:
        _open_task(request, to_status)
    return request


def _notify_applicant(request: LeaveRequest, topic: str, subject: str,
                      body: str, tag: str) -> None:
    notifications.enqueue(
        topic=topic, dedupe_key=f"{tag}:req{request.pk}",
        subject=subject, body=body, recipient_user_id=request.user_id,
        payload={"request_id": request.pk})


# -- submit --------------------------------------------------------------------
@transaction.atomic
def submit_new(*, actor, category: str, start_date: date, end_date: date,
               half_day: str = "", purpose: str = "", station_leave: bool = False,
               station_place: str = "", station_contact: str = "",
               substitute_user_id: int | None = None) -> LeaveRequest:
    user_id = actor.user_id
    cfg = config.type_config(category)
    days = _validate_new(user_id=user_id, category=category, start=start_date,
                         end=end_date, half_day=half_day)
    if cfg.requires_substitute:
        if substitute_user_id is None:
            _fail("substitute_required", "This leave requires a substitute.")
        _validate_substitute(user_id=user_id,
                             substitute_user_id=substitute_user_id,
                             start=start_date, end=end_date)

    director = is_director(actor)
    hier = config.hierarchy_for(category)
    request = LeaveRequest.objects.create(
        user_id=user_id, kind=e.NEW, category=category,
        start_date=start_date, end_date=end_date, half_day=half_day or "",
        days=days, purpose=purpose, station_leave=station_leave,
        station_place=station_place, station_contact=station_contact,
        substitute_user_id=substitute_user_id,
        department=_department(user_id),
        status=e.DRAFT,
        route={"applicant_is_director": director,
               "establishment_required": hier.establishment_required,
               "final_authority": hier.final_authority_designation})
    if cfg.requires_substitute:
        SubstituteAssignment.objects.create(
            request=request, substitute_user_id=substitute_user_id,
            responsibility_start=start_date, responsibility_end=end_date,
            nominated_by_user_id=user_id)

    status = routing.initial_status(
        substitute_required=cfg.requires_substitute,
        applicant_is_director=director)
    actor_role = e.DIRECTOR if (director and not cfg.requires_substitute) else e.EMPLOYEE
    _audit_submit(request, status, actor_user_id=user_id, actor_role=actor_role)
    _notify_applicant(request, "request.submitted",
                      f"Leave request #{request.pk} submitted",
                      "Your leave request has been submitted for processing.",
                      "submitted")
    return request


def _audit_submit(request: LeaveRequest, status: str, *, actor_user_id: int,
                  actor_role: str) -> None:
    frm = request.status
    request.status = status
    request.save(update_fields=["status", "updated_at"])
    LeaveRequestEvent.objects.create(
        request=request, from_status=frm, to_status=status,
        actor_user_id=actor_user_id, actor_role=actor_role)
    _open_task(request, status)


# -- cancellation --------------------------------------------------------------
@transaction.atomic
def request_cancellation(*, actor, request_id: int) -> LeaveRequest:
    original = LeaveRequest.objects.select_related().filter(pk=request_id).first()
    if original is None or original.user_id != actor.user_id:
        _fail("not_found", "No such leave request.")
    if original.kind != e.NEW or original.status != e.APPROVED:
        _fail("not_cancellable", "Only an approved leave can be cancelled.")
    if original.start_date <= timezone.localdate():
        _fail("already_started",
              "Approved leave can only be cancelled before it begins.")
    if LeaveRequest.objects.filter(original=original, kind=e.CANCELLATION,
                                   status__in=[*e.PENDING_APPROVAL,
                                               e.APPROVED]).exists():
        _fail("duplicate_cancellation",
              "A cancellation for this leave is already in progress.")

    director = is_director(actor)
    hier = config.hierarchy_for(original.category)
    request = LeaveRequest.objects.create(
        user_id=actor.user_id, kind=e.CANCELLATION, category=original.category,
        start_date=original.start_date, end_date=original.end_date,
        half_day=original.half_day, days=original.days,
        purpose=f"Cancellation of request #{original.pk}",
        original=original, department=original.department, status=e.DRAFT,
        route=dict(original.route or {}) or {
            "applicant_is_director": director,
            "establishment_required": hier.establishment_required,
            "final_authority": hier.final_authority_designation})
    status = routing.initial_status(substitute_required=False,
                                    applicant_is_director=director)
    actor_role = e.DIRECTOR if director else e.EMPLOYEE
    _audit_submit(request, status, actor_user_id=actor.user_id,
                  actor_role=actor_role)
    return request


# -- extension -----------------------------------------------------------------
@transaction.atomic
def request_extension(*, actor, request_id: int, new_end: date, reason: str = "",
                      substitute_user_id: int | None = None) -> LeaveRequest:
    original = LeaveRequest.objects.select_related().filter(pk=request_id).first()
    if original is None or original.user_id != actor.user_id:
        _fail("not_found", "No such leave request.")
    if original.kind != e.NEW or original.status != e.APPROVED:
        _fail("not_extendable", "Only an approved leave can be extended.")
    if original.category not in e.EXTENSION:
        _fail("not_extendable",
              f"{original.category} leave cannot be extended.")
    today = timezone.localdate()
    if not (original.start_date <= today <= original.end_date):
        _fail("not_ongoing", "Only an ongoing leave can be extended.")
    if new_end <= original.end_date:
        _fail("bad_period", "The new end date must be after the current end date.")

    cfg = config.type_config(original.category)
    start = date.fromordinal(original.end_date.toordinal() + 1)
    days = _validate_new(user_id=actor.user_id, category=original.category,
                         start=start, end=new_end, half_day="",
                         kind=e.EXTENSION_KIND, exclude=(original.pk,))
    if cfg.requires_substitute:
        if substitute_user_id is None:
            _fail("substitute_required", "This extension requires a substitute.")
        _validate_substitute(user_id=actor.user_id,
                             substitute_user_id=substitute_user_id,
                             start=start, end=new_end)

    director = is_director(actor)
    request = LeaveRequest.objects.create(
        user_id=actor.user_id, kind=e.EXTENSION_KIND, category=original.category,
        start_date=start, end_date=new_end, days=days,
        purpose=reason or f"Extension of request #{original.pk}",
        original=original, substitute_user_id=substitute_user_id,
        department=original.department, status=e.DRAFT,
        route=dict(original.route or {}))
    if cfg.requires_substitute:
        SubstituteAssignment.objects.create(
            request=request, substitute_user_id=substitute_user_id,
            responsibility_start=start, responsibility_end=new_end,
            nominated_by_user_id=actor.user_id)
    status = routing.initial_status(
        substitute_required=cfg.requires_substitute,
        applicant_is_director=director)
    actor_role = e.DIRECTOR if (director and not cfg.requires_substitute) else e.EMPLOYEE
    _audit_submit(request, status, actor_user_id=actor.user_id,
                  actor_role=actor_role)
    return request


# -- withdrawal ----------------------------------------------------------------
@transaction.atomic
def withdraw(*, actor, request_id: int, reason: str = "") -> LeaveRequest:
    request = LeaveRequest.objects.filter(pk=request_id).first()
    if request is None or request.user_id != actor.user_id:
        _fail("not_found", "No such leave request.")
    if request.status not in e.PENDING_APPROVAL:
        _fail("not_withdrawable",
              "Only a request awaiting approval can be withdrawn.")
    advance(request=request, to_status=e.WITHDRAWN, actor_user_id=actor.user_id,
            actor_role=e.EMPLOYEE, note=reason)
    _notify_applicant(request, "request.withdrawn",
                      f"Leave request #{request.pk} withdrawn",
                      "Your leave request has been withdrawn.",
                      "withdrawn")
    return request


# -- replacement nomination ----------------------------------------------------
@transaction.atomic
def nominate_replacement(*, actor, request_id: int,
                         substitute_user_id: int) -> LeaveRequest:
    request = LeaveRequest.objects.filter(pk=request_id).first()
    if request is None or request.user_id != actor.user_id:
        _fail("not_found", "No such leave request.")
    if request.status != e.APPLICANT_ACTION_REQUIRED:
        _fail("not_awaiting_replacement",
              "This request is not awaiting a replacement substitute.")
    _validate_substitute(user_id=actor.user_id,
                         substitute_user_id=substitute_user_id,
                         start=request.start_date, end=request.end_date)
    request.substitute_user_id = substitute_user_id
    request.save(update_fields=["substitute_user_id", "updated_at"])
    SubstituteAssignment.objects.create(
        request=request, substitute_user_id=substitute_user_id,
        responsibility_start=request.start_date,
        responsibility_end=request.end_date,
        nominated_by_user_id=actor.user_id)
    advance(request=request, to_status=e.AWAITING_SUBSTITUTE,
            actor_user_id=actor.user_id, actor_role=e.EMPLOYEE)
    return request
