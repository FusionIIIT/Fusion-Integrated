"""Gap tests: walk-in registration and contingency (UC-017, UC-033, BR-050, BR-053, BW-07/08)."""
from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError
from modules.vms.models import Notification, VisitRequest
from modules.vms.services import checkout, gate, walkin
from modules.vms.tests import factories as f

from .conftest import HOST, walkin_data

pytestmark = pytest.mark.django_db


def _register(security, **over):
    host_user = over.pop("host_user_id", HOST)
    return walkin.register(security_actor=security, data=walkin_data(**over),
                           host_user_id=host_user)


def test_uc_017_walkin_registration_host_not_found_rejected(security):
    """VMS-UC-017: unknown host yields 400."""
    with pytest.raises(BadRequestError):
        _register(security, host_user_id=987654321)


def test_uc_017_walkin_vip_visitor_skips_host_approval(security):
    """VMS-UC-017: VIP walk-in skips host approval."""
    v = f.make_visitor(full_name="Wanda Walker", phone="9123456789", id_doc_number="WK123456")
    f.make_vip_permission(visitor=v)
    vr = _register(security)
    assert vr.status == "approved"


def test_uc_017_walkin_with_active_preauth_issues_pass(security):
    """VMS-UC-017: pre-auth honoured at walk-in."""
    v = f.make_visitor(full_name="Wanda Walker", phone="9123456789", id_doc_number="WK123456")
    f.make_pre_authorization(visitor=v, host_user_id=HOST)
    vr = _register(security)
    assert vr.status == "approved"


def test_uc_017_walkin_notifies_host_with_decision_link(security):
    """VMS-UC-017: host is notified on registration."""
    _register(security)
    rows = Notification.objects.filter(topic="walkin.submitted", recipient_user_id=HOST)
    assert rows.exists()
    assert all("Wanda Walker" in n.body and "Delivery" in n.body for n in rows)


def test_uc_017_walkin_duplicate_pending_same_visitor_rejected(security):
    """VMS-UC-017 / BR-038: same pending visitor+host rejected for walk-in."""
    _register(security)
    with pytest.raises((BadRequestError, ConflictError)):
        _register(security)


def test_br_050_contingency_before_sla_expiry_rejected_and_exact_boundary_accepted(
        security, admin):
    """VMS-BR-050: SLA instant is inclusive."""
    vr = _register(security)
    t0 = timezone.now() - timedelta(hours=1)
    VisitRequest.objects.filter(pk=vr.pk).update(created_at=t0)
    early = t0 + timedelta(minutes=15, seconds=-1)
    with (mock.patch("django.utils.timezone.now", return_value=early),
          pytest.raises(ConflictError) as e):
        walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    assert e.value.code == "contingency_not_allowed"
    with mock.patch("django.utils.timezone.now", return_value=t0 + timedelta(minutes=15)):
        out, vp = walkin.contingency_decide(admin_actor=admin, request_id=vr.pk,
                                            decision="approve")
    assert out.status == "approved" and vp is not None


def test_br_050_contingency_after_host_responds_late_conflict(security, admin, host):
    """VMS-BR-050: host decision wins over a late contingency."""
    vr = _register(security)
    VisitRequest.objects.filter(pk=vr.pk).update(
        created_at=timezone.now() - timedelta(minutes=30))
    walkin.host_decide_walkin(host, vr.pk, "reject")
    with pytest.raises(ConflictError) as e:
        walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    assert e.value.code == "contingency_not_allowed"
    assert VisitRequest.objects.get(pk=vr.pk).status == "rejected"


def test_br_053_walkin_duration_uses_published_policy_at_registration(security, host):
    """VMS-BR-053: later policy publication does not change the registered window."""
    f.make_published_policy(version=2, walk_in_pass_hours=3, max_visit_hours=8)
    vr = _register(security)
    f.make_published_policy(version=3, walk_in_pass_hours=6, max_visit_hours=8)
    assert vr.scheduled_end - vr.scheduled_start == timedelta(hours=3)
    _, vp = walkin.host_decide_walkin(host, vr.pk, "approve")
    assert vp.valid_until - vp.valid_from == timedelta(hours=3)


def test_bw_07_contingency_pass_checks_in_and_out_completed(security, admin):
    """BW-VMS-07: contingency pass -> check-in -> check-out -> completed."""
    g = f.make_gate()
    vr = _register(security, host_available=False)
    _, vp = walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    res = gate.validate_and_check_in(security_actor=security,
                                     credential={"qr_token": vp.qr_token}, gate_id=g.pk)
    assert res.outcome == gate.CHECKED_IN
    checkout.gate_checkout(security_actor=security, credential=vp.qr_token, gate_id=g.pk)
    assert VisitRequest.objects.get(pk=vr.pk).status == "completed"


def test_bw_08_rejected_walkin_gate_denied(security, host):
    """BW-VMS-08: a rejected walk-in has no pass; gate treats credentials as unknown."""
    g = f.make_gate()
    vr = _register(security)
    _, vp = walkin.host_decide_walkin(host, vr.pk, "reject")
    assert vp is None and not vr.passes.exists()
    res = gate.validate_and_check_in(security_actor=security, credential={"otp": "000000"},
                                     gate_id=g.pk)
    assert res.outcome != gate.CHECKED_IN


def test_uc_033_contingency_admin_notifies_security_and_host(security, admin):
    """VMS-UC-033: host is notified of the contingency decision."""
    vr = _register(security, host_available=False)
    Notification.objects.all().delete()
    walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    assert Notification.objects.filter(recipient_user_id=HOST).exists()


def test_uc_033_contingency_decision_notifies_visitor(security, admin):
    """VMS-UC-033: contingency decision enqueues a visitor notice."""
    vr = _register(security, host_available=False)
    walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="reject")
    assert Notification.objects.filter(topic="request.decided",
                                       recipient_visitor=vr.visitor).exists()


def test_uc_033_contingency_blacklisted_since_registration_blocked(security, admin):
    """VMS-UC-033: blacklist published after registration blocks approval."""
    vr = _register(security, host_available=False)
    live = f.make_blacklist_version(version=1, status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=live, name="x", id_doc_number="WK123456", reason="barred")
    with pytest.raises((BadRequestError, ConflictError)):
        walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
