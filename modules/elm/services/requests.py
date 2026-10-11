"""Every write to a leave request (EL-UC-001..011, EL-UC-019).

Approval-chain design: the whole route is resolved once, at submission, into
ApprovalStep rows. Each decision closes the active step and opens the next;
the request state follows the stage of the active step through `_move`.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.directory import contracts as directory
from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm
from modules.elm.models import (
    ApprovalStep,
    LeaveRequest,
    LedgerEntry,
    Notification,
    RequestEvent,
    SanctionRoute,
    UnitHead,
)
from modules.elm.selectors import accounts as acc
from modules.elm.services import accounts as ledger

DIRECTOR_ROLE = "Director"


class LeaveRuleError(DomainError):
    code = "leave_rule"


def _rule(fn, *args):
    try:
        return fn(*args)
    except policy.PolicyViolation as exc:
        raise LeaveRuleError(exc.message, code=exc.code) from exc


def notify(user_id: int | None, message: str, request=None) -> None:
    if user_id:
        Notification.objects.create(user_id=user_id, message=message[:300],
                                    request=request)


def _move(req: LeaveRequest, to: str, actor: str, actor_id: int | None, *,
          note: str = "") -> LeaveRequest:
    frm = req.state if req.pk else sm.DRAFT
    sm.resolve(frm, to, actor)
    req.state = to
    req.save()
    RequestEvent.objects.create(request=req, actor_id=actor_id, actor_role=actor,
                                from_state=frm, to_state=to, note=note[:500])
    return req


def _locked(request_id: int) -> LeaveRequest:
    try:
        return LeaveRequest.objects.select_for_update().get(pk=request_id)
    except LeaveRequest.DoesNotExist as exc:
        raise NotFoundError("That leave request does not exist.") from exc


def _active(req: LeaveRequest) -> ApprovalStep | None:
    return (ApprovalStep.objects.select_for_update()
            .filter(request=req, status=ApprovalStep.ACTIVE).first())


# -- resolution, all at submission ---------------------------------------------
def _unit_of(user_id: int) -> str:
    dto = directory.get_users([user_id]).get(user_id)
    return (dto.department if dto else "") or ""


def _unit_head_for(applicant_id: int, unit: str) -> int:
    head = UnitHead.objects.filter(unit=unit).values_list("head_user_id",
                                                           flat=True).first()
    if head is None:
        raise ConflictError(
            f"No Unit Head is configured for your unit "
            f"'{unit or 'unknown'}'. Ask the Leave Administrator to set one.",
            code="unit_head_missing")
    if head == applicant_id:
        raise ConflictError(
            "You are the configured Unit Head of your own unit. Ask the Leave "
            "Administrator to configure who reviews your leave.",
            code="unit_head_is_applicant")
    return head


def _route_for(req: LeaveRequest) -> SanctionRoute:
    """BR-EL-019: resolved from category and employee kind, current config."""
    route = SanctionRoute.objects.filter(
        category=req.category, applicant_kind=req.applicant_kind).first()
    if route is None:
        raise ConflictError(
            f"No sanctioning path is configured for {req.category} of "
            f"{req.applicant_kind}. Ask the Leave Administrator to configure it.",
            code="route_missing")
    if req.user_id in (route.authority_user_id, route.establishment_user_id):
        raise ConflictError(
            "The configured sanctioning path names the applicant. Ask the Leave "
            "Administrator to configure another authority.",
            code="route_names_applicant")
    return route


def _check_substitute(substitute_id: int, applicant_id: int, start: date,
                      end: date) -> None:
    """BR-EL-014."""
    if substitute_id == applicant_id:
        raise LeaveRuleError("You cannot nominate yourself as substitute.",
                             code="substitute_is_applicant")
    dto = directory.get_users([substitute_id]).get(substitute_id)
    if dto is None or dto.kind not in policy.EMPLOYEE_KINDS:
        raise LeaveRuleError("The substitute must be another employee.",
                             code="substitute_not_employee")
    period = policy.Interval(start, end)
    if any(policy.overlaps(period, i) for i in acc.active_intervals(substitute_id)):
        raise LeaveRuleError(
            "The substitute has pending or approved leave in this period. "
            "Nominate someone else.", code="substitute_unavailable")


def _resolve_chain(req: LeaveRequest) -> list[tuple[str, int]]:
    """Every stage and its assignee, or a refusal naming the missing config."""
    resumption = req.kind == LeaveRequest.RESUMPTION
    unit_head_final = req.category in policy.UNIT_HEAD_FINAL
    route = None
    if not req.is_director_applicant and (resumption or not unit_head_final):
        route = _route_for(req)
    stages = sm.build_chain(
        unit_head_final=unit_head_final, has_substitute=bool(req.substitute_id),
        is_director=req.is_director_applicant,
        has_establishment=bool(route and route.establishment_user_id),
        resumption=resumption)
    who = {
        sm.SUBSTITUTE: lambda: req.substitute_id,
        sm.DIRECTOR: lambda: req.user_id,
        sm.UNIT_HEAD: lambda: _unit_head_for(req.user_id, req.unit),
        sm.ESTABLISHMENT: lambda: route.establishment_user_id,
        sm.AUTHORITY: lambda: route.authority_user_id,
    }
    return [(stage, who[stage]()) for stage in stages]


def _state_for(req: LeaveRequest, stage: str) -> str:
    if req.kind == LeaveRequest.RESUMPTION:
        return sm.AWAITING_RESUMPTION_REVIEW
    return sm.STAGE_STATE[stage]


def _activate(step: ApprovalStep) -> None:
    step.status, step.assigned_at = ApprovalStep.ACTIVE, timezone.now()
    step.save(update_fields=["status", "assigned_at", "updated_at"])
    if step.stage != sm.DIRECTOR:
        # BR-EL-035
        req = step.request
        notify(step.assignee_id, f"A {req.get_kind_display().lower()} request "
                                 f"for {req.category} needs your action.", req)


def _submit(req: LeaveRequest, actor_id: int) -> LeaveRequest:
    chain = _resolve_chain(req)
    _move(req, _state_for(req, chain[0][0]), sm.EMPLOYEE, actor_id)
    steps = ApprovalStep.objects.bulk_create(
        ApprovalStep(request=req, sequence=i, stage=stage, assignee_id=uid)
        for i, (stage, uid) in enumerate(chain))
    _activate(steps[0])
    return req


def _advance(req: LeaveRequest, step: ApprovalStep, actor: str, uid: int,
             outcome: str, remarks: str) -> LeaveRequest:
    """Close this step and open the next one."""
    step.status, step.outcome = ApprovalStep.DONE, outcome
    step.remarks, step.acted_at = remarks[:500], timezone.now()
    step.save()
    nxt = (ApprovalStep.objects.filter(request=req, status=ApprovalStep.WAITING)
           .order_by("sequence", "id").first())
    _move(req, _state_for(req, nxt.stage), actor, uid, note=remarks)
    _activate(nxt)
    return req


def _close_chain(req: LeaveRequest) -> set[int]:
    """Cancel every open step; returns who was holding one."""
    open_steps = ApprovalStep.objects.filter(
        request=req, status__in=(ApprovalStep.WAITING, ApprovalStep.ACTIVE))
    holders = set(open_steps.filter(status=ApprovalStep.ACTIVE)
                  .values_list("assignee_id", flat=True))
    open_steps.update(status=ApprovalStep.CANCELLED, updated_at=timezone.now())
    return holders


# -- EL-UC-001 / EL-UC-009 ----------------------------------------------------
def _validate_new(principal, category: str, start: date, end: date,
                  half: str | None, exclude_id: int | None = None) -> Decimal:
    """BR-EL-001, 003, 006, 010-012. Ordered so the most useful refusal wins."""
    _rule(policy.check_category, category, principal.kind)
    _rule(policy.check_period, category, start, end, half)
    if category == policy.RH:
        _rule(policy.check_restricted_holidays, start, end,
              acc.holiday_dates(start, end, "restricted"))
    if category == policy.VL:
        _rule(policy.check_vacation, start, end, acc.vacation_periods())
    days = policy.count_days(category, start, end, half,
                             acc.holiday_dates(start, end, "closed"))
    _rule(policy.check_counted, days)
    mine = policy.Interval(start, end, half)
    if any(policy.overlaps(mine, i)
           for i in acc.active_intervals(principal.user_id, exclude_id)):
        raise LeaveRuleError("This overlaps a pending or approved leave of yours.",
                             code="overlap")
    _rule(policy.check_balance, days,
          ledger.available(principal.user_id, principal.kind, category,
                           start.year))
    return days


@transaction.atomic
def apply(principal, *, category: str, start_date: date, end_date: date,
          half: str | None = None, purpose: str = "", station_leave: bool = False,
          station_address: str = "", substitute_id: int | None = None
          ) -> LeaveRequest:
    ledger.lock_account(principal.user_id)
    days = _validate_new(principal, category, start_date, end_date, half)
    if substitute_id:
        _check_substitute(substitute_id, principal.user_id, start_date, end_date)
    req = LeaveRequest(
        user_id=principal.user_id, kind=LeaveRequest.LEAVE, category=category,
        applicant_kind=principal.kind, unit=_unit_of(principal.user_id),
        start_date=start_date, end_date=end_date, half=half or "", days=days,
        purpose=purpose, station_leave=station_leave,
        station_address=station_address if station_leave else "",
        substitute_id=substitute_id,
        is_director_applicant=DIRECTOR_ROLE in principal.roles,
        state=sm.DRAFT)
    return _submit(req, principal.user_id)


def _own(principal, request_id: int, kind: str | None = None) -> LeaveRequest:
    req = _locked(request_id)
    if req.user_id != principal.user_id or (kind and req.kind != kind):
        raise NotFoundError("That leave request does not exist.")
    return req


@transaction.atomic
def request_extension(principal, *, parent_id: int, end_date: date,
                      purpose: str = "", substitute_id: int | None = None
                      ) -> LeaveRequest:
    """BR-EL-025: only ongoing approved EL/COL/VL; posts the increment only."""
    ledger.lock_account(principal.user_id)
    parent = _own(principal, parent_id, LeaveRequest.LEAVE)
    today = timezone.localdate()
    current_end = acc.effective_end(parent)
    if parent.state != sm.APPROVED or parent.category not in policy.EXTENDABLE:
        raise ConflictError("Only approved EL, COL or VL can be extended.",
                            code="not_extendable")
    if not parent.start_date <= today <= current_end:
        raise ConflictError("Extension is only for leave you are on right now.",
                            code="not_ongoing")
    start = current_end + timedelta(days=1)
    days = _validate_new(principal, parent.category, start, end_date, None)
    if substitute_id:
        _check_substitute(substitute_id, principal.user_id, start, end_date)
    req = LeaveRequest(
        user_id=principal.user_id, kind=LeaveRequest.EXTENSION, parent=parent,
        category=parent.category, applicant_kind=parent.applicant_kind,
        unit=parent.unit, start_date=start, end_date=end_date, days=days,
        purpose=purpose, substitute_id=substitute_id,
        is_director_applicant=parent.is_director_applicant, state=sm.DRAFT)
    return _submit(req, principal.user_id)


@transaction.atomic
def request_cancellation(principal, *, parent_id: int, reason: str = ""
                         ) -> LeaveRequest:
    """BR-EL-023: before the start date, through the same hierarchy."""
    parent = _own(principal, parent_id, LeaveRequest.LEAVE)
    if parent.state != sm.APPROVED:
        raise ConflictError(
            "Only approved leave can be cancelled. Withdraw a pending request "
            "instead.", code="not_approved")
    if timezone.localdate() >= parent.start_date:
        raise ConflictError(
            "This leave has already started, so it cannot be cancelled. Use "
            "extension or resumption.", code="already_started")
    if parent.children.filter(kind=LeaveRequest.CANCELLATION,
                              state__in=sm.PENDING).exists():
        raise ConflictError("A cancellation for this leave is already pending.",
                            code="cancellation_pending")
    req = LeaveRequest(
        user_id=principal.user_id, kind=LeaveRequest.CANCELLATION, parent=parent,
        category=parent.category, applicant_kind=parent.applicant_kind,
        unit=parent.unit, start_date=parent.start_date, end_date=parent.end_date,
        half=parent.half, days=parent.days, purpose=reason,
        is_director_applicant=parent.is_director_applicant, state=sm.DRAFT)
    return _submit(req, principal.user_id)


@transaction.atomic
def submit_resumption(principal, *, parent_id: int, actual_date: date,
                      remarks: str = "") -> LeaveRequest:
    """BR-EL-027: EL/COL/VL only, reviewed by the applicable authority."""
    parent = _own(principal, parent_id, LeaveRequest.LEAVE)
    if parent.state != sm.APPROVED or parent.category not in policy.EXTENDABLE:
        raise ConflictError("Resumption is submitted only after approved EL, COL "
                            "or VL.", code="not_resumable")
    if actual_date < parent.start_date:
        raise LeaveRuleError("You cannot resume before the leave started.",
                             code="bad_resumption_date")
    if parent.children.filter(kind=LeaveRequest.RESUMPTION).exclude(
            state=sm.WITHDRAWN).exists():
        raise ConflictError("Resumption for this leave is already submitted.",
                            code="resumption_exists")
    req = LeaveRequest(
        user_id=principal.user_id, kind=LeaveRequest.RESUMPTION, parent=parent,
        category=parent.category, applicant_kind=parent.applicant_kind,
        unit=parent.unit, start_date=parent.start_date,
        end_date=acc.effective_end(parent), days=Decimal("0"), purpose=remarks,
        actual_resumption_date=actual_date,
        is_director_applicant=parent.is_director_applicant, state=sm.DRAFT)
    return _submit(req, principal.user_id)


# -- EL-UC-002 / EL-UC-019 / EL-UC-007 ----------------------------------------
@transaction.atomic
def respond_as_substitute(principal, request_id: int, *, accept: bool
                          ) -> LeaveRequest:
    req = _locked(request_id)
    if req.substitute_id != principal.user_id:
        raise NotFoundError("That leave request does not exist.")
    step = _active(req)
    if (req.state != sm.AWAITING_SUBSTITUTE or step is None
            or step.assignee_id != principal.user_id):
        raise ConflictError("This request is no longer waiting for your reply.",
                            code="stale_response")
    if accept:
        return _advance(req, step, sm.SUBSTITUTE, principal.user_id, "accepted", "")
    step.status, step.outcome = ApprovalStep.DECLINED, "declined"
    step.acted_at = timezone.now()
    step.save()
    req = _move(req, sm.APPLICANT_ACTION, sm.SUBSTITUTE, principal.user_id,
                note="Substitute declined")
    notify(req.user_id, "Your substitute declined. Nominate another "
                        "substitute or withdraw the request.", req)
    return req


@transaction.atomic
def renominate(principal, request_id: int, *, substitute_id: int) -> LeaveRequest:
    """EL-UC-019: a fresh substitute step takes the declined one's place."""
    req = _own(principal, request_id)
    if req.state != sm.APPLICANT_ACTION:
        raise ConflictError("A new substitute is only needed after a decline.",
                            code="not_awaiting_applicant")
    _check_substitute(substitute_id, req.user_id, req.start_date, req.end_date)
    req.substitute_id = substitute_id
    req = _move(req, sm.AWAITING_SUBSTITUTE, sm.EMPLOYEE, principal.user_id,
                note="Replacement substitute")
    step = ApprovalStep.objects.create(request=req, sequence=0,
                                       stage=sm.SUBSTITUTE,
                                       assignee_id=substitute_id)
    _activate(step)
    return req


