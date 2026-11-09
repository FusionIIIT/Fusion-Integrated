"""Gap tests for zone access, elevation, alerts and offline reconciliation."""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.vms.models import Alert, AuditLog, OfflineSyncRun, VisitLog
from modules.vms.services import checkout, termination
from modules.vms.services import gate as gsvc
from modules.vms.services import offline_sync as sync
from modules.vms.services import zone_access as za
from modules.vms.tests import factories as f
from modules.vms.tests.gaps.gate.conftest import blacklist, cred

pytestmark = pytest.mark.django_db


@pytest.fixture
def zone():
    return f.make_zone(is_restricted=True)


def check(sec, vp, zone, gate, **kw):
    return za.check_zone(actor=sec, pass_id=vp.pk, zone_id=zone.pk, reader_id="rdr-1",
                         gate_id=gate.pk, **kw)


def grant(admin, vp, zone, minutes=30, reason="Escorted"):
    return za.grant_elevation(admin_actor=admin, pass_id=vp.pk, zone_id=zone.pk,
                              ends_at=timezone.now() + timedelta(minutes=minutes),
                              reason=reason)


# --- zone checks ---------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="BUG: check_zone does not require the visitor to be "
                   "on site (no open check-in), so a never-checked-in pass is allowed")
def test_uc_023_zone_check_for_visitor_not_on_site_denied(sec, vpass, gate):
    """VMS-UC-023: a visitor not inside gets a denial."""
    zone = f.make_zone()
    assert not check(sec, vpass, zone, gate)["allowed"]


def test_uc_023_zone_check_pass_expired_mid_visit_denied(sec, vpass, gate):
    """VMS-UC-023: validity end is enforced in zone checks."""
    zone = f.make_zone()
    vpass.allowed_zones.add(zone)
    assert check(sec, vpass, zone, gate)["allowed"]
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    res = check(sec, vpass, zone, gate)
    assert not res["allowed"] and res["failures"][0].code == "outside_validity"


def test_uc_023_restricted_zone_needs_explicit_grant(sec, vpass, gate):
    """VMS-UC-023: a restricted zone is denied until explicitly granted on the pass."""
    zone = f.make_zone(is_restricted=True)
    other = f.make_zone()
    vpass.allowed_zones.add(other)
    assert not check(sec, vpass, zone, gate)["allowed"]
    vpass.allowed_zones.add(zone)
    assert check(sec, vpass, zone, gate)["allowed"]


def test_br_192_restricted_zone_denial_is_high_severity_logged(sec, vpass, zone, gate):
    """VMS-BR-192: restricted zone denial logs a high-severity alert."""
    check(sec, vpass, zone, gate)
    alert = Alert.objects.get()
    assert alert.severity == "high" and alert.kind == "zone_violation"
    assert alert.detail["zone_id"] == zone.pk and alert.detail["failures"] == [
        "zone_not_permitted"]


def test_br_191_empty_pass_zones_deny_restricted_target(sec, vpass, zone, gate):
    """VMS-BR-191: an empty zone list is not a wildcard for restricted zones."""
    assert not vpass.allowed_zones.exists()
    assert not check(sec, vpass, zone, gate)["allowed"]
    assert check(sec, vpass, f.make_zone(), gate)["allowed"]


def test_bw_12_service_token_zone_allowed(vpass, zone, gate):
    """BW-VMS-12: access-control-system caller gets an allowed zone logged."""
    vpass.allowed_zones.add(zone)
    svc_actor = f.make_actor(kind="service", user_id=9001)
    res = za.check_zone(actor=svc_actor, pass_id=vpass.pk, zone_id=zone.pk, reader_id="acs-1")
    assert res["allowed"] and not Alert.objects.exists()
    log = vpass.logs.get()
    assert (log.event, log.device_id, log.logged_by_user_id) == ("zone_allowed", "acs-1", 9001)


def test_bw_13_denied_alert_handled_then_visit_continues(sec, admin, vpass, zone, gate):
    """BW-VMS-13: handling the alert leaves the visit on site and the alert closed."""
    gsvc.validate_and_check_in(security_actor=sec, credential=cred(vpass), gate_id=gate.pk)
    check(sec, vpass, zone, gate)
    alert = Alert.objects.get()
    za.handle_alert(actor=sec, alert_id=alert.pk, outcome="false_alarm", note="ok")
    alert.refresh_from_db()
    assert alert.status == "handled" and alert.detail["outcome"] == "false_alarm"
    vpass.visit_request.refresh_from_db()
    assert vpass.visit_request.status == "approved"
    assert gsvc.gate_sel.open_check_in(vpass.pk) is not None
    assert AuditLog.objects.filter(action="vms.alert.handled").exists()


