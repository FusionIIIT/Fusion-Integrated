"""Auto check-out and expiry sweeps (UC-038; BR-101, BR-105, BR-190; D-11)."""
from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.vms.jobs import duration
from modules.vms.models import AuditLog, VisitLog
from modules.vms.schedule import BEAT_SCHEDULE
from modules.vms.services import autocheckout
from modules.vms.services import extensions as ext_svc

from .conftest import on_site_pass

pytestmark = pytest.mark.django_db
T0 = "2026-03-02 09:00:00+00:00"


def test_beat_schedule_cadence():
    assert BEAT_SCHEDULE["vms-auto-checkout-sweep"]["schedule"] == 300.0
    assert BEAT_SCHEDULE["vms-expire-unused-passes"]["schedule"] == 3600.0
    assert "vms-expire-pending" in BEAT_SCHEDULE      # lane E key still present
    assert duration.auto_checkout_sweep.name == "vms.auto_checkout_sweep"


def test_br_101_auto_checkout_at_validity_end():
    with freeze_time(T0):
        vp = on_site_pass(hours=2)
        assert autocheckout.sweep() == 0                # not yet
    with freeze_time("2026-03-02 11:00:00+00:00"):
        assert autocheckout.sweep() == 1
    vp.refresh_from_db()
    vp.visit_request.refresh_from_db()
    assert vp.visit_request.status == "completed"       # BR-105
    assert VisitLog.objects.filter(visit_pass=vp, event="auto_check_out").count() == 1


def test_auto_checkout_respects_approved_extension(host, admin):
    with freeze_time(T0):
        vp = on_site_pass(hours=2)
        ext = ext_svc.request_extension(requester=host, request_id=vp.visit_request_id,
                                        new_end=timezone.now() + timedelta(hours=5))
        assert ext.status == "approved"
    with freeze_time("2026-03-02 11:30:00+00:00"):      # old end passed
        assert autocheckout.sweep() == 0
    with freeze_time("2026-03-02 14:00:00+00:00"):
        assert autocheckout.sweep() == 1


def test_pending_extension_does_not_hold_checkout(host):
    with freeze_time(T0):
        vp = on_site_pass(hours=2)
        ext_svc.request_extension(requester=host, request_id=vp.visit_request_id,
                                  new_end=timezone.now() + timedelta(hours=10))
    with freeze_time("2026-03-02 11:00:00+00:00"):
        assert autocheckout.sweep() == 1


def test_auto_checkout_idempotent():
    with freeze_time(T0):
        on_site_pass(hours=1)
    with freeze_time("2026-03-02 10:30:00+00:00"):
        assert autocheckout.sweep() == 1
        assert autocheckout.sweep() == 0
    assert VisitLog.objects.filter(event="auto_check_out").count() == 1


def test_auto_checkout_actor_is_system_in_audit():
    with freeze_time(T0):
        vp = on_site_pass(hours=1)
    with freeze_time("2026-03-02 10:30:00+00:00"):
        autocheckout.sweep()
    row = AuditLog.objects.get(action="vms.visit.completed")
    assert row.actor_user_id is None and row.actor_role == "system"
    assert VisitLog.objects.get(event="auto_check_out").logged_by_user_id is None
    assert row.detail["pass_id"] == vp.pk


def test_sweep_skips_visitors_not_on_site_and_manual_checkouts():
    with freeze_time(T0):
        on_site_pass(hours=1, on_site=False)
        done = on_site_pass(hours=1)
        VisitLog.objects.create(visit_pass=done, event="check_out", logged_by_user_id=1)
    with freeze_time("2026-03-02 10:30:00+00:00"):
        assert autocheckout.sweep() == 0


def test_one_bad_row_does_not_stop_sweep(monkeypatch):
    with freeze_time(T0):
        a, b = on_site_pass(hours=1), on_site_pass(hours=1)
    from modules.vms.services import checkout
    real = checkout.complete_visit

    def flaky(pk, reason, actor=None):
        if pk == min(a.pk, b.pk):
            raise RuntimeError("boom")
        return real(pk, reason, actor=actor)

    monkeypatch.setattr(checkout, "complete_visit", flaky)
    with freeze_time("2026-03-02 10:30:00+00:00"):
        assert autocheckout.sweep() == 1


def test_unused_pass_expires():
    with freeze_time(T0):
        unused = on_site_pass(hours=1, on_site=False)
        inside = on_site_pass(hours=1)
        fresh = on_site_pass(hours=6, on_site=False)
    with freeze_time("2026-03-02 10:30:00+00:00"):
        assert autocheckout.expire_unused_passes() == 1
        assert autocheckout.expire_unused_passes() == 0           # idempotent
    for vp in (unused, inside, fresh):
        vp.refresh_from_db()
    assert not unused.is_active and inside.is_active and fresh.is_active
    row = AuditLog.objects.get(action="vms.pass.expired")
    assert row.actor_role == "system"
