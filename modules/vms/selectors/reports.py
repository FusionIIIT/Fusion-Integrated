"""Report aggregations (VMS-UC-007, CFR-008, SRS 3.10). Read-only.

Every function takes ``(start, end, filters)`` and returns a plain dict::

    {"columns": [...], "rows": [dict, ...], "summary": {...}, "truncated": bool}

``start``/``end`` are aware datetimes, ``start`` inclusive and ``end``
exclusive. ``filters`` may carry ``zone_ids`` (a set; ``None`` means every
zone), plus report specific keys. Aggregation happens in the database
(``values().annotate()``); grouped result sets are capped at ``ROW_CAP`` and
flag ``truncated``. Identity columns are returned raw: anonymisation is the
service's job (D-9).

TODO(integration): ``event_attendance`` (needs lane G's selectors/events.py) and
``muster_history`` (needs lane F's muster data) are added at integration.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.db.models import Case as SqlCase
from django.db.models import (
    Count,
    DateTimeField,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    When,
)
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import (
    Cast,
    Coalesce,
    ExtractHour,
    TruncDate,
    TruncMonth,
    TruncWeek,
)
from django.utils import timezone

from modules.vms.models import (
    AccessPolicy,
    Alert,
    Gate,
    GateOverride,
    VisitLog,
    VisitRequest,
    Zone,
)

ROW_CAP = 10_000
DEFAULT_SLA_HOURS = 24      # services.policy defaults when nothing is published
TOP_MAX = 100
Status = VisitRequest.Status
Ev = VisitLog.Event


# --- shared pieces ----------------------------------------------------------------------

def _capped(qs) -> tuple[list, bool]:
    rows = list(qs[:ROW_CAP + 1])
    return rows[:ROW_CAP], len(rows) > ROW_CAP


def _result(columns, rows, summary=None, truncated=False) -> dict:
    return {"columns": columns, "rows": rows, "summary": summary or {},
            "truncated": truncated}


def _logs(start, end, zone_ids):
    """Gate trail in [start, end) by device time when known (D-10)."""
    qs = (VisitLog.objects.annotate(at=Coalesce("occurred_at", "created_at"))
          .filter(at__gte=start, at__lt=end))
    if zone_ids is not None:
        qs = qs.filter(Q(zone_id__in=zone_ids)
                       | Q(zone__isnull=True, gate__zone_id__in=zone_ids))
    return qs


def _requests(start, end, zone_ids):
    qs = VisitRequest.objects.filter(created_at__gte=start, created_at__lt=end)
    if zone_ids is not None:
        through = VisitRequest.requested_zones.through
        qs = qs.filter(id__in=through.objects.filter(zone_id__in=zone_ids)
                       .values("visitrequest_id"))
    return qs


def _alerts(start, end, zone_ids, kind):
    """Alerts of `kind`; `zid`/`gid` are read out of the JSON detail."""
    qs = (Alert.objects.filter(kind=kind, created_at__gte=start, created_at__lt=end)
          .annotate(zid=Cast(KeyTextTransform("zone_id", "detail"), IntegerField()),
                    gid=Cast(KeyTextTransform("gate_id", "detail"), IntegerField())))
    if zone_ids is not None:
        qs = qs.filter(Q(zid__in=zone_ids) | Q(gid__in=Gate.objects.filter(
            zone_id__in=zone_ids).values("id")))
    return qs


# --- daily_summary ----------------------------------------------------------------------

def daily_summary(start, end, filters) -> dict:
    zones = filters.get("zone_ids")
    req = _requests(start, end, zones).aggregate(
        registered=Count("id"),
        approved=Count("id", filter=Q(status=Status.APPROVED)),
        rejected=Count("id", filter=Q(status=Status.REJECTED)),
        expired=Count("id", filter=Q(status=Status.EXPIRED)),
        completed=Count("id", filter=Q(status=Status.COMPLETED)))
    log = _logs(start, end, zones).aggregate(
        check_ins=Count("id", filter=Q(event=Ev.CHECK_IN)),
        check_outs=Count("id", filter=Q(event__in=[Ev.CHECK_OUT, Ev.AUTO_CHECK_OUT])),
        denials=Count("id", filter=Q(event=Ev.DENIED)))
    summary = {**req, **log}
    rows = [{"metric": k, "value": v} for k, v in summary.items()]
    return _result(["metric", "value"], rows, summary)


# --- volume_trend -----------------------------------------------------------------------

_TRUNC = {"day": TruncDate, "week": TruncWeek, "month": TruncMonth}


def _as_date(v):
    return v.date() if hasattr(v, "date") else v


def volume_trend(start, end, filters) -> dict:
    zones = filters.get("zone_ids")
    trunc = _TRUNC[filters.get("granularity", "day")]
    req = (_requests(start, end, zones).annotate(bucket=trunc("created_at"))
           .values("bucket").annotate(requests=Count("id"),
                                      visitors=Count("visitor_id", distinct=True))
           .order_by("bucket"))
    chk = (_logs(start, end, zones).filter(event=Ev.CHECK_IN)
           .annotate(bucket=trunc("at")).values("bucket")
           .annotate(check_ins=Count("id")).order_by("bucket"))
    data: dict = defaultdict(lambda: {"requests": 0, "visitors": 0, "check_ins": 0})
    rows, truncated = _capped(req)
    for r in rows:
        data[_as_date(r["bucket"])].update(requests=r["requests"], visitors=r["visitors"])
    chk_rows, t2 = _capped(chk)
    for r in chk_rows:
        data[_as_date(r["bucket"])]["check_ins"] = r["check_ins"]
    out = [{"period": d.isoformat(), **v} for d, v in sorted(data.items())]
    return _result(["period", "requests", "visitors", "check_ins"], out,
                   {"granularity": filters.get("granularity", "day"),
                    "total_requests": sum(r["requests"] for r in out),
                    "total_check_ins": sum(r["check_ins"] for r in out)},
                   truncated or t2)


# --- peak_hours -------------------------------------------------------------------------

def peak_hours(start, end, filters) -> dict:
    counts = dict(_logs(start, end, filters.get("zone_ids")).filter(event=Ev.CHECK_IN)
                  .annotate(hour=ExtractHour("at")).values_list("hour")
                  .annotate(n=Count("id")).order_by("hour"))
    rows = [{"hour": h, "check_ins": counts.get(h, 0)} for h in range(24)]
    peak = max(rows, key=lambda r: (r["check_ins"], -r["hour"]))
    return _result(["hour", "check_ins"], rows, {
        "total_check_ins": sum(counts.values()),
        "peak_hour": peak["hour"] if peak["check_ins"] else None})


# --- frequent_visitors ------------------------------------------------------------------

def frequent_visitors(start, end, filters) -> dict:
    """Visitors ranked by approved/completed visits created in the range."""
    top = min(max(int(filters.get("top") or 10), 1), TOP_MAX)
    qs = (_requests(start, end, filters.get("zone_ids"))
          .filter(status__in=[Status.APPROVED, Status.COMPLETED])
          .values("visitor_id", full_name=F("visitor__full_name"),
                  phone=F("visitor__phone"), email=F("visitor__email"),
                  id_doc_number=F("visitor__id_doc_number"))
          .annotate(visits=Count("id")).order_by("-visits", "visitor_id")[:top])
    rows = list(qs)
    return _result(["visitor_id", "full_name", "phone", "email", "id_doc_number", "visits"],
                   rows, {"top": top})


# --- denial_stats -----------------------------------------------------------------------

def denial_stats(start, end, filters) -> dict:
    """A denial with several failure codes counts once under each code."""
    grouped = (_logs(start, end, filters.get("zone_ids")).filter(event=Ev.DENIED)
               .annotate(hour=ExtractHour("at"))
               .values("reason", "gate_id", "gate__name", "hour")
               .annotate(n=Count("id")))
    data, truncated = _capped(grouped)
    by_reason: dict = defaultdict(int)
    by_gate: dict = defaultdict(int)
    by_hour: dict = defaultdict(int)
    total = 0
    for r in data:
        total += r["n"]
        for code in [c for c in r["reason"].split(",") if c] or ["unknown"]:
            by_reason[code] += r["n"]
        by_gate[r["gate__name"] or "(no gate)"] += r["n"]
        by_hour[f"{r['hour']:02d}"] += r["n"]
    rows = [{"dimension": dim, "bucket": k, "count": v}
            for dim, d in (("reason", by_reason), ("gate", by_gate), ("hour", by_hour))
            for k, v in sorted(d.items())]
    return _result(["dimension", "bucket", "count"], rows,
                   {"total_denials": total}, truncated)


# --- sla_compliance ---------------------------------------------------------------------

def _deadline_expr():
    """created_at + the approval_timeout_hours that applied then (BR-129)."""
    pols = list(AccessPolicy.objects.filter(status=AccessPolicy.Status.PUBLISHED)
                .order_by("published_at", "version")
                .values_list("published_at", "approval_timeout_hours"))
    if not pols:
        return F("created_at") + timedelta(hours=DEFAULT_SLA_HOURS), []
    if len(pols) == 1:
        return F("created_at") + timedelta(hours=pols[0][1]), pols
    whens = []
    for i, (pub, hours) in enumerate(pols):
        cond = Q()
        if i > 0:                      # the oldest policy also covers earlier requests
            cond &= Q(created_at__gte=pub)
        if i + 1 < len(pols):
            cond &= Q(created_at__lt=pols[i + 1][0])
        whens.append(When(cond, then=ExpressionWrapper(
            F("created_at") + timedelta(hours=hours), output_field=DateTimeField())))
    return SqlCase(*whens, output_field=DateTimeField()), pols


def sla_compliance(start, end, filters) -> dict:
    """Per host: approval time distribution vs approval_timeout_hours.

    The service rolls hosts up into departments. A request decided exactly at
    its deadline is within SLA; an expired one never is.
    """
    deadline, _ = _deadline_expr()
    decided = Q(decided_at__isnull=False) & ~Q(status=Status.EXPIRED)
    h = timedelta(hours=1)
    qs = (_requests(start, end, filters.get("zone_ids"))
          .annotate(deadline=deadline,
                    elapsed=ExpressionWrapper(F("decided_at") - F("created_at"),
                                              output_field=DurationField()))
          .values("host_user_id").annotate(
              total=Count("id"),
              decided=Count("id", filter=decided),
              within_sla=Count("id", filter=decided & Q(decided_at__lte=F("deadline"))),
              expired=Count("id", filter=Q(status=Status.EXPIRED)),
              lt_1h=Count("id", filter=decided & Q(elapsed__lt=h)),
              h1_4=Count("id", filter=decided & Q(elapsed__gte=h, elapsed__lt=4 * h)),
              h4_12=Count("id", filter=decided & Q(elapsed__gte=4 * h, elapsed__lt=12 * h)),
              h12_24=Count("id", filter=decided & Q(elapsed__gte=12 * h,
                                                    elapsed__lt=24 * h)),
              ge_24h=Count("id", filter=decided & Q(elapsed__gte=24 * h)))
          .order_by("host_user_id"))
    rows, truncated = _capped(qs)
    return _result(SLA_HOST_COLUMNS, rows, {}, truncated)


SLA_HOST_COLUMNS = ["host_user_id", "total", "decided", "within_sla", "expired", "lt_1h",
                    "h1_4", "h4_12", "h12_24", "ge_24h"]


# --- audit_trail ------------------------------------------------------------------------

_ORDER = {"request_created": 0, "decision": 1, "log": 2, "override": 3}


def audit_trail(start, end, filters) -> dict:
    """Ordered requests, decisions, gate logs and overrides, by visitor and/or range."""
    zones = filters.get("zone_ids")
    vid = filters.get("visitor_id")
    req_qs = _requests(start, end, zones)
    log_qs = _logs(start, end, zones)
    if vid:
        req_qs = req_qs.filter(visitor_id=vid)
        log_qs = log_qs.filter(visit_pass__visit_request__visitor_id=vid)
    ident = {"full_name": "visitor__full_name", "phone": "visitor__phone",
             "email": "visitor__email", "id_doc_number": "visitor__id_doc_number"}
    reqs, t1 = _capped(req_qs.order_by("created_at", "id").values(
        "id", "visitor_id", "host_user_id", "status", "source", "is_urgent", "created_at",
        "decided_at", "decision_note", **{k: F(v) for k, v in ident.items()}))
    lid = "visit_pass__visit_request__"
    logs, t2 = _capped(log_qs.order_by("at", "id").values(
        "id", "at", "event", "reason", "logged_by_user_id", "gate_id", "zone_id",
        request_id=F(lid + "id"), visitor_id=F(lid + "visitor_id"),
        **{k: F(lid + v) for k, v in ident.items()}))
    ovr_qs = GateOverride.objects.filter(visit_log__in=log_qs.values("id"))
    ovrs, t3 = _capped(ovr_qs.order_by("created_at", "id").values(
        "id", "created_at", "admin_user_id", "justification", log_id=F("visit_log_id"),
        request_id=F("visit_log__visit_pass__visit_request_id"),
        visitor_id=F("visit_log__" + lid + "visitor_id"),
        **{k: F("visit_log__" + lid + v) for k, v in ident.items()}))
    events = []
    for r in reqs:
        who = {k: r[k] for k in ("visitor_id", *ident)}
        events.append({"at": r["created_at"], "type": "request_created",
                       "request_id": r["id"], "actor_user_id": r["host_user_id"],
                       "event": r["source"], "status": "pending",
                       "reason": "urgent" if r["is_urgent"] else "", **who})
        if r["decided_at"]:
            events.append({"at": r["decided_at"], "type": "decision",
                           "request_id": r["id"], "actor_user_id": r["host_user_id"],
                           "event": "decided", "status": r["status"],
                           "reason": r["decision_note"], **who})
    events.extend(
        {"at": r["at"], "type": "log", "request_id": r["request_id"],
         "actor_user_id": r["logged_by_user_id"], "event": r["event"],
         "status": "", "reason": r["reason"],
         **{k: r[k] for k in ("visitor_id", *ident)}} for r in logs)
    events.extend(
        {"at": r["created_at"], "type": "override",
         "request_id": r["request_id"], "actor_user_id": r["admin_user_id"],
         "event": "override", "status": "", "justification": r["justification"],
         "reason": "", **{k: r[k] for k in ("visitor_id", *ident)}} for r in ovrs)
    events.sort(key=lambda e: (e["at"], _ORDER[e["type"]], e["request_id"] or 0))
    truncated = t1 or t2 or t3 or len(events) > ROW_CAP
    for e in events:
        e["at"] = timezone.localtime(e["at"]).isoformat()
        e.setdefault("justification", "")
    return _result(AUDIT_COLUMNS, events[:ROW_CAP], {"events": len(events)}, truncated)


AUDIT_COLUMNS = ["at", "type", "request_id", "visitor_id", "full_name", "phone", "email",
                 "id_doc_number", "actor_user_id", "event", "status", "reason",
                 "justification"]


# --- zone_access ------------------------------------------------------------------------

def zone_access(start, end, filters) -> dict:
    zones = filters.get("zone_ids")
    logs, t1 = _capped(_logs(start, end, zones)
                       .filter(event__in=[Ev.ZONE_ALLOWED, Ev.ZONE_DENIED],
                               zone__isnull=False)
                       .values("zone_id").annotate(
                           allowed=Count("id", filter=Q(event=Ev.ZONE_ALLOWED)),
                           denied=Count("id", filter=Q(event=Ev.ZONE_DENIED)))
                       .order_by("zone_id"))
    alerts, t2 = _capped(_alerts(start, end, zones, Alert.Kind.ZONE_VIOLATION)
                         .values("zid").annotate(n=Count("id")).order_by("zid"))
    data: dict = defaultdict(lambda: {"allowed": 0, "denied": 0, "violations": 0})
    for r in logs:
        data[r["zone_id"]].update(allowed=r["allowed"], denied=r["denied"])
    for r in alerts:
        if r["zid"] is not None and (zones is None or r["zid"] in zones):
            data[r["zid"]]["violations"] = r["n"]
    names = dict(Zone.objects.filter(pk__in=list(data)).values_list("id", "name"))
    rows = [{"zone_id": z, "zone": names.get(z, ""), **v} for z, v in sorted(data.items())]
    return _result(["zone_id", "zone", "allowed", "denied", "violations"], rows, {
        "allowed": sum(r["allowed"] for r in rows),
        "denied": sum(r["denied"] for r in rows),
        "violations": sum(r["violations"] for r in rows)}, t1 or t2)


# --- blacklist_hits ---------------------------------------------------------------------

def blacklist_hits(start, end, filters) -> dict:
    """Hits by severity, checkpoint and date. Zone-scoped callers see gate hits in
    their zones only (registration-time hits carry no zone)."""
    qs = _alerts(start, end, filters.get("zone_ids"), Alert.Kind.BLACKLIST_HIT)
    grouped, truncated = _capped(
        qs.annotate(checkpoint=KeyTextTransform("checkpoint", "detail"),
                    day=TruncDate("created_at"))
        .values("severity", "checkpoint", "day").annotate(n=Count("id")))
    by: dict = {"severity": defaultdict(int), "checkpoint": defaultdict(int),
                "date": defaultdict(int)}
    total = 0
    for r in grouped:
        total += r["n"]
        by["severity"][r["severity"]] += r["n"]
        by["checkpoint"][r["checkpoint"] or "gate"] += r["n"]
        by["date"][r["day"].isoformat()] += r["n"]
    rows = [{"dimension": dim, "bucket": k, "count": v, "visitor": ""}
            for dim, d in by.items() for k, v in sorted(d.items())]
    result = _result(["dimension", "bucket", "count", "visitor"], rows,
                     {"total_hits": total}, truncated)
    if filters.get("with_names"):          # PII only: the label alerts carry (D-9)
        named, t2 = _capped(qs.order_by("created_at", "id").values(
            "id", "severity", label=KeyTextTransform("visitor", "detail")))
        result["rows"] += [{"dimension": "hit", "bucket": f"alert {r['id']} ({r['severity']})",
                            "count": 1, "visitor": r["label"] or ""} for r in named]
        result["truncated"] = truncated or t2
    return result