def test_uc_025_handle_alert_twice_conflicts(sec, vpass, zone, gate):
    """VMS-UC-025: a handled alert cannot be handled again and keeps first outcome."""
    check(sec, vpass, zone, gate)
    alert = Alert.objects.get()
    za.handle_alert(actor=sec, alert_id=alert.pk, outcome="resolved")
    from core.api.exceptions import ConflictError
    with pytest.raises(ConflictError) as e:
        za.handle_alert(actor=sec, alert_id=alert.pk, outcome="escalated")
    assert e.value.code == "already_handled"
    alert.refresh_from_db()
    assert alert.detail["outcome"] == "resolved"


# --- elevation -----------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="BUG: elevation is time-boxed only; there is no "
                   "single-use limit, so unlimited re-validations succeed")
def test_uc_024_elevation_allows_exactly_one_revalidation(sec, admin, vpass, zone, gate):
    """VMS-UC-024: a second re-validation after the elevation was used is denied."""
    grant(admin, vpass, zone)
    assert check(sec, vpass, zone, gate)["allowed"]
    assert not check(sec, vpass, zone, gate)["allowed"]


def test_uc_024_elevation_unused_expires_at_time_box_end(sec, admin, vpass, zone, gate):
    """VMS-UC-024: re-validation after the end of the time box is denied."""
    el = grant(admin, vpass, zone)
    el.starts_at = timezone.now() - timedelta(hours=2)
    el.ends_at = timezone.now() - timedelta(minutes=1)
    el.save()
    assert not check(sec, vpass, zone, gate)["allowed"]


def test_uc_024_elevation_scope_single_zone_only(sec, admin, vpass, zone, gate):
    """VMS-UC-024: elevation grants only its zone; another restricted zone is denied."""
    other = f.make_zone(is_restricted=True)
    grant(admin, vpass, zone)
    assert check(sec, vpass, zone, gate)["allowed"]
    assert not check(sec, vpass, other, gate)["allowed"]


def test_uc_024_elevation_audited_with_reason_and_end(admin, vpass, zone):
    """VMS-UC-024: grant audit holds actor, reason, zone and end."""
    el = grant(admin, vpass, zone, reason="Escort by Dean")
    row = AuditLog.objects.get(action="vms.zone.elevation_granted")
    assert row.actor_user_id == 4001
    assert row.detail["reason"] == "Escort by Dean" and row.detail["zone_id"] == zone.pk
    assert row.detail["ends_at"] == el.ends_at.isoformat()
    assert el.granted_by_user_id == 4001


def test_br_096_cap_boundary_accepted_one_minute_over_rejected(admin, vpass, zone):
    """VMS-BR-096: exactly max minutes ok, one minute over rejected."""
    cap = za.max_elevation_minutes()
    with pytest.raises(BadRequestError) as e:
        grant(admin, vpass, zone, minutes=cap + 1)
    assert e.value.code == "elevation_too_long"
    assert grant(admin, vpass, zone, minutes=cap).pk
    assert vpass.elevations.count() == 1


def test_bw_14_denied_elevated_revalidated_then_denied_after_revoke(
        sec, admin, vpass, zone, gate):
    """BW-VMS-14: denied, elevated, re-validated allowed, denied again once revoked."""
    assert not check(sec, vpass, zone, gate)["allowed"]
    el = grant(admin, vpass, zone)
    assert check(sec, vpass, zone, gate)["allowed"]
    za.revoke_elevation(admin_actor=admin, elevation_id=el.pk)
    assert not check(sec, vpass, zone, gate)["allowed"]
    assert list(vpass.logs.order_by("id").values_list("event", flat=True)) == [
        "zone_denied", "zone_allowed", "zone_denied"]


def test_cw_04_grant_deny_elevate_revalidate_checkout(sec, admin, vpass, zone, gate):
    """CW-VMS-04: composite zone chain ending in checkout."""
    gsvc.validate_and_check_in(security_actor=sec, credential=cred(vpass), gate_id=gate.pk)
    assert not check(sec, vpass, zone, gate)["allowed"]
    grant(admin, vpass, zone)
    assert check(sec, vpass, zone, gate)["allowed"]
    checkout.gate_checkout(security_actor=sec, credential=vpass.qr_token, gate_id=gate.pk)
    vpass.visit_request.refresh_from_db()
    assert vpass.visit_request.status == "completed"


# --- offline -------------------------------------------------------------------------

def ev(vp, when=None, kind="check_in", **kw):
    return {"client_event_id": uuid.uuid4(), "event": kind, "qr_token": vp.qr_token,
            "occurred_at": when or timezone.now() - timedelta(minutes=10), **kw}


def run(sec, gate, events):
    return sync.sync(security_actor=sec, gate_id=gate.pk, events=events)


