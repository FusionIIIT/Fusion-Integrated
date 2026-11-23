"""The scheduled deadline sweep: alerts, expiry and escalations (BR-PMS-038, 097..104)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.pms.domain import deadlines as dl
from modules.pms.domain import state_machine as sm
from modules.pms.models import Application, DeadlineAlert
from modules.pms.selectors import deadlines as deadline_selector
from modules.pms.selectors import policy as policy_selector
from modules.pms.services import escalations, notifications, revision

log = logging.getLogger("fusion.pms.deadlines")
WORDS = {dl.REVIEW: "Director review", dl.REVISION: "resubmission",
         dl.OFFICE_ACTION: "office-action response", dl.MAINTENANCE: "maintenance decision"}
MISSED = {dl.REVIEW: "missed_review", dl.OFFICE_ACTION: "missed_office_action",
          dl.MAINTENANCE: "missed_maintenance"}


@dataclass
class SweepReport:
    alerts: int = 0
    expired: int = 0
    escalated: int = 0

    def __str__(self) -> str:
        return f"alerts={self.alerts} expired={self.expired} escalated={self.escalated}"


def _alert(row, offset: int) -> bool:
    try:
        with transaction.atomic():
            alert = DeadlineAlert.objects.create(kind=row.kind, subject_id=row.subject_id,
                                                 deadline=row.due_on, offset_days=offset,
                                                 application_id=row.application_id)
    except IntegrityError:
        return False
    notifications.enqueue(
        topic="deadline.reminder", dedupe_key=f"deadline:{alert.pk}",
        recipient_user_id=row.responsible_user_id,
        subject=f"{WORDS[row.kind].capitalize()} due in {offset} days: {row.reference}",
        body=f"The {WORDS[row.kind]} for {row.reference} is due on {row.due_on.isoformat()}.")
    return True


def _expire(application_id: int, today) -> bool:
    """Lock, look again, and expire only if the period is still over (safe when rerun)."""
    with transaction.atomic():
        app = Application.objects.select_for_update().get(pk=application_id)
        if app.status not in sm.REVISABLE or app.revision_due_on is None \
                or not dl.missed(app.revision_due_on, today):
            return False
        revision.expire(app)
        return True


def sweep(*, today=None) -> SweepReport:
    """Idempotent: alerts and escalations are unique, and expiry rechecks under its lock."""
    today = today or timezone.localdate()
    offsets = policy_selector.current().alert_offsets_days
    report = SweepReport()
    live = Application.objects.exclude(status__in=sorted(sm.TERMINAL))
    for row in deadline_selector.tracked(live):
        if dl.missed(row.due_on, today):
            if row.kind == dl.REVISION:
                report.expired += _expire(row.application_id, today)
            else:
                app = Application.objects.get(pk=row.application_id)
                if escalations.raise_case(MISSED[row.kind], app, row.subject_id,
                                          deadline=row.due_on):
                    report.escalated += 1
            continue
        offset = dl.alert_due(row.due_on, today, offsets)
        if offset is not None and _alert(row, offset):
            report.alerts += 1
    log.info("pms.deadlines.sweep %s", report)
    return report
