"""Everything an applicant does before a decision (EL-UC-001, 006, 007,
011, 019; BR-EL-010…014, 022, 029).

Each function owns one rule cluster and speaks the shared envelope through
`validated`; status movement, audit and task hand-off all go via workflow.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.directory import contracts as directory
from modules.leave.domain import counting, states as st, validation as v
from modules.leave.domain.categories import (
    CATEGORIES,
    EXTENDABLE_CATEGORIES,
    RESUMABLE_CATEGORIES,
    label_for,
)
from modules.leave.models import (
    LeaveRequest,
    LeaveRequestEvent,
    LeaveResumption,
    SlaThreshold,
)
from modules.leave.services import (
    authz,
    balances,
    calendar as calendar_service,
    hierarchy,
    notifications,
    policy as policy_service,
    workflow,
)
from modules.leave.services.errors import validated

BUSY_STATUSES = [*st.PENDING, st.APPROVED]


def _intervals(user_id: int, *, statuses: list[str] | None = None
               ) -> list[v.Interval]:
    rows = LeaveRequest.objects.filter(
        user_id=user_id, status__in=statuses or BUSY_STATUSES)
    return [v.Interval(r.start_date, r.end_date, r.half_day, r.category)
            for r in rows]


def _validate_substitute(*, nominee, applicant: int, start, end) -> None:
    if nominee is None:
        raise v.ValidationError(
            "This leave needs responsibility coverage: nominate a substitute.",
            code="substitute_required")
    v.check_substitute(nominee=nominee, applicant=applicant,
                       employee_ids=directory.held_employee_ids())
    probe = v.Interval(start, end, "none", "el")
    for other in _intervals(nominee):
        if v.intervals_overlap(probe, other):
            raise v.ValidationError(
                "The nominated substitute is already on leave during that "
                "period.", code="substitute_busy")


def _routing(*, department: str, applicant_id: int, needs_substitute: bool
             ) -> tuple[str, int | None, int | None, bool]:
    """Where a submitted file starts: the substitute gate first (BR-EL-015 —
    routing cannot continue until consent), then the Director's own file
    self-sanctions (BR-EL-020), otherwise Unit Head review. An applicant who
    *is* their unit's head never waits on their own desk — their file enters
    at establishment instead (self-approval guard)."""
    director = hierarchy.is_director(applicant_id)
    if director:
        return (st.AWAITING_SUBSTITUTE if needs_substitute
                else st.AWAITING_DIRECTOR), None, None, True
    head = hierarchy.require_unit_head(department)
    if head == applicant_id:
        establishment = hierarchy.establishment_assignee(department)
        if establishment is None:
            from core.api.exceptions import ConflictError
            raise ConflictError(
                "You are your unit's head, and no establishment desk is "
                "configured to carry your file; ask an administrator to "
                "assign one.", code="no_establishment_step")
        return (st.AWAITING_SUBSTITUTE if needs_substitute
                else st.AWAITING_ESTABLISHMENT), head, establishment, False
    return (st.AWAITING_SUBSTITUTE if needs_substitute
            else st.AWAITING_UH_REVIEW), head, None, False


def _calendar_checks(category: str, start, end) -> tuple[object, set]:
    """RH and VL are only valid against the published calendars (BR-EL-003,
    BR-EL-006, BR-EL-031). Returns (calendar, closed_dates) for counting."""
    calendar = calendar_service.effective_calendar()
    if category == "rh":
        restricted = calendar_service.restricted_dates(calendar)
        if not restricted:
            raise ConflictError(
                "No published Restricted Holiday calendar is in effect yet.",
                code="no_rh_calendar")
        v.check_rh_calendar(start=start, end=end, restricted_dates=restricted)
    elif category == "vl":
        windows = calendar_service.vacation_windows()
        if not windows:
            raise ConflictError(
                "No vacation period has been published from the Academic "
                "Calendar yet.", code="no_vacation")
        v.check_vl_vacation_period(start=start, end=end,
                                   vacation_periods=windows)
    return calendar, calendar_service.closed_dates(calendar)


@validated
@transaction.atomic
def submit(*, actor, category: str, start_date, end_date,
           half_day: str = "none", purpose: str = "",
           evidence_note: str = "", station_leave: bool = False,
           station_place: str = "", station_reason: str = "",
           substitute_user_id=None) -> LeaveRequest:
    """EL-UC-001. Born in its first workflow state — there is no draft."""
    authz.require_employee(actor)
    authz.require(actor, "leave.request.create")
    if category not in CATEGORIES:
        raise BadRequestError(f"Unknown leave category {category!r}.",
                              code="unknown_category")
    faculty = policy_service.is_faculty(actor.kind)
    v.check_category_applicable(category=category, is_faculty=faculty)
    v.check_interval(start=start_date, end=end_date, half_day=half_day,
                     category=category)

    policy = policy_service.current_policy()
    calendar, closed = _calendar_checks(category, start_date, end_date)
    days = counting.chargeable_days(
        category=category, start=start_date, end=end_date, half_day=half_day,
        closed_holidays=closed)
    year = policy_service.leave_year_of(policy, start_date)

    held = balances.available(actor.user_id, category, year, kind=actor.kind)
    v.check_balance(available=held, required=days, category=category)
    v.check_overlap(start=start_date, end=end_date, half_day=half_day,
                    category=category, existing=_intervals(actor.user_id))

    needs_substitute = policy_service.substitute_required(policy, category)
    if needs_substitute:
        _validate_substitute(nominee=substitute_user_id,
                             applicant=actor.user_id,
                             start=start_date, end=end_date)

    status, unit_head, establishment, director = _routing(
        department=hierarchy.department_of(actor.user_id),
        applicant_id=actor.user_id, needs_substitute=needs_substitute)

    request = LeaveRequest.objects.create(
        user_id=actor.user_id, kind=LeaveRequest.NEW, source="elm",
        category=category, status=status,
        start_date=start_date, end_date=end_date, half_day=half_day,
        purpose=purpose, evidence_note=evidence_note,
        station_leave=station_leave, station_place=station_place,
        station_reason=station_reason,
        chargeable_days=days, year=year,
        substitute_user_id=substitute_user_id if needs_substitute else None,
        substitute_status="pending" if needs_substitute else "none",
        unit_head_user_id=unit_head,
        establishment_user_id=establishment,
        is_director_self_sanction=director,
    )
    workflow.record_event(request, LeaveRequestEvent.SUBMITTED, actor=actor,
                          note=f"{label_for(category)} "
                               f"{start_date.isoformat()}…{end_date.isoformat()}"
                               f" ({days} day(s))")
    workflow.assign_task(request, actor=actor)
    return request


@transaction.atomic
def withdraw(actor, request: LeaveRequest) -> LeaveRequest:
    """BR-EL-022 / CFR-EL-018: immediate, applicant-only, pending-only."""
    authz.require(actor, "leave.request.delete")
    authz.require_applicant(actor, request)
    if request.status not in st.PENDING:
        raise ConflictError("Only a pending request can be withdrawn.",
                            code="not_pending")
    holder, frm = request.task_user_id, request.status
    request.status = st.WITHDRAWN
    request.save(update_fields=["status", "updated_at"])
    workflow.record_event(request, LeaveRequestEvent.STATUS_CHANGE, frm=frm,
                          to=st.WITHDRAWN, actor=actor,
                          note="withdrawn by applicant")
    workflow.close_task(request)
    notifications.notify(holder, "withdrawn",
                         "A leave request you were handling has been "
                         "withdrawn.", request)
    notifications.notify(request.user_id, "withdrawn",
                         "Your leave request has been withdrawn.", request)
    return request


@validated
@transaction.atomic
def nominate_substitute(actor, request: LeaveRequest,
                        substitute_user_id: int) -> LeaveRequest:
    """EL-UC-019: replace a declined nominee (or change one still pending)."""
    authz.require(actor, "leave.request.create")
    authz.require_applicant(actor, request)
    if request.status not in (st.APPLICANT_ACTION, st.AWAITING_SUBSTITUTE):
        raise ConflictError(
            "A substitute can only be nominated while one is being sought.",
            code="substitute_not_open")
    _validate_substitute(nominee=substitute_user_id,
                         applicant=request.user_id,
                         start=request.start_date, end=request.end_date)
    request.substitute_user_id = substitute_user_id
    request.substitute_status = "pending"
    request.save(update_fields=["substitute_user_id", "substitute_status",
                                "updated_at"])
    if request.status == st.APPLICANT_ACTION:
        workflow.move(request, st.AWAITING_SUBSTITUTE, actor=actor,
                      actor_kind=st.EMPLOYEE,
                      permission="leave.request.create",
                      guards=("replacement_nominated",),
                      note=f"nominee → {substitute_user_id}")
    else:
        workflow.assign_task(request, actor=actor, note="nominee replaced")
    return request


@validated
@transaction.atomic
def request_cancellation(actor, base: LeaveRequest, *,
                         reason: str = "") -> LeaveRequest:
    """EL-UC-006: a separate request row; the approved leave stands until
    this one is sanctioned (which then restores the balance)."""
    authz.require(actor, "leave.request.create")
    authz.require_applicant(actor, base)
    if base.status != st.APPROVED or base.kind != LeaveRequest.NEW:
        raise ConflictError(
            "Only an approved leave application can be cancelled.",
            code="not_cancellable")
    department = hierarchy.department_of(actor.user_id)
    status, unit_head, establishment, director = _routing(
        department=department, applicant_id=actor.user_id,
        needs_substitute=False)
    derived = LeaveRequest.objects.create(
        user_id=actor.user_id, kind=LeaveRequest.CANCELLATION, source="elm",
        category=base.category, status=status,
        start_date=base.start_date, end_date=base.end_date,
        half_day=base.half_day, purpose=reason,
        chargeable_days=base.chargeable_days, year=base.year,
        base_request=base, unit_head_user_id=unit_head,
        establishment_user_id=establishment,
        is_director_self_sanction=director,
    )
    workflow.record_event(derived, LeaveRequestEvent.SUBMITTED, actor=actor,
                          note=f"cancellation of #{base.id}")
    workflow.assign_task(derived, actor=actor)
    notifications.notify(
        base.user_id, "cancellation_requested",
        "Your cancellation request is now in review; the leave stands until "
        "it is sanctioned.", derived)
    return derived


@validated
@transaction.atomic
def request_extension(actor, base: LeaveRequest, *, new_end_date,
                      reason: str = "", substitute_user_id=None
                      ) -> LeaveRequest:
    """EL-UC-008: only the incremental period is charged and checked."""
    authz.require(actor, "leave.request.create")
    authz.require_applicant(actor, base)
    if base.status != st.APPROVED or base.kind != LeaveRequest.NEW:
        raise ConflictError("Only an approved leave can be extended.",
                            code="not_approved")
    if base.category not in EXTENDABLE_CATEGORIES:
        raise BadRequestError(
            f"{label_for(base.category)} cannot be extended; apply for fresh "
            "leave instead.", code="not_extendable")
    if new_end_date <= base.end_date:
        raise v.ValidationError(
            "An extension must end after the current leave ends.",
            code="invalid_interval")

    start = base.end_date + timedelta(days=1)
    policy = policy_service.current_policy()
    _, closed = _calendar_checks(base.category, start, new_end_date)
    days = counting.chargeable_days(
        category=base.category, start=start, end=new_end_date,
        half_day="none", closed_holidays=closed)

    held = balances.available(actor.user_id, base.category, base.year,
                              kind=actor.kind)
    v.check_balance(available=held, required=days, category=base.category)
    v.check_overlap(start=start, end=new_end_date, half_day="none",
                    category=base.category,
                    existing=_intervals(actor.user_id))

    needs_substitute = policy_service.substitute_required(policy,
                                                           base.category)
    if needs_substitute:
        _validate_substitute(nominee=substitute_user_id,
                             applicant=actor.user_id,
                             start=start, end=new_end_date)

    status, unit_head, establishment, director = _routing(
        department=hierarchy.department_of(actor.user_id),
        applicant_id=actor.user_id, needs_substitute=needs_substitute)
    derived = LeaveRequest.objects.create(
        user_id=actor.user_id, kind=LeaveRequest.EXTENSION, source="elm",
        category=base.category, status=status,
        start_date=start, end_date=new_end_date, half_day="none",
        purpose=reason, chargeable_days=days, year=base.year,
        base_request=base, unit_head_user_id=unit_head,
        establishment_user_id=establishment,
        is_director_self_sanction=director,
        substitute_user_id=substitute_user_id if needs_substitute else None,
        substitute_status="pending" if needs_substitute else "none",
    )
    workflow.record_event(derived, LeaveRequestEvent.SUBMITTED, actor=actor,
                          note=f"extension of #{base.id} through "
                               f"{new_end_date.isoformat()} ({days} day(s))")
    workflow.assign_task(derived, actor=actor)
    return derived


@validated
@transaction.atomic
def submit_resumption(actor, base: LeaveRequest, *, actual_date,
                      details: str = "") -> LeaveResumption:
    """EL-UC-011: the employee reports the real return; the authority's
    review adjusts the balance to match (BR-EL-026)."""
    authz.require(actor, "leave.request.create")
    authz.require_applicant(actor, base)
    if base.status != st.APPROVED or base.kind != LeaveRequest.NEW:
        raise ConflictError(
            "A resumption can only be filed against an approved leave.",
            code="not_approved")
    if base.category not in RESUMABLE_CATEGORIES:
        raise BadRequestError(
            f"{label_for(base.category)} has no formal resumption.",
            code="not_resumable")
    if actual_date < base.start_date:
        raise v.ValidationError(
            "The actual return cannot be before the leave began.",
            code="invalid_interval")
    if base.resumptions.filter(status=LeaveResumption.PENDING).exists():
        raise ConflictError("A resumption for this leave is already awaiting "
                            "review.", code="resumption_pending")

    approved_end = base.actual_end_date or base.end_date
    resumption = LeaveResumption.objects.create(
        request=base, actual_date=actual_date, details=details,
        approved_end_date=approved_end)
    reviewer = base.authority_user_id or base.unit_head_user_id
    base.task_class = SlaThreshold.RESUMPTION_REVIEW
    base.task_user_id = reviewer
    base.task_assigned_at = timezone.now()
    base.reminder_sent_at = None
    base.escalated_at = None
    base.save(update_fields=["task_class", "task_user_id", "task_assigned_at",
                             "reminder_sent_at", "escalated_at", "updated_at"])
    workflow.record_event(base, LeaveRequestEvent.NOTE, actor=actor,
                          note=f"resumption filed: actual {actual_date.isoformat()}")
    notifications.notify(reviewer, "assigned",
                         "A resumption report awaits your review.", base)
    return resumption


@validated
@transaction.atomic
def record_offline(actor, *, user_id: int, category: str, start_date,
                   end_date, half_day: str = "none", purpose: str = "",
                   sanction_reference: str, note: str = "") -> LeaveRequest:
    """BR-EL-029: recorded straight to approved with its paper reference —
    never a second workflow, never a silent balance change."""
    authz.require(actor, "leave.record.manage")
    if category not in CATEGORIES:
        raise BadRequestError(f"Unknown leave category {category!r}.",
                              code="unknown_category")
    if not str(sanction_reference).strip():
        raise v.ValidationError(
            "An offline record needs its paper reference (sanction order "
            "number or letter).", code="reference_required")
    person = directory.get_users([user_id]).get(user_id)
    if person is None or person.kind not in ("faculty", "staff"):
        raise BadRequestError(
            "Offline leave can only be recorded for an employee.",
            code="not_employee")
    v.check_interval(start=start_date, end=end_date, half_day=half_day,
                     category=category)

    policy = policy_service.current_policy()
    _, closed = _calendar_checks(category, start_date, end_date)
    days = counting.chargeable_days(
        category=category, start=start_date, end=end_date, half_day=half_day,
        closed_holidays=closed)
    year = policy_service.leave_year_of(policy, start_date)

    held = balances.available(user_id, category, year, kind=person.kind)
    v.check_balance(available=held, required=days, category=category)
    v.check_overlap(start=start_date, end=end_date, half_day=half_day,
                    category=category, existing=_intervals(user_id))

    request = LeaveRequest.objects.create(
        user_id=user_id, kind=LeaveRequest.OFFLINE, source="offline",
        category=category, status=st.APPROVED,
        start_date=start_date, end_date=end_date, half_day=half_day,
        purpose=purpose, chargeable_days=days, year=year,
        sanction_reference=sanction_reference.strip(),
        admin_note=note,
    )
    balances.deduct(user_id, category, year, days, request=request,
                    note=f"offline record {request.sanction_reference}",
                    actor_user_id=getattr(actor, "user_id", None))
    workflow.record_event(request, LeaveRequestEvent.DECISION, actor=actor,
                          note=f"offline entry, reference "
                               f"{request.sanction_reference}")
    workflow.record_event(request, LeaveRequestEvent.BALANCE_EFFECT,
                          actor=actor,
                          note=f"-{days} {category.upper()}")
    notifications.notify(user_id, "offline_recorded",
                         f"An offline {label_for(category)} "
                         f"({days} day(s)) was recorded for you.",
                         request)
    return request
