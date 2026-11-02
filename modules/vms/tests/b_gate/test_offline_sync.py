"""Offline gate continuity (CFR-025, D-10)."""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.vms.models import Alert, OfflineSyncRun, VisitLog
from modules.vms.selectors import gate as gate_sel
from modules.vms.services import offline_sync as sync
from modules.vms.tests import factories as f
from modules.vms.tests.b_gate.conftest import blacklist

pytestmark = pytest.mark.django_db


def ev(vp, when=None, kind="check_in", **kw):
    return {"client_event_id": uuid.uuid4(), "event": kind, "qr_token": vp.qr_token,
            "occurred_at": when or timezone.now() - timedelta(minutes=10), **kw}


def run(sec, gate, events):
    return sync.sync(security_actor=sec, gate_id=gate.pk, events=events)


def test_offline_sync_applies_events_and_records_a_run(sec, gate, vpass):
    out = run(sec, gate, [ev(vpass)])
    assert (out["applied"], out["conflicted"]) == (1, 0)
    log = vpass.logs.get()
    assert log.offline and log.synced_at and log.occurred_at and not log.conflict
    r = OfflineSyncRun.objects.get()
    assert (r.events_total, r.events_applied, r.events_conflicted) == (1, 1, 0)


def test_offline_sync_idempotent(sec, gate, vpass):
    e = ev(vpass)
    run(sec, gate, [e])
    out = run(sec, gate, [e])
    assert out["results"][0]["status"] == "duplicate" and out["applied"] == 0
    assert vpass.logs.count() == 1


def test_offline_events_apply_in_occurred_at_order(sec, gate, vpass):
    t = timezone.now() - timedelta(minutes=30)
    out_of_order = [ev(vpass, t + timedelta(minutes=10), kind="check_out"),
                    ev(vpass, t, kind="check_in")]
    out = run(sec, gate, out_of_order)
    assert [r["status"] for r in out["results"]] == ["applied", "applied"]
    assert list(vpass.logs.order_by("id").values_list("event", flat=True)) == [
        "check_in", "check_out"]
    assert gate_sel.open_check_in(vpass.pk) is None


def test_offline_conflict_flagged(sec, gate, vpass, admin):
    vpass.is_active = False
    vpass.save()
    out = run(sec, gate, [ev(vpass)])
    assert out["conflicted"] == 1
    log = vpass.logs.get()
    assert log.conflict and log.reason == "pass_inactive"      # stored, not dropped
    assert Alert.objects.filter(kind="gate_failure", ref_id=log.pk).exists()
    assert OfflineSyncRun.objects.get().events_conflicted == 1


def test_offline_blacklist_conflict_raises_blacklist_alert(sec, gate, vpass):
    blacklist(vpass.visit_request.visitor, severity="critical")
    run(sec, gate, [ev(vpass)])
    assert Alert.objects.get().kind == "blacklist_hit"


def test_event_judged_as_of_occurred_at_not_now(sec, gate, vpass):
    vpass.valid_until = timezone.now() - timedelta(minutes=5)       # expired by now
    vpass.save()
    inside_window = vpass.valid_until - timedelta(minutes=20)
    out = run(sec, gate, [ev(vpass, inside_window)])
    assert out["applied"] == 1
    late = ev(f.make_visit_pass(
        visit_request=f.make_visit_request(status="approved"),
        valid_from=timezone.now() - timedelta(hours=3),
        valid_until=timezone.now() - timedelta(hours=2)))
    assert run(sec, gate, [late])["conflicted"] == 1


def test_offline_check_out_without_check_in_is_a_conflict(sec, gate, vpass):
    out = run(sec, gate, [ev(vpass, kind="check_out")])
    assert out["conflicted"] == 1 and vpass.logs.get().reason == "no_open_check_in"


def test_offline_second_check_in_is_flagged_already_inside(sec, gate, vpass):
    t = timezone.now() - timedelta(minutes=30)
    out = run(sec, gate, [ev(vpass, t), ev(vpass, t + timedelta(minutes=1))])
    assert [r["status"] for r in out["results"]] == ["applied", "conflict"]


def test_offline_unknown_credential_alerts(sec, gate):
    out = run(sec, gate, [{"client_event_id": uuid.uuid4(), "event": "check_in",
                           "qr_token": "ghost", "occurred_at": timezone.now()}])
    assert out["results"][0]["status"] == "unknown_credential"
    assert VisitLog.objects.count() == 0 and Alert.objects.count() == 1


def test_offline_sync_needs_scoped_role(gate, vpass):
    other_gate = f.make_gate()
    f.make_role_assignment(user_id=3300, scope_type="gate", scope_id=other_gate.pk)
    with pytest.raises(PermissionDeniedError):
        run(f.make_actor(user_id=3300), gate, [ev(vpass)])


def test_batch_size_limited(sec, gate, vpass):
    with pytest.raises(BadRequestError):
        run(sec, gate, [ev(vpass)] * (sync.MAX_BATCH + 1))


def test_cached_roster_has_no_pii_beyond_initials(sec, gate, vpass):
    vpass.visit_request.visitor.full_name = "Ravi Kumar Singh"
    vpass.visit_request.visitor.save()
    zone = f.make_zone()
    vpass.allowed_zones.add(zone)
    expired = f.make_visit_pass(visit_request=f.make_visit_request(status="approved"),
                                valid_until=timezone.now() - timedelta(minutes=1),
                                valid_from=timezone.now() - timedelta(hours=1))
    rows = sync.cached_roster(security_actor=sec, gate_id=gate.pk)
    assert [r["pass_id"] for r in rows] == [vpass.pk]
    row = rows[0]
    assert row["initials"] == "RKS" and row["zone_ids"] == [zone.pk]
    blob = str(row)
    assert vpass.qr_token not in blob and vpass.otp not in blob
    assert "Ravi" not in blob and expired.pk not in [r["pass_id"] for r in rows]
