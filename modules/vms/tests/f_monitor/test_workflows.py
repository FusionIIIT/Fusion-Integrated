"""Workflow tests: BW-VMS-19 (admin-triggered) and BW-VMS-20 (security-triggered) muster.

Both: Normal Operations -> (UC-026 / UC-032) Muster Active -> (UC-027 roll-call by
Security) Muster Completed (CW-VMS-06).
"""
import pytest

from modules.vms.models import EmergencyMuster, Notification
from modules.vms.services import monitor, muster
from modules.vms.tests.f_monitor.conftest import SEC, put_on_site

pytestmark = pytest.mark.django_db


def _roll_call_all(guard, m, status="accounted"):
    for row in muster.roster_entries(actor=guard, muster_id=m.pk):
        muster.roll_call(actor=guard, muster_id=m.pk, pass_id=row["pass_id"], status=status)


def test_bw_vms_19_admin_triggered_muster(admin, security, zone):
    vps = [put_on_site(zone) for _ in range(4)]
    assert monitor.dashboard(actor=security)["on_site"] == 4      # roster available
    m = muster.trigger(actor=admin, reason="Fire alarm")           # UC-026 (admin)
    assert (m.status, m.trigger_role) == ("open", "admin")         # Muster Active
    assert Notification.objects.filter(
        topic="muster.alert", recipient_visitor__isnull=False).count() == 8
    guard_view = muster.roster_entries(actor=security, muster_id=m.pk)
    assert {r["pass_id"] for r in guard_view} == {vp.pk for vp in vps}
    _roll_call_all(security, m)                                    # UC-027 (security)
    muster.close(actor=security, muster_id=m.pk)
    m.refresh_from_db()
    assert m.status == EmergencyMuster.Status.CLOSED               # Muster Completed
    assert muster.report(actor=security, muster_id=m.pk)["totals"]["accounted"] == 4


def test_bw_vms_20_security_triggered_muster(security, admin, zone):
    vps = [put_on_site(zone) for _ in range(3)]
    m = muster.trigger(actor=security, reason="Gas leak")          # UC-032 (security)
    assert (m.status, m.trigger_role) == ("open", "security")
    assert m.triggered_by_user_id == SEC
    for vp in vps[:2]:
        muster.roll_call(actor=security, muster_id=m.pk, pass_id=vp.pk, status="evacuated")
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=vps[2].pk, status="accounted")
    closed = muster.close(actor=security, muster_id=m.pk, note="done")
    assert closed.summary["totals"] == {"total": 3, "accounted": 1, "evacuated": 2,
                                        "unaccounted": 0}
    # admins are told, and the admin sees the report
    assert Notification.objects.filter(topic="muster.report", recipient_user_id=4001).exists()
    assert muster.report(actor=admin, muster_id=m.pk)["provisional"] is False


def test_cw_vms_06_offline_roster_then_reconcile(security, zone):
    """Composite: a guard works from a cached roster offline, then reconciles."""
    from datetime import timedelta

    from django.utils import timezone
    vps = [put_on_site(zone) for _ in range(3)]
    m = muster.trigger(actor=security)
    cached = muster.roster_entries(actor=security, muster_id=m.pk)          # cached on device
    t0 = timezone.now()
    marks = [{"pass_id": r["pass_id"], "status": "accounted",
              "marked_at": t0 - timedelta(seconds=i)} for i, r in enumerate(cached)]
    muster.roll_call(actor=security, muster_id=m.pk, pass_id=vps[0].pk, status="accounted")
    res = muster.reconcile_cached(actor=security, muster_id=m.pk, entries=marks)
    assert len(res["applied"]) == 2 and len(res["unchanged"]) == 1 and res["remaining"] == 0
    muster.close(actor=security, muster_id=m.pk)
