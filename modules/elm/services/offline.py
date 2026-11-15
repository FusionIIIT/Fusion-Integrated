"""Offline-sanctioned leave is record synchronisation, not approval (EL-UC-016)."""
from __future__ import annotations

from datetime import date

from django.db import transaction

from core.api.exceptions import NotFoundError
from fusion_auth.client import IamUnavailable
from modules.directory import contracts as directory
from modules.elm.domain import categories as c
from modules.elm.domain import counting, overlap
from modules.elm.domain import permissions as p
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, LedgerEntry, OfflineLeaveRecord
from modules.elm.selectors import config as config_sel
from modules.elm.selectors import ledger as ledger_sel
from modules.elm.services import ledger, notify
from modules.elm.services.authz import DirectoryUnavailable, require
from modules.elm.services.requests import LeaveInvalid, _active_overlap, _policy
from modules.elm.services.transitions import move


def record(actor, *, user_id: int, category: str, start_date: date, end_date: date,
           half: str, purpose: str, sanction_reference: str, sanctioned_by: str,
           sanctioned_on: date, evidence_note: str = "") -> LeaveRequest:
    require(actor, p.P_OFFLINE)
    pv, policy, _ = _policy()
    try:
        emp = directory.get_users([user_id]).get(user_id)
    except IamUnavailable as exc:
        raise DirectoryUnavailable() from exc
    if emp is None or emp.kind not in c.EMPLOYEE_KINDS:
        raise NotFoundError("No such employee.")
    if not sanction_reference.strip() or not sanctioned_by.strip():
        raise LeaveInvalid("Record the sanction reference and who sanctioned it.",
                           code="evidence_insufficient")
    if user_id == getattr(actor, "user_id", None):
        raise LeaveInvalid("You cannot record offline leave for yourself.",
                           code="self_record")
    cal = config_sel.calendar_for(config_sel.effective_calendar_version(start_date))
    try:
        policy.check_eligible(emp.kind, category)
        days = counting.chargeable_days(category, start_date, end_date, half or None, cal)
    except Exception as exc:
        raise LeaveInvalid(str(exc), code="record_inconsistent") from exc
    with transaction.atomic():
        ledger.lock_employee(user_id)
        if _active_overlap(user_id, overlap.Interval(start_date, end_date, half or None),
                           set()) is not None:
            raise LeaveInvalid("This employee already has leave recorded on these dates.",
                               code="record_inconsistent")
        ledger.ensure_annual_credits(user_id, emp.kind, start_date.year, policy)
        available = ledger_sel.balances(user_id)[category]
        if days > available:
            raise LeaveInvalid(f"The employee has only {available} day(s) of "
                               f"{c.LABELS[category]}; the record needs {days}.",
                               code="record_inconsistent")
        req = LeaveRequest(user_id=user_id, kind=LeaveRequest.OFFLINE, category=category,
                           applicant_kind=emp.kind, applicant_unit=emp.department,
                           start_date=start_date, end_date=end_date, half=half or "",
                           days=days, purpose=purpose or "Offline sanctioned leave",
                           route=[], policy_version_id=pv.pk)
        move(req, event=sm.RECORD_OFFLINE, actor_kind=sm.ADMIN, to=sm.APPROVED,
             actor=actor, note=f"Offline sanction {sanction_reference}")
        OfflineLeaveRecord.objects.create(
            request=req, sanction_reference=sanction_reference,
            sanctioned_by=sanctioned_by, sanctioned_on=sanctioned_on,
            evidence_note=evidence_note, recorded_by_user_id=actor.user_id)
        ledger.post(req, LedgerEntry.OFFLINE_DEBIT, -days, f"offline {sanction_reference}")
        notify.to_user(user_id, req,
                       f"Offline-sanctioned leave ({sanction_reference}) was recorded "
                       "on your account.")
        return req
