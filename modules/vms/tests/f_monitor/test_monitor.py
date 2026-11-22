"""Live monitoring: dashboard, on-site list, movements, geofence (CFR-017, UC-022)."""
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.vms.models import Alert, RoleAssignment
from modules.vms.services import monitor
from modules.vms.tests import factories as f
from modules.vms.tests.f_monitor.conftest import (
    HOST,
    MONITOR_PERMS,
    check_out,
    put_on_site,
    zone_event,
)

pytestmark = pytest.mark.django_db


def test_dashboard_counts(security):
    z1, z2 = f.make_zone(), f.make_zone()
    put_on_site(z1)
    put_on_site(z1)
    put_on_site(z2, host=2002)
    gone = put_on_site(z1)
    check_out(gone)
    overstayer = put_on_site(z2, valid_until=timezone.now() - timedelta(minutes=5))
    f.make_alert(kind="zone_violation", detail={"zone_id": z1.pk})
    f.make_alert(kind="muster", status="handled")
    d = monitor.dashboard(actor=security)
    assert d["on_site"] == 4
    assert {z["zone_id"]: z["count"] for z in d["by_zone"]} == {z1.pk: 2, z2.pk: 2}
    assert d["by_department"] == [{"department": "Physics", "count": 4}]
    assert d["open_alerts"]["total"] == 1
    assert d["overstays"]["count"] == 1
    assert d["overstays"]["passes"][0]["pass_id"] == overstayer.pk


def test_dashboard_lists_recent_denials(security):
    z = f.make_zone()
    vp = put_on_site(z)
    zone_event(vp, z, "zone_denied", "zone_not_permitted")
    d = monitor.dashboard(actor=security)
    assert d["recent_denials"][0]["event"] == "zone_denied"


def test_dashboard_scoped_to_role():
    za, zb = f.make_zone(), f.make_zone()
    put_on_site(za)
    put_on_site(zb)
    put_on_site(zb)
    f.make_role_assignment(user_id=3050, role="security",
                           scope_type=RoleAssignment.ScopeType.ZONE, scope_id=zb.pk)
    f.make_alert(kind="zone_violation", detail={"zone_id": za.pk})
    f.make_alert(kind="zone_violation", detail={"zone_id": zb.pk})
    guard = f.make_actor(permissions=MONITOR_PERMS, user_id=3050)
    d = monitor.dashboard(actor=guard)
    assert d["on_site"] == 2
    assert [z["zone_id"] for z in d["by_zone"]] == [zb.pk]
    assert d["open_alerts"]["total"] == 1
    assert len(monitor.on_site(actor=guard)) == 2
    with pytest.raises(PermissionDeniedError):
        monitor.dashboard(actor=guard, zone_id=za.pk)


def test_monitor_requires_role_and_permission():
    no_role = f.make_actor(permissions=MONITOR_PERMS, user_id=9001)
    with pytest.raises(PermissionDeniedError):
        monitor.dashboard(actor=no_role)
    f.make_role_assignment(user_id=9002, role="security")
    no_perm = f.make_actor(permissions=(), user_id=9002)
    with pytest.raises(PermissionDeniedError):
        monitor.on_site(actor=no_perm)


def test_on_site_row_shape_and_terminated_listed(security, zone):
    vp = put_on_site(zone)
    vp.terminated_at = timezone.now()
    vp.save(update_fields=["terminated_at"])
    [row] = monitor.on_site(actor=security)
    assert row["terminated"] is True
    assert row["zone_name"] == zone.name
    assert row["host_name"] == f"Host {HOST}"
    assert row["last_seen_at"] is not None


def test_on_site_zone_filter(security):
    za, zb = f.make_zone(), f.make_zone()
    put_on_site(za)
    put_on_site(zb)
    assert len(monitor.on_site(actor=security, zone_id=za.pk)) == 1


def test_movements_ordered_for_pass(security):
    za, zb = f.make_zone(), f.make_zone()
    vp = put_on_site(za)
    zone_event(vp, zb)
    zone_event(vp, za, "zone_denied")
    f.make_visit_log(visit_pass=vp, event="override")
    events = [m.event for m in monitor.movements(actor=security, pass_id=vp.pk)]
    assert events == ["check_in", "zone_allowed", "zone_denied"]


