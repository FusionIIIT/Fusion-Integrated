"""Gap tests for gate validation, override, escalation and manual entry."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import Alert, AuditLog, EventAttendee, GateOverride, Notification
from modules.vms.services import checkout
from modules.vms.services import gate as svc
from modules.vms.tests import factories as f
from modules.vms.tests.gaps.gate.conftest import SECURITY_PERMS, blacklist, cred

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"


def go(sec, gate, credential, **kw):
    return svc.validate_and_check_in(security_actor=sec, credential=credential,
                                     gate_id=gate.pk, **kw)


def _other_pass():
    return f.make_visit_pass(visit_request=f.make_visit_request(status="approved"),
                             valid_from=timezone.now() - timedelta(hours=1),
                             valid_until=timezone.now() + timedelta(hours=1))


def _denial(sec, gate, vpass):
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    return go(sec, gate, cred(vpass)).log


def test_uc_018_validity_uses_extended_end_only(sec, gate, vpass):
    """VMS-UC-018: validity follows the (extended) valid_until."""
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    assert go(sec, gate, cred(vpass)).outcome == svc.DENIED
    vpass.valid_until = timezone.now() + timedelta(hours=1)
    vpass.save()
    assert go(sec, gate, cred(vpass)).outcome == svc.CHECKED_IN


def test_uc_018_qr_and_otp_equivalent(sec, gate, vpass):
    """VMS-UC-018: QR and OTP credentials give the same decision."""
    other = _other_pass()
    assert go(sec, gate, cred(vpass)).outcome == svc.CHECKED_IN
    assert go(sec, gate, {"otp": other.otp}).outcome == svc.CHECKED_IN
    a2 = go(sec, gate, cred(vpass))
    b2 = go(sec, gate, {"otp": other.otp})
    assert [x.code for x in a2.failures] == [x.code for x in b2.failures] == ["already_inside"]


def test_uc_018_pending_walkin_pass_denied_inactive(sec, gate):
    """VMS-UC-018: pending walk-in credentials are denied pass_inactive."""
    vp = _other_pass()
    vp.visit_request.status = "pending"
    vp.visit_request.save()
    res = go(sec, gate, cred(vp))
    assert res.outcome == svc.DENIED and res.failures[0].code == "pass_inactive"


def test_uc_018_event_pass_outside_slot_denied(sec, gate, vpass):
    """VMS-UC-018: event pass outside its slot gets outside_slot."""
    batch = f.make_event_batch()
    vpass.event = batch
    vpass.save()
    now = timezone.now()
    EventAttendee.objects.create(batch=batch, name="A", visit_pass=vpass,
                                 slot_start=now + timedelta(minutes=30),
                                 slot_end=now + timedelta(hours=1))
    res = go(sec, gate, cred(vpass))
    assert "outside_slot" in [x.code for x in res.failures]


def test_uc_018_host_notified_only_on_first_check_in(sec, gate, vpass):
    """VMS-UC-018: a denial sends no arrival notice; only one check-in notifies."""
    vpass.is_active = False
    vpass.save()
    go(sec, gate, cred(vpass))
    assert not Notification.objects.filter(topic="visit.checked_in").exists()
    vpass.is_active = True
    vpass.save()
    go(sec, gate, cred(vpass))
    assert go(sec, gate, cred(vpass)).outcome == svc.DENIED       # already inside
    assert Notification.objects.filter(topic="visit.checked_in").count() == 1


@pytest.mark.parametrize("status", ["rejected", "expired"])
def test_br_077_rejected_or_expired_request_never_admits(sec, gate, status):
    """VMS-BR-077: a pass on a rejected/expired request is denied."""
    vp = _other_pass()
    vp.visit_request.status = status
    vp.visit_request.save()
    res = go(sec, gate, cred(vp))
    assert res.outcome == svc.DENIED and res.failures[0].code == "pass_inactive"
    assert not vp.logs.filter(event="check_in").exists()


def test_br_082_combined_failures_in_documented_order(sec, gate, vpass):
    """VMS-BR-082: failure order is stable for combined failures."""
    zone = f.make_zone(is_restricted=True)
    vpass.is_active = False
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    res = go(sec, gate, cred(vpass), zone_id=zone.pk)
    assert [x.code for x in res.failures] == [
        "pass_inactive", "outside_validity", "zone_not_permitted"]


def test_br_082_denial_log_has_gate_actor_and_codes(sec, gate, vpass):
    """VMS-BR-082: denial log row stores gate, actor, device and failure codes."""
    vpass.is_active = False
    vpass.save()
    log = go(sec, gate, cred(vpass), device_id="d7").log
    assert (log.event, log.gate_id, log.logged_by_user_id, log.device_id) == (
        "denied", gate.pk, 3001, "d7")
    assert log.detail["failures"] == ["pass_inactive"]


def test_bw_09_denied_then_retry_after_cause_cleared_succeeds(sec, gate, vpass):
    """BW-VMS-09: a denial is not sticky once the cause is fixed."""
    _denial(sec, gate, vpass)
    vpass.valid_until = timezone.now() + timedelta(hours=1)
    vpass.save()
    assert go(sec, gate, cred(vpass)).outcome == svc.CHECKED_IN
    assert list(vpass.logs.order_by("id").values_list("event", flat=True)) == [
        "denied", "check_in"]


def test_bw_10_override_then_checkout_completes_visit(sec, admin, gate, vpass):
    """BW-VMS-10: denial, override, check-in, checkout to Completed."""
    denial = _denial(sec, gate, vpass)
    res = svc.override(admin_actor=admin, denial_log_id=denial.pk,
                       justification="Visitor confirmed by host in person")
    assert res.outcome == svc.CHECKED_IN
    checkout.gate_checkout(security_actor=sec, credential=vpass.qr_token, gate_id=gate.pk)
    vpass.visit_request.refresh_from_db()
    assert vpass.visit_request.status == "completed"
    assert vpass.logs.filter(event="check_out").exists()


def test_br_085_override_by_security_role_forbidden(sec, gate, vpass):
    """VMS-BR-085: only an Admin may authorise an override."""
    denial = _denial(sec, gate, vpass)
    with pytest.raises(PermissionDeniedError):
        svc.override(admin_actor=sec, denial_log_id=denial.pk,
                     justification="long enough justification text")
    perm_only = f.make_actor(user_id=4090, permissions=["vms.gate.override"])
    with pytest.raises(PermissionDeniedError):
        svc.override(admin_actor=perm_only, denial_log_id=denial.pk,
                     justification="long enough justification text")
    assert not GateOverride.objects.exists()


def test_br_085_justification_min_length_and_stored(sec, admin, gate, vpass):
    """VMS-BR-085: short justification rejected; accepted one stored and audited."""
    denial = _denial(sec, gate, vpass)
    for bad in ("", "   ", "too short"):
        with pytest.raises(BadRequestError) as e:
            svc.override(admin_actor=admin, denial_log_id=denial.pk, justification=bad)
        assert e.value.code == "justification_required"
    text = "x" * svc.MIN_JUSTIFICATION
    svc.override(admin_actor=admin, denial_log_id=denial.pk, justification=text)
    assert GateOverride.objects.get().justification == text
    row = AuditLog.objects.get(action="vms.gate.override_check_in")
    assert row.detail["justification"] == text


def test_uc_019_override_twice_conflicts(sec, admin, gate, vpass):
    """VMS-UC-019: a denial can be overridden once only."""
    denial = _denial(sec, gate, vpass)
    svc.override(admin_actor=admin, denial_log_id=denial.pk,
                 justification="first and only override ok")
    with pytest.raises(ConflictError) as e:
        svc.override(admin_actor=admin, denial_log_id=denial.pk,
                     justification="second override attempt ok")
    assert e.value.code == "already_overridden"


def test_uc_019_override_notifies_host_and_audits_both_actors(sec, admin, gate, vpass):
    """VMS-UC-019: override notifies the host; audit rows for both actors."""
    denial = _denial(sec, gate, vpass)
    svc.override(admin_actor=admin, denial_log_id=denial.pk,
                 justification="Host vouches for visitor")
    assert Notification.objects.filter(topic="visit.checked_in",
                                       recipient_user_id=2001).exists()
    assert AuditLog.objects.filter(action="vms.gate.denied", actor_user_id=3001).exists()
    assert AuditLog.objects.filter(action="vms.gate.override_check_in",
                                   actor_user_id=4001).exists()


def test_uc_019_override_blocked_if_blacklisted_since_denial(sec, admin, gate, vpass):
    """VMS-UC-019: a blacklist hit after the denial blocks the override."""
    denial = _denial(sec, gate, vpass)
    blacklist(vpass.visit_request.visitor)
    with pytest.raises(ConflictError) as e:
        svc.override(admin_actor=admin, denial_log_id=denial.pk,
                     justification="Trying anyway with text")
    assert e.value.code == "not_overridable"


def test_uc_019_escalate_twice_conflicts_then_resolve_once(sec, admin, gate, vpass):
    """VMS-UC-019: escalation open once; resolved once."""
    denial = _denial(sec, gate, vpass)
    esc = svc.escalate(security_actor=sec, visit_log_id=denial.pk, note="Looks odd")
    with pytest.raises(ConflictError) as e:
        svc.escalate(security_actor=sec, visit_log_id=denial.pk, note="again")
    assert e.value.code == "already_escalated"
    svc.resolve_escalation(admin_actor=admin, escalation_id=esc.pk, note="Reviewed")
    with pytest.raises(ConflictError) as e:
        svc.resolve_escalation(admin_actor=admin, escalation_id=esc.pk, note="Again")
    assert e.value.code == "already_resolved"


def test_uc_020_manual_entry_unknown_pass_rejected(sec, gate):
    """VMS-UC-020: manual log needs an existing pass."""
    with pytest.raises(NotFoundError):
        svc.record_manual_entry(security_actor=sec, pass_id=999999, event="check_in",
                                reason="device down", gate_id=gate.pk)


def test_uc_020_manual_check_out_flagged_manual(sec, gate, vpass):
    """VMS-UC-020: manual check-out is flagged manual and completes the visit."""
    go(sec, gate, cred(vpass))
    res = svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_out",
                                  reason="scanner broke", gate_id=gate.pk)
    assert res.outcome == "checked_out"
    assert res.log.entry_point == "manual" and res.log.detail["manual"] is True
    vpass.visit_request.refresh_from_db()
    assert vpass.visit_request.status == "completed"


def test_uc_020_manual_check_out_without_check_in_conflicts(sec, gate, vpass):
    """VMS-UC-020: manual check-out needs an open check-in."""
    with pytest.raises(ConflictError) as e:
        svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_out",
                                reason="scanner broke", gate_id=gate.pk)
    assert e.value.code == "no_open_check_in"


def test_br_116_admin_cannot_waive_blacklist_at_manual_entry(admin, gate, vpass):
    """VMS-BR-116: an admin manual entry still denies a blacklisted visitor."""
    blacklist(vpass.visit_request.visitor)
    res = svc.record_manual_entry(security_actor=admin, pass_id=vpass.pk, event="check_in",
                                  reason="device down", gate_id=gate.pk)
    assert res.outcome == svc.DENIED and res.failures[0].code == "blacklisted"
    assert not vpass.logs.filter(event="check_in").exists()


def test_br_116_admin_manual_entry_waives_overridable_failure(admin, gate, vpass):
    """VMS-BR-116: admin may waive an override-eligible failure by hand."""
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    res = svc.record_manual_entry(security_actor=admin, pass_id=vpass.pk, event="check_in",
                                  reason="device down", gate_id=gate.pk)
    assert res.outcome == svc.CHECKED_IN
    assert res.log.detail["waived"] == ["outside_validity"]


def test_br_117_each_blacklist_attempt_raises_its_own_alert(sec, gate, vpass):
    """VMS-BR-117: every blacklisted attempt is logged with an alert."""
    blacklist(vpass.visit_request.visitor)
    for _ in range(3):
        go(sec, gate, cred(vpass))
    assert Alert.objects.filter(kind="blacklist_hit").count() == 3
    assert vpass.logs.filter(event="denied").count() == 3


def test_br_191_empty_zone_list_is_not_a_wildcard_for_restricted(sec, gate, vpass):
    """VMS-BR-191: empty allowed zones never admit a restricted zone."""
    zone = f.make_zone(is_restricted=True)
    res = go(sec, gate, cred(vpass), zone_id=zone.pk)
    assert [x.code for x in res.failures] == ["zone_not_permitted"]
    assert go(sec, gate, cred(_other_pass()), zone_id=f.make_zone().pk).outcome == svc.CHECKED_IN


def test_br_190_validity_edges_through_api(api_as, sec, gate, vpass):
    """VMS-BR-190: just inside the window admits, not-yet-valid denies (API)."""
    client = api_as(user_id=3001, permissions=SECURITY_PERMS)
    vpass.valid_until = timezone.now() + timedelta(seconds=30)
    vpass.save()
    ok = client.post(BASE + "gate/validate", {"qr_token": vpass.qr_token, "gate_id": gate.pk},
                     format="json")
    assert ok.status_code == 200
    early = _other_pass()
    early.valid_from = timezone.now() + timedelta(seconds=30)
    early.save()
    bad = client.post(BASE + "gate/validate", {"qr_token": early.qr_token, "gate_id": gate.pk},
                      format="json")
    assert bad.status_code == 403 and bad.json()["code"] == "outside_validity"
