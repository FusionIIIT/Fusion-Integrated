"""Gate validation, override, escalation and manual entry (services)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.vms.domain import pass_rules
from modules.vms.models import (
    Alert,
    AuditLog,
    Escalation,
    GateOverride,
    Notification,
    VisitLog,
)
from modules.vms.selectors import gate as gate_sel
from modules.vms.services import gate as svc
from modules.vms.tests import factories as f
from modules.vms.tests.b_gate.conftest import blacklist, cred

pytestmark = pytest.mark.django_db


def go(sec, gate, credential, **kw):
    return svc.validate_and_check_in(security_actor=sec, credential=credential,
                                     gate_id=gate.pk, **kw)


def events(vp):
    return list(vp.logs.order_by("id").values_list("event", "reason"))


def test_valid_pass_checks_in_and_notifies_host(sec, gate, vpass):
    res = go(sec, gate, cred(vpass), device_id="dev-9")
    assert res.outcome == svc.CHECKED_IN
    log = vpass.logs.get()
    assert (log.event, log.gate_id, log.device_id) == ("check_in", gate.pk, "dev-9")
    vpass.visit_request.refresh_from_db()
    assert vpass.visit_request.status == "approved"
    assert Notification.objects.filter(topic="visit.checked_in",
                                       recipient_user_id=2001).exists()
    assert AuditLog.objects.filter(action="vms.gate.checked_in").exists()


def test_br_077_inactive_pass_denied(sec, gate, vpass):
    vpass.is_active = False
    vpass.save()
    res = go(sec, gate, cred(vpass))
    assert res.outcome == svc.DENIED and res.failures[0].code == "pass_inactive"
    assert events(vpass) == [("denied", "pass_inactive")]


def test_br_190_outside_window_denied(sec, gate, vpass):
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    res = go(sec, gate, cred(vpass))
    assert [x.code for x in res.failures] == ["outside_validity"]
    assert res.override_eligible


def test_all_failures_returned_first_is_logged(sec, gate, vpass):
    vpass.is_active = False
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    res = go(sec, gate, cred(vpass))
    assert [x.code for x in res.failures] == ["pass_inactive", "outside_validity"]
    assert res.log.reason.startswith("pass_inactive")


def test_br_116_blacklist_denied_and_not_in_override_set(sec, gate, vpass):
    blacklist(vpass.visit_request.visitor)
    res = go(sec, gate, cred(vpass))
    assert res.outcome == svc.DENIED and res.failures[0].code == "blacklisted"
    assert "blacklisted" not in pass_rules.OVERRIDE_ELIGIBLE
    assert res.override_eligible is False


def test_br_117_alert_on_blacklist_hit(sec, gate, vpass, admin):
    blacklist(vpass.visit_request.visitor, severity="critical")
    res = go(sec, gate, cred(vpass))
    alert = Alert.objects.get(kind="blacklist_hit")
    assert alert.severity == "critical" and alert.ref_id == res.log.pk
    assert alert.detail["gate_id"] == gate.pk
    assert Notification.objects.filter(topic="gate.denied", recipient_user_id=4001).exists()


def test_other_denials_raise_gate_failure_alert(sec, gate, vpass):
    vpass.is_active = False
    vpass.save()
    go(sec, gate, cred(vpass))
    assert Alert.objects.filter(kind="gate_failure").count() == 1


def test_double_check_in_blocked(sec, gate, vpass):
    assert go(sec, gate, cred(vpass)).outcome == svc.CHECKED_IN
    res = go(sec, gate, cred(vpass))
    assert res.outcome == svc.DENIED and res.failures[0].code == "already_inside"
    assert events(vpass) == [("check_in", ""), ("denied", "already_inside")]


def test_terminated_pass_denied_and_not_overridable(sec, gate, vpass):
    vpass.is_active = False
    vpass.terminated_at = timezone.now() - timedelta(minutes=5)
    vpass.save()
    res = go(sec, gate, cred(vpass))
    assert [x.code for x in res.failures] == ["terminated"]
    assert not res.override_eligible


def test_completed_request_is_not_admitted(sec, gate, vpass):
    vpass.visit_request.status = "completed"
    vpass.visit_request.save()
    assert go(sec, gate, cred(vpass)).failures[0].code == "pass_inactive"


def test_otp_only_matches_active_pass(sec, gate, vpass):
    vpass.is_active = False
    vpass.save()
    res = go(sec, gate, {"otp": vpass.otp})
    assert res.outcome == svc.UNKNOWN
    vpass.is_active = True
    vpass.save()
    assert go(sec, gate, {"otp": vpass.otp}).outcome == svc.CHECKED_IN


def test_unknown_credential_no_log_but_alert(sec, gate):
    res = go(sec, gate, {"qr_token": "nope-nope"})
    assert res.outcome == svc.UNKNOWN
    assert VisitLog.objects.count() == 0
    alert = Alert.objects.get(kind="gate_failure")
    assert alert.detail["failures"] == ["unknown_credential"]
    assert "nope-nope" not in str(alert.detail)           # only a fingerprint is kept
    assert AuditLog.objects.filter(action="vms.gate.unknown_credential").exists()


def test_credential_is_required(sec, gate):
    with pytest.raises(BadRequestError):
        go(sec, gate, {})


def test_br_191_zone_not_on_pass_denied(sec, gate, vpass):
    z1, z2 = f.make_zone(), f.make_zone()
    vpass.allowed_zones.add(z1)
    res = go(sec, gate, cred(vpass), zone_id=z2.pk)
    assert res.failures[0].code == "zone_not_permitted"
    assert go(sec, gate, cred(vpass), zone_id=z1.pk).outcome == svc.CHECKED_IN


def test_restricted_zone_needs_explicit_permission(sec, gate, vpass):
    restricted = f.make_zone(is_restricted=True)
    assert go(sec, gate, cred(vpass), zone_id=restricted.pk).outcome == svc.DENIED


def test_unknown_zone_is_a_400(sec, gate, vpass):
    with pytest.raises(BadRequestError):
        go(sec, gate, cred(vpass), zone_id=999999)


def test_br_197_vip_scope_only(sec, gate, vpass):
    vip_zone, other = f.make_zone(is_restricted=True), f.make_zone(is_restricted=True)
    vpass.pass_type = "VIP"
    vpass.save()
    vip = f.make_vip_permission(visitor=vpass.visit_request.visitor)
    vip.zones.add(vip_zone)
    # outside the VIP zones: validated normally
    assert go(sec, gate, cred(vpass), zone_id=other.pk).failures[0].code == "zone_not_permitted"
    res = go(sec, gate, cred(vpass), zone_id=vip_zone.pk)
    assert res.outcome == svc.CHECKED_IN and res.vip_override
    assert res.log.reason == "vip_override"
    assert AuditLog.objects.get(action="vms.gate.checked_in").detail["vip_override"] is True


def test_br_197_vip_window_and_revocation_respected(sec, gate, vpass):
    zone = f.make_zone(is_restricted=True)
    vpass.pass_type = "VIP"
    vpass.save()
    vip = f.make_vip_permission(visitor=vpass.visit_request.visitor,
                                valid_until=timezone.now() - timedelta(minutes=1),
                                valid_from=timezone.now() - timedelta(days=1))
    vip.zones.add(zone)
    assert go(sec, gate, cred(vpass), zone_id=zone.pk).outcome == svc.DENIED


def test_br_197_vip_never_bypasses_blacklist_or_inactivity(sec, gate, vpass):
    zone = f.make_zone(is_restricted=True)
    vpass.pass_type = "VIP"
    vpass.is_active = False
    vpass.save()
    f.make_vip_permission(visitor=vpass.visit_request.visitor).zones.add(zone)
    blacklist(vpass.visit_request.visitor)
    codes = [x.code for x in go(sec, gate, cred(vpass), zone_id=zone.pk).failures]
    assert "blacklisted" in codes and "pass_inactive" in codes


def test_security_role_scoped_to_gate(sec, gate, vpass):
    other_gate = f.make_gate()
    with pytest.raises(PermissionDeniedError):
        go(sec, other_gate, cred(vpass))
    assert VisitLog.objects.count() == 0


def test_zone_scoped_role_covers_the_gates_in_that_zone(gate, vpass):
    f.make_role_assignment(user_id=3002, scope_type="zone", scope_id=gate.zone_id)
    actor = f.make_actor(user_id=3002)
    assert go(actor, gate, cred(vpass)).outcome == svc.CHECKED_IN


def test_expired_role_assignment_denied(gate, vpass):
    now = timezone.now()
    f.make_role_assignment(user_id=3003, starts_at=now - timedelta(days=2),
                           ends_at=now - timedelta(days=1))
    with pytest.raises(PermissionDeniedError):
        go(f.make_actor(user_id=3003), gate, cred(vpass))


def test_revoked_role_assignment_denied(gate, vpass):
    f.make_role_assignment(user_id=3004, revoked_at=timezone.now())
    with pytest.raises(PermissionDeniedError):
        go(f.make_actor(user_id=3004), gate, cred(vpass))


def test_inactive_gate_rejected(sec, gate, vpass):
    gate.is_active = False
    gate.save()
    with pytest.raises(ConflictError):
        go(sec, gate, cred(vpass))


def test_open_check_in_selector(sec, gate, vpass):
    assert gate_sel.open_check_in(vpass.pk) is None
    go(sec, gate, cred(vpass))
    assert gate_sel.open_check_in(vpass.pk) is not None
    f.make_visit_log(visit_pass=vpass, event="check_out")
    assert gate_sel.open_check_in(vpass.pk) is None


# --- override (BW-VMS-10) ------------------------------------------------------------

JUSTIFICATION = "Visitor escorted by the registrar in person"


def denied_log(sec, gate, vpass):
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    return go(sec, gate, cred(vpass)).log


def test_br_085_override_needs_justification_and_admin(sec, gate, vpass, admin):
    log = denied_log(sec, gate, vpass)
    with pytest.raises(BadRequestError):
        svc.override(admin_actor=admin, denial_log_id=log.pk, justification="too short")
    # a security officer holds neither the permission nor the admin role
    with pytest.raises(PermissionDeniedError):
        svc.override(admin_actor=sec, denial_log_id=log.pk, justification=JUSTIFICATION)
    perm_only = f.make_actor(user_id=3099, permissions=["vms.gate.override"])
    with pytest.raises(PermissionDeniedError):          # permission without the role
        svc.override(admin_actor=perm_only, denial_log_id=log.pk, justification=JUSTIFICATION)
    assert GateOverride.objects.count() == 0


def test_override_checks_in_and_records_everything(sec, gate, vpass, admin):
    log = denied_log(sec, gate, vpass)
    res = svc.override(admin_actor=admin, denial_log_id=log.pk, justification=JUSTIFICATION)
    assert res.outcome == svc.CHECKED_IN and res.log.reason == "override_check_in"
    assert res.log.logged_by_user_id == 4001 and res.log.gate_id == gate.pk
    ov = GateOverride.objects.get()
    assert (ov.visit_log_id, ov.admin_user_id, ov.justification) == (log.pk, 4001, JUSTIFICATION)
    assert AuditLog.objects.filter(action="vms.gate.override_check_in").exists()
    assert gate_sel.open_check_in(vpass.pk) is not None


def test_override_once_only(sec, gate, vpass, admin):
    log = denied_log(sec, gate, vpass)
    svc.override(admin_actor=admin, denial_log_id=log.pk, justification=JUSTIFICATION)
    with pytest.raises(ConflictError):
        svc.override(admin_actor=admin, denial_log_id=log.pk, justification=JUSTIFICATION)


def test_br_085_blacklist_denial_cannot_be_overridden(sec, gate, vpass, admin):
    blacklist(vpass.visit_request.visitor)
    log = go(sec, gate, cred(vpass)).log
    with pytest.raises(ConflictError) as e:
        svc.override(admin_actor=admin, denial_log_id=log.pk, justification=JUSTIFICATION)
    assert e.value.code == "not_overridable"


def test_override_blocked_if_blacklisted_since_the_denial(sec, gate, vpass, admin):
    log = denied_log(sec, gate, vpass)
    blacklist(vpass.visit_request.visitor)
    with pytest.raises(ConflictError):
        svc.override(admin_actor=admin, denial_log_id=log.pk, justification=JUSTIFICATION)
    assert not GateOverride.objects.exists()


def test_override_requires_a_denial_log(sec, gate, vpass, admin):
    go(sec, gate, cred(vpass))
    ok = vpass.logs.get()
    from core.api.exceptions import NotFoundError
    with pytest.raises(NotFoundError):
        svc.override(admin_actor=admin, denial_log_id=ok.pk, justification=JUSTIFICATION)


def test_gate_scoped_admin_cannot_override_other_gate(sec, gate, vpass):
    log = denied_log(sec, gate, vpass)
    f.make_role_assignment(user_id=4002, role="admin", scope_type="gate",
                           scope_id=f.make_gate().pk)
    other = f.make_actor(user_id=4002, permissions=["vms.gate.override"])
    with pytest.raises(PermissionDeniedError):
        svc.override(admin_actor=other, denial_log_id=log.pk, justification=JUSTIFICATION)


# --- escalation (UC-019) -------------------------------------------------------------

def test_escalation_flow(sec, gate, vpass, admin):
    log = denied_log(sec, gate, vpass)
    esc = svc.escalate(security_actor=sec, visit_log_id=log.pk, note="Looks suspicious")
    assert esc.status == "open"
    assert Alert.objects.filter(kind="suspicious", ref_id=esc.pk).exists()
    assert Notification.objects.filter(topic="gate.escalated", recipient_user_id=4001).exists()
    with pytest.raises(ConflictError):
        svc.escalate(security_actor=sec, visit_log_id=log.pk, note="again")
    done = svc.resolve_escalation(admin_actor=admin, escalation_id=esc.pk, note="Cleared")
    assert done.status == "resolved" and done.resolved_by_user_id == 4001
    with pytest.raises(ConflictError):
        svc.resolve_escalation(admin_actor=admin, escalation_id=esc.pk, note="again")
    assert Escalation.objects.count() == 1


def test_escalation_needs_a_note_and_scoped_role(sec, gate, vpass):
    log = denied_log(sec, gate, vpass)
    with pytest.raises(BadRequestError):
        svc.escalate(security_actor=sec, visit_log_id=log.pk, note="  ")
    f.make_role_assignment(user_id=3050, scope_type="gate", scope_id=f.make_gate().pk)
    with pytest.raises(PermissionDeniedError):
        svc.escalate(security_actor=f.make_actor(user_id=3050), visit_log_id=log.pk,
                     note="x")


# --- manual entry (UC-020) -----------------------------------------------------------

def test_manual_entry_requires_reason(sec, gate, vpass):
    with pytest.raises(BadRequestError):
        svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_in",
                                reason=" ", gate_id=gate.pk)


def test_manual_check_in_is_flagged_manual(sec, gate, vpass):
    res = svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_in",
                                  reason="Reader offline", gate_id=gate.pk)
    assert res.outcome == svc.CHECKED_IN
    assert res.log.entry_point == "manual" and "Reader offline" in res.log.reason
    assert AuditLog.objects.get(action="vms.gate.manual_entry").detail["manual"] is True


def test_manual_entry_runs_same_validations_for_security(sec, gate, vpass):
    vpass.is_active = False
    vpass.save()
    res = svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_in",
                                  reason="Reader offline", gate_id=gate.pk)
    assert res.outcome == svc.DENIED


def test_manual_entry_admin_may_waive_eligible_but_not_blacklist(gate, vpass, admin):
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    res = svc.record_manual_entry(security_actor=admin, pass_id=vpass.pk, event="check_in",
                                  reason="Reader offline", gate_id=gate.pk)
    assert res.outcome == svc.CHECKED_IN
    f.make_visit_log(visit_pass=vpass, event="check_out")
    blacklist(vpass.visit_request.visitor)
    res = svc.record_manual_entry(security_actor=admin, pass_id=vpass.pk, event="check_in",
                                  reason="Reader offline", gate_id=gate.pk)
    assert res.outcome == svc.DENIED


def test_manual_check_out_completes_the_visit(sec, gate, vpass):
    go(sec, gate, cred(vpass))
    res = svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_out",
                                  reason="Reader offline", gate_id=gate.pk)
    assert res.outcome == "checked_out"
    vpass.visit_request.refresh_from_db()
    assert vpass.visit_request.status == "completed"
    with pytest.raises(ConflictError):
        svc.record_manual_entry(security_actor=sec, pass_id=vpass.pk, event="check_out",
                                reason="again", gate_id=gate.pk)

