"""Endpoint auth matrix and shapes for monitor/* and muster/*."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.services import muster
from modules.vms.tests import factories as f
from modules.vms.tests.f_monitor.conftest import (
    ADMIN,
    ADMIN_PERMS,
    SEC,
    SEC_PERMS,
    put_on_site,
    zone_event,
)

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"

ENDPOINTS = [
    ("get", "monitor/dashboard", "vms.monitor.view"),
    ("get", "monitor/on-site", "vms.monitor.view"),
    ("get", "monitor/movements?pass_id=1", "vms.monitor.view"),
    ("get", "monitor/out-of-bounds", "vms.monitor.view"),
    ("post", "muster", "vms.muster.trigger"),
    ("get", "muster/current", "vms.monitor.view"),
    ("get", "muster/1", "vms.monitor.view"),
    ("get", "muster/1/roster", "vms.monitor.view"),
    ("post", "muster/1/roll-call", "vms.muster.rollcall"),
    ("post", "muster/1/roll-call/bulk", "vms.muster.rollcall"),
    ("post", "muster/1/reconcile", "vms.muster.rollcall"),
    ("post", "muster/1/close", "vms.muster.trigger"),
    ("get", "muster/1/report", "vms.monitor.view"),
    ("get", "muster/1/report.csv", "vms.report.export"),
]


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_anonymous_is_401(api_as, method, path, perm):
    assert getattr(api_as(anonymous=True), method)(BASE + path).status_code == 401


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_wrong_permission_is_403(api_as, method, path, perm):
    r = getattr(api_as(permissions=["vms.report.view"]), method)(BASE + path)
    assert r.status_code == 403


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_permission_without_role_is_403(api_as, method, path, perm):
    """Holding the IAM permission is not enough: the time-bound role decides (BR-181)."""
    mark = {"pass_id": 1, "status": "accounted"}
    payload = {"muster/1/roll-call": mark, "muster/1/roll-call/bulk": {"marks": [mark]},
               "muster/1/reconcile": {"entries": [{**mark, "marked_at": "2026-01-01T00:00:00Z"}]}}
    r = getattr(api_as(user_id=8123, permissions=[perm]), method)(
        BASE + path, payload.get(path, {}), format="json")
    assert r.status_code == 403


def test_unknown_muster_is_404(api_as, security):
    client = api_as(user_id=SEC, permissions=SEC_PERMS)
    for path in ("muster/9999", "muster/9999/roster", "muster/9999/report"):
        assert client.get(BASE + path).status_code == 404
    assert client.post(BASE + "muster/9999/roll-call", {"pass_id": 1, "status": "accounted"},
                       format="json").status_code == 404
    assert client.post(BASE + "muster/9999/close", {}, format="json").status_code == 404


def test_monitor_endpoints_shapes(api_as, security, zone):
    vp = put_on_site(zone)
    zone_event(vp, zone, "zone_denied")
    client = api_as(user_id=SEC, permissions=SEC_PERMS)
    d = client.get(BASE + "monitor/dashboard").json()
    assert d["on_site"] == 1 and d["recent_denials"]
    rows = client.get(BASE + "monitor/on-site").json()
    assert rows["count"] == 1 and rows["results"][0]["zone_name"] == zone.name
    mv = client.get(BASE + f"monitor/movements?pass_id={vp.pk}").json()["results"]
    assert [m["event"] for m in mv] == ["check_in", "zone_denied"]
    assert client.get(BASE + "monitor/movements").status_code == 400
    assert client.get(BASE + "monitor/movements?pass_id=x").status_code == 400
    assert client.get(BASE + "monitor/movements?pass_id=1&since=nope").status_code == 400
    assert client.get(BASE + "monitor/out-of-bounds").json()["count"] == 1


def test_scoped_guard_cannot_filter_other_zone(api_as):
    mine, other = f.make_zone(), f.make_zone()
    f.make_role_assignment(user_id=3060, role="security", scope_type="zone", scope_id=mine.pk)
    client = api_as(user_id=3060, permissions=SEC_PERMS)
    assert client.get(BASE + f"monitor/on-site?zone_id={other.pk}").status_code == 403
    assert client.get(BASE + f"monitor/on-site?zone_id={mine.pk}").status_code == 200


def test_muster_endpoints_flow(api_as, security, admin, zone):
    a, b = put_on_site(zone), put_on_site(zone)
    sec = api_as(user_id=SEC, permissions=SEC_PERMS)
    assert sec.get(BASE + "muster/current").json() == {"muster": None}
    r = sec.post(BASE + "muster", {"reason": "drill"}, format="json")
    assert r.status_code == 201
    body = r.json()
    mid = body["id"]
    assert body["counts"]["unaccounted"] == 2 and body["trigger_role"] == "security"
    assert sec.post(BASE + "muster", {}, format="json").status_code == 409
    assert sec.get(BASE + "muster/current").json()["muster"]["id"] == mid
    roster = sec.get(BASE + f"muster/{mid}/roster?status=unaccounted").json()
    assert roster["count"] == 2 and roster["results"][0]["visitor_phone"]
    assert sec.get(BASE + f"muster/{mid}/roster?status=zzz").status_code == 400
    rc = sec.post(BASE + f"muster/{mid}/roll-call", {"pass_id": a.pk, "status": "accounted"},
                  format="json")
    assert rc.status_code == 200 and rc.json()["remaining"] == 1
    assert sec.post(BASE + f"muster/{mid}/roll-call", {"pass_id": a.pk, "status": "bogus"},
                    format="json").status_code == 400
    bulk = sec.post(BASE + f"muster/{mid}/roll-call/bulk",
                    {"marks": [{"pass_id": b.pk, "status": "evacuated"}]}, format="json")
    assert bulk.json()["remaining"] == 0
    rec = sec.post(BASE + f"muster/{mid}/reconcile", {"entries": [
        {"pass_id": a.pk, "status": "accounted",
         "marked_at": (timezone.now() - timedelta(minutes=1)).isoformat()}]}, format="json")
    assert rec.status_code == 200 and rec.json()["unchanged"] == [a.pk]
    closed = sec.post(BASE + f"muster/{mid}/close", {"note": "all clear"}, format="json")
    assert closed.status_code == 200 and closed.json()["summary"]["totals"]["total"] == 2
    rep = sec.get(BASE + f"muster/{mid}/report").json()
    assert rep["status"] == "closed" and rep["totals"]["evacuated"] == 1
    assert sec.get(BASE + f"muster/{mid}/report.csv").status_code == 403   # no export permission
    csv_resp = api_as(user_id=ADMIN, permissions=ADMIN_PERMS).get(
        BASE + f"muster/{mid}/report.csv")
    assert csv_resp.status_code == 200 and csv_resp["Content-Type"].startswith("text/csv")
    assert b"visitor_name" in csv_resp.content


def test_close_unaccounted_is_409(api_as, security, zone):
    put_on_site(zone)
    sec = api_as(user_id=SEC, permissions=SEC_PERMS)
    mid = sec.post(BASE + "muster", {}, format="json").json()["id"]
    r = sec.post(BASE + f"muster/{mid}/close", {}, format="json")
    assert r.status_code == 409 and r.json()["error"]["code"] == "unaccounted_remain"
    forced = sec.post(BASE + f"muster/{mid}/close", {"force": True, "note": "x"}, format="json")
    assert forced.status_code == 200


def test_trigger_with_gate_only_permission_is_403(api_as, security):
    client = api_as(user_id=SEC, permissions=["vms.gate.operate"])
    assert client.post(BASE + "muster", {}, format="json").status_code == 403
    assert not muster.current()
