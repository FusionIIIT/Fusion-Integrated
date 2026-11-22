"""Applying for leave, and deciding on it (CW-EL-01, BR-EL-011..024).

Each public function is one transaction: the state change, the task that names
who acts next, the ledger postings that approval causes, and the notifications
all commit together or not at all. Nothing here trusts the caller â€” dates,
categories, authority and balance are re-checked at the point of decision,
because a draft applied last month was validated against last month's policy.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    PermissionDeniedError,
)
from modules.leave.services.errors import ValidationError
from modules.leave.domain import categories as cat
from modules.leave.domain import counting, eligibility, overlap, routing, state_machine as sm
from modules.leave.models import (
    DEBIT,
    ApprovalTask,
    LeaveRequest,
    SubstituteNomination,
)
from modules.leave.models.requests import (
    KIND_DIRECTOR_SELF_SANCTION,
    KIND_ESTABLISHMENT_ROUTING,
    KIND_FINAL_SANCTION,
    KIND_SUBSTITUTE_RESPONSE,
    KIND_UNIT_HEAD_DECISION,
    NOMINATION_ACCEPTED,
    NOMINATION_DECLINED,
    NOMINATION_PENDING,
    NOMINATION_WITHDRAWN,
    NOT_RECOMMENDED,
    RECOMMENDED,
    TASK_PENDING,
)
from modules.directory import contracts as directory
from modules.leave.services import authz, calendar, eligibility, ledger, lifecycle
from modules.leave.services import notifications, policy
from modules.leave.services import tasks as task_service

log = logging.getLogger("fusion.leave")


@dataclass(frozen=True)
class Person:
    """Who is asking and who they are, resolved once by the caller."""
    user_id: int
    kind: str
    department: str = ""


def _half_day_length(requested: date, end: date) -> Decimal:
    """An approved half day consumes 0.5; nothing else is fractional (BR-EL-011)."""
    return Decimal("0.5") if requested == end else Decimal("1")


#: Findings that make a draft meaningless, so it is refused at the point of entry
#: rather than allowed to sit in a draft list.
STRUCTURAL_REASONS: frozenset[str] = frozenset({"unknown_category",
                                                "category_not_applicable",
                                                "overlapping_leave"})


def findings_for(**kwargs):
    return eligibility.assess(**kwargs)


def _raise_on_blocking(findings) -> None:
    blocking = eligibility.blocking(findings)
    if blocking:
        raise ValidationError(
            "This request cannot be submitted yet.",
            details=[{"field": f.reason, "message": f.message} for f in blocking])


def _raise_on_structural(findings) -> None:
    """A draft records what the applicant intends; it only refuses what cannot
    become a valid request at all."""
    structural = [f for f in findings.outcomes if f.reason in STRUCTURAL_REASONS]
    if structural:
        raise ValidationError(
            "This request cannot be created.",
            details=[{"field": f.reason, "message": f.message} for f in structural])


def calculate_days(*, category: str, start_date: date, end_date: date,
                   half_day: bool, kind: str = "") -> Decimal:
    """The count the applicant sees, from the same rules the approval debits."""
    if start_date > end_date:
        raise ValidationError("The last date cannot be before the first date.")
    if half_day and start_date != end_date:
        raise ValidationError("A half day applies to a single date.")
    excluded: set[date] = set()
    if category in cat.CONTINUOUS:
        excluded = calendar.closed_holiday_dates(start_date, end_date)
    if category == cat.RESTRICTED_HOLIDAY:
        excluded = calendar.restricted_holiday_dates(start_date, end_date)
    count = counting.count_days(category, start_date, end_date,
                                excluded_holidays=excluded)
    if count == 0:
        return _half_day_length(start_date, end_date)
    return Decimal(count)


@transaction.atomic
def apply(*, actor, category: str, start_date: date, end_date: date,
          purpose: str, half_day: bool = False, half: str = "",
          station_leave_required: bool = False,
          station_leave_details: str = "",
          medical_evidence_reference: str = "") -> LeaveRequest:
    """Create a draft. Nothing is routed until the employee submits it, so a
    half-typed application notifies nobody."""
    authz.require(actor, authz.P_CREATE)
    person = _person(actor)
    pol = policy.current_policy()

    if category not in cat.CATEGORIES:
        raise ValidationError(f"Unknown leave type {category!r}.")
    if not purpose.strip():
        raise ValidationError("Give a reason for the leave.")
    if start_date < date.today():
        raise ValidationError("Leave cannot start in the past.")
    if station_leave_required and not station_leave_details.strip():
        # BR-EL-013: station leave cannot be requested as a bare checkbox.
        raise ValidationError("Describe the station arrangements.")
    if not policy.category_allowed(person.kind, category, pol):
        raise ValidationError(
            f"{_kind_label(person.kind)} cannot take {category} leave.")
    if category == cat.VACATION and not calendar.within_vacation_period(start_date):
        # BR-EL-006: VL is confined to the published vacation periods.
        raise ValidationError(
            "Vacation Leave can only be taken in a published vacation period.")

    days = calculate_days(category=category, start_date=start_date,
                          end_date=end_date, half_day=half_day, kind=person.kind)
    # A draft may be started while a balance is short or the calendar is not yet
    # published, so those become notes on the draft. Anything that would make the
    # request meaningless â€” an unknown type, a forbidden combination, an
    # impossible date range â€” is refused here.
    _raise_on_structural(findings_for(
        person_id=person.user_id, category=category, start_date=start_date,
        end_date=end_date, requested_days=days, kind=person.kind, half_day=half_day,
        half=half))

    unit = policy.org_unit_for(person.department)
    return LeaveRequest.objects.create(
        user_id=person.user_id, category=category, start_date=start_date,
        end_date=end_date, requested_days=days, half_day=half_day, half=half,
        purpose=purpose.strip(),
        station_leave_required=station_leave_required,
        station_leave_details=station_leave_details.strip(),
        medical_evidence_reference=medical_evidence_reference.strip(),
        substitute_required=policy.substitute_required(category, pol),
        kind=person.kind, department=person.department, org_unit=unit,
        status=sm.DRAFT)


@transaction.atomic
def update_draft(actor, request_obj: LeaveRequest, **changes) -> LeaveRequest:
    """Edit a draft. Only the owner may, and only while it is a draft."""
    authz.require(actor, authz.P_CREATE)
    authz.require_owner(actor, request_obj)
    authz.require_draft(request_obj)

    allowed = {"category", "start_date", "end_date", "purpose", "half_day",
               "half", "station_leave_required", "station_leave_details",
               "medical_evidence_reference"}
    unknown = set(changes) - allowed
    if unknown:
        raise BadRequestError(f"Cannot change {', '.join(sorted(unknown))}.")

    pol = policy.current_policy()
    category = changes.get("category", request_obj.category)
    start = changes.get("start_date", request_obj.start_date)
    end = changes.get("end_date", request_obj.end_date)
    half_day = changes.get("half_day", request_obj.half_day)
    if category not in cat.CATEGORIES:
        raise ValidationError(f"Unknown leave type {category!r}.")
    if not policy.category_allowed(request_obj.kind, category, pol):
        raise ValidationError(f"{_kind_label(request_obj.kind)} cannot take "
                              f"{category} leave.")
    if half_day and start != end:
        raise ValidationError("A half day applies to a single date.")

    for field, value in changes.items():
        setattr(request_obj, field, value)
    request_obj.requested_days = calculate_days(
        category=category, start_date=start, end_date=end, half_day=half_day,
        kind=request_obj.kind)
    request_obj.substitute_required = policy.substitute_required(category, pol)
    request_obj.save()
    return request_obj


@transaction.atomic
def delete_draft(actor, request_obj: LeaveRequest) -> None:
    authz.require(actor, authz.P_DELETE)
    authz.require_owner(actor, request_obj)
    authz.require_draft(request_obj)
    request_obj.delete()


#: States a substitution may be (re-)nominated from: a draft that has not been
#: sent yet, a request waiting for a substitute, and one a declining substitute
#: has sent back to the applicant (CW-EL-01 STT rows 1, 4 and 7).
NOMINATABLE: frozenset[str] = frozenset(
    {sm.DRAFT, sm.AWAITING_SUBSTITUTE, sm.APPLICANT_ACTION_REQUIRED})


@transaction.atomic
def nominate_substitute(actor, request_obj: LeaveRequest, nominee_user_id: int,
                        *, extension_request_id: int | None = None
                        ) -> SubstituteNomination:
    """Name the person who will cover. BR-EL-014: the nominee is not the
    approver, so the applicant cannot simply nominate their own decision.

    The applicant needs only `leave.request.create`; the answer is what needs
    `leave.substitute.respond`, and demanding it here would stop every employee
    who was never granted a substitute role from nominating anyone at all.
    """
    authz.require(actor, authz.P_CREATE)
    authz.require_owner(actor, request_obj)
    if nominee_user_id == request_obj.user_id:
        raise ValidationError("You cannot nominate yourself as your substitute.")

    extension = None
    if extension_request_id is None:
        if request_obj.status not in NOMINATABLE:
            raise ConflictError(
                f"A request that is {request_obj.status} cannot take a substitute "
                "nomination any more.")
        # A request a declining substitute sent back waits in
        # applicant_action_required; a nomination puts it back in the state the
        # next substitute's answer moves (CW-EL-01 STT row 7).
        if request_obj.status == sm.APPLICANT_ACTION_REQUIRED:
            _assert_edge(request_obj, sm.AWAITING_SUBSTITUTE)
            request_obj.status = sm.AWAITING_SUBSTITUTE
            request_obj.save(update_fields=["status", "updated_at"])
        start, end = request_obj.start_date, request_obj.end_date
    else:
        from modules.leave.models import ExtensionRequest

        extension = ExtensionRequest.objects.filter(
            pk=extension_request_id, leave_request=request_obj).first()
        if extension is None:
            raise ValidationError("Unknown extension.")
        if extension.status not in (sm.EXT_AWAITING_SUBSTITUTE,
                                    sm.EXT_APPLICANT_ACTION_REQUIRED):
            raise ConflictError(
                f"An extension that is {extension.status} cannot take a "
                "substitute nomination any more.")
        start, end = extension.additional_start_date, extension.additional_end_date

    # BR-EL-014: somebody else, an employee, and free for the whole period.
    refusal = eligibility.substitute_eligible(
        nominee_id=nominee_user_id, applicant_id=request_obj.user_id,
        period_start=start, period_end=end,
        nominee_kind=_person_for(nominee_user_id).kind)
    if refusal is not None:
        raise ValidationError(refusal.message, details=[{"field": refusal.reason,
                                                         "message": refusal.message}])

    pending = SubstituteNomination.objects.filter(
        leave_request=request_obj, extension_request_id=extension_request_id,
        status=NOMINATION_PENDING).first()
    if pending is not None:
        # BR-EL-014: re-nominating supersedes the standing nomination.
        pending.status = NOMINATION_WITHDRAWN
        pending.save(update_fields=["status", "updated_at"])

    nomination = SubstituteNomination.objects.create(
        leave_request=request_obj, extension_request_id=extension_request_id,
        nominee_user_id=nominee_user_id, status=NOMINATION_PENDING,
        period_start=start, period_end=end)
    task_service.open_task(
        leave_request=request_obj,
        subject_type=sm.EXTENSION if extension is not None else sm.NEW_LEAVE,
        subject_id=extension.pk if extension is not None else request_obj.pk,
        kind=KIND_SUBSTITUTE_RESPONSE,
        assignee_user_id=nominee_user_id)
    if extension is not None:
        lifecycle.nomination_created(extension)
    notifications.enqueue(
        topic="leave.substitute.nominated",
        dedupe_key=f"nominated:{nomination.pk}",
        recipient_user_id=nominee_user_id,
        subject="You have been nominated as substitute",
        body=f"{actor.display_name} nominated you to cover leave request "
             f"#{request_obj.pk} from {start} to {end}.")
    return nomination


def _person_for(user_id: int) -> Person:
    """The directory projection, which is the only place kind and department are
    known. Absent directory means absent knowledge, never a guess."""
    if user_id is None:
        return Person(user_id=None, kind="")
    kind = department = ""
    try:
        dto = directory.get_users([user_id]).get(user_id)
    except Exception as exc:                                       # noqa: BLE001
        log.warning("leave.directory_unavailable user=%s err=%s", user_id, exc)
    else:
        if dto is not None:
            kind, department = dto.kind, dto.department
    return Person(user_id=user_id, kind=kind, department=department)


@transaction.atomic
def respond_to_nomination(actor, nomination: SubstituteNomination, *, accept: bool
                          ) -> SubstituteNomination:
    """The nominated substitute's answer (BR-EL-015). Only they may answer."""
    authz.require(actor, authz.P_SUBSTITUTE_RESPOND)
    if nomination.nominee_user_id != authz.own_id(actor):
        raise PermissionDeniedError("This nomination is addressed to someone else.")
    if nomination.status != NOMINATION_PENDING:
        raise ConflictError("This nomination has already been answered.")

    nomination.status = NOMINATION_ACCEPTED if accept else NOMINATION_DECLINED
    nomination.responded_at = timezone.now()
    nomination.save(update_fields=["status", "responded_at", "updated_at"])
    subject_type = (sm.EXTENSION if nomination.extension_request_id is not None
                    else sm.NEW_LEAVE)
    subject_id = nomination.extension_request_id or nomination.leave_request_id
    task_service.cancel_open_tasks(subject_type=subject_type, subject_id=subject_id,
                                   kinds=(KIND_SUBSTITUTE_RESPONSE,))

    if accept:
        _advance_after_acceptance(nomination, now=nomination.responded_at)
        notifications.enqueue(
            topic="leave.substitute.accepted",
            dedupe_key=f"sub-accepted:{nomination.pk}",
            recipient_user_id=nomination.leave_request.user_id,
            subject="Your substitute accepted",
            body=f"Your substitute accepted cover for request "
                 f"#{nomination.leave_request_id}.")
    else:
        # BR-EL-014: a refusal returns the application to the employee to nominate
        # someone else, and it does not reach the Unit Head. CW-EL-01 row 7 lands
        # in applicant_action_required, not back in a review queue.
        applicant = nomination.leave_request.user_id
        if nomination.extension_request_id is not None:
            lifecycle.substitute_declined(nomination)
        else:
            _assert_edge(nomination.leave_request, sm.APPLICANT_ACTION_REQUIRED)
            nomination.leave_request.status = sm.APPLICANT_ACTION_REQUIRED
            nomination.leave_request.save(update_fields=["status", "updated_at"])
        notifications.enqueue(
            topic="leave.replacement_substitute.required",
            dedupe_key=f"sub-declined:{nomination.pk}",
            recipient_user_id=applicant,
            subject="A substitute must be nominated",
            body=f"The nominated substitute declined request "
                 f"#{nomination.leave_request_id}. Please nominate another.")
    return nomination


