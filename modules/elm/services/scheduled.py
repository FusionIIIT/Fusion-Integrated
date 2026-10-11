"""Event-triggered work: year-end (EL-UC-020) and SLA thresholds (EL-UC-021)."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.elm.domain import policy
from modules.elm.domain import state_machine as sm
from modules.elm.models import LeaveRequest, LedgerEntry, RequestEvent, SlaPolicy
from modules.elm.selectors import accounts as acc
from modules.elm.services import accounts as ledger
from modules.elm.services.requests import notify

log = logging.getLogger("fusion.elm.scheduled")


def _once(user_id: int, category: str, year: int, kind: str, days: Decimal,
          note: str) -> None:
    if days:
        LedgerEntry.objects.get_or_create(
            user_id=user_id, category=category, year=year, kind=kind,
            defaults={"days": days, "note": note})


def year_end(year: int) -> dict:
    """BR-EL-002..009. Idempotent: every entry is once-a-year by constraint."""
    users = (LedgerEntry.objects.filter(year=year)
             .values_list("user_id", flat=True).distinct())
    done, failed = 0, []
    for uid in users:
        try:
            with transaction.atomic():
                ledger.lock_account(uid)
                bal = acc.balances(uid, year)
                for cat in policy.LAPSING:
                    _once(uid, cat, year, LedgerEntry.LAPSE, -bal[cat],
                          "Unused leave lapses")
                vl = bal[policy.VL]
                _once(uid, policy.VL, year, LedgerEntry.CONVERSION_OUT, -vl,
                      "Unused VL converted to EL")
                for cat in policy.CARRY_FORWARD:
                    _once(uid, cat, year + 1, LedgerEntry.CARRY_FORWARD, bal[cat],
                          f"Carried forward from {year}")
                _once(uid, policy.EL, year + 1, LedgerEntry.CONVERSION_IN,
                      policy.vl_to_el(vl), f"From {vl} unused VL of {year}")
            done += 1
        except Exception as exc:
            log.exception("elm.year_end.failed user=%s", uid)
            failed.append({"user_id": uid, "error": str(exc)})
    return {"year": year, "processed": done, "exceptions": failed}


def sla_sweep(now=None) -> dict:
    """BR-EL-032/033: remind, then escalate, only while the task is pending."""
    now = now or timezone.now()
    sla = SlaPolicy.objects.order_by("-created_at", "-id").first()
    if sla is None:
        return {"reminded": 0, "escalated": 0, "skipped": "no SLA configured"}
    open_states = sm.PENDING | {sm.AWAITING_RESUMPTION_REVIEW}
    reminded = escalated = 0
    due = LeaveRequest.objects.filter(
        state__in=open_states, assignee_id__isnull=False,
        reminded_at__isnull=True,
        assigned_at__lte=now - timedelta(hours=sla.reminder_hours))
    for req_id in due.values_list("id", flat=True):
        with transaction.atomic():
            req = LeaveRequest.objects.select_for_update().get(pk=req_id)
            if req.state not in open_states or req.reminded_at:
                continue
            req.reminded_at = now
            req.save(update_fields=["reminded_at", "updated_at"])
            notify(req.assignee_id, f"Reminder: a {req.category} request is "
                                    "still waiting for your action.", req)
            RequestEvent.objects.create(request=req, actor_role=sm.SYSTEM,
                                        note="SLA reminder")
            reminded += 1
    if sla.escalation_user_id:
        late = LeaveRequest.objects.filter(
            state__in=open_states, assignee_id__isnull=False,
            escalated_at__isnull=True,
            assigned_at__lte=now - timedelta(hours=sla.escalation_hours))
        for req_id in late.values_list("id", flat=True):
            with transaction.atomic():
                req = LeaveRequest.objects.select_for_update().get(pk=req_id)
                if req.state not in open_states or req.escalated_at:
                    continue
                req.escalated_at = now
                req.save(update_fields=["escalated_at", "updated_at"])
                # ponytail: notification-only escalation; rerouting needs a rule.
                notify(sla.escalation_user_id,
                       f"Escalation: a {req.category} request has waited past "
                       "its SLA.", req)
                RequestEvent.objects.create(request=req, actor_role=sm.SYSTEM,
                                            note="SLA escalation")
                escalated += 1
    return {"reminded": reminded, "escalated": escalated}


def previous_year(today: date | None = None) -> int:
    return (today or timezone.localdate()).year - 1
