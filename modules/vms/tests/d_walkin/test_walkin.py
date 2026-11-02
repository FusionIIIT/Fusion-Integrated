"""BW-VMS-06/07/08 and BR-049..053, BR-112."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import Alert, AuditLog, Notification, Visitor, VisitPass, VisitRequest
from modules.vms.services import blacklist, walkin
from modules.vms.tests import factories as f

from .conftest import HOST, walkin_data

pytestmark = pytest.mark.django_db


def _register(security, **over):
    host_user = over.pop("host_user_id", HOST)
    return walkin.register(security_actor=security, data=walkin_data(**over),
                           host_user_id=host_user)


def test_register_requires_permission_and_security_role(security):
    nobody = f.make_actor("staff", permissions=(), user_id=9999)
    with pytest.raises(PermissionDeniedError):
        walkin.register(security_actor=nobody, data=walkin_data(), host_user_id=HOST)
    no_role = f.make_actor("staff", permissions=("vms.walkin.register",), user_id=9998)
    with pytest.raises(PermissionDeniedError):
        walkin.register(security_actor=no_role, data=walkin_data(), host_user_id=HOST)


def test_register_mandatory_fields(security):
    with pytest.raises(BadRequestError) as e:
        _register(security, id_doc_number="")
    assert e.value.code == "missing_fields"


def test_register_host_available_is_pending_and_notifies_host(security):
    vr = _register(security)
    assert (vr.status, vr.source) == ("pending", "walk_in")
    assert vr.contingency_requested_at is None
    assert Notification.objects.filter(topic="walkin.submitted", recipient_user_id=HOST).exists()
    assert AuditLog.objects.filter(action="vms.walkin.registered").exists()


def test_register_host_unavailable_awaits_admin(security):
    vr = _register(security, host_available=False)
    assert vr.status == "awaiting_admin" and vr.contingency_requested_at is not None


def test_br_051_walkin_blacklist_rejected_before_pass(security):
    f.make_blacklist_version(version=1, status="published", published_at=timezone.now())
    blacklist.add_entry(actor=None, name="x", id_doc_number="WK123456", reason="barred")
    with pytest.raises(BadRequestError) as e:
        _register(security)
    assert e.value.code == "visitor_blacklisted"
    assert not VisitRequest.objects.exists() and not Visitor.objects.exists()
    assert not VisitPass.objects.exists()
    assert Alert.objects.filter(kind="blacklist_hit").count() == 1
    assert Notification.objects.filter(topic="walkin.blocked").exists()


def test_walkin_rate_limit(security):
    f.make_published_policy(version=2, walkin_rate_limit_per_hour=2)
    _register(security, id_doc_number="A1")
    _register(security, id_doc_number="A2")
    with pytest.raises(ConflictError) as e:
        _register(security, id_doc_number="A3")
    assert e.value.code == "walkin_rate_limited"


def test_walkin_rate_limit_per_gate(security):
    f.make_published_policy(version=2, walkin_rate_limit_per_hour=1)
    g1, g2 = f.make_gate(), f.make_gate()
    _register(security, gate_id=g1.pk, id_doc_number="A1")
    _register(security, gate_id=g2.pk, id_doc_number="A2")
    with pytest.raises(ConflictError):
        _register(security, gate_id=g1.pk, id_doc_number="A3")


def test_br_053_default_walkin_duration(security, host):
    f.make_published_policy(version=2, walk_in_pass_hours=3, max_visit_hours=8)
    vr = _register(security)
    _, vp = walkin.host_decide_walkin(host, vr.pk, "approve")
    assert vp.pass_type == "WALK_IN"
    assert vp.valid_until - vp.valid_from == timedelta(hours=3)


def test_br_053_duration_capped_by_max_visit_hours(security, host):
    f.make_published_policy(version=2, walk_in_pass_hours=6, max_visit_hours=2)
    vr = _register(security)
    _, vp = walkin.host_decide_walkin(host, vr.pk, "approve")
    assert vp.valid_until - vp.valid_from == timedelta(hours=2)


def test_bw06_host_approves_issues_walkin_pass(security, host):
    vr = _register(security)
    vr, vp = walkin.host_decide_walkin(host, vr.pk, "approve", "ok")
    assert vr.status == "approved" and vp.is_active and vp.issued_for_source == "walk_in"
    assert AuditLog.objects.filter(action="vms.walkin.host_decided").exists()
    assert Notification.objects.filter(topic="request.decided").exists()


def test_host_rejects_walkin_no_pass(security, host):
    vr = _register(security)
    vr, vp = walkin.host_decide_walkin(host, vr.pk, "reject", "no")
    assert vr.status == "rejected" and vp is None and not VisitPass.objects.exists()


def test_host_cannot_decide_twice(security, host):
    vr = _register(security)
    walkin.host_decide_walkin(host, vr.pk, "approve")
    with pytest.raises(ConflictError):
        walkin.host_decide_walkin(host, vr.pk, "reject")


def test_other_host_gets_404(security):
    vr = _register(security)
    other = f.make_actor("faculty", permissions=("vms.request.decide",), user_id=7777)
    with pytest.raises(NotFoundError):
        walkin.host_decide_walkin(other, vr.pk, "approve")


def test_host_decision_on_pre_registered_request_is_404(host):
    vr = f.make_visit_request(host_user_id=HOST)
    with pytest.raises(NotFoundError):
        walkin.host_decide_walkin(host, vr.pk, "approve")


def test_bw07_contingency_approval_issues_pass(security, admin):
    vr = _register(security, host_available=False)
    vr, vp = walkin.contingency_decide(admin_actor=admin, request_id=vr.pk,
                                       decision="approve", note="host away")
    assert vr.status == "approved" and vp.pass_type == "WALK_IN"
    assert vr.contingency_approved_by_user_id == admin.user_id
    log = AuditLog.objects.get(action="vms.walkin.contingency_decided")
    assert log.detail["note"] == "host away"


def test_contingency_reject(security, admin):
    vr = _register(security, host_available=False)
    vr, vp = walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="reject")
    assert vr.status == "rejected" and vp is None


def test_br_049_contingency_only_when_host_unavailable(security, admin):
    vr = _register(security)   # host available, just registered
    with pytest.raises(ConflictError) as e:
        walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    assert e.value.code == "contingency_not_allowed"


def test_br_049_only_admin_role_may_decide(security):
    vr = _register(security, host_available=False)
    sec_only = f.make_actor("staff", permissions=("vms.walkin.contingency_decide",),
                            user_id=security.user_id)
    with pytest.raises(PermissionDeniedError):
        walkin.contingency_decide(admin_actor=sec_only, request_id=vr.pk, decision="approve")


def test_br_049_admin_must_cover_request_zone(security):
    z1, z2 = f.make_zone(), f.make_zone()
    f.make_role_assignment(user_id=4001, role="admin", scope_type="zone", scope_id=z2.pk)
    other_admin = f.make_actor("staff", permissions=("vms.walkin.contingency_decide",),
                               user_id=4001)
    vr = _register(security, host_available=False, zone_ids=[z1.pk])
    with pytest.raises(PermissionDeniedError):
        walkin.contingency_decide(admin_actor=other_admin, request_id=vr.pk, decision="approve")


def test_br_050_contingency_after_sla(security, admin):
    vr = _register(security)                      # host available but silent
    with pytest.raises(ConflictError):
        walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    VisitRequest.objects.filter(pk=vr.pk).update(
        created_at=timezone.now() - timedelta(minutes=16))
    vr, vp = walkin.contingency_decide(admin_actor=admin, request_id=vr.pk, decision="approve")
    assert vr.status == "approved" and vp is not None


def test_list_registrations_filters_status(security):
    _register(security)
    _register(security, host_available=False, id_doc_number="Z9")
    assert walkin.list_registrations(actor=security).count() == 2
    assert walkin.list_registrations(actor=security, status="awaiting_admin").count() == 1