def _advance_after_acceptance(nomination: SubstituteNomination, *, now) -> None:
    """Acceptance is what releases the request into the hierarchy (BR-EL-014).

    A nomination already routes the new request, so re-reading the status here
    would be wrong; it starts from the state acceptance can move it to.
    """
    if nomination.extension_request_id is not None:
        # An extension has its own state machine; lifecycle.py advances it.
        lifecycle.substitute_accepted(nomination, now=now)
        return
    request_obj = nomination.leave_request
    _assert_edge(request_obj, sm.AWAITING_SUBSTITUTE)
    target = routing.submission_target(
        category=request_obj.category,
        applicant_is_director=policy.is_director_user(request_obj.user_id),
        has_unit_head=bool(policy.unit_head_for(request_obj.department)),
        substitute_required=False)
    request_obj.status = target
    request_obj.save(update_fields=["status", "updated_at"])
    _assign_next(leave_request=request_obj, status=target, now=now)


@transaction.atomic
def submit(actor, request_obj: LeaveRequest, *, now=None) -> LeaveRequest:
    """Route a valid draft to whoever acts first (BR-EL-011, BR-EL-014)."""
    authz.require(actor, authz.P_CREATE)
    authz.require_owner(actor, request_obj)
    authz.require_draft(request_obj)
    now = now or timezone.now()
    pol = policy.current_policy()

    if request_obj.start_date < now.date():
        raise ValidationError("Leave cannot start in the past.")
    days = calculate_days(
        category=request_obj.category, start_date=request_obj.start_date,
        end_date=request_obj.end_date, half_day=request_obj.half_day,
        kind=request_obj.kind)
    # Submission is where every condition must hold: the balance, the calendar
    # and the absence of an overlap.
    _raise_on_blocking(findings_for(
        person_id=request_obj.user_id, category=request_obj.category,
        start_date=request_obj.start_date, end_date=request_obj.end_date,
        requested_days=days, kind=request_obj.kind,
        half_day=request_obj.half_day, half=request_obj.half,
        exclude_request_id=request_obj.pk))

    request_obj.requested_days = days
    request_obj.substitute_required = policy.substitute_required(
        request_obj.category, pol)

    # A substitute who has already accepted is not asked again; otherwise a
    # category that needs one lands in awaiting_substitute_response and waits for
    # the applicant to nominate (CW-EL-01 STT row 1).
    accepted = SubstituteNomination.objects.filter(
        leave_request=request_obj, extension_request_id__isnull=True,
        status=NOMINATION_ACCEPTED).exists()
    target = routing.submission_target(
        category=request_obj.category,
        applicant_is_director=policy.is_director_user(request_obj.user_id),
        has_unit_head=bool(policy.unit_head_for(request_obj.department)),
        substitute_required=request_obj.substitute_required and not accepted)
    _assert_edge(request_obj, target)
    request_obj.status = target
    request_obj.save()

    _assign_next(leave_request=request_obj, status=request_obj.status, now=now)
    notifications.enqueue(
        topic="leave.request.submitted",
        dedupe_key=f"submitted:{request_obj.pk}",
        recipient_user_id=request_obj.user_id,
        subject="Leave request submitted",
        body=f"Your {request_obj.category} request for "
             f"{request_obj.requested_days} day(s) is now with "
             f"{_actor_label(request_obj.status)}.")
    return request_obj


