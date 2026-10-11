"""Every write to a leave application (BR-04..BR-10, BR-14, BR-15).

One transactional choke point. The row is locked, the edge is resolved from the
declarative table, the guards run, and the audit event plus any ledger movement
are written in the same transaction — two paths into the same state is how the
rules drift apart.
"""
from __future__ import annotations

import logging
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm
from modules.elm.models import (
    KIND_DEBIT,
    KIND_REVERSAL,
    LeaveApplication,
    LeaveBalanceEntry,
    LeaveEvent,
    LeaveType,
)
from modules.elm.selectors import queries, scoping
from modules.elm.services import authz
from modules.elm.services import balances as balance_service

log = logging.getLogger("fusion.elm.applications")
NOTE_MAX = 300


def actor_lanes(actor, application) -> tuple[str, ...]:
    """The lanes the actor may act in on this row; permission is checked next.

    An approver keeps the approver lane on their own row, so the refusal they
    get is `self_approval_denied` rather than a vague "your role cannot".
    """
    if actor is None:
        return (sm.SYSTEM,)
    lanes: list[str] = []
    if scoping.is_approver(actor):
        lanes.append(sm.APPROVER)
    if application is None or application.user_id == getattr(actor, "user_id", None):
        lanes.append(sm.EMPLOYEE)
    return tuple(lanes) or (sm.EMPLOYEE,)


def _rules(leave_type: LeaveType) -> policy.LeaveTypeRules:
    return policy.LeaveTypeRules(
        code=leave_type.code, name=leave_type.name,
        counts_calendar_days=leave_type.counts_calendar_days,
        allows_half_day=leave_type.allows_half_day,
        requires_reason=leave_type.requires_reason)


def _label(actor) -> str:
    name = getattr(actor, "display_name", "") or getattr(actor, "username", "")
    return str(name)[:80]


def _reject_overlap(user_id: int, start: date, end: date) -> None:
    clash = (LeaveApplication.objects
             .filter(user_id=user_id,
                     status__in=LeaveApplication.ACTIVE_STATUSES,
                     start_date__lte=end, end_date__gte=start)
             .order_by("start_date").first())
    if clash is not None:
        raise ConflictError(
            f"Leave from {clash.start_date} to {clash.end_date} already covers"
            " part of this period. Withdraw that request first, or pick dates"
            " that do not overlap.",
            code="overlapping_leave",
            details=[{"application_id": clash.pk,
                      "start_date": str(clash.start_date),
                      "end_date": str(clash.end_date)}])


def _locked(application_id: int) -> LeaveApplication:
    """The row every decision is made against, locked for the transition."""
    application = (LeaveApplication.objects.select_for_update()
                   .select_related("leave_type")
                   .filter(pk=application_id).first())
    if application is None:
        raise NotFoundError("That leave request does not exist.",
                            code="not_found")
    return application


def _resolve(frm: str, to: str, lanes: tuple[str, ...]) -> sm.Transition:
    """Pair first, then lane: the two refusals mean different things."""
    try:
        edge = sm.resolve(frm, to)
    except sm.InvalidTransition as exc:
        raise ConflictError(
            f"A leave request cannot move from '{exc.frm}' to '{exc.to}'.",
            code="invalid_transition",
            details=[{"from": exc.frm, "to": exc.to,
                      "allowed": sorted({t.to for lane in lanes
                                         for t in sm.TRANSITIONS
                                         if t.frm == exc.frm and lane in t.actors})}]
        ) from exc
    if not any(lane in edge.actors for lane in lanes):
        raise PermissionDeniedError(
            "Your role cannot make that change.", code="actor_not_allowed",
            details=[{"from": frm, "to": to, "actor": "/".join(lanes)}])
    return edge


def _run_guards(edge: sm.Transition, *, application: LeaveApplication,
                actor, note: str) -> None:
    for guard in edge.guards:
        if guard == "not_self_approval" and application.user_id == actor.user_id:
            raise PermissionDeniedError(
                "You cannot decide your own leave request.",
                code="self_approval_denied")
        if guard == "has_decision_note" and not (note or "").strip():
            raise ConflictError(
                "Add a note explaining the decision so the applicant knows why.",
                code="decision_note_required")
        if guard == "balance_sufficient":
            available = queries.available_days(application.user_id,
                                               application.leave_type.code,
                                               application.start_date.year)
            if available < application.days:
                raise ConflictError(
                    f"Only {available} day(s) of {application.leave_type.name}"
                    f" remain for {application.start_date.year}; this request"
                    f" needs {application.days}.", code="insufficient_balance",
                    details=[{"available": str(available),
                              "required": str(application.days)}])
        if guard == "not_finished" and timezone.localdate() > application.end_date:
            raise ConflictError(
                "This leave has already finished; ask a leave administrator to"
                " correct the record instead.", code="leave_finished")


