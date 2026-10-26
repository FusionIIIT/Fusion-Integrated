"""The one choke point every leave request moves through (CW-EL-01/02/03, XTP-EL-01)."""
from __future__ import annotations

import logging
from datetime import date

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import categories as cat
from modules.leave.domain import routing
from modules.leave.domain import state_machine as sm
from modules.leave.domain.authority import (
    NOT_RECOMMENDED,
    RECOMMENDED,
    STEP_EVENTS,
    STEP_PERMISSIONS,
)
from modules.leave.models import LeaveRequest, RequestEvent, Substitution, Task
from modules.leave.services import accounts, authz, configuration, notifications

log = logging.getLogger("fusion.leave.workflow")

#: What a decider sends, mapped to the edge it means at each step.
ACTIONS = {
    (sm.UNIT_HEAD, "approve"): (sm.UNIT_HEAD_APPROVE, "approved"),
    (sm.UNIT_HEAD, "reject"): (sm.UNIT_HEAD_REJECT, "rejected"),
    (sm.UNIT_HEAD, "recommend"): (sm.UNIT_HEAD_RECOMMEND, RECOMMENDED),
    (sm.UNIT_HEAD, "not_recommend"): (sm.UNIT_HEAD_RECOMMEND, NOT_RECOMMENDED),
    (sm.ESTABLISHMENT, "forward"): (sm.ESTABLISHMENT_FORWARD, "forwarded"),
    (sm.AUTHORITY, "approve"): (sm.SANCTION_APPROVE, "approved"),
    (sm.AUTHORITY, "reject"): (sm.SANCTION_REJECT, "rejected"),
    (sm.DIRECTOR, "approve"): (sm.SANCTION_APPROVE, "approved"),
    (sm.DIRECTOR, "reject"): (sm.SANCTION_REJECT, "rejected"),
}


def today() -> date:
    return timezone.localdate()


def ruling_category(req: LeaveRequest) -> str:
    return req.parent.category if req.parent_id else req.category


def effective_end(leave: LeaveRequest) -> date:
    """The base leave plus every approved extension; the base row itself is never edited."""
    ext = (LeaveRequest.objects.filter(parent=leave, kind=sm.EXTENSION, status=sm.APPROVED)
           .aggregate(end=Max("end_date"))["end"])
    return max(leave.end_date, ext) if ext else leave.end_date


def _route(req: LeaveRequest) -> routing.SanctionRoute:
    h = configuration.current_hierarchy()
    return routing.sanction_route(h, kind=req.applicant_kind, category=ruling_category(req),
                                  department=req.applicant_department,
                                  roles=req.applicant_roles)


def designation_for(req: LeaveRequest, step: str) -> str:
    """Resolved when the task is opened, against the configuration current at that moment."""
    try:
        if step == sm.DIRECTOR:
            return routing.DIRECTOR_DESIGNATION
        if step == sm.UNIT_HEAD:
            return routing.unit_head(configuration.current_hierarchy(),
                                     department=req.applicant_department,
                                     roles=req.applicant_roles)
        route = _route(req)
        name = route.establishment_designation if step == sm.ESTABLISHMENT else (
            route.sanction_designation)
    except routing.RoutingUnresolved as exc:
        raise ConflictError(str(exc), code="routing_unresolved") from exc
    if not name:
        raise ConflictError("The configured route names no authority for this step. Ask the "
                            "Leave Administrator to correct the hierarchy.",
                            code="routing_unresolved")
    return name


def check_routable(req: LeaveRequest) -> None:
    """EL-UC-004 A2: refuse at submission what could not be forwarded later."""
    if req.is_director_applicant:
        return
    designation_for(req, sm.UNIT_HEAD)
    if not cat.get(ruling_category(req)).unit_head_final:
        designation_for(req, sm.AUTHORITY)


def flags(req: LeaveRequest, *, needs_substitute: bool = False,
          establishment: bool = False) -> dict[str, bool]:
    return {"needs_substitute": needs_substitute, "director": req.is_director_applicant,
            "uh_final": cat.get(ruling_category(req)).unit_head_final,
            "establishment": establishment}