@transaction.atomic
def withdraw(actor, request_obj: LeaveRequest) -> LeaveRequest:
    """The employee withdraws their own request (BR-EL-034)."""
    authz.require(actor, authz.P_CREATE, authz.P_DELETE)
    authz.require_owner(actor, request_obj)
    if request_obj.status not in sm.PENDING:
        raise ConflictError("Only a request still under consideration can be "
                            "withdrawn. Approved leave is cancelled instead.")
    now = timezone.now()
    task_service.cancel_open_tasks(subject_type=sm.NEW_LEAVE,
                                   subject_id=request_obj.pk)
    request_obj.status = sm.WITHDRAWN
    request_obj.save(update_fields=["status", "updated_at"])
    notifications.enqueue(
        topic="leave.request.withdrawn",
        dedupe_key=f"withdrawn:{request_obj.pk}",
        recipient_user_id=request_obj.user_id,
        subject="Leave request withdrawn",
        body=f"Your request #{request_obj.pk} has been withdrawn.")
    return request_obj


@transaction.atomic
def decide(actor, task: ApprovalTask, *, approve: bool, note: str = "",
           recommendation: str = "", now=None) -> LeaveRequest:
    """A Unit Head, the Establishment, the Sanctioning Authority or the Director
    acts on the task they hold. Only these four edges are reachable here;
    lifecycle workflows go through services.lifecycle (BR-EL-016..022)."""
    authz.require(actor, authz.P_APPROVE)
    authz.require_assignee(actor, task)
    authz.require_pending(task)
    request_obj = task.leave_request
    now = now or timezone.now()

    if task.subject_type != sm.NEW_LEAVE:
        raise ConflictError(
            f"Task #{task.pk} belongs to {task.subject_type}; decide it through "
            "the matching lifecycle action.")
    if task.kind == KIND_UNIT_HEAD_DECISION:
        return _unit_head_step(actor, task, request_obj, approve=approve, note=note,
                               recommendation=recommendation, now=now)
    if task.kind == KIND_SUBSTITUTE_RESPONSE:
        raise ConflictError("Only the nominated substitute can answer this.")

    target = _target_for(task.kind, approve)
    _assert_edge(request_obj, target)
    task_service.complete_task(task, outcome=target, note=note, now=now)
    if target == sm.APPROVED:
        _post_debit(request_obj, created_by_user_id=authz.own_id(actor))
    _record_decision(request_obj, actor, status=target, note=note, now=now)
    _announce_decision(request_obj, approve, note, dedupe_key=f"decided:{task.kind}:{task.pk}")
    if target != sm.APPROVED:
        task_service.cancel_open_tasks(subject_type=sm.NEW_LEAVE,
                                       subject_id=request_obj.pk)
    return request_obj


