"""Ops gaps: emergency muster and live monitor."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.vms.models import Alert, AuditLog, Notification, VisitLog
from modules.vms.services import monitor, muster
from modules.vms.tests import factories as f
from modules.vms.tests.gaps.ops.conftest import ADMIN, SEC, SEC_PERMS, put_on_site

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("policy")]

BASE = "/api/v1/vms/"


def test_uc_026_muster_trigger_audited_with_reason(security, zone):
    """VMS-UC-026: the trigger is audited with its reason and trigger role."""
    put_on_site(zone)
    m = muster.trigger(actor=security, reason="  Fire drill  ")
    log = AuditLog.objects.get(action="vms.muster.triggered")
    assert log.entity_id == str(m.pk) and log.actor_user_id == SEC
    assert log.detail["reason"] == "Fire drill" and log.detail["on_site"] == 1
    assert m.reason == "Fire drill"


def test_uc_027_roll_call_on_closed_muster_conflict(security, zone):
    """VMS-UC-027: marking against a closed muster is a 409 muster_closed."""
    vp = put_on_site(zone)
    m = muster.trigger(actor=security)
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=vp.pk, status="accounted")
    muster.close(actor=security, muster_id=m.pk)
    with pytest.raises(ConflictError) as e:
        muster.roll_call(actor=security, muster_id=m.pk, pass_id=vp.pk, status="accounted")
    assert e.value.code == "muster_closed"


def test_uc_027_roll_call_for_visitor_not_in_snapshot_404(security, zone):
    """VMS-UC-027: a pass that was not on site at trigger time is not on the list."""
    put_on_site(zone)
    m = muster.trigger(actor=security)
    stranger = put_on_site(zone)
    with pytest.raises(NotFoundError):
        muster.roll_call(actor=security, muster_id=m.pk, pass_id=stranger.pk,
                         status="accounted")


def test_uc_032_security_muster_notifies_admins(security, zone):
    """VMS-UC-032: admins (and security) holding roles get the staff alert."""
    f.make_role_assignment(user_id=ADMIN, role="admin")
    f.make_role_assignment(user_id=4002, role="admin", revoked_at=timezone.now())
    put_on_site(zone)
    muster.trigger(actor=security)
    staff = Notification.objects.filter(topic="muster.alert", recipient_user_id__isnull=False)
    assert {n.recipient_user_id for n in staff} == {ADMIN, SEC}
    assert "security" in staff.first().body


def test_bw_19_visitor_checking_out_during_muster_still_in_snapshot(security, zone):
    """BW-VMS-19: the snapshot is immutable; a later check-out does not remove the entry."""
    vp = put_on_site(zone)
    m = muster.trigger(actor=security)
    f.make_visit_log(visit_pass=vp, event=VisitLog.Event.CHECK_OUT)
    assert m.entries.filter(visit_pass=vp, status="unaccounted").count() == 1
    r = muster.roll_call(actor=security, muster_id=m.pk, pass_id=vp.pk, status="evacuated")
    assert r["remaining"] == 0
    assert m.entries.count() == 1


def test_bw_20_completed_muster_notifies_host_of_unaccounted(security, zone):
    """BW-VMS-20: closing with unaccounted visitors tells their hosts."""
    put_on_site(zone, host=2555)
    m = muster.trigger(actor=security)
    muster.close(actor=security, muster_id=m.pk, force=True, note="left campus")
    assert Notification.objects.filter(topic="muster.report", recipient_user_id=2555).exists()


def test_br_130_muster_trigger_by_host_forbidden(api_as):
    """VMS-BR-130: a host (no VMS role) cannot trigger a muster."""
    c = api_as(user_id=2001, permissions=("vms.muster.trigger",))
    assert c.post(BASE + "muster", {}, format="json").status_code == 403
    assert c.post(BASE + "muster", {}, format="json").json() is not None
    from modules.vms.models import EmergencyMuster
    assert not EmergencyMuster.objects.exists()


def test_cw_06_admin_trigger_security_roll_call_force_close_report(api_as, security, admin, zone):
    """CW-VMS-06: admin triggers, security calls the roll, admin force-closes, report."""
    a, b = put_on_site(zone), put_on_site(zone)
    admin_perms = ("vms.monitor.view", "vms.muster.trigger", "vms.muster.rollcall",
                   "vms.report.export")
    adm = api_as(user_id=ADMIN, permissions=admin_perms)
    r = adm.post(BASE + "muster", {"reason": "Alarm"}, format="json")
    assert r.status_code in (200, 201)
    mid = r.json()["id"]
    ok = api_as(user_id=SEC, permissions=SEC_PERMS).post(BASE + f"muster/{mid}/roll-call", {"pass_id": a.pk, "status": "accounted"},
                  format="json")
    assert ok.status_code == 200 and ok.json()["remaining"] == 1
    adm = api_as(user_id=ADMIN, permissions=admin_perms)      # the IAM stub is per-call
    assert adm.post(BASE + f"muster/{mid}/close", {}, format="json").status_code == 409
    forced = adm.post(BASE + f"muster/{mid}/close", {"force": True, "note": "b left"},
                      format="json")
    assert forced.status_code == 200
    rep = adm.get(BASE + f"muster/{mid}/report").json()
    assert rep["totals"] == {"total": 2, "accounted": 1, "evacuated": 0,
                                        "unaccounted": 1}
    assert rep["forced"] is True and rep["unaccounted"][0]["pass_id"] == b.pk
    assert adm.get(BASE + f"muster/{mid}/report.csv").status_code == 200


def test_uc_022_dashboard_excludes_checked_out_and_counts_zone_occupancy(security):
    """VMS-UC-022: only people still inside are counted, grouped by zone."""
    za, zb = f.make_zone(name="Lab"), f.make_zone(name="Hall")
    put_on_site(za), put_on_site(za), put_on_site(zb)
    gone = put_on_site(za)
    f.make_visit_log(visit_pass=gone, event=VisitLog.Event.CHECK_OUT)
    d = monitor.dashboard(actor=security)
    assert d["on_site"] == 3
    assert {(z["zone_name"], z["count"]) for z in d["by_zone"]} == {("Lab", 2), ("Hall", 1)}


def test_uc_022_dashboard_open_alerts_listed_by_kind(security, zone):
    """VMS-UC-022: open alerts counted by kind; resolved ones are excluded."""
    f.make_alert(kind="suspicious", severity="high")
    f.make_alert(kind="suspicious", severity="low")
    f.make_alert(kind="muster", severity="critical")
    done = f.make_alert(kind="blacklist_hit", severity="high")
    Alert.objects.filter(pk=done.pk).update(status="handled")
    alerts = monitor.dashboard(actor=security)["open_alerts"]
    assert alerts["total"] == 3
    assert alerts["by_kind"] == {"suspicious": 2, "muster": 1}


def test_uc_022_monitor_stale_visitors_alert_threshold_boundary(security):
    """VMS-UC-022: a muster open exactly six hours alerts; one second less does not."""
    m = muster.trigger(actor=security)
    at = m.triggered_at + muster.STALE_AFTER
    assert muster.stale_check(now=at - timedelta(seconds=1)) == 0
    assert muster.stale_check(now=at) == 1
    assert Alert.objects.filter(ref_type="emergency_muster_stale", ref_id=m.pk).count() == 1
