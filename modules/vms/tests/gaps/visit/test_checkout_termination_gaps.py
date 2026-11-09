"""Gap tests: check-out, self check-out and termination (UC-016/021/031/036, BR-073, BW-16/18)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.models import Alert, AuditLog, Notification, VisitLog, VisitRequest
from modules.vms.services import checkout, termination
from modules.vms.tests import factories as f

from .conftest import ADMIN, HOST, SEC, on_site_pass

pytestmark = pytest.mark.django_db
BASE = "/api/v1/vms/"


def test_uc_021_checkout_notifies_host(security):
    """VMS-UC-021: host notified on check-out."""
    vp = on_site_pass()
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert Notification.objects.filter(topic="visit.checked_out", recipient_user_id=HOST).exists()


def test_uc_021_checkout_expired_pass_still_allowed_when_inside(security):
    """VMS-UC-021: checkout after validity end works."""
    vp = on_site_pass()
    vp.valid_until = timezone.now() - timedelta(hours=1)
    vp.save()
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert VisitRequest.objects.get(pk=vp.visit_request_id).status == "completed"


def test_uc_021_checkout_records_exit_gate_and_time(security):
    """VMS-UC-021: exit log carries gate and actor."""
    g = f.make_gate()
    vp = on_site_pass()
    log = checkout.gate_checkout(security_actor=security, credential=vp.qr_token, gate_id=g.pk)
    assert (log.event, log.gate_id, log.logged_by_user_id) == ("check_out", g.pk, SEC)
    assert log.visit_pass_id == vp.pk and log.created_at is not None


def test_uc_021_checkout_without_open_checkin_rejected(security):
    """VMS-UC-021: nothing to check out is a 400."""
    vp = f.make_visit_pass(visit_request=f.make_visit_request(status="approved"))
    with pytest.raises(BadRequestError) as e:
        checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert e.value.code == "no_open_check_in"


def test_uc_031_self_checkout_requires_on_site_status():
    """VMS-UC-031: not inside is rejected."""
    f.make_integration_setting(key="kiosk_enabled", value=True)
    vp = f.make_visit_pass(visit_request=f.make_visit_request(status="approved"))
    with pytest.raises(BadRequestError) as e:
        checkout.self_checkout(session=f.make_visitor_session(visitor=vp.visit_request.visitor),
                               pass_token=vp.qr_token)
    assert e.value.code == "no_open_check_in"


def test_uc_031_self_checkout_after_termination_rejected():
    """VMS-UC-031: terminated-before-entry visit cannot self check out."""
    f.make_integration_setting(key="kiosk_enabled", value=True)
    vp = f.make_visit_pass(visit_request=f.make_visit_request(status="approved",
                                                              host_user_id=HOST))
    host = f.make_actor("faculty", permissions=("vms.pass.terminate",), user_id=HOST)
    termination.terminate(actor=host, pass_id=vp.pk, reason="no")
    with pytest.raises(BadRequestError):
        checkout.self_checkout(session=f.make_visitor_session(visitor=vp.visit_request.visitor),
                               pass_token=vp.qr_token)


def test_uc_031_self_checkout_other_visitors_pass_not_found():
    """VMS-UC-031: another visitor's token is a 404."""
    f.make_integration_setting(key="kiosk_enabled", value=True)
    vp = on_site_pass()
    with pytest.raises(NotFoundError):
        checkout.self_checkout(session=f.make_visitor_session(), pass_token=vp.qr_token)


def test_uc_016_host_terminate_notifies_visitor(host):
    """VMS-UC-016: visitor notified of termination."""
    vp = on_site_pass()
    termination.terminate(actor=host, pass_id=vp.pk, reason="breach")
    n = Notification.objects.filter(topic="pass.terminated",
                                    recipient_visitor=vp.visit_request.visitor)
    assert n.exists() and "exit" in n.first().body.lower()
    assert not Notification.objects.filter(topic="pass.terminated",
                                           recipient_user_id=HOST).exists()