@transaction.atomic
def withdraw(principal, request_id: int) -> LeaveRequest:
    """BR-EL-022: immediate, from any pending state, informs concerned roles."""
    req = _own(principal, request_id)
    if req.state not in sm.PENDING:
        raise ConflictError(
            "Only a pending request can be withdrawn. Approved leave can be "
            "cancelled before it starts.", code="not_pending")
    concerned = _close_chain(req) - {req.user_id}
    req = _move(req, sm.WITHDRAWN, sm.EMPLOYEE, principal.user_id)
    for uid in concerned:
        notify(uid, f"A {req.category} request you were handling was withdrawn.",
               req)
    return req


# -- EL-UC-003 / 004 / 005 / 011 ----------------------------------------------
APPROVE, REJECT = "approve", "reject"
FORWARD = "forward"
OUTCOMES = (APPROVE, REJECT, LeaveRequest.RECOMMENDED,
            LeaveRequest.NOT_RECOMMENDED, FORWARD)


@transaction.atomic
def decide(principal, request_id: int, *, outcome: str, remarks: str = ""
           ) -> LeaveRequest:
    req = _locked(request_id)
    step = _active(req)
    if (step is None or step.assignee_id != principal.user_id
            or step.stage == sm.SUBSTITUTE):
        raise NotFoundError("That leave request does not exist.")
    if not principal.has_permission(sm.STAGE_PERMISSION[step.stage]):
        raise PermissionDeniedError("Your current role cannot act at this stage.")
    if req.user_id == principal.user_id and step.stage != sm.DIRECTOR:
        raise PermissionDeniedError("You cannot decide your own request.")
    uid = principal.user_id

    if req.kind == LeaveRequest.RESUMPTION:
        return _review_resumption(req, step, uid, remarks)
    if step.stage == sm.UNIT_HEAD and req.category not in policy.UNIT_HEAD_FINAL:
        # BR-EL-017: either recommendation continues upward.
        if outcome not in (LeaveRequest.RECOMMENDED, LeaveRequest.NOT_RECOMMENDED):
            raise ConflictError("Record Recommended or Not Recommended.",
                                code="bad_outcome")
        req.recommendation = outcome
        return _advance(req, step, sm.UNIT_HEAD, uid, outcome, remarks)
    if step.stage == sm.ESTABLISHMENT:
        if outcome != FORWARD:
            raise ConflictError("Establishment can only forward the request.",
                                code="bad_outcome")
        return _advance(req, step, sm.ESTABLISHMENT, uid, outcome, remarks)
    if outcome not in (APPROVE, REJECT):
        raise ConflictError("Choose approve or reject.", code="bad_outcome")
    return _finalise(req, step, uid, outcome == APPROVE, remarks)


