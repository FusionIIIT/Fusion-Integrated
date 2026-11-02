"""Check-out (BR-105, BR-101), termination (BR-073), roster; BW-VMS-15..18."""
import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import Alert, AuditLog, Notification, VisitLog
from modules.vms.selectors import roster
from modules.vms.services import checkout, passes, termination
from modules.vms.tests import factories as f

from .conftest import HOST, on_site_pass

pytestmark = pytest.mark.django_db
E = VisitLog.Event


# --- check-out ------------------------------------------------------------------------

def test_br_105_checkout_completes_visit(security):
    vp = on_site_pass()
    log = checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    vp.visit_request.refresh_from_db()
    assert log.event == E.CHECK_OUT and vp.visit_request.status == "completed"
    assert AuditLog.objects.filter(action="vms.visit.completed").exists()
    assert Notification.objects.filter(topic="visit.checked_out", recipient_user_id=HOST).exists()
    assert roster.open_check_in(vp) is None


def test_checkout_by_otp(security):
    vp = on_site_pass()
    checkout.gate_checkout(security_actor=security, credential=vp.otp)
    assert not roster.on_site().filter(pk=vp.pk).exists()


def test_checkout_without_checkin_rejected(security):
    vp = f.make_visit_pass(visit_request=f.make_visit_request(status="approved"))
    with pytest.raises(BadRequestError) as e:
        checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert e.value.code == "no_open_check_in"


def test_checkout_twice_rejected(security):
    vp = on_site_pass()
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    with pytest.raises(BadRequestError):
        checkout.gate_checkout(security_actor=security, credential=vp.qr_token)


def test_checkout_unknown_pass_404(security):
    with pytest.raises(NotFoundError):
        checkout.gate_checkout(security_actor=security, credential="nope")


def test_checkout_requires_security_role():
    vp = on_site_pass()
    actor = f.make_actor("staff", permissions=("vms.gate.operate",), user_id=9001)
    with pytest.raises(PermissionDeniedError):
        checkout.gate_checkout(security_actor=actor, credential=vp.qr_token)


def test_walkin_checkout_completes(security):
    vp = on_site_pass(source="walk_in")
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    vp.visit_request.refresh_from_db()
    assert vp.visit_request.status == "completed"


def test_br_101_complete_visit_auto(security):
    vp = on_site_pass()
    log = checkout.complete_visit(vp.pk, "valid_until reached")
    vp.visit_request.refresh_from_db()
    assert log.event == E.AUTO_CHECK_OUT and log.logged_by_user_id is None
    assert vp.visit_request.status == "completed"
    assert checkout.complete_visit(vp.pk, "again") is None      # idempotent


def test_complete_visit_not_on_site_is_noop():
    vp = f.make_visit_pass(visit_request=f.make_visit_request(status="approved"))
    assert checkout.complete_visit(vp.pk, "x") is None


def test_self_checkout_disabled_by_default():
    vp = on_site_pass()
    session = f.make_visitor_session(visitor=vp.visit_request.visitor)
    with pytest.raises(PermissionDeniedError) as e:
        checkout.self_checkout(session=session, pass_token=vp.qr_token)
    assert e.value.code == "self_checkout_disabled"


def test_self_checkout_when_kiosk_enabled():
    f.make_integration_setting(key="kiosk_enabled", value=True)
    vp = on_site_pass()
    session = f.make_visitor_session(visitor=vp.visit_request.visitor)
    log = checkout.self_checkout(session=session, pass_token=vp.qr_token)
    vp.visit_request.refresh_from_db()
    assert log.reason == "self" and vp.visit_request.status == "completed"


def test_self_checkout_other_visitors_pass_404():
    f.make_integration_setting(key="kiosk_enabled", value={"enabled": True})
    vp = on_site_pass()
    stranger = f.make_visitor_session()
    with pytest.raises(NotFoundError):
        checkout.self_checkout(session=stranger, pass_token=vp.qr_token)


# --- termination ----------------------------------------------------------------------

def test_bw15_host_terminates_before_checkin(host):
    vr = f.make_visit_request(status="approved", host_user_id=HOST)
    vp = f.make_visit_pass(visit_request=vr)
    termination.terminate(actor=host, pass_id=vp.pk, reason="policy breach")
    vp.refresh_from_db()
    vr.refresh_from_db()
    assert not vp.is_active and vp.termination_reason == "policy breach"
    assert vp.terminated_at and vp.terminated_by_user_id == HOST
    assert vr.status == "completed"
    assert not VisitLog.objects.filter(event=E.TERMINATED).exists()
    assert not Alert.objects.exists()
    assert Notification.objects.filter(topic="pass.terminated").exists()
    assert AuditLog.objects.filter(action="vms.pass.terminated").exists()


def test_bw17_admin_terminates_before_checkin(admin):
    vr = f.make_visit_request(status="approved", host_user_id=HOST)
    vp = f.make_visit_pass(visit_request=vr)
    termination.terminate(actor=admin, pass_id=vp.pk, reason="breach")
    vp.refresh_from_db()
    assert not vp.is_active
    assert Notification.objects.filter(topic="pass.terminated", recipient_user_id=HOST).exists()


