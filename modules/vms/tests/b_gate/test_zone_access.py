"""Zone checks, elevation and alert handling (BW-VMS-12/13/14)."""
import inspect
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.vms.models import Alert, AuditLog, IntegrationSetting, Notification, VisitLog
from modules.vms.services import zone_access as za
from modules.vms.tests import factories as f
from modules.vms.tests.b_gate.conftest import blacklist

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _on_site(request):
    """Zone checks need an open check-in (UC-023); tests that check a zone start on site."""
    src = inspect.getsource(request.function)
    if ("check(" in src and "validate_and_check_in" not in src and "not_on_site" not in src
            and "vpass" in request.fixturenames):
        f.make_visit_log(visit_pass=request.getfixturevalue("vpass"))


@pytest.fixture
def zone():
    return f.make_zone(is_restricted=True)


def check(sec, vp, zone, **kw):
    return za.check_zone(actor=sec, pass_id=vp.pk, zone_id=zone.pk, reader_id="rdr-1", **kw)


def test_zone_allowed_is_logged(sec, vpass, zone, gate):
    vpass.allowed_zones.add(zone)
    res = check(sec, vpass, zone, gate_id=gate.pk)
    assert res["allowed"]
    log = vpass.logs.exclude(event="check_in").get()
    assert (log.event, log.zone_id, log.device_id) == ("zone_allowed", zone.pk, "rdr-1")
    assert not Alert.objects.exists()


def test_br_191_zone_denied_logged(sec, vpass, zone, gate, admin):
    res = check(sec, vpass, zone, gate_id=gate.pk)
    assert not res["allowed"]
    log = vpass.logs.exclude(event="check_in").get()
    assert log.event == "zone_denied" and log.reason == "zone_not_permitted"
    alert = Alert.objects.get(kind="zone_violation")
    assert alert.severity == "high" and alert.ref_id == log.pk       # restricted zone
    assert Notification.objects.filter(topic="zone.violation", recipient_user_id=4001).exists()
    assert AuditLog.objects.filter(action="vms.zone.denied").exists()


def test_br_192_unrestricted_zone_denial_is_medium(sec, vpass, gate):
    zone = f.make_zone()
    other = f.make_zone()
    vpass.allowed_zones.add(other)
    check(sec, vpass, zone, gate_id=gate.pk)
    assert Alert.objects.get().severity == "medium"


def test_service_token_may_report_zone_events(vpass, zone):
    svc_actor = f.make_actor(kind="service", user_id=9001)
    assert not za.check_zone(actor=svc_actor, pass_id=vpass.pk, zone_id=zone.pk)["allowed"]


def test_zone_check_needs_security_role_in_scope(vpass, zone):
    with pytest.raises(PermissionDeniedError):
        check(f.make_actor(user_id=7777), vpass, zone)
    f.make_role_assignment(user_id=7778, scope_type="zone", scope_id=f.make_zone().pk)
    with pytest.raises(PermissionDeniedError):
        check(f.make_actor(user_id=7778), vpass, zone)


def test_vip_zone_waiver_in_zone_check(sec, vpass, zone, gate):
    vpass.pass_type = "VIP"
    vpass.save()
    f.make_vip_permission(visitor=vpass.visit_request.visitor).zones.add(zone)
    res = check(sec, vpass, zone, gate_id=gate.pk)
    assert res["allowed"] and res["vip_override"]


def test_blacklisted_visitor_denied_in_zone_with_critical_alert(sec, vpass, zone, gate):
    vpass.allowed_zones.add(zone)
    blacklist(vpass.visit_request.visitor)
    assert not check(sec, vpass, zone, gate_id=gate.pk)["allowed"]
    assert Alert.objects.get().severity == "critical"


# --- elevation (BR-096, D-15) --------------------------------------------------------

def grant(admin, vp, zone, minutes=30, reason="Escorted"):
    return za.grant_elevation(admin_actor=admin, pass_id=vp.pk, zone_id=zone.pk,
                              ends_at=timezone.now() + timedelta(minutes=minutes),
                              reason=reason)


def test_br_096_elevation_capped_and_expires(sec, admin, vpass, zone, gate):
    with pytest.raises(BadRequestError) as e:
        grant(admin, vpass, zone, minutes=121)
    assert e.value.code == "elevation_too_long"
    el = grant(admin, vpass, zone, minutes=120)
    assert check(sec, vpass, zone, gate_id=gate.pk)["allowed"]            # BW-14 re-validation
    el.ends_at = timezone.now() - timedelta(seconds=1)
    el.starts_at = el.ends_at - timedelta(hours=1)
    el.save()
    assert not check(sec, vpass, zone, gate_id=gate.pk)["allowed"]


