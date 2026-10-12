"""Substitute consent and routed decisions (EL-UC-002..005, 008, 009)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.elm.domain import categories as c
from modules.elm.domain import overlap
from modules.elm.domain import permissions as p
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, LedgerEntry
from modules.elm.selectors import scoping
from modules.elm.services import ledger, notify
from modules.elm.services.authz import require
from modules.elm.services.requests import LeaveInvalid, _active_overlap
from modules.elm.services.transitions import enter_stage, move


def respond_substitution(actor, pk: int, *, accept: bool, note: str = "") -> LeaveRequest:
    require(actor, p.P_SUBSTITUTE)
    with transaction.atomic():
        req = (scoping.substitution_requests(actor).select_for_update()
               .filter(pk=pk).first())
        if req is None:
            raise NotFoundError("No such substitution request.")
        if req.status != sm.AWAITING_SUBSTITUTE:
            raise ConflictError("This substitution request is no longer awaiting you.",
                                code="not_awaiting_substitute")
        if not accept:
            req.substitute_status = "declined"
            move(req, event=sm.SUBSTITUTE_DECLINE, actor_kind=sm.SUBSTITUTE,
                 to=sm.SUBSTITUTE_DECLINED, actor=actor, note=note)
            notify.to_user(req.user_id, req,
                           f"Your substitute declined leave #{req.pk}. Nominate another "
                           "substitute or withdraw the request.")
            return req
        if _active_overlap(actor.user_id, overlap.Interval(req.start_date, req.end_date),
                           set()) is not None:
            raise LeaveInvalid("You have leave during this period, so you cannot accept "
                               "this responsibility.", code="substitute_unavailable")
        req.substitute_status = "accepted"
        to = enter_stage(req, 0)
        move(req, event=sm.SUBSTITUTE_ACCEPT, actor_kind=sm.SUBSTITUTE, to=to,
             actor=actor, note=note)
        notify.to_user(req.user_id, req, f"Your substitute accepted leave #{req.pk}.")
        notify.to_role(req.current_role, req, f"Leave #{req.pk} awaits your action.")
        return req


def decide(actor, pk: int, *, event: str, note: str = "") -> LeaveRequest:
    require(actor, p.P_REVIEW, p.P_APPROVE)
    with transaction.atomic():
        req = scoping.decision_queue(actor).select_for_update().filter(pk=pk).first()
        if req is None:
            raise NotFoundError("No such request in your queue.")
        step = req.current_step
        if step is None or step["role"] != actor.active_role:
            raise ConflictError("This request is not at your step.", code="not_your_step")
        cancelling = req.status == sm.CANCELLATION_PENDING
        allowed = sm.decision_events(step["step"], req.category in c.UNIT_HEAD_FINAL,
                                     cancelling)
        if event not in allowed:
            raise BadRequestError(
                f"At this step you can only {' or '.join(e.replace('_', ' ') for e in allowed)}.",
                code="invalid_decision")
        if event in (sm.REJECT, sm.NOT_RECOMMEND, sm.CANCEL_REJECT) and not note.strip():
            raise BadRequestError("Give a reason for this decision.", code="reason_required")

        actor_kind = sm.ACTOR_FOR_STEP[step["step"]]
        frm = req.status
        if event in (sm.RECOMMEND, sm.NOT_RECOMMEND, sm.FORWARD, sm.CANCEL_ADVANCE):
            if event in (sm.RECOMMEND, sm.NOT_RECOMMEND):
                req.recommendation = "recommended" if event == sm.RECOMMEND else "not_recommended"
            to = enter_stage(req, req.stage + 1)
            if cancelling:
                to = sm.CANCELLATION_PENDING
            move(req, event=event, actor_kind=actor_kind, to=to, actor=actor, note=note)
            notify.to_role(req.current_role, req, f"Leave #{req.pk} awaits your action.")
            return req

        req.decided_at, req.decision_note = timezone.now(), note[:500]
        req.current_role = ""
        if event == sm.APPROVE:
            move(req, event=event, actor_kind=actor_kind, to=sm.APPROVED, actor=actor,
                 note=note)
            ledger.lock_employee(req.user_id)
            ledger.post(req, LedgerEntry.DEBIT, -req.days, f"approved {req.kind}")
            notify.to_user(req.user_id, req, f"Leave #{req.pk} was approved.")
        elif event == sm.REJECT:
            move(req, event=event, actor_kind=actor_kind, to=sm.REJECTED, actor=actor,
                 note=note)
            notify.to_user(req.user_id, req, f"Leave #{req.pk} was rejected: {note}")
        elif event == sm.CANCEL_APPROVE:
            move(req, event=event, actor_kind=actor_kind, to=sm.CANCELLED, actor=actor,
                 note=note)
            ledger.lock_employee(req.user_id)
            ledger.post(req, LedgerEntry.REVERSAL, req.days, "cancellation approved")
            notify.to_user(req.user_id, req, f"Cancellation of leave #{req.pk} was approved.")
        else:
            move(req, event=event, actor_kind=actor_kind, to=sm.APPROVED, actor=actor,
                 note=note)
            notify.to_user(req.user_id, req,
                           f"Cancellation of leave #{req.pk} was rejected; the leave stands.")
        if req.substitute_user_id and frm != sm.CANCELLATION_PENDING:
            notify.to_user(req.substitute_user_id, req,
                           f"Leave #{req.pk} you cover was {req.status}.")
        return req
