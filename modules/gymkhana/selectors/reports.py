"""Event report read selectors for Gymkhana."""

from __future__ import annotations

from core.api.exceptions import NotFoundError
from modules.gymkhana.models.report import ClubEventReport


def get_event_report_by_id(report_id: int) -> ClubEventReport:
    """Return event report by ID or raise NotFound."""
    report = ClubEventReport.objects.select_related("club").filter(id=report_id).first()
    if not report:
        raise NotFoundError(f"Event report {report_id} not found.")
    return report
