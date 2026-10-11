"""Writes to a leave request — CW-EL-01, CW-EL-02 and CW-EL-03.

Raises domain errors, never DRF exceptions, so every path here is callable from
a Celery task or a management command. Four things must all hold:

    state machine   which actor kind may drive this edge, and where it lands
    permission      whether the caller holds the right (BR-EL-036)
    assignment      whether the task is theirs, or their office's
    guards          the business conditions the transition row declares

The route a request takes is resolved once, at submission, from the current
hierarchy configuration and frozen onto the row (BR-EL-019, BR-EL-030): a later
configuration edit must not rewrite the history of a decision already taken.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import categories as cat
from modules.leave.domain import counting, eligibility, routing
from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    LeaveRequest,
    LeaveRequestTransition,
    LeaveSubstituteAssignment,
    WorkflowTask,
)
from modules.leave.selectors import leave as sel
from modules.leave.services import accounts, authz, facts, notifications

log = logging.getLogger("fusion.leave.applications")

ZERO = Decimal("0")


# -- Reading the frozen route --------------------------------------------------
def route_of(request) -> tuple[routing.Step, ...]:
    return tuple(
        routing.Step(order=int(s["order"]), kind=s["kind"],
                     authority=s.get("authority", ""), label=s.get("label", ""))
        for s in (request.route or [])
    )


def facts_for(request, route) -> dict[str, bool]:
    """The branch facts the STT rows are conditioned on."""
    return {
        "substitute_required": request.substitute_required,
        "applicant_is_director": request.applicant_is_director,
        "establishment_configured": routing.establishment_configured(route),
        "unit_head_final": request.category in cat.UNIT_HEAD_FINAL,
    }


def resolve_or_raise(*, request, action: str, actor_kind: str):
    """`sm.resolve` with its errors translated, so an illegal move is a 409."""
    route = route_of(request)
    try:
        return sm.resolve(request.kind, request.status, action, actor_kind,
                          facts=facts_for(request, route))
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"A {request.kind} request in '{exc.frm}' cannot perform "
            f"'{exc.action}'.", code="invalid_transition",
            details=[{"from": exc.frm, "action": exc.action,
                      "allowed": sm.allowed_actions(request.kind, exc.frm,
                                                    actor_kind)}]) from exc
    except sm.ActorNotAllowed as exc:
        raise PermissionDeniedError(
            "Your role cannot make that change.", code="actor_not_allowed",
            details=[{"from": exc.frm, "action": exc.action,
                      "actor": exc.actor_kind}]) from exc


# -- Tasks ---------------------------------------------------------------------
def _open_task(*, request, step: routing.Step, unit: str,
               assignee_user_id: int | None = None) -> WorkflowTask:
    """Open the actionable step and notify its holder (BR-EL-035)."""
    task = WorkflowTask.objects.create(
        request=request, step_order=step.order, step_kind=step.kind,
        task_class=step.task_class, authority=step.authority,
        assignee_user_id=assignee_user_id,
        assignee_role="" if assignee_user_id else routing.role_for_step(step, unit=unit),
    )
    notifications.notify_assignment(request=request, task=task)
    return task


def _close_tasks(*, request, actor) -> None:
    """Every pending task on this request ends when the request leaves a
    pending state, so no approver can act on a decided request."""
    pending = WorkflowTask.objects.filter(request=request, status="pending")
    assignee = getattr(actor, "user_id", None)
    pending.filter(assignee_user_id=assignee).update(
        status="completed", completed_at=timezone.now(), completed_by_user_id=assignee)
    pending.exclude(assignee_user_id=assignee).update(
        status="cancelled", completed_at=timezone.now())


def _advance(*, request, transition: sm.Transition, actor, unit: str,
             note: str = "") -> None:
    """Apply one STT row: status, audit, withdrawal of downstream tasks, and the
    task for whatever comes next."""
    frm, request.status = request.status, transition.to
    fields = ["status", "updated_at"]
    if note:
        request.decision_note = note[:300]
        fields.append("decision_note")
    request.save(update_fields=fields)

    LeaveRequestTransition.objects.create(
        request=request, from_status=frm, to_status=transition.to,
        action=transition.action, actor_user_id=getattr(actor, "user_id", None),
        actor_role=transition.step_kind, step_kind=transition.step_kind,
        note=note[:300])

    if transition.to not in sm.PENDING:
        _close_tasks(request=request, actor=actor)
        return

    # The next actionable step is whatever this state represents.
    route = route_of(request)
    step = _step_for_state(route, transition.to)
    if step is None:
        # A substitute response is assigned to one person, not to an office.
        step = routing.Step(order=0, kind="substitute", label="Substitute response")
        assignment = (LeaveSubstituteAssignment.objects
                      .filter(request=request, status="nominated").first())
        _open_task(request=request, step=step, unit=unit,
                   assignee_user_id=getattr(assignment, "nominee_user_id", None))
        return
    _open_task(request=request, step=step, unit=unit)


def _step_for_state(route, status: str) -> routing.Step | None:
    """Which configured step the new state belongs to."""
    if status in (sm.AWAITING_UNIT_HEAD, sm.AWAITING_EXT_UNIT_HEAD,
                  sm.CANCELLATION_UNIT_HEAD):
        return routing.Step(order=0, kind=routing.UNIT_HEAD, label="Unit Head review")
    if status in (sm.AWAITING_ESTABLISHMENT, sm.EXT_ESTABLISHMENT,
                  sm.CANCELLATION_ESTABLISHMENT):
        return routing.Step(order=1, kind=routing.ESTABLISHMENT,
                            authority="deputy_registrar_estt")
    if status in (sm.AWAITING_SANCTION, sm.EXT_FINAL, sm.CANCELLATION_FINAL):
        return routing.sanction_step(route) or routing.Step(
            order=99, kind=routing.SANCTION,
            authority=routing.DEFAULT_AUTHORITY)
    if status == sm.AWAITING_DIRECTOR_SELF_SANCTION:
        return routing.Step(order=1, kind=routing.SANCTION, authority="director",
                            label="Director self-sanction")
    return None


def _post_leave(*, request, days: Decimal, employee_kind: str,
                entitlements: dict | None, note: str) -> None:
    """Deduct the approved days, or the incremental additional period."""
    accounts.debit(user_id=request.user_id, category=request.category,
                   leave_year=request.period_from.year, days=days,
                   request_id=request.pk,
                   entitled_days=accounts.entitlement_for(
                       request.category, employee_kind, entitlements=entitlements),
                   note=note)


# -- EL-UC-001: apply ----------------------------------------------------------
def assess(*, actor, category: str, period_from: date, period_to: date,
           half: str = "", days: Decimal | None = None) -> dict:
    """Validate a would-be request without creating one (EL-UC-001 M4).

    The same function the submit path uses, so the preview cannot disagree with
    what submission will decide.
    """
    employee = facts.employee(actor.user_id) or facts.Employee(
        user_id=getattr(actor, "user_id", 0))
    policy = sel.current_policy(period_from.year)
    entitlements = (policy.entitlements if policy else None)
    leave_year = period_from.year

    count = counting.chargeable_days(category=category, start=period_from,
                                     end=period_to, half=half)
    chargeable = days if days is not None else count.days
    available = accounts.available_days(
        user_id=employee.user_id, category=category, leave_year=leave_year,
        employee_kind=employee.kind, entitlements=entitlements)

    failures = eligibility.validate_new_request(
        category=category, employee_kind=employee.kind, start=period_from,
        end=period_to, half=half, days=chargeable, available=available,
        existing=sel.active_intervals(user_id=employee.user_id),
        rh_dates=sel.rh_dates(leave_year))

    return {
        "employee_kind": employee.kind,
        "unit": employee.unit,
        "leave_year": leave_year,
        "chargeable_days": chargeable,
        "charged": [d.isoformat() for d in count.charged],
        "skipped": [d.isoformat() for d in count.skipped],
        "available_days": available,
        "failures": failures,
        "is_valid": not failures,
    }


@transaction.atomic
def submit_new(*, actor, category: str, period_from: date, period_to: date,
               half: str = "", purpose: str = "", station_leave: dict | None = None,
               substitute_user_id: int | None = None) -> LeaveRequest:
    """Create and submit one leave application (EL-UC-001)."""
    authz.require(actor, sm.P_APPLY)
    check = assess(actor=actor, category=category, period_from=period_from,
                   period_to=period_to, half=half)
    if not check["is_valid"]:
        first = check["failures"][0]
        raise ConflictError(
            first.message, code=first.code,
            details=[{"code": f.code, "message": f.message, "details": f.details}
                     for f in check["failures"]])

    employee = facts.employee(actor.user_id)
    unit = employee.unit if employee else ""
    applicant_is_director = "Director" in tuple(getattr(actor, "roles", ()) or ())

    policy = sel.current_policy(period_from.year)
    entitlements = policy.entitlements if policy else None
    route = routing.resolve_route(
        category=category, unit=unit,
        rules=sel.hierarchy_rules(),
        applicant_is_director=applicant_is_director)
    route_payload = [{"order": s.order, "kind": s.kind, "authority": s.authority,
                      "label": s.label, "task_class": s.task_class} for s in route]

    substitute_required = bool(substitute_user_id)
    request = LeaveRequest.objects.create(
        kind=sm.NEW, category=category, status=sm.DRAFT, user_id=actor.user_id,
        period_from=period_from, period_to=period_to, half=half,
        days_counted=check["chargeable_days"], purpose=purpose[:300],
        station_leave=station_leave or {},
        substitute_user_id=substitute_user_id,
        substitute_required=substitute_required,
        route=route_payload, applicant_is_director=applicant_is_director,
        submitted_at=timezone.now())
    request.reference = f"ELM-{period_from.year}-{request.pk:06d}"
    request.save(update_fields=["reference", "updated_at"])

    if substitute_required:
        _nominate(request=request, applicant=request.user_id,
                  nominee_user_id=int(substitute_user_id))

    transition = resolve_or_raise(request=request, action=sm.SUBMIT,
                                  actor_kind=sm.EMPLOYEE)
    authz.require(actor, transition.permission)
    _advance(request=request, transition=transition, actor=actor, unit=unit)
    _ensure_account(request=request, employee_kind=check["employee_kind"],
                    entitlements=entitlements)
    log.info("leave.request.submitted id=%s category=%s user=%s",
             request.pk, request.category, request.user_id)
    return request


def _ensure_account(*, request, employee_kind: str,
                    entitlements: dict | None) -> None:
    """Open the account the request will draw on, so the balance screen shows it."""
    accounts.ensure_balance(
        user_id=request.user_id, category=request.category,
        leave_year=request.period_from.year,
        entitled_days=accounts.entitlement_for(request.category, employee_kind,
                                               entitlements=entitlements))


# -- EL-UC-002 / EL-UC-019: substitute consent and recovery ---------------------
def _nominate(*, request, applicant: int, nominee_user_id: int) -> LeaveSubstituteAssignment:
    """BR-EL-014 — one nominee, another employee, free during the period."""
    employees = facts.employees([applicant, nominee_user_id])
    eligible = sel.assignable_employee(
        nominee_user_id=nominee_user_id, applicant_user_id=applicant,
        exists=nominee_user_id in employees)
    if not eligible:
        raise ConflictError(
            "The nominated substitute must be another employee.",
            code="substitute_ineligible",
            details=[{"reason": "not_an_employee_or_is_the_applicant"}])

    busy = sel.active_intervals(user_id=nominee_user_id,
                                exclude_request_ids=[request.pk])
    problem = eligibility.substitute_eligibility(
        applicant_user_id=applicant, nominee_user_id=nominee_user_id,
        nominee_exists=True, nominee_leave=[
            i for i in busy
            if not (i.end < request.period_from or request.period_to < i.start)])
    if problem:
        raise ConflictError(problem.message, code=problem.code,
                            details=[problem.details] if problem.details else [])

    # A replacement supersedes whatever was awaiting a response.
    LeaveSubstituteAssignment.objects.filter(request=request,
                                             status="nominated").update(
        status="superseded")
    assignment = LeaveSubstituteAssignment.objects.create(
        request=request, nominee_user_id=nominee_user_id, status="nominated")
    request.substitute_user_id = nominee_user_id
    request.substitute_required = True
    request.save(update_fields=["substitute_user_id", "substitute_required",
                                "updated_at"])
    return assignment


@transaction.atomic
def respond_to_substitute(*, actor, assignment_id: int, accept: bool,
                          note: str = "") -> LeaveSubstituteAssignment:
    """EL-UC-002 — accept or decline a responsibility assignment.

    No permission is checked: the assignment is the authority (BR-EL-014). A
    stale response on a request that is no longer pending is refused, which is
    EL-UC-002's single alternative flow.
    """
    assignment = (LeaveSubstituteAssignment.objects
                  .select_related("request")
                  .filter(pk=assignment_id).first())
    if assignment is None:
        raise NotFoundError("No such substitute request.")
    if assignment.nominee_user_id != getattr(actor, "user_id", None):
        raise PermissionDeniedError("This responsibility request is not yours.",
                                    code="not_the_nominee")
    request = assignment.request
    if request.status not in (sm.AWAITING_SUBSTITUTE, sm.AWAITING_EXT_SUBSTITUTE):
        raise ConflictError(
            "That responsibility request is no longer awaiting a response.",
            code="stale_substitution")

    employee = facts.employee(request.user_id)
    unit = employee.unit if employee else ""
    action = sm.SUBSTITUTE_ACCEPT if accept else sm.SUBSTITUTE_DECLINE
    transition = resolve_or_raise(request=request, action=action,
                                  actor_kind=sm.SUBSTITUTE)

    assignment.status = "accepted" if accept else "declined"
    assignment.responded_at = timezone.now()
    assignment.response_note = note[:300]
    assignment.save(update_fields=["status", "responded_at", "response_note"])

    _advance(request=request, transition=transition, actor=actor, unit=unit,
             note=note)
    return assignment


@transaction.atomic
def nominate_replacement(*, actor, request_id: int,
                         substitute_user_id: int) -> LeaveSubstituteAssignment:
    """EL-UC-019 — recover from a decline with one replacement nominee."""
    request = _locked_request(request_id)
    authz.require(actor, sm.P_APPLY)
    authz.require_owner(actor, request)
    if request.status not in (sm.APPLICANT_ACTION_REQUIRED,
                              sm.EXT_APPLICANT_ACTION_REQUIRED):
        raise ConflictError(
            "A replacement can only be nominated after a substitute declines.",
            code="replacement_not_available")
    transition = resolve_or_raise(request=request, action=sm.NOMINATE_REPLACEMENT,
                                  actor_kind=sm.EMPLOYEE)
    authz.require(actor, transition.permission)
    assignment = _nominate(request=request, applicant=request.user_id,
                           nominee_user_id=substitute_user_id)
    employee = facts.employee(request.user_id)
    _advance(request=request, transition=transition, actor=actor,
             unit=employee.unit if employee else "")
    return assignment


# -- EL-UC-003/004/005: routed decisions ---------------------------------------
@transaction.atomic
def decide(*, actor, task_id: int, action: str, note: str = "",
           recommendation: str = "") -> LeaveRequest:
    """Drive one routed step: recommend, verify, approve or reject.

    `recommendation` is the Unit Head's recorded outcome for a higher-sanction
    request. Both outcomes continue through the path (BR-EL-017), so it is a
    value on the request rather than a different transition.
    """
    task = WorkflowTask.objects.select_related("request").filter(pk=task_id).first()
    if task is None:
        raise NotFoundError("No such task.")
    if not authz.may_act(actor, task):
        raise PermissionDeniedError("This task is not in your queue.",
                                    code="not_your_task")
    if task.status != "pending":
        raise ConflictError("That task has already been dealt with.",
                            code="task_not_pending")

    request = LeaveRequest.objects.select_for_update().get(pk=task.request_id)
    if request.status in sm.TERMINAL:
        raise ConflictError("That request has already been decided.",
                            code="already_decided")

    actor_kind = authz.task_actor_kind(task)
    authz.require(actor, sm.P_DECIDE)
    transition = resolve_or_raise(request=request, action=action,
                                  actor_kind=actor_kind)
    _guard(action=action, request=request, note=note)

    applicant = facts.employee(request.user_id)
    employee_kind = applicant.kind if applicant else cat.STAFF
    unit = applicant.unit if applicant else ""
    policy = sel.current_policy(request.period_from.year)
    entitlements = policy.entitlements if policy else None

    if action == sm.RECOMMEND:
        request.recommendation = (recommendation
                                  if recommendation in ("recommended",
                                                        "not_recommended")
                                  else "recommended")
        request.recommendation_note = note[:300]
        request.save(update_fields=["recommendation", "recommendation_note",
                                    "updated_at"])
        if request.kind == sm.CANCELLATION:
            _guard_cancellation_review(request)

    _advance(request=request, transition=transition, actor=actor, unit=unit,
             note=note)

    if transition.to == sm.APPROVED:
        request.decided_at = timezone.now()
        request.decided_by_user_id = getattr(actor, "user_id", None)
        request.save(update_fields=["decided_at", "decided_by_user_id", "updated_at"])
        _post_leave(request=request, days=request.days_counted,
                    employee_kind=employee_kind, entitlements=entitlements,
                    note="Leave posted on final approval")
        notifications.notify_decision(
            request=request, subject="Your leave is approved",
            body=(f"{cat.LABELS[request.category]} from {request.period_from} to "
                  f"{request.period_to} has been approved."))
    elif transition.to == sm.REJECTED:
        request.decided_at = timezone.now()
        request.decided_by_user_id = getattr(actor, "user_id", None)
        request.save(update_fields=["decided_at", "decided_by_user_id", "updated_at"])
        notifications.notify_decision(
            request=request, subject="Your leave request was not approved",
            body=(f"{cat.LABELS[request.category]} from {request.period_from} to "
                  f"{request.period_to} was not approved."))
    elif transition.to == sm.EXTENDED:
        incremental = request.days_counted
        _post_leave(request=request, days=incremental, employee_kind=employee_kind,
                    entitlements=entitlements,
                    note="Incremental extension period posted")
        notifications.notify_decision(
            request=request, subject="Your leave extension is approved",
            body=f"The additional period to {request.period_to} has been approved.")
    elif transition.to == sm.EXTENSION_REJECTED:
        notifications.notify_decision(
            request=request, subject="Your leave extension was not approved",
            body="The original approved leave is unchanged.")
    elif transition.to == sm.CANCELLED:
        _reverse_approval(request=request)
    elif transition.to == sm.CANCELLATION_REJECTED:
        notifications.notify_decision(
            request=request, subject="Your cancellation request was not approved",
            body="The original approved leave remains unchanged.")

    return request


def _guard(*, action: str, request, note: str) -> None:
    """A rejection says why.

    BR-EL-017 keeps a Unit Head's "Not Recommended" off the rejection path, so
    this bites on the two actions that really do end a request, plus a
    cancellation refusal.
    """
    if action in (sm.REJECT, sm.REJECT_CANCELLATION) and not (note or "").strip():
        raise ConflictError("A rejection needs a reason.", code="reason_required")


def _guard_cancellation_review(request) -> None:
    """BR-EL-023 — abandonment of the approved leave is what is being reviewed."""
    if request.base_request is None:
        raise ConflictError("This cancellation is not attached to a leave.",
                            code="orphan_cancellation")


def _reverse_approval(*, request) -> None:
    """BR-EL-023 — approving a cancellation restores the deducted balance and
    marks the leave Cancelled. The approved leave row is never edited."""
    base = request.base_request
    if base is None:
        raise ConflictError("This cancellation is not attached to a leave.",
                            code="orphan_cancellation")
    accounts.restore(user_id=base.user_id, category=base.category,
                     leave_year=base.period_from.year, days=base.days_counted,
                     request_id=base.pk, note="Approved leave cancelled")
    request.cancelled_at = timezone.now()
    request.save(update_fields=["cancelled_at", "updated_at"])
    LeaveRequestTransition.objects.create(
        request=base, from_status=sm.APPROVED, to_status=sm.CANCELLED,
        action="cancelled", actor_user_id=request.decided_by_user_id,
        step_kind="sanction", note=f"Cancellation {request.reference} approved")
    notifications.notify_decision(
        request=base, subject="Your leave has been cancelled",
        body=(f"{cat.LABELS[base.category]} from {base.period_from} to "
              f"{base.period_to} is cancelled and the balance has been restored."))


# -- EL-UC-007: withdrawal -----------------------------------------------------
@transaction.atomic
def withdraw(*, actor, request_id: int, reason: str = "") -> LeaveRequest:
    """Immediate termination of a pending request (BR-EL-022, BR-EL-034)."""
    request = _locked_request(request_id)
    authz.require(actor, sm.P_WITHDRAW)
    authz.require_owner(actor, request)
    employee = facts.employee(request.user_id)
    unit = employee.unit if employee else ""
    transition = resolve_or_raise(request=request, action=sm.WITHDRAW,
                                  actor_kind=sm.EMPLOYEE)
    _advance(request=request, transition=transition, actor=actor, unit=unit,
             note=reason)
    request.withdrawn_at = timezone.now()
    request.save(update_fields=["withdrawn_at", "updated_at"])
    LeaveSubstituteAssignment.objects.filter(request=request,
                                             status="nominated").update(
        status="superseded")
    notifications.notify_roles(
        request=request, subject="A leave request was withdrawn",
        body=(f"{request.reference} was withdrawn by the applicant; remaining "
              "approval processing has stopped."))
    return request


# -- EL-UC-008: cancellation of an approved leave -------------------------------
@transaction.atomic
def request_cancellation(*, actor, request_id: int, note: str = "") -> LeaveRequest:
    """Create a cancellation request without editing the approved leave."""
    base = _locked_request(request_id)
    authz.require(actor, sm.P_WITHDRAW)
    authz.require_owner(actor, base)
    if base.status not in (sm.APPROVED, sm.EXTENDED):
        raise ConflictError("Only an approved leave can be cancelled.",
                            code="leave_not_approved")

    problem = eligibility.cancellation_window(approved_start=base.period_from,
                                              today=timezone.localdate())
    if problem:
        raise ConflictError(problem.message, code=problem.code,
                            details=[problem.details] if problem.details else [])

    employee = facts.employee(base.user_id)
    route = routing.resolve_route(
        category=base.category, unit=employee.unit if employee else "",
        rules=sel.hierarchy_rules(),
        applicant_is_director=base.applicant_is_director)
    cancellation = LeaveRequest.objects.create(
        kind=sm.CANCELLATION, category=base.category, status=sm.DRAFT,
        user_id=base.user_id, base_request=base, period_from=base.period_from,
        period_to=base.period_to, days_counted=base.days_counted,
        purpose=note[:300] or "Cancellation of approved leave",
        route=[{"order": s.order, "kind": s.kind, "authority": s.authority,
                "label": s.label, "task_class": s.task_class} for s in route],
        applicant_is_director=base.applicant_is_director,
        submitted_at=timezone.now())
    cancellation.reference = f"ELMC-{base.period_from.year}-{cancellation.pk:06d}"
    cancellation.save(update_fields=["reference", "updated_at"])

    transition = resolve_or_raise(request=cancellation, action=sm.SEND,
                                  actor_kind=sm.EMPLOYEE)
    _advance(request=cancellation, transition=transition, actor=actor,
             unit=employee.unit if employee else "", note=note)
    return cancellation


# -- EL-UC-009: extension of ongoing leave -------------------------------------
@transaction.atomic
def request_extension(*, actor, request_id: int, period_to: date,
                      purpose: str = "",
                      substitute_user_id: int | None = None) -> LeaveRequest:
    """Additional EL/COL/VL while the leave is ongoing (BR-EL-025)."""
    base = _locked_request(request_id)
    authz.require(actor, sm.P_APPLY)
    authz.require_owner(actor, base)
    if base.status not in (sm.APPROVED, sm.EXTENDED):
        raise ConflictError("Only an approved leave can be extended.",
                            code="leave_not_approved")

    # The additional period begins the day after the approved end date.
    period_from = base.period_to + timedelta(days=1)
    problem = eligibility.extension_window(
        category=base.category, base_from=base.period_from, base_to=base.period_to,
        requested_from=period_from, requested_to=period_to)
    if problem:
        raise ConflictError(problem.message, code=problem.code,
                            details=[problem.details] if problem.details else [])

    incremental = counting.chargeable_days(category=base.category,
                                           start=period_from, end=period_to).days
    employee = facts.employee(base.user_id)
    employee_kind = employee.kind if employee else cat.STAFF
    policy = sel.current_policy(period_from.year)
    available = accounts.available_days(
        user_id=base.user_id, category=base.category,
        leave_year=period_from.year, employee_kind=employee_kind,
        entitlements=policy.entitlements if policy else None)
    if available < incremental:
        raise ConflictError(
            f"Only {available} day(s) remain, {incremental} requested.",
            code="insufficient_balance")

    route = routing.resolve_route(
        category=base.category, unit=employee.unit if employee else "",
        rules=sel.hierarchy_rules(),
        applicant_is_director=base.applicant_is_director)
    extension = LeaveRequest.objects.create(
        kind=sm.EXTENSION, category=base.category, status=sm.DRAFT,
        user_id=base.user_id, base_request=base, period_from=period_from,
        period_to=period_to, days_counted=incremental, purpose=purpose[:300],
        substitute_user_id=substitute_user_id,
        substitute_required=bool(substitute_user_id),
        route=[{"order": s.order, "kind": s.kind, "authority": s.authority,
                "label": s.label, "task_class": s.task_class} for s in route],
        applicant_is_director=base.applicant_is_director,
        submitted_at=timezone.now())
    extension.reference = f"ELMX-{period_to.year}-{extension.pk:06d}"
    extension.save(update_fields=["reference", "updated_at"])

    if substitute_user_id:
        _nominate(request=extension, applicant=extension.user_id,
                  nominee_user_id=int(substitute_user_id))

    transition = resolve_or_raise(request=extension, action=sm.SEND,
                                  actor_kind=sm.EMPLOYEE)
    _advance(request=extension, transition=transition, actor=actor,
             unit=employee.unit if employee else "", note=purpose)
    return extension


# -- helpers -------------------------------------------------------------------
def _locked_request(request_id: int) -> LeaveRequest:
    request = (LeaveRequest.objects.select_for_update().filter(pk=request_id)
               .first())
    if request is None:
        raise NotFoundError("No such leave request.")
    return request