def test_movements_since_and_zone(security):
    za, zb = f.make_zone(), f.make_zone()
    vp = put_on_site(za)
    zone_event(vp, zb)
    rows = monitor.movements(actor=security, zone_id=zb.pk)
    assert [r.zone_id for r in rows] == [zb.pk]
    future = timezone.now() + timedelta(minutes=1)
    assert monitor.movements(actor=security, zone_id=zb.pk, since=future) == []


def test_movements_needs_a_filter(security):
    with pytest.raises(BadRequestError):
        monitor.movements(actor=security)


def test_out_of_bounds_denial_and_restricted(security):
    open_z = f.make_zone()
    lab = f.make_zone(is_restricted=True)
    denied = put_on_site(open_z)
    zone_event(denied, lab, "zone_denied")
    sneaky = put_on_site(open_z)
    zone_event(sneaky, lab)                       # allowed but not in allowed_zones
    permitted = put_on_site(open_z)
    permitted.allowed_zones.add(lab)
    zone_event(permitted, lab)
    elevated = put_on_site(open_z)
    f.make_zone_elevation(visit_pass=elevated, zone=lab,
                          starts_at=timezone.now() - timedelta(minutes=1),
                          ends_at=timezone.now() + timedelta(hours=1), granted_by_user_id=1)
    zone_event(elevated, lab)
    vip = put_on_site(open_z)
    zone_event(vip, lab, reason="vip_override")
    recovered = put_on_site(open_z)
    zone_event(recovered, lab, "zone_denied")
    zone_event(recovered, open_z)                 # moved back: latest event is fine
    rows = {r["pass_id"]: r["reason"] for r in monitor.out_of_bounds(actor=security)}
    assert rows == {denied.pk: "zone_denied", sneaky.pk: "restricted_without_permission"}


def test_out_of_bounds_ignores_checked_out(security):
    lab = f.make_zone(is_restricted=True)
    vp = put_on_site(lab)
    zone_event(vp, lab, "zone_denied")
    check_out(vp)
    assert monitor.out_of_bounds(actor=security) == []


# --- query budgets -----------------------------------------------------------------------

def test_on_site_500_visitors_query_budget(security):
    zones = [f.make_zone() for _ in range(5)]
    now = timezone.now()
    from modules.vms.models import VisitLog, Visitor, VisitPass, VisitRequest
    visitors = Visitor.objects.bulk_create(
        [Visitor(full_name=f"V{i}", phone=f"9{i:09d}", email=f"v{i}@x.org",
                 id_doc_type="passport", id_doc_number=f"ID{i:07d}") for i in range(500)])
    reqs = VisitRequest.objects.bulk_create(
        [VisitRequest(visitor=v, host_user_id=2000 + i % 7, purpose="x", status="approved",
                      scheduled_start=now, scheduled_end=now + timedelta(hours=2))
         for i, v in enumerate(visitors)])
    passes = VisitPass.objects.bulk_create(
        [VisitPass(visit_request=r, pass_type="PRE_REGISTERED", qr_token=f"qr{i:06d}",
                   otp="123456", valid_from=now - timedelta(hours=1),
                   valid_until=now + timedelta(hours=2), issued_by_user_id=1)
         for i, r in enumerate(reqs)])
    VisitLog.objects.bulk_create(
        [VisitLog(visit_pass=p, event="check_in", zone=zones[i % 5], logged_by_user_id=1)
         for i, p in enumerate(passes)])
    with CaptureQueriesContext(connection) as ctx:
        rows = monitor.on_site(actor=security)
    assert len(rows) == 500
    assert len(ctx) <= 5, [q["sql"][:80] for q in ctx]
    with CaptureQueriesContext(connection) as ctx:
        d = monitor.dashboard(actor=security)
    assert d["on_site"] == 500
    assert len(ctx) <= 6, [q["sql"][:80] for q in ctx]
    with CaptureQueriesContext(connection) as ctx:
        monitor.out_of_bounds(actor=security)
    assert len(ctx) <= 6


def test_alert_model_unchanged_by_dashboard(security):
    f.make_alert(kind="muster")
    monitor.dashboard(actor=security)
    assert Alert.objects.count() == 1
