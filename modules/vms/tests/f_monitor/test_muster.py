"""Emergency muster service: trigger, snapshot, roll-call, reconcile, close, report."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import (
    Alert,
    AuditLog,
    EmergencyMuster,
    MusterEntry,
    Notification,
    RoleAssignment,
)
from modules.vms.services import muster
from modules.vms.tests import factories as f
from modules.vms.tests.f_monitor.conftest import (
    SEC_PERMS,
    check_out,
    put_on_site,
    zone_event,
)

pytestmark = pytest.mark.django_db


def test_br_130_visitor_cannot_trigger_muster():
    visitor = f.make_actor("visitor", permissions=(), user_id=9100)
    with pytest.raises(PermissionDeniedError):
        muster.trigger(actor=visitor)


def test_br_130_permission_without_active_role_is_denied():
    actor = f.make_actor(permissions=SEC_PERMS, user_id=9101)
    with pytest.raises(PermissionDeniedError):
        muster.trigger(actor=actor)
    now = timezone.now()
    f.make_role_assignment(user_id=9101, role="security", starts_at=now - timedelta(days=2),
                           ends_at=now - timedelta(days=1))
    with pytest.raises(PermissionDeniedError):
        muster.trigger(actor=actor)           # expired assignment (BR-181)
    assert not EmergencyMuster.objects.exists()


def test_security_and_admin_can_trigger(security, admin):
    m1 = muster.trigger(actor=security, reason="drill")
    assert (m1.trigger_role, m1.status) == ("security", "open")
    muster.close(actor=security, muster_id=m1.pk)
    m2 = muster.trigger(actor=admin)
    assert m2.trigger_role == "admin"


def test_zone_scoped_security_can_trigger():
    z = f.make_zone()
    f.make_role_assignment(user_id=9102, role="security",
                           scope_type=RoleAssignment.ScopeType.ZONE, scope_id=z.pk)
    m = muster.trigger(actor=f.make_actor(permissions=SEC_PERMS, user_id=9102))
    assert m.trigger_role == "security"


def test_second_open_muster_conflict(security, admin):
    muster.trigger(actor=security)
    with pytest.raises(ConflictError) as e:
        muster.trigger(actor=admin)
    assert e.value.code == "muster_already_open"
    assert EmergencyMuster.objects.count() == 1


def test_snapshot_contains_only_on_site_visitors(security, zone):
    inside = put_on_site(zone)
    moved_out = put_on_site(zone)
    check_out(moved_out)
    never_in = f.make_visit_pass()                  # approved, no check-in
    terminated = put_on_site(zone)
    terminated.terminated_at = timezone.now()
    terminated.save(update_fields=["terminated_at"])
    m = muster.trigger(actor=security)
    ids = set(m.entries.values_list("visit_pass_id", flat=True))
    assert ids == {inside.pk, terminated.pk}        # terminated stays until exit
    assert never_in.pk not in ids and moved_out.pk not in ids
    assert set(m.entries.values_list("status", flat=True)) == {"unaccounted"}


def test_snapshot_records_last_zone_time_and_host(security):
    za, zb = f.make_zone(), f.make_zone()
    vp = put_on_site(za, host=2077)
    zone_event(vp, zb)
    m = muster.trigger(actor=security)
    entry = m.entries.get()
    assert entry.last_zone_id == zb.pk and entry.last_seen_at is not None
    [row] = muster.roster_entries(actor=security, muster_id=m.pk)
    assert row["visitor_name"] == vp.visit_request.visitor.full_name
    assert row["visitor_phone"] and row["visitor_email"]
    assert row["host_user_id"] == 2077 and row["host_name"] == "Host 2077"
    assert row["last_zone_name"] == zb.name


def test_muster_alert_enqueued_per_visitor(security, zone):
    f.make_integration_setting(key="assembly_instructions",
                               value={"text": "Gather at the main lawn."})
    vps = [put_on_site(zone) for _ in range(3)]
    f.make_role_assignment(user_id=4999, role="admin")
    m = muster.trigger(actor=security)
    visitor_rows = Notification.objects.filter(topic="muster.alert",
                                               recipient_visitor__isnull=False)
    assert visitor_rows.count() == 6                 # 3 visitors x (sms, inapp)
    assert {n.recipient_visitor_id for n in visitor_rows} == {
        vp.visit_request.visitor_id for vp in vps}
    assert all("main lawn" in n.body for n in visitor_rows)
    assert set(visitor_rows.values_list("channel", flat=True)) == {"sms", "inapp"}
    staff = Notification.objects.filter(topic="muster.alert", recipient_user_id__isnull=False)
    assert {n.recipient_user_id for n in staff} >= {4999, 3001}
    assert Alert.objects.filter(kind="muster", ref_id=m.pk).count() == 1
    assert AuditLog.objects.filter(action="vms.muster.triggered").count() == 1


def test_muster_alert_without_instructions_setting(security, zone):
    put_on_site(zone)
    muster.trigger(actor=security)
    n = Notification.objects.filter(topic="muster.alert", recipient_visitor__isnull=False).first()
    assert "Assembly instructions" not in n.body


def test_roll_call_idempotent(security, zone):
    a, b = put_on_site(zone), put_on_site(zone)
    m = muster.trigger(actor=security)
    r1 = muster.roll_call(actor=security, muster_id=m.pk, pass_id=a.pk, status="accounted")
    assert (r1["outcome"], r1["remaining"]) == ("applied", 1)
    first = MusterEntry.objects.get(muster=m, visit_pass=a)
    stamp = first.marked_at
    r2 = muster.roll_call(actor=security, muster_id=m.pk, pass_id=a.pk, status="accounted")
    assert (r2["outcome"], r2["remaining"]) == ("unchanged", 1)
    first.refresh_from_db()
    assert first.marked_at == stamp and first.marked_by_user_id == 3001
    assert AuditLog.objects.filter(action="vms.muster.rollcall").count() == 1
    r3 = muster.roll_call(actor=security, muster_id=m.pk, pass_id=b.pk, status="evacuated")
    assert r3["remaining"] == 0


def test_roll_call_different_status_is_conflict(security, zone):
    a = put_on_site(zone)
    m = muster.trigger(actor=security)
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=a.pk, status="accounted")
    with pytest.raises(ConflictError) as e:
        muster.roll_call(actor=security, muster_id=m.pk, pass_id=a.pk, status="evacuated")
    assert e.value.code == "already_marked"


def test_roll_call_rejects_bad_input(security, zone):
    a = put_on_site(zone)
    m = muster.trigger(actor=security)
    with pytest.raises(BadRequestError):
        muster.roll_call(actor=security, muster_id=m.pk, pass_id=a.pk, status="unaccounted")
    with pytest.raises(NotFoundError):
        muster.roll_call(actor=security, muster_id=m.pk, pass_id=999999, status="accounted")
    with pytest.raises(NotFoundError):
        muster.roll_call(actor=security, muster_id=999999, pass_id=a.pk, status="accounted")


def test_roll_call_needs_permission_and_role(security, zone):
    a = put_on_site(zone)
    m = muster.trigger(actor=security)
    no_perm = f.make_actor(permissions=("vms.monitor.view",), user_id=3001)
    with pytest.raises(PermissionDeniedError):
        muster.roll_call(actor=no_perm, muster_id=m.pk, pass_id=a.pk, status="accounted")
    no_role = f.make_actor(permissions=SEC_PERMS, user_id=9200)
    with pytest.raises(PermissionDeniedError):
        muster.roll_call(actor=no_role, muster_id=m.pk, pass_id=a.pk, status="accounted")


def test_bulk_roll_call(security, zone):
    vps = [put_on_site(zone) for _ in range(3)]
    m = muster.trigger(actor=security)
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=vps[0].pk, status="evacuated")
    res = muster.bulk_roll_call(actor=security, muster_id=m.pk, marks=[
        {"pass_id": vps[0].pk, "status": "evacuated"},     # unchanged
        {"pass_id": vps[1].pk, "status": "accounted"},     # applied
        {"pass_id": vps[1].pk, "status": "evacuated"},     # conflicts with the line above
        {"pass_id": 424242, "status": "accounted"}])       # not on the list
    assert res["applied"] == [vps[1].pk] and res["unchanged"] == [vps[0].pk]
    assert res["not_found"] == [424242]
    assert res["conflicts"][0]["current"] == "accounted"
    assert res["remaining"] == 1


def test_reconcile_cached_marks(security, zone):
    a, b, c, d = (put_on_site(zone) for _ in range(4))
    m = muster.trigger(actor=security)
    now = timezone.now()
    EmergencyMuster.objects.filter(pk=m.pk).update(triggered_at=now - timedelta(hours=1))
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=b.pk, status="accounted")  # live
    res = muster.reconcile_cached(actor=security, muster_id=m.pk, entries=[
        {"pass_id": c.pk, "status": "evacuated", "marked_at": now - timedelta(minutes=1)},
        {"pass_id": a.pk, "status": "accounted", "marked_at": now - timedelta(minutes=5)},
        {"pass_id": b.pk, "status": "evacuated", "marked_at": now - timedelta(minutes=3)},
        {"pass_id": 777777, "status": "accounted", "marked_at": now}])
    assert res["applied"] == [a.pk, c.pk]            # applied in marked_at order
    [clash] = res["conflicts"]
    assert clash["pass_id"] == b.pk and clash["kept_status"] == "accounted"
    assert clash["resolution"] == "existing_mark_kept"
    assert res["not_found"] == [777777] and res["remaining"] == 1
    ea = MusterEntry.objects.get(muster=m, visit_pass=a)
    assert abs((ea.marked_at - (now - timedelta(minutes=5))).total_seconds()) < 1
    assert MusterEntry.objects.get(muster=m, visit_pass=b).status == "accounted"
    assert MusterEntry.objects.get(muster=m, visit_pass=d).status == "unaccounted"
    # replaying the same cached list changes nothing
    again = muster.reconcile_cached(actor=security, muster_id=m.pk, entries=[
        {"pass_id": a.pk, "status": "accounted", "marked_at": now - timedelta(minutes=5)}])
    assert again["unchanged"] == [a.pk] and again["applied"] == []


def test_reconcile_clamps_future_and_pre_trigger_times(security, zone):
    a, b = put_on_site(zone), put_on_site(zone)
    m = muster.trigger(actor=security)
    now = timezone.now()
    muster.reconcile_cached(actor=security, muster_id=m.pk, entries=[
        {"pass_id": a.pk, "status": "accounted", "marked_at": now + timedelta(days=1)},
        {"pass_id": b.pk, "status": "accounted", "marked_at": now - timedelta(days=1)}])
    ea = MusterEntry.objects.get(muster=m, visit_pass=a)
    eb = MusterEntry.objects.get(muster=m, visit_pass=b)
    assert ea.marked_at <= timezone.now()
    assert eb.marked_at == m.triggered_at


def test_close_requires_all_accounted_or_force(security, zone):
    a, b = put_on_site(zone), put_on_site(zone)
    m = muster.trigger(actor=security)
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=a.pk, status="accounted")
    with pytest.raises(ConflictError) as e:
        muster.close(actor=security, muster_id=m.pk)
    assert e.value.code == "unaccounted_remain"
    with pytest.raises(BadRequestError) as e2:
        muster.close(actor=security, muster_id=m.pk, force=True)      # note missing
    assert e2.value.code == "note_required"
    closed = muster.close(actor=security, muster_id=m.pk, force=True, note="Left campus")
    assert closed.status == "closed" and closed.closed_at
    assert closed.summary["forced"] is True
    assert [u["pass_id"] for u in closed.summary["unaccounted"]] == [b.pk]
    with pytest.raises(ConflictError):
        muster.close(actor=security, muster_id=m.pk)                  # already closed
    with pytest.raises(ConflictError) as e3:
        muster.roll_call(actor=security, muster_id=m.pk, pass_id=b.pk, status="accounted")
    assert e3.value.code == "muster_closed"


def test_close_with_empty_roster_and_new_muster_after(security):
    m = muster.trigger(actor=security)
    muster.close(actor=security, muster_id=m.pk)
    assert muster.trigger(actor=security).pk != m.pk


def test_report_totals_match_entries(security, admin):
    za, zb = f.make_zone(), f.make_zone()
    vps = [put_on_site(za), put_on_site(za), put_on_site(zb), put_on_site(zb)]
    m = muster.trigger(actor=admin, reason="fire drill")
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=vps[0].pk, status="accounted")
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=vps[1].pk, status="evacuated")
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=vps[2].pk, status="accounted")
    live = muster.report(actor=security, muster_id=m.pk)
    assert live["provisional"] is True and live["totals"]["unaccounted"] == 1
    muster.close(actor=security, muster_id=m.pk, force=True, note="one missing")
    rep = muster.report(actor=security, muster_id=m.pk)
    counts = {s: MusterEntry.objects.filter(muster=m, status=s).count()
              for s in ("accounted", "evacuated", "unaccounted")}
    assert rep["provisional"] is False
    assert rep["totals"] == {"total": 4, **counts}
    assert sum(z["total"] for z in rep["per_zone"]) == 4
    assert {z["zone_id"]: z["accounted"] for z in rep["per_zone"]} == {za.pk: 1, zb.pk: 1}
    assert rep["responder"]["trigger_role"] == "admin"
    assert rep["responder"]["marks_by_user"] == {"3001": 3}
    assert rep["timings"]["duration_seconds"] >= 0 and rep["reason"] == "fire drill"
    report_mail = Notification.objects.filter(topic="muster.report")
    host_ids = {vps[3].visit_request.host_user_id}       # the one unaccounted visitor
    assert {n.recipient_user_id for n in report_mail} == {4001} | host_ids


def test_report_csv(security, admin, zone):
    vp = put_on_site(zone)
    vp.visit_request.visitor.full_name = "=cmd()"
    vp.visit_request.visitor.save()
    m = muster.trigger(actor=security)
    name, text = muster.report_csv(actor=admin, muster_id=m.pk)
    assert name == f"muster-{m.pk}.csv"
    lines = text.strip().splitlines()
    assert len(lines) == 2 and "'=cmd()" in lines[1]
    with pytest.raises(PermissionDeniedError):
        muster.report_csv(actor=security, muster_id=m.pk)             # no export permission


def test_stale_check_alerts_once(security, admin, zone):
    m = muster.trigger(actor=security)
    assert muster.stale_check() == 0
    later = timezone.now() + timedelta(hours=7)
    assert muster.stale_check(now=later) == 1
    assert muster.stale_check(now=later) == 0
    assert Alert.objects.filter(ref_type="emergency_muster_stale", ref_id=m.pk).count() == 1
    muster.close(actor=security, muster_id=m.pk)
    assert muster.stale_check(now=later + timedelta(hours=1)) == 0


def test_stale_job_task_registered():
    from modules.vms.jobs import muster as job
    from modules.vms.schedule import BEAT_SCHEDULE
    assert "vms-muster-stale-check" in BEAT_SCHEDULE
    assert job.muster_stale_check() == 0


def test_trigger_with_50_on_site_then_full_roll_call_and_report(security, zone):
    vps = [put_on_site(zone) for _ in range(50)]
    m = muster.trigger(actor=security)
    assert m.entries.count() == 50
    res = muster.bulk_roll_call(actor=security, muster_id=m.pk, marks=[
        {"pass_id": vp.pk, "status": "accounted" if i % 2 else "evacuated"}
        for i, vp in enumerate(vps)])
    assert len(res["applied"]) == 50 and res["remaining"] == 0
    muster.close(actor=security, muster_id=m.pk)
    rep = muster.report(actor=security, muster_id=m.pk)
    assert rep["totals"] == {"total": 50, "accounted": 25, "evacuated": 25, "unaccounted": 0}
    assert rep["unaccounted"] == []