def _target_for(kind: str, approve: bool) -> str:
    if kind == KIND_ESTABLISHMENT_ROUTING:
        return sm.AWAITING_FINAL_DECISION
    return sm.APPROVED if approve else sm.REJECTED


def _assert_edge(request_obj: LeaveRequest, target: str) -> None:
    if not sm.is_legal(sm.NEW_LEAVE, request_obj.status, target):
        raise ConflictError(
            f"Request #{request_obj.pk} is {request_obj.status}, which does not "
            f"allow moving to {target}.")


def _record_decision(request_obj: LeaveRequest, actor, *, status: str, note: str,
                     now) -> LeaveRequest:
    request_obj.status = status
    request_obj.decided_by_user_id = authz.own_id(actor)
    request_obj.decided_at = now
    request_obj.decision_note = note[:500]
    request_obj.save()
    return request_obj


def _announce_decision(request_obj: LeaveRequest, approve: bool, note: str, *,
                       dedupe_key: str) -> None:
    notifications.enqueue(
        topic="leave.decision.approved" if approve else "leave.decision.rejected",
        dedupe_key=dedupe_key, recipient_user_id=request_obj.user_id,
        subject="Leave approved" if approve else "Leave rejected",
        body=f"Your {request_obj.category} request #{request_obj.pk} was "
             f"{'approved' if approve else 'rejected'}."
             + (f" {note}" if note else ""))