def lock_request(request_id: int, scope=None) -> LeaveRequest:
    qs = scope if scope is not None else LeaveRequest.objects.all()
    req = qs.select_for_update(of=("self",)).select_related("parent").filter(
        pk=request_id).first()
    if req is None:
        raise NotFoundError("No such leave request.")
    return req


def move(req: LeaveRequest, event: str, *, actor_lane: str, actor=None, outcome: str = "",
         remarks: str = "", needs_substitute: bool = False, substitute_id: int | None = None
         ) -> LeaveRequest:
    """Every state change; the caller holds the request lock and has authorised the actor."""
    if req.status in sm.TERMINAL:
        raise ConflictError("This request has already been decided or withdrawn; nothing more "
                            "can be done to it.", code="request_closed")
    frm = req.status if req.pk and req.submitted_at else sm.DRAFT
    establishment = False
    if event == sm.UNIT_HEAD_RECOMMEND:
        establishment = bool(designation_for_establishment(req))
    try:
        t = sm.resolve(req.kind, frm, event, actor_lane,
                       flags(req, needs_substitute=needs_substitute,
                             establishment=establishment))
    except sm.InvalidTransition as exc:
        raise ConflictError("That action is not available for this request in its current "
                            "state.", code="invalid_transition",
                            details=[{"from": frm, "event": event,
                                      "allowed": sm.events_from(req.kind, frm, actor_lane)}]
                            ) from exc

    now = timezone.now()
    actor_id = getattr(actor, "user_id", None)
    role = authz.acting_role(actor) if actor is not None else "system"
    if frm == sm.DRAFT:
        req.submitted_at = now
    req.status = t.to
    if event in (sm.UNIT_HEAD_RECOMMEND, sm.UNIT_HEAD_APPROVE, sm.UNIT_HEAD_REJECT):
        req.unit_head_outcome = outcome
    if t.to in (sm.APPROVED, sm.REJECTED) and event != sm.SUBMIT:
        req.decision, req.decided_by_user_id, req.decided_role = outcome, actor_id, role
        req.decided_at, req.decision_remarks = now, remarks[:500]
    if t.to == sm.WITHDRAWN:
        req.withdrawn_at = now
    req.save()
    RequestEvent.objects.create(request=req, event=event, from_status=frm, to_status=t.to,
                                actor_user_id=actor_id, actor_role=role, outcome=outcome,
                                remarks=remarks[:500])

    _close_open_task(req, actor_id, cancelled=t.to == sm.WITHDRAWN)
    if t.to in sm.STEP_OF_STATE:
        _open_task(req, sm.STEP_OF_STATE[t.to], substitute_id=substitute_id)
    elif t.to == sm.APPLICANT_ACTION:
        notifications.enqueue(
            topic="substitute.declined", dedupe_key=f"declined:{req.pk}:{now.timestamp()}",
            user_id=req.user_id, subject="Your substitute declined — action needed",
            body=f"Your nominated substitute declined leave request #{req.pk}. Nominate "
                 f"another colleague or withdraw the request.")
    if t.to in sm.TERMINAL:
        _effects(req, t.to, actor_id=actor_id)
    return req


def designation_for_establishment(req: LeaveRequest) -> str:
    if req.is_director_applicant:
        return ""
    try:
        return _route(req).establishment_designation
    except routing.RoutingUnresolved as exc:
        raise ConflictError(str(exc), code="routing_unresolved") from exc


def _close_open_task(req: LeaveRequest, actor_id: int | None, *, cancelled: bool) -> None:
    Task.objects.filter(request=req, status=Task.OPEN).update(
        status=Task.CANCELLED if cancelled else Task.DONE, closed_at=timezone.now(),
        closed_by_user_id=actor_id)


