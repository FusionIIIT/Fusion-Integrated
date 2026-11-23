"""Reports: generation, export, saved definitions and their schedule (UC-PMS-024, 030, 031)."""
from __future__ import annotations

import logging
from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.pms.domain import reports as rp
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import ReportDefinition, ReportRun
from modules.pms.selectors import reports as report_selector
from modules.pms.selectors import scoping
from modules.pms.services import audit, notifications
from modules.pms.services.base import require, ruled

log = logging.getLogger("fusion.pms.reports")
P_VIEW = "pms.report.view"
P_EXPORT = "pms.report.export"
P_SAVE = "pms.report_definition.create"


def _spec(actor, report_type: str, filters: dict, columns) -> tuple[str, dict, tuple]:
    kind = rp.check_type(report_type, applicant_only=scoping.lane(actor) == scoping.APPLICANT)
    return kind, rp.check_filters(filters or {}), rp.check_columns(kind, columns)


@ruled
def generate(*, actor, report_type: str, filters: dict, columns=None,
             export: bool = False) -> tuple[tuple[str, ...], list[dict]]:
    """PMS-AFR-191: every view and every export of a report is logged."""
    require(actor, P_EXPORT if export else P_VIEW)
    kind, clean, cols = _spec(actor, report_type, filters, columns)
    rows = report_selector.report_rows(actor, kind, clean, cols)
    audit.record(actor, "report.exported" if export else "report.viewed",
                 details={"report_type": kind, "rows": len(rows)})
    return cols, rows


@ruled
def save_definition(*, actor, name: str, report_type: str, filters: dict, columns,
                    schedule: str) -> ReportDefinition:
    require(actor, P_SAVE)
    label = (name or "").strip()
    if not label or len(label) > 120:
        raise InvalidInput("Name the report (at most 120 characters).", code="name_required")
    kind, clean, cols = _spec(actor, report_type, filters, columns)
    row = ReportDefinition.objects.create(
        owner_user_id=actor.user_id, owner_role=actor.active_role or "", name=label,
        report_type=kind, filters={k: str(v) for k, v in clean.items()}, columns=list(cols),
        schedule=rp.check_schedule(schedule))
    audit.record(actor, "report_definition.saved", obj=row, details={"report_type": kind})
    return row


@ruled
def deactivate(*, actor, definition_id: int) -> ReportDefinition:
    require(actor, P_SAVE)
    with transaction.atomic():
        row = (ReportDefinition.objects.select_for_update()
               .filter(pk=definition_id, owner_user_id=actor.user_id).first())
        if row is None:
            raise NotFoundError("No such saved report.", code="not_found")
        if not row.active:
            raise ConflictError("This saved report is already switched off.",
                                code="already_inactive")
        row.active = False
        row.save(update_fields=["active", "updated_at"])
        audit.record(actor, "report_definition.deactivated", obj=row)
    return row


def run_download(*, actor, run_id: int):
    """Blueprint S-1: the rows are built now, from the owner's live role and scope."""
    run = (ReportRun.objects.select_related("definition")
           .filter(pk=run_id, definition__owner_user_id=actor.user_id).first())
    if run is None:
        raise NotFoundError("No such report run.", code="not_found")
    d = run.definition
    return run, generate(actor=actor, report_type=d.report_type, filters=d.filters,
                         columns=d.columns, export=True)


def period_for(schedule: str, day: date) -> str | None:
    if schedule == "weekly" and day.weekday() == 0:
        return f"{day.isocalendar().year}-W{day.isocalendar().week:02d}"
    if schedule == "monthly" and day.day == 1:
        return day.strftime("%Y-%m")
    return None


def run_scheduled(*, today: date | None = None) -> int:
    """PMS-AFR-188: one run per definition per period; the owner is told where to download it."""
    today = today or timezone.localdate()
    made = 0
    for d in ReportDefinition.objects.filter(active=True).exclude(schedule="none"):
        period = period_for(d.schedule, today)
        if period is None:
            continue
        try:
            with transaction.atomic():
                run = ReportRun.objects.create(definition=d, period=period)
        except IntegrityError:
            continue
        notifications.enqueue(
            topic="report.ready", dedupe_key=f"report.run:{run.pk}",
            recipient_user_id=d.owner_user_id, subject=f"Report ready: {d.name}",
            body=f"Your scheduled report '{d.name}' for {period} is ready. Open Patent "
                 f"Management, Reports, to download it.")
        made += 1
    log.info("pms.reports.scheduled runs=%d", made)
    return made
