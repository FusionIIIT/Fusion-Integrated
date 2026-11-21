"""Event-triggered work: EL-UC-020 year-end and EL-UC-021 SLA thresholds."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.db import transaction

from modules.leave.domain.accounting import year_end_postings
from modules.leave.domain.workflow import State
from modules.leave.models import LeaveRequest, LedgerEntry, SlaPolicy
from modules.leave.selectors import accounts as reads
from modules.leave.services import accounts
from modules.leave.services.notify import notify
from modules.leave.services.workflow import _describe, assignee_of

log = logging.getLogger("fusion.leave.periodic")


def run_year_end(year: int) -> dict:
    """Idempotent: every posting carries a key, so a rerun posts nothing new."""
    report = {"year": year, "employees": 0, "postings": 0, "exceptions": []}
    user_ids = (LedgerEntry.objects.filter(year=year)
                .values_list("user_id", flat=True).distinct())
    for uid in user_ids:
        try:
            with transaction.atomic():
                accounts.lock(uid)
                for p in year_end_postings(year, reads.balances(uid, year)):
                    accounts.post(uid, p.category, p.year, p.days, p.reason,
                                  key=f"yearend:{year}:{p.category}:{p.reason}:{uid}")
                    report["postings"] += 1
            report["employees"] += 1
        except Exception as exc:
            log.exception("leave.year_end.failed user=%s", uid)
            report["exceptions"].append({"user_id": uid, "error": str(exc)})
    return report


def process_sla(now: datetime) -> dict:
    """BR-EL-032/033: only a task still pending in the same state is chased."""
    report = {"reminders": 0, "escalations": 0}
    for sla in SlaPolicy.objects.all():
        state = State(sla.state)
        due = LeaveRequest.objects.filter(
            status=state.value,
            status_changed_at__lte=now - timedelta(hours=sla.reminder_hours))
        for req in due:
            entered = req.status_changed_at.isoformat()
            report["reminders"] += notify(
                [assignee_of(req)], "reminder", f"Reminder: {_describe(req)} awaits you.",
                request=req, key=f"sla:remind:{req.pk}:{state}:{entered}")
            if req.status_changed_at <= now - timedelta(hours=sla.escalation_hours):
                target = sla.escalate_to_user_id or req.sanctioning_user_id
                report["escalations"] += notify(
                    [target], "escalation",
                    f"Escalated: {_describe(req)} is overdue at {state.value}.",
                    request=req, key=f"sla:escalate:{req.pk}:{state}:{entered}")
    return report