def _open_task(req: LeaveRequest, step: str, *, substitute_id: int | None) -> Task:
    """BR-EL-035: every task that lands on someone is announced to them."""
    if step == sm.SUBSTITUTE:
        sub = substitute_id or Substitution.objects.filter(
            request=req, status=Substitution.PENDING).values_list(
            "substitute_user_id", flat=True).first()
        task = Task.objects.create(request=req, step=step, assignee_user_id=sub)
        notifications.enqueue(
            topic="task.assigned", dedupe_key=f"task:{task.pk}", user_id=sub,
            subject="You have been nominated as a substitute",
            body=f"A colleague has nominated you to cover their responsibilities from "
                 f"{req.start_date} to {req.end_date}. Accept or decline in Leave.")
        return task
    designation = designation_for(req, step)
    task = Task.objects.create(request=req, step=step, assignee_designation=designation)
    notifications.enqueue(
        topic="task.assigned", dedupe_key=f"task:{task.pk}", designation=designation,
        subject=f"Leave request #{req.pk} awaits your action",
        body=f"A {req.get_kind_display().lower()} request for {req.category} from "
             f"{req.start_date} to {req.end_date} is waiting in your Leave approvals queue.")
    return task


def _effects(req: LeaveRequest, status: str, *, actor_id: int | None) -> None:
    """What a final decision does to the record and the ledger (BR-EL-023, BR-EL-025)."""
    if status == sm.APPROVED and req.kind in (sm.NEW, sm.EXTENSION):
        accounts.lock(req.user_id)
        held = accounts.balances([req.user_id], req.leave_year)[req.user_id][req.category]
        if held < req.days:
            raise ConflictError(
                f"Approving this would take {req.category} below zero: {req.days} day(s) "
                f"requested, {held} held. The applicant must withdraw it or the balance must "
                f"be corrected first.", code="insufficient_balance")
        accounts.post(user_id=req.user_id, year=req.leave_year, category=req.category,
                      delta=-req.days, entry_type="debit", key=f"debit:{req.pk}", request=req,
                      note=f"{req.get_kind_display()} #{req.pk}", actor_id=actor_id)
    if status == sm.APPROVED and req.kind == sm.CANCELLATION:
        leave = LeaveRequest.objects.select_for_update().get(pk=req.parent_id)
        if leave.start_date <= today():
            raise ConflictError(
                "This leave has already begun, so it can no longer be cancelled. Reject the "
                "cancellation; the employee's return is handled through resumption.",
                code="leave_already_started")
        accounts.lock(leave.user_id)
        charged = sum((e.delta for e in leave.ledger_entries.all()), start=0)
        leave.status = sm.CANCELLED
        leave.save(update_fields=["status", "updated_at"])
        RequestEvent.objects.create(request=leave, event="cancelled", from_status=sm.APPROVED,
                                    to_status=sm.CANCELLED, actor_user_id=actor_id,
                                    remarks=f"Cancellation #{req.pk} approved")
        if charged:
            accounts.post(user_id=leave.user_id, year=leave.leave_year,
                          category=leave.category, delta=-charged, entry_type="reversal",
                          key=f"reversal:{leave.pk}", request=leave,
                          note=f"Cancellation #{req.pk} approved", actor_id=actor_id)
    if status in (sm.APPROVED, sm.REJECTED):
        notifications.enqueue(
            topic="decision.final", dedupe_key=f"decision:{req.pk}", user_id=req.user_id,
            subject=f"Your {req.get_kind_display().lower()} request #{req.pk} was {status}",
            body=f"Your {req.get_kind_display().lower()} request for {req.category} from "
                 f"{req.start_date} to {req.end_date} was {status}."
                 + (f" Remarks: {req.decision_remarks}" if req.decision_remarks else ""))
    Substitution.objects.filter(request=req, status=Substitution.PENDING).update(
        status=Substitution.VOID)


# -- decisions -------------------------------------------------------------------
def authorise_task(task: Task, req: LeaveRequest, actor) -> None:
    """Permission, acting role and the no-self-decision rule; BR-EL-020 is the one exception."""
    authz.require(actor, STEP_PERMISSIONS[task.step])
    role = authz.acting_role(actor)
    own = req.user_id == actor.user_id
    if task.step == sm.DIRECTOR:
        if not (own and role == routing.DIRECTOR_DESIGNATION):
            raise NotFoundError("No such task in your queue.")
        return
    if task.assignee_designation != role:
        raise NotFoundError("No such task in your queue.")
    if own:
        raise PermissionDeniedError("You cannot decide your own leave request.",
                                    code="own_request")


