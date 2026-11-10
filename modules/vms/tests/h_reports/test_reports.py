"""Each report against the exact numbers of the fixed dataset (see conftest)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.vms.services import reports
from modules.vms.tests import factories as f
from modules.vms.tests.h_reports.conftest import D1, D2, D3, FEB, at

pytestmark = pytest.mark.django_db

MARCH = {"start": D1, "end": D3}
TWO_DAYS = {"start": D1, "end": D2}


def rows_by(res, *keys):
    return {tuple(r[k] for k in keys) if len(keys) > 1 else r[keys[0]]: r
            for r in res["rows"]}


def test_each_report_matches_fixture_numbers(data, reporter):
    run = reports.run
    # daily_summary
    assert run(reporter, "daily_summary", {"date": D1})["summary"] == {
        "registered": 7, "approved": 3, "rejected": 1, "expired": 1, "completed": 1,
        "check_ins": 4, "check_outs": 3, "denials": 3}
    assert run(reporter, "daily_summary", {"date": D2})["summary"] == {
        "registered": 6, "approved": 3, "rejected": 1, "expired": 1, "completed": 1,
        "check_ins": 3, "check_outs": 1, "denials": 1}

    # volume_trend: day / week / month
    day = run(reporter, "volume_trend", {"start": FEB, "end": D3})
    assert [(r["period"], r["requests"], r["visitors"], r["check_ins"])
            for r in day["rows"]] == [
        ("2026-02-20", 1, 1, 0), (D1, 7, 4, 4), (D2, 6, 4, 3), (D3, 2, 1, 1)]
    week = run(reporter, "volume_trend", {"start": FEB, "end": D3, "granularity": "week"})
    assert [(r["period"], r["requests"], r["visitors"], r["check_ins"])
            for r in week["rows"]] == [
        ("2026-02-16", 1, 1, 0), ("2026-03-09", 13, 5, 7), ("2026-03-16", 2, 1, 1)]
    month = run(reporter, "volume_trend", {"start": FEB, "end": D3, "granularity": "month"})
    assert [(r["period"], r["requests"], r["visitors"], r["check_ins"])
            for r in month["rows"]] == [("2026-02-01", 1, 1, 0), ("2026-03-01", 15, 5, 8)]

    # peak_hours
    peak = run(reporter, "peak_hours", TWO_DAYS)
    assert len(peak["rows"]) == 24
    assert {r["hour"]: r["check_ins"] for r in peak["rows"] if r["check_ins"]} == {
        9: 4, 10: 2, 14: 1}
    assert peak["summary"] == {"total_check_ins": 7, "peak_hour": 9}

    # frequent_visitors (V1 7 visits, V2 2, V5 1; rejected/expired do not count)
    top = run(reporter, "frequent_visitors", {**MARCH, "top": 3})
    assert [r["visits"] for r in top["rows"]] == [7, 2, 1]
    assert len(run(reporter, "frequent_visitors", {**MARCH, "top": 2})["rows"]) == 2

    # denial_stats
    den = run(reporter, "denial_stats", TWO_DAYS)
    assert den["summary"] == {"total_denials": 4}
    assert [(r["dimension"], r["bucket"], r["count"]) for r in den["rows"]] == [
        ("reason", "blacklisted", 1), ("reason", "outside_validity", 1),
        ("reason", "pass_inactive", 2), ("reason", "zone_not_permitted", 1),
        ("gate", "Gate A", 3), ("gate", "Gate B", 1),
        ("hour", "08", 3), ("hour", "17", 1)]

    # sla_compliance per host department
    sla = run(reporter, "sla_compliance", MARCH)
    by = rows_by(sla, "department")
    keys = ("total", "decided", "within_sla", "expired", "lt_1h", "h1_4", "h4_12",
            "h12_24", "ge_24h", "pct_within_sla")
    assert tuple(by["CS"][k] for k in keys) == (7, 7, 5, 0, 0, 4, 2, 0, 1, 71.4)
    assert tuple(by["EE"][k] for k in keys) == (5, 3, 1, 2, 1, 0, 1, 1, 0, 20.0)
    assert tuple(by["Unknown"][k] for k in keys) == (3, 2, 1, 0, 1, 1, 0, 0, 0, 50.0)
    assert tuple(sla["summary"][k] for k in keys) == (15, 12, 7, 2, 2, 5, 3, 1, 1, 50.0)

    # zone_access
    za = rows_by(run(reporter, "zone_access", TWO_DAYS), "zone")
    assert (za["Z1"]["allowed"], za["Z1"]["denied"], za["Z1"]["violations"]) == (4, 1, 1)
    assert (za["Z2"]["allowed"], za["Z2"]["denied"], za["Z2"]["violations"]) == (1, 2, 3)

    # blacklist_hits
    bl = run(reporter, "blacklist_hits", TWO_DAYS)
    assert bl["summary"] == {"total_hits": 4}
    assert [(r["dimension"], r["bucket"], r["count"]) for r in bl["rows"]] == [
        ("severity", "critical", 1), ("severity", "high", 3),
        ("checkpoint", "gate", 1), ("checkpoint", "pre_registration", 2),
        ("checkpoint", "walk_in", 1), ("date", D1, 2), ("date", D2, 2)]

    # audit_trail for V5, ordered
    trail = run(reporter, "audit_trail", {**TWO_DAYS, "visitor_id": data.v[5].pk})
    assert [(r["at"][11:16], r["type"], r["event"]) for r in trail["rows"]] == [
        ("08:00", "log", "denied"), ("10:00", "request_created", "pre_registered"), ("10:05", "log", "check_in"),
        ("10:30", "request_created", "pre_registered"), ("10:50", "decision", "decided"),
        ("13:00", "decision", "decided"), ("13:10", "override", "override")]


def test_audit_trail_full_range_counts(data, reporter):
    trail = reports.run(reporter, "audit_trail", TWO_DAYS)
    types = [r["type"] for r in trail["rows"]]
    assert types.count("request_created") == 13
    assert types.count("decision") == 10      # r1-4,7,8-12 decided
    assert types.count("override") == 1
    assert trail["rows"] == sorted(trail["rows"], key=lambda r: r["at"])


def test_sla_compliance_boundaries(db, reporter):
    """Exactly at the deadline is within SLA; one second late is not; expired never."""
    f.make_published_policy(version=1, published_at=at("2026-01-01"),
                            approval_timeout_hours=2)
    base = at("2026-04-01", 9)
    for delta in (timedelta(hours=2), timedelta(hours=2, seconds=1),
                  timedelta(hours=1, minutes=59, seconds=59)):
        r = f.make_visit_request(host_user_id=2101, status="approved",
                                 decided_at=base + delta)
        type(r).objects.filter(pk=r.pk).update(created_at=base)
    r = f.make_visit_request(host_user_id=2101, status="expired")
    type(r).objects.filter(pk=r.pk).update(created_at=base)
    res = reports.run(reporter, "sla_compliance", {"start": "2026-04-01", "end": "2026-04-01"})
    s = res["summary"]
    assert (s["total"], s["decided"], s["within_sla"], s["expired"]) == (4, 3, 2, 1)
    assert s["pct_within_sla"] == 50.0       # 2 of 4 judged


def test_sla_uses_policy_in_force_at_creation(data, reporter):
    """r8 (D2, +1h59) is within P2's 2h; the same delta on D1 would be within P1's 4h too,
    but r10 (+3h on D2) breaches P2 while +3h on D1 would not."""
    sla = reports.run(reporter, "sla_compliance", {"start": D2, "end": D2})
    assert sla["summary"]["within_sla"] == 3          # r8, r9 (exact 2h), r11
    assert sla["summary"]["decided"] == 5


def test_br_129_no_policy_published_defaults_to_24h(db, reporter):
    base = at("2026-05-04", 9)
    for hours in (24, 25):
        r = f.make_visit_request(host_user_id=2101, status="approved",
                                 decided_at=base + timedelta(hours=hours))
        type(r).objects.filter(pk=r.pk).update(created_at=base)
    s = reports.run(reporter, "sla_compliance",
                    {"start": "2026-05-04", "end": "2026-05-04"})["summary"]
    assert (s["decided"], s["within_sla"]) == (2, 1)


def test_range_cap(data, reporter):
    ok = reports.run(reporter, "peak_hours", {"start": "2025-03-11", "end": "2026-03-11"})
    assert ok["params"]["start"] == "2025-03-11"          # 366 days inclusive
    with pytest.raises(BadRequestError) as e:
        reports.run(reporter, "peak_hours", {"start": "2025-03-10", "end": "2026-03-11"})
    assert e.value.code == "range_too_large"
    with pytest.raises(BadRequestError):
        reports.run(reporter, "peak_hours", {"start": D2, "end": D1})
    with pytest.raises(BadRequestError):
        reports.run(reporter, "volume_trend", {"granularity": "year"})
    with pytest.raises(BadRequestError):
        reports.run(reporter, "peak_hours", {"start": "not-a-date"})
    with pytest.raises(NotFoundError):
        reports.run(reporter, "no_such_report", {})


def test_unbuilt_reports_are_not_in_catalogue(reporter):
    keys = {c["key"] for c in reports.catalogue(reporter)}
    assert keys == {"daily_summary", "volume_trend", "peak_hours", "frequent_visitors",
                    "denial_stats", "sla_compliance", "audit_trail", "zone_access",
                    "blacklist_hits",
                    "event_attendance", "muster_history"}


def test_admin_scope_limited_to_own_zones(data, zone_admin):
    daily = reports.run(zone_admin, "daily_summary", {"date": D1})["summary"]
    assert daily == {"registered": 4, "approved": 3, "rejected": 0, "expired": 0,
                     "completed": 0, "check_ins": 4, "check_outs": 3, "denials": 2}
    za = reports.run(zone_admin, "zone_access", TWO_DAYS)
    assert [(r["zone"], r["allowed"], r["denied"], r["violations"]) for r in za["rows"]] == [
        ("Z1", 4, 1, 1)]
    bl = reports.run(zone_admin, "blacklist_hits", TWO_DAYS)
    assert bl["summary"] == {"total_hits": 1}     # only the Z1 gate hit
    # a zone outside the scope looks like a missing zone, not a forbidden one
    with pytest.raises(NotFoundError):
        reports.run(zone_admin, "daily_summary", {"date": D1, "zone": data.z2.pk})
    assert reports.run(zone_admin, "daily_summary",
                       {"date": D1, "zone": data.z1.pk})["summary"]["registered"] == 4


def test_campus_admin_and_zone_filter(data, reporter):
    f.make_role_assignment(user_id=reporter.user_id, role="admin", scope_type="campus")
    assert reports.run(reporter, "daily_summary", {"date": D1})["summary"]["registered"] == 7
    z2 = reports.run(reporter, "daily_summary", {"date": D1, "zone": data.z2.pk})
    assert z2["summary"]["registered"] == 3        # r3, r4, r5


def test_gate_scoped_admin_resolves_to_gate_zone(data):
    f.make_role_assignment(user_id=4010, role="admin", scope_type="gate",
                           scope_id=data.ga.pk)
    actor = f.make_actor(permissions=["vms.report.view"], user_id=4010)
    assert reports.zone_scope(actor) == frozenset({data.z1.pk})


def test_missing_permission(data):
    nobody = f.make_actor(permissions=[], user_id=4999)
    with pytest.raises(PermissionDeniedError):
        reports.run(nobody, "daily_summary", {})
    with pytest.raises(PermissionDeniedError):
        reports.export(f.make_actor(permissions=["vms.report.view"]), "daily_summary", {})


def test_event_attendance_report_exact_numbers(reporter):
    now = timezone.now()
    ev = f.make_event_batch(valid_from=now - timedelta(hours=2),
                            valid_until=now + timedelta(hours=1))
    p1, p2 = f.make_visit_pass(event=ev), f.make_visit_pass(event=ev)
    f.make_event_attendee(batch=ev, visit_pass=p1)
    f.make_event_attendee(batch=ev, visit_pass=p2)
    f.make_event_attendee(batch=ev)
    f.make_visit_log(visit_pass=p1, event="check_in")
    f.make_visit_log(visit_pass=p2, event="check_in")
    f.make_visit_log(visit_pass=p2, event="check_out")
    res = reports.run(reporter, "event_attendance", {"event_id": ev.pk})
    assert res["summary"]["invited"] == 3
    assert res["summary"]["passes_issued"] == 2
    assert res["summary"]["checked_in"] == 2
    assert res["summary"]["current_inside"] == 1
    assert sum(r["check_ins"] for r in res["rows"]) == 2
    assert sum(r["check_outs"] for r in res["rows"]) == 1
    with pytest.raises(BadRequestError):
        reports.run(reporter, "event_attendance", {})
    with pytest.raises(NotFoundError):
        reports.run(reporter, "event_attendance", {"event_id": 999999})


def test_muster_history_report_exact_numbers(reporter):
    now = timezone.now()
    f.make_emergency_muster(
        status="closed", closed_at=now,
        summary={"totals": {"total": 4, "accounted": 3, "evacuated": 0, "unaccounted": 1}})
    m = f.make_emergency_muster(
        status="closed", closed_at=now,
        summary={"totals": {"total": 2, "accounted": 1, "evacuated": 1, "unaccounted": 0}})
    type(m).objects.filter(pk=m.pk).update(triggered_at=now - timedelta(seconds=90))
    res = reports.run(reporter, "muster_history", {})
    assert res["summary"] == {"musters": 2, "total": 6, "accounted": 4,
                              "accounted_ratio": 0.667}
    by_id = {r["id"]: r for r in res["rows"]}
    assert by_id[m.pk]["accounted_ratio"] == 0.5
    assert by_id[m.pk]["duration_seconds"] == 90
