"""Gap tests: pre-authorisation and VIP bypass edge cases, blacklist precedence
(UC-014, UC-003, BR-195/196, BR-051, BR-112, BW-VMS-05)."""
from datetime import timedelta

import pytest
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.vms.models import AccessPolicy, AuditLog, PreAuthorization, VipPermission
from modules.vms.services import registration, vip
from modules.vms.tests import factories as f
from modules.vms.tests.gaps.registration.conftest import HOST_ID, local_slot, payload

pytestmark = pytest.mark.django_db


def _submit(visitor, **over):
    d = payload(**over)
    for k in ("scheduled_start", "scheduled_end"):
        if isinstance(d[k], str):
            d[k] = parse_datetime(d[k])
    return registration.submit(session_visitor=visitor, data=d)


@pytest.fixture
def me():
    return f.make_visitor(id_doc_type="", id_doc_number="", full_name="",
                          email="ravi@example.com")


@pytest.fixture
def person():
    return f.make_visitor(id_doc_type="passport", id_doc_number="P1234567",
                          full_name="Ravi Kumar")


def test_uc_014_preauth_second_visit_uses_grant_and_decrements_remaining(me, person):
    """VMS-UC-014: each use increments the used count; the N+1th falls back to approval."""
    pa = f.make_pre_authorization(visitor=person, host_user_id=HOST_ID, max_visits=2)
    for day in (1, 2):
        s, e = local_slot(days=day)
        assert _submit(me, scheduled_start=s, scheduled_end=e).status == "approved"
    pa.refresh_from_db()
    assert pa.used_visits == 2
    s, e = local_slot(days=3)
    assert _submit(me, scheduled_start=s, scheduled_end=e).status == "pending"
    pa.refresh_from_db()
    assert pa.used_visits == 2


def test_uc_014_preauth_expired_grant_falls_back_to_pending_host(me, person):
    """VMS-UC-014: an expired grant means the normal approval path."""
    f.make_pre_authorization(visitor=person, host_user_id=HOST_ID,
                             valid_from=timezone.now() - timedelta(days=5),
                             valid_until=timezone.now() - timedelta(days=1))
    assert _submit(me).status == "pending"


def test_uc_014_preauth_scope_mismatch_zone_not_applied(me, person):
    """VMS-UC-014: a request for a zone outside the grant is not auto-approved."""
    allowed, other = f.make_zone(), f.make_zone()
    pa = f.make_pre_authorization(visitor=person, host_user_id=HOST_ID)
    pa.zones.set([allowed])
    vr = _submit(me, requested_zones=[other])
    assert vr.status == "pending" and vr.source == "pre_registered"
    pa.refresh_from_db()
    assert pa.used_visits == 0


def test_uc_014_preauth_scope_mismatch_window_not_applied(me, person):
    """VMS-UC-014: a visit extending past the grant's validity is not auto-approved."""
    f.make_pre_authorization(visitor=person, host_user_id=HOST_ID,
                             valid_until=timezone.now() + timedelta(hours=3))
    assert _submit(me).status == "pending"       # slot starts tomorrow


def test_br_195_preauth_pass_validity_still_capped_by_policy(me, person):
    """VMS-BR-195: bypassing approval does not bypass the BR-193 duration cap."""
    AccessPolicy.objects.update(max_visit_hours=1)
    f.make_pre_authorization(visitor=person, host_user_id=HOST_ID)
    vp = _submit(me).passes.get()           # requested window is 2 h
    assert vp.valid_until - vp.valid_from == timedelta(hours=1)


def test_br_195_preauth_issue_is_audited(me, person):
    """VMS-BR-195: a bypass use is recorded in the audit trail."""
    f.make_pre_authorization(visitor=person, host_user_id=HOST_ID)
    vr = _submit(me)
    assert AuditLog.objects.filter(action="vms.preauth.used").exists()
    assert AuditLog.objects.filter(action="vms.request.submitted",
                                   entity_id=str(vr.pk)).exists()


def test_uc_003_vip_grant_expired_reverts_to_standard_flow(me, person):
    """VMS-UC-003: an expired VIP grant no longer bypasses the host."""
    f.make_vip_permission(visitor=person, valid_from=timezone.now() - timedelta(days=3),
                          valid_until=timezone.now() - timedelta(days=1))
    vr = _submit(me)
    assert vr.status == "pending" and vr.source == "pre_registered"


def test_bw_vms_05_bw05_vip_revoked_before_registration_takes_normal_path(me, person):
    """BW-VMS-05: a revoked VIP follows the BW-01 host-approval path."""
    f.make_vip_permission(visitor=person, revoked_at=timezone.now())
    vr = _submit(me)
    assert vr.status == "pending" and not vr.passes.exists()


def test_br_196_vip_grant_by_actor_without_permission_forbidden(person):
    """VMS-BR-196: creating or revoking a VIP grant needs vms.vip.manage."""
    plain = f.make_actor(kind="staff", user_id=4001, permissions=["vms.report.view"])
    with pytest.raises(PermissionDeniedError):
        vip.grant(actor=plain, valid_until=timezone.now() + timedelta(days=1),
                  visitor_id=person.pk)
    grant = f.make_vip_permission(visitor=person)
    with pytest.raises(PermissionDeniedError):
        vip.revoke(actor=plain, vip_id=grant.pk)
    assert VipPermission.objects.filter(pk=grant.pk, revoked_at__isnull=True).exists()


def test_br_196_vip_grant_audit_records_scope_and_validity(person):
    """VMS-BR-196: audit detail for a VIP grant contains scope and valid_until."""
    zone = f.make_zone()
    admin = f.make_actor(kind="staff", user_id=1, permissions=["vms.vip.manage"])
    until = timezone.now() + timedelta(days=5)
    grant = vip.grant(actor=admin, valid_until=until, visitor_id=person.pk, zone_ids=[zone.pk])
    row = AuditLog.objects.get(action="vms.vip.granted", entity_id=str(grant.pk))
    assert row.detail["zone_ids"] == [zone.pk]
    assert row.detail["valid_until"] == until.isoformat()


def test_br_051_preauth_registration_blacklist_hit_blocked_despite_grant(me, person):
    """VMS-BR-051: blacklist beats the pre-authorisation bypass at registration."""
    pa = f.make_pre_authorization(visitor=person, host_user_id=HOST_ID)
    v = f.make_blacklist_version(status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=v, id_doc_number="P1234567")
    with pytest.raises(BadRequestError) as e:
        _submit(me)
    assert e.value.code == "visitor_blacklisted"
    assert PreAuthorization.objects.get(pk=pa.pk).used_visits == 0


def test_br_112_blacklist_checkpoint_registration_uses_published_version_only(me):
    """VMS-BR-112: draft blacklist entries do not block registration."""
    draft = f.make_blacklist_version(status="draft")
    f.make_blacklist_entry(version=draft, id_doc_number="P1234567")
    assert _submit(me).status == "pending"


def test_br_112_blacklist_expired_entry_does_not_block(me):
    """VMS-BR-112: an entry past its expiry date no longer blocks registration."""
    v = f.make_blacklist_version(status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=v, id_doc_number="P1234567",
                           expiry_date=(timezone.now() - timedelta(days=2)).date())
    assert _submit(me).status == "pending"