def test_elevation_cap_comes_from_integration_setting(admin, vpass, zone):
    IntegrationSetting.objects.create(key="max_elevation_minutes", value={"minutes": 30})
    assert za.max_elevation_minutes() == 30
    with pytest.raises(BadRequestError):
        grant(admin, vpass, zone, minutes=31)
    grant(admin, vpass, zone, minutes=30)


def test_elevation_cap_setting_may_be_a_bare_number(db):
    IntegrationSetting.objects.create(key="max_elevation_minutes", value=45)
    assert za.max_elevation_minutes() == 45


def test_elevation_cap_defaults_to_120(db):
    assert za.max_elevation_minutes() == 120


def test_elevation_requires_future_end_and_reason(admin, vpass, zone):
    with pytest.raises(BadRequestError):
        grant(admin, vpass, zone, minutes=-5)
    with pytest.raises(BadRequestError):
        grant(admin, vpass, zone, reason=" ")
    with pytest.raises(BadRequestError):
        za.grant_elevation(admin_actor=admin, pass_id=vpass.pk, zone_id=zone.pk,
                           ends_at=None, reason="x")


def test_elevation_needs_permission_and_admin_role(sec, vpass, zone):
    with pytest.raises(PermissionDeniedError):
        grant(sec, vpass, zone)
    perm_only = f.make_actor(user_id=4090, permissions=["vms.zone.elevate"])
    with pytest.raises(PermissionDeniedError):
        grant(perm_only, vpass, zone)


def test_elevation_refused_for_inactive_terminated_or_blacklisted_pass(admin, vpass, zone):
    blacklist(vpass.visit_request.visitor)
    with pytest.raises(ConflictError) as e:
        grant(admin, vpass, zone)
    assert e.value.code == "blacklisted"


def test_elevation_refused_for_inactive_pass(admin, vpass, zone):
    vpass.is_active = False
    vpass.save()
    with pytest.raises(ConflictError):
        grant(admin, vpass, zone)


def test_elevation_on_unrestricted_empty_pass_keeps_other_zones(sec, admin, vpass, zone, gate):
    other = f.make_zone()
    grant(admin, vpass, zone)
    assert check(sec, vpass, other, gate_id=gate.pk)["allowed"]


def test_elevation_zone_counts_at_gate_validate(sec, admin, vpass, zone, gate):
    from modules.vms.services import gate as gsvc
    grant(admin, vpass, zone)
    res = gsvc.validate_and_check_in(security_actor=sec, credential={"qr_token": vpass.qr_token},
                                     gate_id=gate.pk, zone_id=zone.pk)
    assert res.outcome == gsvc.CHECKED_IN


def test_revoke_elevation(sec, admin, vpass, zone, gate):
    el = grant(admin, vpass, zone)
    za.revoke_elevation(admin_actor=admin, elevation_id=el.pk)
    assert not check(sec, vpass, zone, gate_id=gate.pk)["allowed"]
    with pytest.raises(ConflictError):
        za.revoke_elevation(admin_actor=admin, elevation_id=el.pk)
    assert AuditLog.objects.filter(action="vms.zone.elevation_revoked").exists()


# --- alerts (UC-025) -----------------------------------------------------------------

def test_handle_alert(sec, vpass, zone, gate):
    check(sec, vpass, zone, gate_id=gate.pk)
    alert = Alert.objects.get()
    done = za.handle_alert(actor=sec, alert_id=alert.pk, outcome="resolved", note="Escorted out")
    assert done.status == "handled" and done.handled_by_user_id == 3001
    assert done.detail["outcome"] == "resolved"
    with pytest.raises(ConflictError):
        za.handle_alert(actor=sec, alert_id=alert.pk, outcome="resolved")


def test_handle_alert_validates_outcome_and_role(sec, vpass, zone, gate):
    check(sec, vpass, zone, gate_id=gate.pk)
    alert = Alert.objects.get()
    with pytest.raises(BadRequestError):
        za.handle_alert(actor=sec, alert_id=alert.pk, outcome="whatever")
    with pytest.raises(PermissionDeniedError):
        za.handle_alert(actor=f.make_actor(user_id=1), alert_id=alert.pk, outcome="resolved")


def test_zone_events_are_visit_log_rows(sec, vpass, zone, gate):
    vpass.allowed_zones.add(zone)
    check(sec, vpass, zone, gate_id=gate.pk)
    assert VisitLog.objects.filter(event=VisitLog.Event.ZONE_ALLOWED).count() == 1