@transaction.atomic
def decide(*, task_id: int, action: str, actor, remarks: str = "") -> LeaveRequest:
    """EL-UC-003/004/005: one decision on one open task, by the role it is assigned to."""
    task = Task.objects.filter(pk=task_id).select_related("request").first()
    if task is None or task.step == sm.SUBSTITUTE:
        raise NotFoundError("No such task in your queue.")
    req = lock_request(task.request_id)
    task = Task.objects.select_for_update().get(pk=task.pk)
    authorise_task(task, req, actor)
    if task.status != Task.OPEN:
        raise ConflictError("This task has already been acted on or withdrawn.",
                            code="task_closed")
    if action in ("reject", "not_recommend") and not remarks.strip():
        raise ConflictError("Give a reason for this decision; the employee will read it.",
                            code="reason_required")
    entry = ACTIONS.get((task.step, action))
    if entry is None or entry[0] not in STEP_EVENTS.get(task.step, ()):
        raise ConflictError(f"{action!r} is not a decision this step can take.",
                            code="invalid_action")
    event, outcome = entry
    return move(req, event, actor_lane=task.step, actor=actor, outcome=outcome,
                remarks=remarks)


@transaction.atomic
def withdraw(*, request_id: int, actor, reason: str = "") -> LeaveRequest:
    """EL-UC-007, BR-EL-022: immediate, terminal, and every open task closes with it."""
    authz.require(actor, "leave.request.revoke")
    req = lock_request(request_id, LeaveRequest.objects.filter(user_id=actor.user_id))
    if req.status == sm.APPROVED:
        raise ConflictError("An approved leave cannot be withdrawn. Request its cancellation "
                            "instead, before it begins.", code="already_approved")
    return _withdraw(req, sm.WITHDRAW, actor_lane=sm.EMPLOYEE, actor=actor,
                     outcome="withdrawn", remarks=reason, why="was withdrawn by the applicant")


def _withdraw(req: LeaveRequest, event: str, *, actor_lane: str, actor, outcome: str,
              remarks: str, why: str) -> LeaveRequest:
    open_task = Task.objects.filter(request=req, status=Task.OPEN).first()
    move(req, event, actor_lane=actor_lane, actor=actor, outcome=outcome, remarks=remarks)
    if open_task is not None:
        notifications.enqueue(
            topic="request.withdrawn", dedupe_key=f"withdrawn:{req.pk}",
            user_id=open_task.assignee_user_id,
            designation="" if open_task.assignee_user_id else open_task.assignee_designation,
            subject=f"Leave request #{req.pk} was withdrawn",
            body=f"Leave request #{req.pk} ({req.category}, {req.start_date} to "
                 f"{req.end_date}) {why}. No action is needed.")
    return req


def lapse_stale_cancellations() -> int:
    """BR-EL-023: a cancellation still pending when its leave begins can never be approved;
    close it rather than leave it waiting and holding up the account's year-end."""
    ids = list(LeaveRequest.objects.filter(
        kind=sm.CANCELLATION, status__in=sm.PENDING, parent__start_date__lte=today())
        .values_list("pk", flat=True))
    lapsed = 0
    for pk in ids:
        with transaction.atomic():
            req = lock_request(pk)
            if req.status not in sm.PENDING:
                continue
            _withdraw(req, sm.LAPSE, actor_lane=sm.SYSTEM, actor=None, outcome="lapsed",
                      remarks="The leave began before the cancellation was decided.",
                      why="lapsed because the leave began before it was decided")
            notifications.enqueue(
                topic="request.withdrawn", dedupe_key=f"lapsed:{req.pk}", user_id=req.user_id,
                subject=f"Your cancellation request #{req.pk} lapsed",
                body=f"Your leave from {req.start_date} began before the cancellation was "
                     f"decided, so it stands as approved. Use an extension or your resumption "
                     f"instead.")
            lapsed += 1
    return lapsed