def test_terminate_on_site_alerts_security(host, security):
    vp = on_site_pass()
    termination.terminate(actor=host, pass_id=vp.pk, reason="trespass")   # BW-16
    vp.visit_request.refresh_from_db()
    assert VisitLog.objects.filter(visit_pass=vp, event=E.TERMINATED).exists()
    alert = Alert.objects.get()
    assert alert.kind == "suspicious" and alert.ref_id == vp.pk
    assert alert.detail["action"] == "escort_out"
    # still on site, pending exit; request completes on physical check-out
    assert vp.visit_request.status == "approved"
    assert roster.on_site().filter(pk=vp.pk).exists()
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    vp.visit_request.refresh_from_db()
    assert vp.visit_request.status == "completed"
    assert not roster.on_site().filter(pk=vp.pk).exists()


def test_bw18_admin_terminates_on_site(admin):
    vp = on_site_pass()
    termination.terminate(actor=admin, pass_id=vp.pk, reason="breach")
    assert Alert.objects.filter(kind="suspicious").count() == 1


def test_terminate_requires_reason(host):
    vp = on_site_pass()
    for reason in ("", "   "):
        with pytest.raises(BadRequestError) as e:
            termination.terminate(actor=host, pass_id=vp.pk, reason=reason)
        assert e.value.code == "reason_required"


def test_host_cannot_terminate_other_hosts_visitor_404():
    vp = on_site_pass(host_id=555)
    other = f.make_actor("faculty", permissions=("vms.pass.terminate",), user_id=HOST)
    with pytest.raises(NotFoundError):
        termination.terminate(actor=other, pass_id=vp.pk, reason="x")
    vp.refresh_from_db()
    assert vp.is_active


def test_br_073_only_host_or_admin_terminates(security):
    vp = on_site_pass()
    with pytest.raises(PermissionDeniedError):      # no terminate permission
        termination.terminate(actor=f.make_actor("staff", user_id=1), pass_id=vp.pk, reason="x")
    sec = f.make_actor("staff", permissions=("vms.pass.terminate",), user_id=security.user_id)
    with pytest.raises(NotFoundError):              # security is neither host nor admin
        termination.terminate(actor=sec, pass_id=vp.pk, reason="x")


def test_terminate_out_of_scope_admin_404():
    z1, z2 = f.make_zone(), f.make_zone()
    f.make_role_assignment(user_id=4001, role="admin", scope_type="zone", scope_id=z2.pk)
    adm = f.make_actor("staff", permissions=("vms.pass.terminate",), user_id=4001)
    vp = on_site_pass()
    vp.allowed_zones.set([z1])
    with pytest.raises(NotFoundError):
        termination.terminate(actor=adm, pass_id=vp.pk, reason="x")
    vp.allowed_zones.set([z2])
    termination.terminate(actor=adm, pass_id=vp.pk, reason="x")


def test_terminate_twice_conflicts(host):
    vp = on_site_pass()
    termination.terminate(actor=host, pass_id=vp.pk, reason="x")
    with pytest.raises(ConflictError):
        termination.terminate(actor=host, pass_id=vp.pk, reason="again")


def test_passes_terminate_pass_delegates(host):
    vp = on_site_pass()
    passes.terminate_pass(actor=host, pass_id=vp.pk, reason="via passes")
    vp.refresh_from_db()
    assert vp.termination_reason == "via passes"


# --- roster ---------------------------------------------------------------------------

def test_roster_excludes_checked_out(security):
    inside, left = on_site_pass(), on_site_pass()
    checkout.gate_checkout(security_actor=security, credential=left.qr_token)
    ids = set(roster.on_site().values_list("pk", flat=True))
    assert ids == {inside.pk}


def test_roster_zone_filter_and_zone_moves():
    z1, z2 = f.make_zone(), f.make_zone()
    vp = on_site_pass()
    VisitLog.objects.filter(visit_pass=vp).update(zone=z1)
    assert roster.on_site(zone=z1).count() == 1 and roster.on_site(zone=z2).count() == 0
    f.make_visit_log(visit_pass=vp, event=E.ZONE_ALLOWED, zone=z2)
    assert roster.on_site(zone=z2).count() == 1 and roster.on_site(zone=z1).count() == 0
    f.make_visit_log(visit_pass=vp, event=E.DENIED)       # denial does not change presence
    assert roster.on_site().count() == 1


def test_roster_is_one_query(django_assert_num_queries):
    for _ in range(3):
        on_site_pass()
    with django_assert_num_queries(1):
        rows = list(roster.on_site())
        _ = [r.visit_request.visitor.full_name for r in rows]


def test_visit_history_lists_visitor_logs():
    vp = on_site_pass()
    f.make_visit_log(visit_pass=vp, event=E.CHECK_OUT)
    assert roster.visit_history(vp.visit_request.visitor).count() == 2
