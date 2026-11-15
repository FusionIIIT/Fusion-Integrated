"""Resumption of duty (EL-UC-010, EL-UC-011)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.elm.domain import categories as c
from modules.elm.domain import permissions as p
from modules.elm.domain import routing
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, LedgerEntry
from modules.elm.selectors import config as config_sel
from modules.elm.selectors import scoping
from modules.elm.services import ledger, notify
from modules.elm.services.authz import require
from modules.elm.services.requests import LeaveInvalid, _own_locked, effective_end
from modules.elm.services.transitions import move


def submit(actor, pk: int, *, actual_return_date: date, note: str = "") -> LeaveRequest:
    require(actor, p.P_UPDATE)
    with transaction.atomic():
        req = _own_locked(actor, pk)
        if req.kind != LeaveRequest.LEAVE or req.category not in c.RESUMABLE:
            raise ConflictError("Resumption is submitted only after Earned, Commuted or "
                                "Vacation Leave.", code="not_resumable")
        if req.status != sm.APPROVED:
            raise ConflictError("Resumption can only be submitted for approved leave.",
                                code="not_resumable")
        if actual_return_date <= req.start_date:
            raise LeaveInvalid("The return date must be after the leave started.",
                               code="invalid_return_date")
        if actual_return_date > timezone.localdate():
            raise LeaveInvalid("The return date cannot be in the future.",
                               code="invalid_return_date")
        pv = config_sel.effective_policy()
        hierarchy = pv.hierarchy if pv else {}
        req.actual_return_date = actual_return_date
        req.resumption_note = note[:500]
        req.current_role = routing.resumption_verifier(req.route, hierarchy)
        req.stage_entered_at = timezone.now()
        move(req, event=sm.SUBMIT_RESUMPTION, actor_kind=sm.EMPLOYEE,
             to=sm.RESUMPTION_PENDING, actor=actor, note=note)
        notify.to_role(req.current_role, req,
                       f"Resumption for leave #{req.pk} awaits verification.")
        return req


def verify(actor, pk: int, *, verified: bool, note: str = "") -> LeaveRequest:
    require(actor, p.P_RESUMPTION)
    with transaction.atomic():
        req = scoping.resumption_queue(actor).select_for_update().filter(pk=pk).first()
        if req is None:
            raise NotFoundError("No such resumption in your queue.")
        if not verified:
            notify.to_user(req.user_id, req,
                           f"Your return for leave #{req.pk} could not be verified: {note}")
            return req
        end = effective_end(req)
        req.current_role = ""
        move(req, event=sm.VERIFY_RESUMPTION, actor_kind=sm.VERIFIER, to=sm.CLOSED,
             actor=actor, note=note)
        if req.actual_return_date <= end:
            unused = Decimal((end - req.actual_return_date).days + 1)
            ledger.lock_employee(req.user_id)
            ledger.post(req, LedgerEntry.RESTORE, unused,
                        f"early return on {req.actual_return_date}")
        notify.to_user(req.user_id, req, f"Your resumption for leave #{req.pk} was verified.")
        return req
