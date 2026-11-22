"""Extension request/decision rules (UC-034; BR-193, BR-194, BR-129)."""
from datetime import timedelta

import pytest
from freezegun import freeze_time

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import AuditLog, ExtensionRequest, Notification
from modules.vms.services import extensions as svc
from modules.vms.tests import factories as f

from .conftest import on_site_pass

pytestmark = pytest.mark.django_db
T0 = "2026-03-02 09:00:00+00:00"


def _req(host, vp, hours, reason="Overran"):
    return svc.request_extension(requester=host, request_id=vp.visit_request_id,
                                 new_end=vp.visit_request.scheduled_start + timedelta(hours=hours),
                                 reason=reason)


@freeze_time(T0)
def test_br_193_extension_within_cap_host_direct(host):
    vp = on_site_pass(hours=2)
    ext = _req(host, vp, 6)
    vp.refresh_from_db()
    vp.visit_request.refresh_from_db()
    assert ext.status == "approved" and ext.decided_by_user_id == host.user_id
    assert vp.valid_until == vp.visit_request.scheduled_end == vp.valid_from + timedelta(hours=6)


@freeze_time(T0)
def test_br_194_beyond_cap_needs_admin(host, admin):
    vp = on_site_pass(hours=2)
    before = vp.valid_until
    ext = _req(host, vp, 10)
    vp.refresh_from_db()
    assert ext.status == "pending" and vp.valid_until == before
    assert Notification.objects.filter(topic="extension.requested",
                                       recipient_user_id=admin.user_id).exists()


@freeze_time(T0)
def test_cap_exceeded_without_admin_host_cannot_decide(host):
    vp = on_site_pass(hours=2)
    ext = _req(host, vp, 10)
    with pytest.raises(PermissionDeniedError):
        svc.decide_extension(admin_actor=host, extension_id=ext.pk, decision="approve")
    vp.refresh_from_db()
    assert vp.valid_until == vp.valid_from + timedelta(hours=2)


@freeze_time(T0)
def test_admin_without_role_assignment_cannot_decide(host):
    ext = _req(host, on_site_pass(), 10)
    nobody = f.make_actor("staff", permissions=("vms.extension.decide",), user_id=4444)
    with pytest.raises(PermissionDeniedError):
        svc.decide_extension(admin_actor=nobody, extension_id=ext.pk, decision="approve")


@freeze_time(T0)
def test_extension_updates_pass_and_request_atomically(host, admin):
    vp = on_site_pass(hours=2)
    ext = _req(host, vp, 10)
    svc.decide_extension(admin_actor=admin, extension_id=ext.pk, decision="approve", note="ok")
    vp.refresh_from_db()
    vp.visit_request.refresh_from_db()
    ext.refresh_from_db()
    end = vp.valid_from + timedelta(hours=10)
    assert vp.valid_until == end and vp.visit_request.scheduled_end == end
    assert ext.status == "approved" and ext.decided_by_user_id == admin.user_id
    assert AuditLog.objects.filter(action="vms.extension.approved").exists()
    n = Notification.objects.get(topic="extension.decided", channel="inapp")
    assert n.recipient_user_id == host.user_id


@freeze_time(T0)
def test_br_129_extension_uses_request_policy_snapshot(host):
    from django.utils import timezone
    vp = on_site_pass(hours=2)
    f.make_published_policy(version=2, max_visit_hours=24,
                            published_at=timezone.now() + timedelta(minutes=1))
    with freeze_time("2026-03-02 09:05:00+00:00"):
        # v2 is now in force, but this request froze v1 (8 h cap): 10 h still needs an Admin.
        assert _req(host, vp, 10).status == "pending"


@freeze_time(T0)
def test_rejected_extension_no_change(host, admin):
    vp = on_site_pass(hours=2)
    before = vp.valid_until
    ext = _req(host, vp, 10)
    svc.decide_extension(admin_actor=admin, extension_id=ext.pk, decision="reject", note="no")
    vp.refresh_from_db()
    vp.visit_request.refresh_from_db()
    ext.refresh_from_db()
    assert ext.status == "rejected" and vp.valid_until == before
    assert vp.visit_request.scheduled_end == before
    assert Notification.objects.filter(topic="extension.decided").exists()


@freeze_time(T0)
def test_decided_extension_cannot_be_decided_again(host, admin):
    ext = _req(host, on_site_pass(), 10)
    svc.decide_extension(admin_actor=admin, extension_id=ext.pk, decision="reject")
    with pytest.raises(ConflictError):
        svc.decide_extension(admin_actor=admin, extension_id=ext.pk, decision="approve")


@freeze_time(T0)
def test_one_pending_extension_per_visit(host):
    vp = on_site_pass(hours=2)
    _req(host, vp, 10)
    with pytest.raises(ConflictError) as e:
        _req(host, vp, 11)
    assert e.value.code == "extension_pending"
    assert ExtensionRequest.objects.count() == 1


@freeze_time(T0)
def test_blacklist_blocks_extension(host):
    from modules.vms.tests.b_gate.conftest import blacklist
    vp = on_site_pass(hours=2)
    blacklist(vp.visit_request.visitor)
    with pytest.raises(ConflictError) as e:
        _req(host, vp, 4)
    assert e.value.code == "blacklisted"


@freeze_time(T0)
def test_blacklist_blocks_approval(host, admin):
    from modules.vms.tests.b_gate.conftest import blacklist
    vp = on_site_pass(hours=2)
    ext = _req(host, vp, 10)
    blacklist(vp.visit_request.visitor)
    with pytest.raises(ConflictError):
        svc.decide_extension(admin_actor=admin, extension_id=ext.pk, decision="approve")
    vp.refresh_from_db()
    assert vp.valid_until == vp.valid_from + timedelta(hours=2)


@freeze_time(T0)
def test_not_the_host_is_404(other_host):
    vp = on_site_pass()
    with pytest.raises(NotFoundError):
        _req(other_host, vp, 4)


@freeze_time(T0)
def test_new_end_must_be_later(host):
    with pytest.raises(BadRequestError):
        _req(host, on_site_pass(hours=4), 3)


@freeze_time(T0)
def test_terminated_pass_cannot_be_extended(host):
    vp = on_site_pass()
    vp.is_active = False
    vp.save()
    with pytest.raises(ConflictError):
        _req(host, vp, 4)


@freeze_time(T0)
def test_completed_visit_cannot_be_extended(host):
    vp = on_site_pass()
    vp.visit_request.status = "completed"
    vp.visit_request.save()
    with pytest.raises(ConflictError):
        _req(host, vp, 4)