def test_uc_016_host_terminate_on_site_deactivates_pass_but_visit_stays_until_exit(host):
    """VMS-UC-016: on-site termination keeps the visit approved (pending exit)."""
    vp = on_site_pass()
    termination.terminate(actor=host, pass_id=vp.pk, reason="breach")
    vp.refresh_from_db()
    assert not vp.is_active and vp.termination_reason == "breach"
    assert vp.terminated_by_user_id == HOST
    assert VisitRequest.objects.get(pk=vp.visit_request_id).status == "approved"
    assert VisitLog.objects.filter(visit_pass=vp, event="terminated").exists()
    assert Alert.objects.filter(ref_type="visit_pass", ref_id=vp.pk).exists()


def test_uc_016_host_terminate_before_checkin_ends_visit(host):
    """VMS-UC-016: pre-entry termination ends the request immediately."""
    vp = f.make_visit_pass(visit_request=f.make_visit_request(status="approved",
                                                              host_user_id=HOST))
    termination.terminate(actor=host, pass_id=vp.pk, reason="cancelled")
    assert VisitRequest.objects.get(pk=vp.visit_request_id).status == "completed"


def test_uc_016_terminate_twice_conflicts(host):
    """VMS-UC-016: second termination is a 409."""
    vp = on_site_pass()
    termination.terminate(actor=host, pass_id=vp.pk, reason="a")
    with pytest.raises(ConflictError) as e:
        termination.terminate(actor=host, pass_id=vp.pk, reason="b")
    assert e.value.code == "pass_not_active"


def test_bw_16_after_termination_gate_exit_completes_visit(host, security):
    """BW-VMS-16: terminated on-site visitor exits via check-out -> completed."""
    vp = on_site_pass()
    termination.terminate(actor=host, pass_id=vp.pk, reason="breach")
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert VisitRequest.objects.get(pk=vp.visit_request_id).status == "completed"
    assert AuditLog.objects.filter(action="vms.visit.completed").exists()


def test_bw_18_admin_terminate_on_site_then_exit_completed(admin, security):
    """BW-VMS-18: admin terminates on-site; exit completes the visit."""
    vp = on_site_pass(host_id=555)
    termination.terminate(actor=admin, pass_id=vp.pk, reason="policy")
    assert VisitRequest.objects.get(pk=vp.visit_request_id).status == "approved"
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    assert VisitRequest.objects.get(pk=vp.visit_request_id).status == "completed"


def test_uc_036_admin_terminate_requires_reason_and_audits(admin):
    """VMS-UC-036: blank reason rejected; success audits the admin as actor."""
    vp = on_site_pass(host_id=555)
    with pytest.raises(BadRequestError) as e:
        termination.terminate(actor=admin, pass_id=vp.pk, reason="   ")
    assert e.value.code == "reason_required"
    termination.terminate(actor=admin, pass_id=vp.pk, reason="policy breach")
    row = AuditLog.objects.get(action="vms.pass.terminated")
    assert row.actor_user_id == ADMIN and row.detail["by"] == "admin"
    assert row.detail["reason"] == "policy breach"
    assert Notification.objects.filter(topic="pass.terminated", recipient_user_id=555).exists()


@pytest.mark.xfail(strict=True, reason="BUG: terminate() silently deactivates the pass of an already completed visit")
def test_uc_036_admin_terminate_completed_visit_conflicts(admin, security):
    """VMS-UC-036: terminal state cannot be terminated."""
    vp = on_site_pass(host_id=555)
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token)
    with pytest.raises(ConflictError):
        termination.terminate(actor=admin, pass_id=vp.pk, reason="late")


def test_br_073_security_and_visitor_cannot_terminate(api_as):
    """VMS-BR-073: security without terminate permission and anonymous are denied."""
    f.make_role_assignment(user_id=SEC, role="security")
    vp = on_site_pass()
    url = BASE + f"visit/passes/{vp.pk}/terminate"
    sec = api_as(user_id=SEC, permissions=["vms.gate.operate", "vms.walkin.register"])
    assert sec.post(url, {"reason": "x"}, format="json").status_code == 403
    assert api_as(anonymous=True).post(url, {"reason": "x"}, format="json").status_code == 401
    vp.refresh_from_db()
    assert vp.is_active


def test_br_073_terminate_unknown_pass_404(host):
    """VMS-BR-073: unknown pass id is a 404."""
    with pytest.raises(NotFoundError):
        termination.terminate(actor=host, pass_id=999999, reason="x")