def _unit_head_step(actor, task: ApprovalTask, request_obj: LeaveRequest, *,
                    approve: bool, note: str, recommendation: str,
                    now) -> LeaveRequest:
    """BR-EL-016 for CL/RH: the Unit Head is the deciding authority. BR-EL-017 for
    everything else: a not-recommended decision is a recommendation the higher
    authority still sees â€” it is not a refusal."""
    if recommendation and recommendation not in (RECOMMENDED, NOT_RECOMMENDED):
        raise ValidationError(
            "A Unit Head records a recommendation of 'recommended' or "
            "'not_recommended'.")

    task_service.complete_task(task, outcome=recommendation or "reviewed",
                               note=note, now=now)
    request_obj.unit_head_recommendation = recommendation or (
        RECOMMENDED if approve else NOT_RECOMMENDED)

    if routing.is_unit_head_final(request_obj.category):
        target = sm.APPROVED if approve else sm.REJECTED
    else:
        target = routing.after_unit_head(
            category=request_obj.category,
            establishment_configured=policy.current_policy().establishment_step_enabled)
        task_service.cancel_open_tasks(subject_type=sm.NEW_LEAVE,
                                       subject_id=request_obj.pk)

    _assert_edge(request_obj, target)
    if target == sm.APPROVED:
        _post_debit(request_obj, created_by_user_id=authz.own_id(actor))
    decided = target in (sm.APPROVED, sm.REJECTED)
    _record_decision(request_obj, actor, status=target, note=note, now=now)
    if decided:
        _announce_decision(request_obj, approve, note,
                           dedupe_key=f"decided:unit_head:{task.pk}")
    else:
        notifications.enqueue(
            topic="leave.unit_head.reviewed",
            dedupe_key=f"unit-head-reviewed:{task.pk}",
            recipient_user_id=request_obj.user_id,
            subject="Your request moved to the next authority",
            body=f"The Unit Head recorded '{request_obj.unit_head_recommendation}' "
                 f"for request #{request_obj.pk}.")
    return request_obj