def _finalise(req: LeaveRequest, step: ApprovalStep, uid: int, approved: bool,
              remarks: str) -> LeaveRequest:
    """BR-EL-016 / BR-EL-020 / EL-UC-005: the final word on the chain."""
    req.decided_by_id, req.decided_at = uid, timezone.now()
    req.decision_remarks = remarks[:500]
    if approved:
        _apply_approval(req, uid)
    step.status, step.outcome = ApprovalStep.DONE, "approve" if approved else "reject"
    step.remarks, step.acted_at = remarks[:500], timezone.now()
    step.save()
    _close_chain(req)
    req = _move(req, sm.APPROVED if approved else sm.REJECTED, step.stage, uid,
                note=remarks)
    word = "approved" if approved else "rejected"
    notify(req.user_id, f"Your {req.get_kind_display().lower()} request for "
                        f"{req.category} was {word}.", req)
    return req


def _apply_approval(req: LeaveRequest, uid: int) -> None:
    ledger.lock_account(req.user_id)
    if req.kind in (LeaveRequest.LEAVE, LeaveRequest.EXTENSION):
        have = ledger.available(req.user_id, req.applicant_kind, req.category,
                                req.start_date.year, exclude_request_id=req.pk)
        _rule(policy.check_balance, req.days, have)
        ledger.post(user_id=req.user_id, category=req.category,
                    on=req.start_date, kind=LedgerEntry.DEBIT, days=-req.days,
                    request=req, recorded_by_id=uid)
    elif req.kind == LeaveRequest.CANCELLATION:
        # BR-EL-023
        parent = _locked(req.parent_id)
        if timezone.localdate() >= parent.start_date:
            raise ConflictError("The leave started before the cancellation was "
                                "decided; reject it instead.",
                                code="already_started")
        spent = -sum((e.days for e in parent.ledger.all()), Decimal("0"))
        if spent:
            ledger.post(user_id=req.user_id, category=parent.category,
                        on=parent.start_date, kind=LedgerEntry.RESTORE,
                        days=spent, request=req, recorded_by_id=uid,
                        note="Cancelled before start")
        _move(parent, sm.CANCELLED, sm.SYSTEM, uid, note=f"Cancellation #{req.pk}")


def _review_resumption(req: LeaveRequest, step: ApprovalStep, uid: int,
                       remarks: str) -> LeaveRequest:
    """BR-EL-028: equal dates change nothing; otherwise adjust the balance."""
    delta = policy.resumption_adjustment(req.end_date, req.actual_resumption_date)
    if delta:
        ledger.lock_account(req.user_id)
        ledger.post(user_id=req.user_id, category=req.category,
                    on=req.start_date, kind=LedgerEntry.ADJUSTMENT,
                    days=Decimal(-delta), request=req, recorded_by_id=uid,
                    note=("Late" if delta > 0 else "Early") + " resumption")
    req.decided_by_id, req.decided_at = uid, timezone.now()
    req.decision_remarks = remarks[:500]
    step.status, step.outcome = ApprovalStep.DONE, "reviewed"
    step.remarks, step.acted_at = remarks[:500], timezone.now()
    step.save()
    req = _move(req, sm.RESUMPTION_REVIEWED, sm.AUTHORITY, uid, note=remarks)
    notify(req.user_id, "Your resumption of duty was reviewed.", req)
    return req