def test_uc_028_offline_entry_after_expiry_flagged_conflict(sec, gate, vpass):
    """VMS-UC-028: occurred_at after the pass expiry is flagged as a conflict."""
    vpass.valid_until = timezone.now() - timedelta(hours=1)
    vpass.save()
    out = run(sec, gate, [ev(vpass, timezone.now() - timedelta(minutes=5))])
    assert out["results"][0]["status"] == "conflict"
    assert out["results"][0]["failures"] == ["outside_validity"]
    assert vpass.logs.get().conflict


def test_uc_039_reconcile_partial_batch_reports_per_event(sec, gate, vpass):
    """VMS-UC-039: a conflicting event does not stop the others being applied."""
    bad = f.make_visit_pass(visit_request=f.make_visit_request(status="approved"),
                            is_active=False,
                            valid_from=timezone.now() - timedelta(hours=1),
                            valid_until=timezone.now() + timedelta(hours=1))
    good_ev = ev(vpass, timezone.now() - timedelta(minutes=20))
    bad_ev = ev(bad, timezone.now() - timedelta(minutes=10))
    ghost = {"client_event_id": uuid.uuid4(), "event": "check_in", "qr_token": "ghost",
             "occurred_at": timezone.now() - timedelta(minutes=5)}
    out = run(sec, gate, [ghost, bad_ev, good_ev])
    assert [r["status"] for r in out["results"]] == ["applied", "conflict", "unknown_credential"]
    assert (out["applied"], out["conflicted"], out["total"]) == (1, 2, 3)
    run_row = OfflineSyncRun.objects.get()
    assert (run_row.events_total, run_row.events_applied, run_row.events_conflicted) == (3, 1, 2)


def test_uc_039_event_for_pass_terminated_before_occurred_at_flagged(
        sec, admin, gate, vpass):
    """VMS-UC-039: terminated before occurred_at is flagged; after it, applied."""
    boss = f.make_actor(user_id=4001, permissions=["vms.pass.terminate"])
    termination.terminate(actor=boss, pass_id=vpass.pk, reason="Policy breach seen")
    vpass.refresh_from_db()
    after = vpass.terminated_at + timedelta(minutes=1)
    before = vpass.terminated_at - timedelta(minutes=1)
    out = run(sec, gate, [ev(vpass, after)])
    assert out["results"][0]["status"] == "conflict"
    assert "terminated" in out["results"][0]["failures"]
    out2 = run(sec, gate, [ev(vpass, before)])
    assert "terminated" not in out2["results"][0]["failures"]


def test_bw_11_cache_entry_then_reconcile_sets_on_site_and_host_notified(sec, gate, vpass):
    """BW-VMS-11: after reconcile the visitor is on site and the log is stamped."""
    occurred = timezone.now() - timedelta(minutes=15)
    out = run(sec, gate, [ev(vpass, occurred)])
    assert out["applied"] == 1
    assert gsvc.gate_sel.open_check_in(vpass.pk) is not None
    log = vpass.logs.get()
    assert log.occurred_at == occurred and log.offline and log.synced_at > occurred
    assert not Alert.objects.exists()


def test_uc_028_offline_check_out_event_requires_prior_check_in_order(sec, gate, vpass):
    """VMS-UC-028: a check_out occurring before its check_in is a conflict."""
    t = timezone.now() - timedelta(minutes=30)
    out = run(sec, gate, [ev(vpass, t, kind="check_in"),
                          ev(vpass, t - timedelta(minutes=5), kind="check_out")])
    statuses = [r["status"] for r in out["results"]]
    assert statuses == ["conflict", "applied"]


def test_br_112_stale_cache_blacklisted_added_after_download_alerts_on_sync(
        sec, gate, vpass):
    """VMS-BR-112: blacklist added after roster download raises a critical alert on sync."""
    rows = sync.cached_roster(security_actor=sec, gate_id=gate.pk)
    assert vpass.pk in [r["pass_id"] for r in rows]
    blacklist(vpass.visit_request.visitor, severity="critical")
    out = run(sec, gate, [ev(vpass)])
    assert out["results"][0]["status"] == "conflict"
    alert = Alert.objects.get()
    assert alert.kind == "blacklist_hit" and alert.severity == "critical"
    assert VisitLog.objects.get().conflict


def test_cw_03_deny_override_offline_reconcile_chain(sec, admin, gate, vpass):
    """CW-VMS-03: deny, override, check out, then an offline replay is a conflict."""
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    denial = gsvc.validate_and_check_in(security_actor=sec, credential=cred(vpass),
                                        gate_id=gate.pk).log
    gsvc.override(admin_actor=admin, denial_log_id=denial.pk,
                  justification="Host escorted visitor in")
    checkout.gate_checkout(security_actor=sec, credential=vpass.qr_token, gate_id=gate.pk)
    out = run(sec, gate, [ev(vpass, timezone.now() - timedelta(minutes=1))])
    assert out["results"][0]["status"] == "conflict"
    assert "outside_validity" in out["results"][0]["failures"]
    assert vpass.logs.filter(event="denied").count() == 1