def _post_debit(request_obj: LeaveRequest, *, created_by_user_id: int | None) -> None:
    """Approval consumes days (BR-EL-011). Posted through the ledger so the
    balance and the entry cannot disagree."""
    ledger.post([ledger.Posting(
        user_id=request_obj.user_id, year=request_obj.start_date.year,
        category=request_obj.category, kind=DEBIT,
        days=Decimal(request_obj.requested_days),
        note=f"Approved leave request #{request_obj.pk}",
        leave_request_id=request_obj.pk)],
        created_by_user_id=created_by_user_id)


#: Which task kind each waiting state needs.
STATE_TASK_KIND: dict[str, str] = {
    sm.AWAITING_UNIT_HEAD: KIND_UNIT_HEAD_DECISION,
    sm.AWAITING_ESTABLISHMENT: KIND_ESTABLISHMENT_ROUTING,
    sm.AWAITING_FINAL_DECISION: KIND_FINAL_SANCTION,
    sm.AWAITING_DIRECTOR: KIND_DIRECTOR_SELF_SANCTION,
}


def _assign_next(*, leave_request: LeaveRequest, status: str,
                 now) -> ApprovalTask | None:
    """Name the person the new state waits on, or say plainly that nobody is
    configured. A request nobody is answerable for is never left waiting."""
    kind = STATE_TASK_KIND.get(status)
    if kind is None:
        return None
    assignee = _next_assignee(leave_request, status)
    if assignee is None:
        raise ValidationError(
            f"No {_actor_label(status).lower()} is configured to handle request "
            f"#{leave_request.pk}. Ask the Leave Administrator to configure the "
            "routing.")
    return task_service.open_task(
        leave_request=leave_request, subject_type=sm.NEW_LEAVE,
        subject_id=leave_request.pk, kind=kind, assignee_user_id=assignee, now=now)


