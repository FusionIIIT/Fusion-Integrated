"""Employee-side use cases: apply, substitute consent, withdraw, cancel, extend."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.leave.domain.categories import (
    EXTENDABLE,
    Category,
    EmployeeKind,
    IneligibleCategory,
    check_eligible,
    parse_kind,
)
from modules.leave.domain.counting import Half, Interval, InvalidPeriod, dates_in, leave_days
from modules.leave.domain.counting import overlaps as collide
from modules.leave.domain.workflow import (
    PENDING,
    Actor,
    Event,
    State,
    entry_state,
    substitute_event,
)
from modules.leave.models import Holiday, LeavePolicy, LeaveRequest, LeaveTransition
from modules.leave.selectors import accounts as reads
from modules.leave.selectors import calendar
from modules.leave.services import accounts, routing
from modules.leave.services.notify import notify
from modules.leave.services.workflow import _describe, advance, assignee_of, route_of


@dataclass(frozen=True)
class Applicant:
    user_id: int
    kind: EmployeeKind
    department: str


@dataclass(frozen=True)
class Application:
    category: Category
    start_date: date
    end_date: date
    purpose: str
    half: Half = Half.FULL
    substitute_user_id: int | None = None
    station_leave: bool = False
    station_address: str = ""
    medical_evidence_ref: str = ""


def applicant_for(user_id: int, kind: str) -> Applicant:
    try:
        employee_kind = parse_kind(kind)
    except IneligibleCategory as exc:
        raise ConflictError(str(exc), code="not_an_employee") from exc
    user = directory.get_users([user_id]).get(user_id)
    return Applicant(user_id, employee_kind, user.department if user else "")


def period_days(category: Category, start: date, end: date, half: Half) -> Decimal:
    """BR-EL-003/006/010/011/031."""
    if start.year != end.year:
        raise BadRequestError("A leave period cannot cross into a new calendar year; "
                              "submit one request for each year.", code="crosses_year")
    closed = calendar.holidays(start.year, Holiday.CLOSED)
    if closed is None:
        raise ConflictError(f"No holiday calendar is published for {start.year} yet. "
                            "Ask the Leave Administrator to publish it.",
                            code="calendar_missing")
    try:
        days = leave_days(category, start, end, half, closed)
    except InvalidPeriod as exc:
        raise BadRequestError(str(exc), code="invalid_period") from exc
    if category is Category.RH:
        restricted = calendar.holidays(start.year, Holiday.RESTRICTED) or set()
        if not set(dates_in(start, end)) <= restricted:
            raise ConflictError("Restricted Holiday can only be taken on a date listed as a "
                                "Restricted Holiday in the published calendar.",
                                code="not_restricted_holiday")
    if category is Category.VL and not calendar.within_vacation(start, end):
        raise ConflictError("Vacation Leave must fall entirely inside a vacation period of "
                            "the Academic Calendar.", code="outside_vacation")
    return days


def check_no_overlap(user_id: int, interval: Interval, exclude_ids=()) -> None:
    """BR-EL-012."""
    for _, booked in reads.booked_intervals([user_id], exclude_ids):
        if collide(interval, booked):
            raise ConflictError(
                f"You already have leave pending or approved from {booked.start:%d %b %Y} "
                f"to {booked.end:%d %b %Y}, which overlaps these dates.", code="overlap")


def check_substitute(applicant_id: int, substitute_id: int, interval: Interval) -> None:
    """BR-EL-014."""
    if substitute_id == applicant_id:
        raise BadRequestError("You cannot nominate yourself as your substitute.",
                              code="self_substitute")
    user = directory.get_users([substitute_id]).get(substitute_id)
    if user is None or user.kind not in (EmployeeKind.FACULTY, EmployeeKind.STAFF):
        raise ConflictError("The nominated substitute must be another faculty or staff "
                            "member.", code="substitute_not_employee")
    for _, booked in reads.booked_intervals([substitute_id]):
        if collide(interval, booked):
            raise ConflictError("The nominated substitute has leave pending or approved "
                                "during your absence. Nominate someone else.",
                                code="substitute_unavailable")


def _policy(category: Category) -> LeavePolicy:
    policy = LeavePolicy.objects.filter(category=category).first()
    if policy is None:
        raise ConflictError(f"{category} has no leave policy configured. Ask the Leave "
                            "Administrator to set it up.", code="policy_missing")
    return policy


def _validate(applicant: Applicant, app: Application, *, exclude_ids=()) -> Decimal:
    """The order is deliberate: the most actionable refusal comes first."""
    try:
        check_eligible(app.category, applicant.kind)
    except IneligibleCategory as exc:
        raise ConflictError(str(exc), code="category_not_eligible") from exc
    if not app.purpose.strip():
        raise BadRequestError("Please state the purpose of the leave.", code="purpose_required")
    if app.station_leave and not app.station_address.strip():
        raise BadRequestError("Give the address you will be at while outside Jabalpur.",
                              code="station_address_required")
    policy = _policy(app.category)
    days = period_days(app.category, app.start_date, app.end_date, app.half)
    if policy.max_days_per_request and days > policy.max_days_per_request:
        raise ConflictError(f"A single {app.category} request may cover at most "
                            f"{policy.max_days_per_request} day(s).", code="too_long")
    interval = Interval(app.start_date, app.end_date, app.half)
    check_no_overlap(applicant.user_id, interval, exclude_ids)
    accounts.ensure_annual_credits(applicant.user_id, applicant.kind, app.start_date.year)
    accounts.require_available(applicant.user_id, app.category, app.start_date.year, days)
    if policy.requires_substitute and app.substitute_user_id is None:
        raise BadRequestError(f"{app.category} requires a substitute to cover your duties.",
                              code="substitute_required")
    if app.substitute_user_id is not None:
        check_substitute(applicant.user_id, app.substitute_user_id, interval)
    return days


def _create(applicant: Applicant, app: Application, days: Decimal, *, kind: str,
            parent: LeaveRequest | None = None) -> LeaveRequest:
    resolved = routing.resolve(applicant.user_id, applicant.kind, applicant.department,
                               app.category)
    status = entry_state(resolved.route, has_substitute=app.substitute_user_id is not None)
    req = LeaveRequest.objects.create(
        user_id=applicant.user_id, kind=kind, parent=parent, category=app.category.value,
        start_date=app.start_date, end_date=app.end_date, half=app.half.value, days=days,
        purpose=app.purpose.strip(), station_leave=app.station_leave,
        station_address=app.station_address.strip(),
        medical_evidence_ref=app.medical_evidence_ref.strip(), status=status.value,
        substitute_user_id=app.substitute_user_id,
        unit_head_user_id=resolved.unit_head_user_id,
        establishment_user_id=resolved.establishment_user_id,
        sanctioning_user_id=resolved.sanctioning_user_id,
        unit_head_final=resolved.route.unit_head_final,
        director_self=resolved.route.director_self)
    LeaveTransition.objects.create(request=req, to_status=status.value, event="submit",
                                   actor_user_id=applicant.user_id)
    notify([assignee_of(req)], "assigned", f"Action needed: {_describe(req)}.", request=req)
    return req


def apply(applicant: Applicant, app: Application) -> LeaveRequest:
    """EL-UC-001."""
    with transaction.atomic():
        accounts.lock(applicant.user_id)
        days = _validate(applicant, app)
        return _create(applicant, app, days, kind=LeaveRequest.NEW)


def respond_as_substitute(request_id: int, user_id: int, accept: bool,
                          note: str = "") -> LeaveRequest:
    """EL-UC-002 / BR-EL-015: a decline leaves the gate closed."""
    req = _get(request_id)
    return advance(request_id, substitute_event(route_of(req), accept), Actor.SUBSTITUTE,
                   user_id, note=note)


def renominate(request_id: int, user_id: int, substitute_id: int) -> LeaveRequest:
    """EL-UC-019."""
    req = _get(request_id)
    check_substitute(req.user_id, substitute_id,
                     Interval(req.start_date, req.end_date, Half(req.half)))

    def swap(r: LeaveRequest) -> None:
        r.substitute_user_id = substitute_id

    return advance(request_id, Event.RENOMINATE, Actor.APPLICANT, user_id, mutate=swap,
                   note=f"Nominated user {substitute_id}")


def withdraw(request_id: int, user_id: int, note: str = "") -> LeaveRequest:
    """EL-UC-007 / BR-EL-022."""
    if _get(request_id).kind == LeaveRequest.CANCELLATION:
        raise ConflictError("A cancellation request cannot be withdrawn; it is decided "
                            "through the same hierarchy as the leave.",
                            code="cancellation_not_withdrawable")
    return advance(request_id, Event.WITHDRAW, Actor.APPLICANT, user_id, note=note)


def _own_approved(leave_id: int, user_id: int) -> LeaveRequest:
    leave = LeaveRequest.objects.select_for_update().filter(
        pk=leave_id, user_id=user_id, kind=LeaveRequest.NEW).first()
    if leave is None:
        raise NotFoundError("That leave does not exist.")
    if leave.status != State.APPROVED:
        raise ConflictError("Only approved leave can be changed this way.", code="not_approved")
    if leave.source == LeaveRequest.OFFLINE:
        raise ConflictError("Leave recorded from an offline sanction is corrected by the "
                            "Leave Administrator.", code="offline_record")
    return leave


def request_cancellation(leave_id: int, user_id: int, reason: str,
                         today: date) -> LeaveRequest:
    """EL-UC-008 / BR-EL-023: before the start date, through the same hierarchy."""
    with transaction.atomic():
        leave = _own_approved(leave_id, user_id)
        if today >= leave.start_date:
            raise ConflictError("This leave has already begun. Request an extension or "
                                "submit your resumption instead.", code="already_started")
        if leave.children.filter(kind=LeaveRequest.CANCELLATION,
                                 status__in=[s.value for s in PENDING]).exists():
            raise ConflictError("A cancellation is already pending for this leave.",
                                code="cancellation_pending")
        status = entry_state(route_of(leave), has_substitute=False)
        req = LeaveRequest.objects.create(
            user_id=user_id, kind=LeaveRequest.CANCELLATION, parent=leave,
            category=leave.category, start_date=leave.start_date, end_date=leave.end_date,
            half=leave.half, days=leave.days, purpose=reason.strip() or "Cancellation",
            status=status.value, unit_head_user_id=leave.unit_head_user_id,
            establishment_user_id=leave.establishment_user_id,
            sanctioning_user_id=leave.sanctioning_user_id,
            unit_head_final=leave.unit_head_final, director_self=leave.director_self)
        LeaveTransition.objects.create(request=req, to_status=status.value, event="submit",
                                       actor_user_id=user_id)
        notify([assignee_of(req)], "assigned", f"Action needed: {_describe(req)}.",
               request=req)
        return req


def request_extension(applicant: Applicant, leave_id: int, new_end: date, purpose: str,
                      today: date, substitute_user_id: int | None = None) -> LeaveRequest:
    """EL-UC-009 / BR-EL-025: only the added days are a new request."""
    with transaction.atomic():
        accounts.lock(applicant.user_id)
        leave = _own_approved(leave_id, applicant.user_id)
        category = Category(leave.category)
        if category not in EXTENDABLE:
            raise ConflictError("Only EL, COL and VL can be extended.", code="not_extendable")
        current_end = reads.effective_end(leave)
        if not leave.start_date <= today <= current_end:
            raise ConflictError("An extension can be requested only while the leave is "
                                "ongoing.", code="not_ongoing")
        if new_end <= current_end:
            raise BadRequestError(f"The new end date must be after {current_end:%d %b %Y}.",
                                  code="not_later")
        app = Application(category=category, start_date=current_end + timedelta(days=1),
                          end_date=new_end, purpose=purpose,
                          substitute_user_id=substitute_user_id)
        days = _validate(applicant, app)
        return _create(applicant, app, days, kind=LeaveRequest.EXTENSION, parent=leave)


def _get(request_id: int) -> LeaveRequest:
    req = LeaveRequest.objects.filter(pk=request_id).first()
    if req is None:
        raise NotFoundError("That leave request does not exist.")
    return req
