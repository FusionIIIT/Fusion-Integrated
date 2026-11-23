"""Report types, their columns, and which filters each accepts (PMS-AFR-182..190, 237..239)."""
from __future__ import annotations

from datetime import date

from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput

COLUMNS: dict[str, tuple[str, ...]] = {
    "status": ("reference", "title", "status", "domain_code", "submitted_at", "updated_at"),
    "financial": ("reference", "title", "budget_status", "filing_fee", "attorney_fee",
                  "admin_cost", "total"),
    "deadlines": ("reference", "kind", "due_on", "days_left", "responsible"),
    "inventors": ("reference", "title", "inventor", "share_percent", "agreement", "consent"),
    "portfolio": ("domain_code", "status", "count"),
    "workload": ("person", "role", "open_items"),
    "dashboard": ("measure", "value"),
    "history": ("month", "submitted", "approved", "rejected", "filed", "granted"),
    "trend": ("month", "submitted", "change"),
}
TYPES = tuple(COLUMNS)
# UC-PMS-030: an applicant's own reports; financial and workload are office reports.
APPLICANT_TYPES = frozenset({"status", "deadlines", "inventors", "portfolio", "dashboard"})
SCHEDULES = ("none", "weekly", "monthly")


def check_type(report_type: str, *, applicant_only: bool) -> str:
    if report_type not in COLUMNS:
        raise InvalidInput(f"Unknown report '{report_type}'. Choose one of: "
                           + ", ".join(TYPES) + ".", code="invalid_report")
    if applicant_only and report_type not in APPLICANT_TYPES:
        raise InvalidInput("That report is available to Directors and PCC_ADMIN only.",
                           code="report_not_available")
    return report_type


def check_columns(report_type: str, columns: list[str] | None) -> tuple[str, ...]:
    allowed = COLUMNS[report_type]
    if not columns:
        return allowed
    unknown = [c for c in columns if c not in allowed]
    if unknown:
        raise InvalidInput(f"These columns are not in the {report_type} report: "
                           + ", ".join(unknown) + ".", code="invalid_columns")
    return tuple(dict.fromkeys(columns))


def check_filters(raw: dict) -> dict:
    """Only status, area and a date range; anything else is refused rather than ignored."""
    allowed = {"status", "domain_code", "date_from", "date_to"}
    unknown = set(raw) - allowed
    if unknown:
        raise InvalidInput("Unknown report filter: " + ", ".join(sorted(unknown)) + ".",
                           code="invalid_filter")
    out: dict = {}
    if raw.get("status"):
        if raw["status"] not in sm.APPLICATION_STATUSES:
            raise InvalidInput("Unknown status filter.", code="invalid_filter")
        out["status"] = raw["status"]
    if raw.get("domain_code"):
        out["domain_code"] = str(raw["domain_code"])[:40]
    for key in ("date_from", "date_to"):
        if raw.get(key):
            try:
                out[key] = date.fromisoformat(str(raw[key]))
            except ValueError as exc:
                raise InvalidInput(f"{key} must be a date like 2026-11-21.",
                                   code="invalid_filter") from exc
    if out.get("date_from") and out.get("date_to") and out["date_from"] > out["date_to"]:
        raise InvalidInput("The start date is after the end date.", code="invalid_filter")
    return out


def check_schedule(value: str) -> str:
    if value not in SCHEDULES:
        raise InvalidInput("Schedule a report weekly, monthly or not at all.",
                           code="invalid_schedule")
    return value