def _next_assignee(request_obj: LeaveRequest, status: str) -> int | None:
    """Route-specific first, then the Unit Head of the person's own department.

    A request never falls through to somebody unrelated: an unconfigured step is
    a gap an administrator must close, not one to guess at.
    """
    unit = request_obj.org_unit
    step_kind = {sm.AWAITING_UNIT_HEAD: routing.UNIT_HEAD_STEP,
                 sm.AWAITING_ESTABLISHMENT: routing.ESTABLISHMENT_STEP,
                 sm.AWAITING_FINAL_DECISION: routing.FINAL_SANCTION_STEP,
                 sm.AWAITING_DIRECTOR: routing.DIRECTOR_SELF_SANCTION_STEP}[status]

    if step_kind == routing.UNIT_HEAD_STEP:
        return unit.head_user_id if unit is not None else None

    step = policy.resolved_route(request_obj.category, org_unit=unit).step(step_kind)
    if step is not None and step.assigned:
        return step.user_id

    # The Unit Head is the standing fallback for their own department, which is
    # what the hierarchy does in the specification's own examples.
    if step_kind in (routing.FINAL_SANCTION_STEP, routing.DIRECTOR_SELF_SANCTION_STEP):
        return unit.head_user_id if unit is not None else None
    return None


def _person(actor) -> Person:
    """The applicant's kind and department come from the directory projection, the
    one place that knows them. The session is only the identity."""
    user_id = authz.own_id(actor)
    dto = _person_for(user_id)
    return Person(user_id=user_id, kind=dto.kind,
                  department=getattr(dto, "department", "") or "")


def _kind_label(kind: str) -> str:
    return {"faculty": "Faculty", "staff": "Staff"}.get(kind, kind or "This person")


def _actor_label(status: str) -> str:
    return {sm.AWAITING_SUBSTITUTE: "your substitute",
            sm.AWAITING_UNIT_HEAD: "your Unit Head",
            sm.AWAITING_ESTABLISHMENT: "the Establishment",
            sm.AWAITING_FINAL_DECISION: "the Sanctioning Authority",
            sm.AWAITING_DIRECTOR: "the Director"}.get(status, "the next authority")


def active_overlap(request_obj: LeaveRequest) -> dict[str, list[LeaveRequest]]:
    """BR-EL-024: overlapping requests for the same person, split by whether a
    concurrent request is exempt."""
    return overlap.split_overlaps(
        other_requests=list(LeaveRequest.objects.filter(
            user_id=request_obj.user_id, status__in=sm.PENDING)
            .exclude(pk=request_obj.pk)),
        category=request_obj.category,
        start_date=request_obj.start_date, end_date=request_obj.end_date)


def pending_tasks_for(user_id: int) -> list[ApprovalTask]:
    return list(ApprovalTask.objects.filter(assignee_user_id=user_id,
                                            status=TASK_PENDING))
