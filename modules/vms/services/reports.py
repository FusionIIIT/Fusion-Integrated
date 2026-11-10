"""Reports, analytics and exports (VMS-UC-007, CFR-008, SRS 3.10).

Read-only: the only rows this module writes are AuditLog entries for PII views
and exports. Reports are anonymised by default (D-9): names become
``Visitor #<hash6>`` (HMAC keyed from SECRET_KEY, so the caller cannot reverse
an id) and phone/email/ID are masked. Un-masked output needs
``vms.report.view_pii`` *and* an explicit ``anonymize=false``, and is audited.

Catalogue is the reports SRS 3.10 names plus ``event_attendance`` (selectors/events.py)
and ``muster_history`` (EmergencyMuster rows).
PDF export: no PDF library is installed, so ``fmt=pdf`` answers 501
(service request h-1); no dependency was added.
"""
from __future__ import annotations

import hashlib
import hmac
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.utils import timezone
from rest_framework import status as http

from core.api.exceptions import (
    BadRequestError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.directory import contracts as directory
from modules.vms.models import Gate, RoleAssignment
from modules.vms.selectors import reports as sel
from modules.vms.services.common import audit, authz

PERM_VIEW = "vms.report.view"
PERM_EXPORT = "vms.report.export"
PERM_PII = "vms.report.view_pii"
MAX_RANGE_DAYS = 366
DEFAULT_RANGE_DAYS = 30
FORMATS = ("csv", "pdf")
GRANULARITIES = ("day", "week", "month")
ACT_PII_VIEW = "vms.report.pii_view"
ACT_EXPORT = "vms.report.exported"
UNKNOWN_DEPARTMENT = "Unknown"


class NotImplementedFormat(DomainError):
    code = "pdf_backend_unavailable"
    status_code = http.HTTP_501_NOT_IMPLEMENTED
    message = "PDF export is not available: no PDF backend is installed."


@dataclass(frozen=True)
class ReportDef:
    key: str
    title: str
    fn: object
    params: tuple[str, ...] = ()
    identity: bool = False      # rows can name a visitor (D-9)


CATALOGUE: dict[str, ReportDef] = {d.key: d for d in (
    ReportDef("daily_summary", "Daily summary", sel.daily_summary, ("date",)),
    ReportDef("volume_trend", "Visitor volume trend", sel.volume_trend, ("granularity",)),
    ReportDef("peak_hours", "Peak hours", sel.peak_hours),
    ReportDef("frequent_visitors", "Frequent visitors", sel.frequent_visitors, ("top",),
              identity=True),
    ReportDef("denial_stats", "Denial statistics", sel.denial_stats),
    ReportDef("sla_compliance", "Approval SLA compliance", sel.sla_compliance),
    ReportDef("audit_trail", "Audit trail", sel.audit_trail, ("visitor_id",), identity=True),
    ReportDef("zone_access", "Zone access", sel.zone_access),
    ReportDef("blacklist_hits", "Blacklist hits", sel.blacklist_hits, identity=True),
    ReportDef("event_attendance", "Event attendance", sel.event_attendance, ("event_id",)),
    ReportDef("muster_history", "Emergency muster history", sel.muster_history),
)}


@dataclass(frozen=True)
class Params:
    key: str
    start: date
    end: date
    zone: int | None = None
    anonymize: bool = True
    granularity: str = "day"
    top: int = 10
    visitor_id: int | None = None
    event_id: int | None = None
    extra: dict = field(default_factory=dict)

    def public(self) -> dict:
        d = {"start": self.start.isoformat(), "end": self.end.isoformat(),
             "anonymize": self.anonymize}
        if self.zone is not None:
            d["zone"] = self.zone
        for name in CATALOGUE[self.key].params:
            if name != "date":
                d[name] = getattr(self, name)
        return d


# --- catalogue & validation -------------------------------------------------------------

def catalogue(actor) -> list[dict]:
    authz.require(actor, PERM_VIEW)
    common = ["start", "end", "zone", "anonymize"]
    return [{"key": d.key, "title": d.title, "params": common + list(d.params),
             "identity": d.identity} for d in CATALOGUE.values()]


def _to_date(name, value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise BadRequestError(f"{name} must be an ISO date (YYYY-MM-DD).",
                              code="validation_error") from None


def _to_int(name, value, lo, hi) -> int | None:
    if value in (None, ""):
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise BadRequestError(f"{name} must be an integer.", code="validation_error") from None
    if not lo <= n <= hi:
        raise BadRequestError(f"{name} must be between {lo} and {hi}.",
                              code="validation_error")
    return n


def _to_bool(value, default=True) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    raise BadRequestError("anonymize must be true or false.", code="validation_error")


def validate(key: str, params: dict | None) -> Params:
    """Known key, start <= end, range <= 366 days, typed options."""
    if key not in CATALOGUE:
        raise NotFoundError("Unknown report.")
    p = params or {}
    today = timezone.localdate()
    on = _to_date("date", p.get("date")) if key == "daily_summary" else None
    start, end = _to_date("start", p.get("start")), _to_date("end", p.get("end"))
    if on:
        start = end = on
    elif key == "daily_summary" and start is None and end is None:
        start = end = today
    end = end or today
    start = start or end - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if start > end:
        raise BadRequestError("start must not be after end.", code="validation_error")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise BadRequestError(f"The date range may not exceed {MAX_RANGE_DAYS} days.",
                              code="range_too_large")
    gran = (p.get("granularity") or "day")
    if gran not in GRANULARITIES:
        raise BadRequestError("granularity must be day, week or month.",
                              code="validation_error")
    if key == "event_attendance" and _to_int("event_id", p.get("event_id"), 1, 2**31 - 1) is None:
        raise BadRequestError("event_id is required.", code="validation_error")
    return Params(
        key=key, start=start, end=end, zone=_to_int("zone", p.get("zone"), 1, 2**31 - 1),
        anonymize=_to_bool(p.get("anonymize")), granularity=gran,
        top=_to_int("top", p.get("top"), 1, sel.TOP_MAX) or 10,
        visitor_id=_to_int("visitor_id", p.get("visitor_id"), 1, 2**31 - 1),
        event_id=_to_int("event_id", p.get("event_id"), 1, 2**31 - 1))


# --- scope ------------------------------------------------------------------------------

def zone_scope(actor) -> frozenset[int] | None:
    """Zones the Admin may report on; None = every zone.

    Derived from the actor's active admin RoleAssignments (BR-181): any campus
    scope, or no admin assignment at all (IAM-granted super admin), is
    unrestricted; otherwise the union of zone scopes and the zones of gate scopes.
    """
    now = timezone.now()
    rows = list(RoleAssignment.objects.filter(
        user_id=actor.user_id, role=RoleAssignment.Role.ADMIN, revoked_at__isnull=True,
        starts_at__lte=now, ends_at__gt=now).values_list("scope_type", "scope_id"))
    if not rows or any(t == RoleAssignment.ScopeType.CAMPUS for t, _ in rows):
        return None
    zones = {i for t, i in rows if t == RoleAssignment.ScopeType.ZONE}
    gates = {i for t, i in rows if t == RoleAssignment.ScopeType.GATE}
    if gates:
        zones |= set(Gate.objects.filter(pk__in=gates).values_list("zone_id", flat=True))
    return frozenset(zones)


def _effective_zones(actor, p: Params) -> frozenset[int] | None:
    scope = zone_scope(actor)
    if p.zone is None:
        return scope
    if scope is not None and p.zone not in scope:
        raise NotFoundError("Zone not found.")      # no id enumeration
    return frozenset({p.zone})


# --- anonymisation (D-9) ----------------------------------------------------------------

def _key() -> bytes:
    return hmac.new(settings.SECRET_KEY.encode(), b"vms.report.anonymise.v1",
                    hashlib.sha256).digest()


def visitor_label(visitor_id) -> str:
    digest = hmac.new(_key(), f"visitor:{visitor_id}".encode(), hashlib.sha256).hexdigest()
    return f"Visitor #{digest[:6]}"


def mask_phone(value: str) -> str:
    return "" if not value else "*" * max(len(value) - 2, 0) + value[-2:]


def mask_email(value: str) -> str:
    return "" if not value else "***@" + value.rpartition("@")[2]


def mask_id(value: str) -> str:
    return "" if not value else "*" * max(len(value) - 2, 0) + value[-2:]


def _apply_identity(result: dict, anonymize: bool) -> None:
    cols = result["columns"]
    if "full_name" not in cols:
        return
    for row in result["rows"]:
        if anonymize:
            row["visitor"] = visitor_label(row["visitor_id"]) if row["visitor_id"] else ""
            row["phone"] = mask_phone(row["phone"] or "")
            row["email"] = mask_email(row["email"] or "")
            row["id_doc_number"] = mask_id(row["id_doc_number"] or "")
            row.pop("visitor_id")
            if row.get("type") == "decision":
                row["reason"] = ""          # free text
            if "justification" in row:
                row["justification"] = ""
        else:
            row["visitor"] = row["full_name"]
        row.pop("full_name")
    new = []
    for c in cols:
        if c == "full_name":
            new.append("visitor")
        elif c != "visitor_id" or not anonymize:
            new.append(c)
    result["columns"] = new


# --- running ----------------------------------------------------------------------------

def _rollup_departments(result: dict) -> None:
    hosts = result["rows"]
    users = _directory_users([h["host_user_id"] for h in hosts])
    depts: dict = defaultdict(lambda: defaultdict(int))
    for h in hosts:
        user = users.get(h["host_user_id"])
        dep = (getattr(user, "department", "") or UNKNOWN_DEPARTMENT) if user \
            else UNKNOWN_DEPARTMENT
        for k, v in h.items():
            if k != "host_user_id":
                depts[dep][k] += v
    rows = []
    for dep in sorted(depts):
        d = dict(depts[dep])
        judged = d["decided"] + d["expired"]
        d["pct_within_sla"] = round(100 * d["within_sla"] / judged, 1) if judged else None
        rows.append({"department": dep, **d})
    total = {k: sum(r[k] for r in rows) for k in sel.SLA_HOST_COLUMNS[1:]}
    judged = total["decided"] + total["expired"]
    result["rows"] = rows
    result["columns"] = ["department", *sel.SLA_HOST_COLUMNS[1:], "pct_within_sla"]
    result["summary"] = {**total, "pct_within_sla":
                         round(100 * total["within_sla"] / judged, 1) if judged else None}


def _directory_users(user_ids):
    return directory.get_users(list(user_ids))


def _tz_bounds(p: Params):
    tz = timezone.get_current_timezone()
    return (timezone.make_aware(datetime.combine(p.start, datetime.min.time()), tz),
            timezone.make_aware(datetime.combine(p.end + timedelta(days=1),
                                                 datetime.min.time()), tz))


def _ref(key: str):
    """Stand-in 'entity' so audit.record can log a report run (no row exists)."""
    return SimpleNamespace(pk=key, _meta=SimpleNamespace(model_name="report"))


def _build(actor, p: Params) -> dict:
    if not p.anonymize and not actor.has_permission(PERM_PII):
        raise PermissionDeniedError("Un-masked output needs the view_pii permission.")
    d = CATALOGUE[p.key]
    filters = {"zone_ids": _effective_zones(actor, p), "granularity": p.granularity,
               "top": p.top, "visitor_id": p.visitor_id,
               "event_id": p.event_id, "with_names": not p.anonymize}
    start, end = _tz_bounds(p)
    result = d.fn(start, end, filters)
    if p.key == "sla_compliance":
        _rollup_departments(result)
    if d.identity:
        _apply_identity(result, p.anonymize)
    return {"key": p.key, "title": d.title, "params": p.public(),
            "anonymized": p.anonymize, **result}


def run(actor, key: str, params: dict | None = None) -> dict:
    """Generate one report (UC-007 steps 1-3). PII-revealing runs are audited."""
    authz.require(actor, PERM_VIEW)
    p = validate(key, params)
    out = _build(actor, p)
    if not p.anonymize:
        audit.record(actor=actor, action=ACT_PII_VIEW, entity=_ref(key),
                     detail={"params": p.public(), "rows": len(out["rows"])})
    return out


def export(actor, key: str, params: dict | None = None, fmt: str = "csv") -> dict:
    """Report for export (UC-007 step 4). Returns ``{filename, header, rows}``.

    Audited with its parameters whether or not it shows PII.
    """
    authz.require(actor, PERM_EXPORT)
    if fmt not in FORMATS:
        raise BadRequestError("fmt must be csv or pdf.", code="validation_error")
    if fmt == "pdf":
        raise NotImplementedFormat()          # service request h-1
    p = validate(key, params)
    out = _build(actor, p)
    audit.record(actor=actor, action=ACT_EXPORT, entity=_ref(key), detail={
        "params": p.public(), "format": fmt, "rows": len(out["rows"]),
        "pii": not p.anonymize})
    if not p.anonymize:
        audit.record(actor=actor, action=ACT_PII_VIEW, entity=_ref(key),
                     detail={"params": p.public(), "rows": len(out["rows"]),
                             "export": True})
    cols = out["columns"]
    return {"filename": f"vms-{key}-{p.start}-{p.end}.csv", "header": cols,
            "rows": ([r.get(c) for c in cols] for r in out["rows"]),
            "row_count": len(out["rows"]), "truncated": out["truncated"]}