def _apply(application: LeaveApplication, edge: sm.Transition, *, actor,
           note: str) -> LeaveApplication:
    """The one place a status changes, its audit event and its ledger row."""
    application.status = edge.to
    fields = ["status", "updated_at"]
    if edge.to in (sm.APPROVED, sm.REJECTED):
        application.decided_by_user_id = getattr(actor, "user_id", None)
        application.decided_at = timezone.now()
        application.decision_note = (note or "").strip()[:NOTE_MAX]
        fields += ["decided_by_user_id", "decided_at", "decision_note"]
    application.save(update_fields=fields)

    LeaveEvent.objects.create(
        application=application, from_status=edge.frm, to_status=edge.to,
        actor_user_id=getattr(actor, "user_id", None), actor_label=_label(actor),
        note=(note or "").strip()[:NOTE_MAX])

    if edge.to == sm.APPROVED:
        LeaveBalanceEntry.objects.create(
            user_id=application.user_id, leave_type=application.leave_type,
            year=application.start_date.year, kind=KIND_DEBIT,
            days=-application.days, application=application,
            granted_by_user_id=getattr(actor, "user_id", None),
            note=f"Debited by leave#{application.pk}")
    if edge.to == sm.CANCELLED:
        LeaveBalanceEntry.objects.create(
            user_id=application.user_id, leave_type=application.leave_type,
            year=application.start_date.year, kind=KIND_REVERSAL,
            days=application.days, application=application,
            granted_by_user_id=getattr(actor, "user_id", None),
            note=f"Reversal on cancellation of leave#{application.pk}")

    log.info("leave#%s %s->%s by u%s", application.pk, edge.frm, edge.to,
             getattr(actor, "user_id", None))
    return application


def submit_application(*, actor, leave_type_id: int, start_date: date,
                       end_date: date, is_half_day: bool = False,
                       half_day_part: str = "", reason: str = ""
                       ) -> LeaveApplication:
    """Validate first, then create; a refused request leaves no row behind."""
    authz.require(actor, "elm.application.create")
    today = timezone.localdate()
    leave_type = LeaveType.objects.filter(pk=leave_type_id).first()
    if leave_type is None:
        raise NotFoundError("That leave type does not exist.",
                            code="leave_type_not_found")
    if not leave_type.is_active or leave_type.effective_from > today:
        raise ConflictError("That leave type is not open for new requests.",
                            code="leave_type_not_effective")

    request = policy.LeaveRequest(start_date=start_date, end_date=end_date,
                                  is_half_day=bool(is_half_day),
                                  half_day_part=half_day_part or "",
                                  reason=reason or "")
    rules = _rules(leave_type)
    holidays = queries.holidays_between(start_date, end_date)
    try:
        policy.validate_request(request, rules, holidays, today)
    except policy.RuleViolation as exc:
        raise ConflictError(exc.message, code=exc.code) from exc
    days = policy.count_days(request, rules, holidays)

    user_id = actor.user_id
    try:
        with transaction.atomic():
            _reject_overlap(user_id, start_date, end_date)
            application = LeaveApplication.objects.create(
                user_id=user_id, leave_type=leave_type, start_date=start_date,
                end_date=end_date, days=days, is_half_day=bool(is_half_day),
                half_day_part=half_day_part or "",
                reason=(reason or "").strip(), status=sm.PENDING)
            # A first request on a fresh database still finds its entitlement.
            balance_service.ensure_annual_grant(
                user_id=user_id, leave_type=leave_type, year=start_date.year)
            LeaveEvent.objects.create(
                application=application, from_status="draft",
                to_status=sm.PENDING, actor_user_id=user_id,
                actor_label=_label(actor), note="Submitted")
    except IntegrityError as exc:
        # The partial unique index on (user_id, start_date) caught a double
        # submit that raced past the overlap check.
        raise ConflictError(
            "You already have an active leave request starting that day.",
            code="duplicate_leave") from exc

    log.info("leave#%s submitted by u%s for %s day(s)", application.pk,
             user_id, days)
    return application


def transition(*, actor, application_id: int, to_status: str, note: str = ""
               ) -> LeaveApplication:
    """The single entry point; every state change goes through here."""
    if to_status not in sm.ALL_STATUSES:
        raise BadRequestError(f"Unknown status {to_status!r}.", code="unknown_status")
    with transaction.atomic():
        application = _locked(application_id)
        if not scoping.can_see(actor, application):
            raise NotFoundError("That leave request does not exist.",
                                code="not_found")
        edge = _resolve(application.status, to_status,
                        actor_lanes(actor, application))
        authz.require(actor, edge.permission)
        _run_guards(edge, application=application, actor=actor, note=note)
        return _apply(application, edge, actor=actor, note=note)
