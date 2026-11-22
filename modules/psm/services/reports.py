# Authorized report generation, CSV export, and scheduled runner (PSM-UC-010, 015, 031, 035).
from __future__ import annotations

import csv
import io
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import DomainError, NotFoundError, PermissionDeniedError
from modules.psm import registry
from modules.psm.models import ReportGenerationLog, ReportSchedule
from modules.psm.selectors import reports as report_sel
from modules.psm.selectors import scoping
from modules.psm.services.common import audit_record

VALID_REPORT_TYPES = frozenset({"operational", "procurement", "stock", "financial"})
VALID_CADENCES = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _escape_csv_cell(value) -> str:
    """Prefix formula-triggering characters with a single quote to prevent CSV injection."""
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(_FORMULA_PREFIXES) else text


def _require_report_permission(actor, report_type: str) -> None:
    if report_type not in VALID_REPORT_TYPES:
        raise DomainError(
            "Select a valid report type: operational, procurement, stock, or financial.",
            code="invalid_report_type",
        )
    needed = "psm.financial_report.view" if report_type == "financial" else "psm.report.view"
    if not actor.has_permission(needed):
        raise PermissionDeniedError(
            "You do not have permission to generate this report type.", code="report_not_authorized"
        )


def generate_report(
    *, actor, report_type: str, filters: dict | None = None, export_format: str = "json"
) -> dict:
    """Generate a scoped report and log the run (PSM-UC-010, 015, BR-PSM-024)."""
    _require_report_permission(actor, report_type)
    clean_filters = filters or {}
    headers, rows = report_sel.build_report_rows(
        actor, report_type=report_type, filters=clean_filters
    )
    log_row = ReportGenerationLog.objects.create(
        report_type=report_type,
        trigger_type="interactive",
        filters=clean_filters,
        export_format=export_format,
        row_count=len(rows),
        status="succeeded",
        actor_user_id=actor.user_id,
    )
    audit_record(
        actor=actor,
        action="report.generated",
        target_type="report_log",
        target_id=log_row.pk,
        details={"report_type": report_type, "rows": len(rows)},
    )
    return {
        "log_id": log_row.pk,
        "report_type": report_type,
        "headers": headers,
        "rows": rows,
        "row_count": len(rows),
    }


def export_report_csv(*, actor, report_type: str, filters: dict | None = None) -> tuple[str, str]:
    """Generate a formula-escaped CSV export and log the run (AFR-PSM-079)."""
    result = generate_report(
        actor=actor, report_type=report_type, filters=filters, export_format="csv"
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(result["headers"])
    for row in result["rows"]:
        writer.writerow([_escape_csv_cell(row.get(h, "")) for h in result["headers"]])
    return f"psm-{report_type}-report.csv", buf.getvalue()


@transaction.atomic
def create_schedule(
    *, actor, name: str, report_type: str, cadence: str, filters: dict | None = None
) -> ReportSchedule:
    """Create an active scheduled report definition (PSM-UC-031, AFR-PSM-080)."""
    _require_report_permission(actor, report_type)
    if cadence not in VALID_CADENCES:
        raise DomainError(
            "Select a valid cadence: daily, weekly, or monthly.", code="invalid_cadence"
        )
    if not (name or "").strip():
        raise DomainError("Provide a name for this scheduled report.", code="name_required")
    schedule = ReportSchedule.objects.create(
        name=name.strip(),
        report_type=report_type,
        filters=filters or {},
        cadence=cadence,
        is_active=True,
        created_by_user_id=actor.user_id,
        created_by_role=scoping.active_role_of(actor),
        next_run_at=timezone.now() + VALID_CADENCES[cadence],
    )
    audit_record(
        actor=actor,
        action="report.schedule_created",
        target_type="report_schedule",
        target_id=schedule.pk,
    )
    return schedule


@transaction.atomic
def update_schedule(
    *, actor, schedule_id: int, is_active: bool | None = None, cadence: str | None = None
) -> ReportSchedule:
    """Enable, disable, or change cadence on a visible report schedule (PSM-UC-031)."""
    schedule = (
        scoping.report_schedules_for(actor).select_for_update().filter(pk=schedule_id).first()
    )
    if schedule is None:
        raise NotFoundError("Report schedule not found.")
    if cadence is not None:
        if cadence not in VALID_CADENCES:
            raise DomainError(
                "Select a valid cadence: daily, weekly, or monthly.", code="invalid_cadence"
            )
        schedule.cadence = cadence
    if is_active is not None:
        schedule.is_active = is_active
    schedule.save(update_fields=["cadence", "is_active", "updated_at"])
    audit_record(
        actor=actor,
        action="report.schedule_updated",
        target_type="report_schedule",
        target_id=schedule.pk,
    )
    return schedule


class _ScheduledActor:
    """Minimal role-bound principal used to evaluate a due ReportSchedule (PSM-UC-035)."""

    def __init__(self, user_id: int, role: str):
        self.user_id = user_id
        self.active_role = role
        self._perms = frozenset(registry.ROLE_GRANTS.get(role, ()))

    def has_permission(self, code: str) -> bool:
        return code in self._perms


def run_due_schedules(*, now=None) -> int:
    """Execute all due active report schedules idempotently (PSM-UC-035, BR-PSM-024)."""
    now = now or timezone.now()
    due_ids = list(
        ReportSchedule.objects.filter(is_active=True, next_run_at__lte=now).values_list(
            "pk", flat=True
        )
    )
    executed = 0
    for pk in due_ids:
        with transaction.atomic():
            sched = ReportSchedule.objects.select_for_update().get(pk=pk)
            if not sched.is_active or sched.next_run_at > now:
                continue
            actor = _ScheduledActor(sched.created_by_user_id, sched.created_by_role)
            needed = (
                "psm.financial_report.view"
                if sched.report_type == "financial"
                else "psm.report.view"
            )
            if not actor.has_permission(needed):
                ReportGenerationLog.objects.create(
                    report_type=sched.report_type,
                    trigger_type="scheduled",
                    schedule=sched,
                    filters=sched.filters,
                    status="blocked",
                    actor_user_id=sched.created_by_user_id,
                    error_message=f"Role '{sched.created_by_role}' no longer holds {needed}.",
                )
                sched.is_active = False
                sched.save(update_fields=["is_active", "updated_at"])
                continue
            _, rows = report_sel.build_report_rows(
                actor, report_type=sched.report_type, filters=sched.filters
            )
            ReportGenerationLog.objects.create(
                report_type=sched.report_type,
                trigger_type="scheduled",
                schedule=sched,
                filters=sched.filters,
                export_format="json",
                row_count=len(rows),
                status="succeeded",
                actor_user_id=sched.created_by_user_id,
            )
            sched.last_run_at = now
            sched.next_run_at = now + VALID_CADENCES.get(sched.cadence, timedelta(days=1))
            sched.save(update_fields=["last_run_at", "next_run_at", "updated_at"])
            executed += 1
    return executed
