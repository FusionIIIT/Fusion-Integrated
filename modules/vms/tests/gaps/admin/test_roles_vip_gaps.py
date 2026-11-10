from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.vms.models import AuditLog, Notification, RoleAssignment
from modules.vms.services import roles, vip
from modules.vms.services.common import authz
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db
BASE = "/api/v1/vms/"


def _ends(days=30):
    return timezone.now() + timedelta(days=days)


def test_uc_001_assign_role_notifies_assignee(directory, super_actor):
    """VMS-UC-001: assignee receives a notice."""
    directory[10] = "staff"
    roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_ends())
    assert Notification.objects.filter(recipient_user_id=10).exists()


def test_uc_001_revoke_role_audited_and_effective_immediately(directory, super_actor):
    """VMS-UC-001: revoke is audited and gate access is lost at once."""
    directory[10] = "staff"
    row = roles.assign(actor=super_actor, user_id=10, role="security",
                       starts_at=timezone.now() - timedelta(minutes=1), ends_at=_ends())
    holder = f.make_actor(user_id=10)
    assert authz.require_role(holder, "security") == row
    roles.revoke(actor=super_actor, assignment_id=row.pk)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(holder, "security")
    assert AuditLog.objects.filter(action="vms.role.revoked", entity_id=str(row.pk)).exists()


def test_br_181_role_end_before_start_rejected(directory, super_actor):
    """VMS-BR-181: an inverted window is a 400."""
    directory[10] = "staff"
    start = timezone.now() + timedelta(days=5)
    with pytest.raises(BadRequestError):
        roles.assign(actor=super_actor, user_id=10, role="security", starts_at=start,
                     ends_at=start - timedelta(days=1))
    assert not RoleAssignment.objects.exists()


def test_br_181_role_end_in_past_rejected(directory, super_actor):
    """VMS-BR-181: an end already past is refused."""
    directory[10] = "staff"
    with pytest.raises(BadRequestError):
        roles.assign(actor=super_actor, user_id=10, role="security",
                     starts_at=timezone.now() - timedelta(days=3),
                     ends_at=timezone.now() - timedelta(days=1))


def test_br_183_handoff_target_must_hold_role_in_scope(directory, super_actor):
    """VMS-BR-183: handoff to an ineligible or unknown user is rejected, nothing moves."""
    directory.update({10: "staff", 11: "student"})
    old = roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_ends())
    for target, code in ((11, "ineligible_user"), (99, "unknown_user")):
        with pytest.raises(BadRequestError) as e:
            roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=target)
        assert e.value.code == code
    old.refresh_from_db()
    assert old.revoked_at is None and RoleAssignment.objects.count() == 1


def test_br_183_handoff_does_not_touch_other_scope_items(directory, super_actor):
    """VMS-BR-183: out-of-scope work is neither counted nor changed."""
    directory.update({10: "staff", 11: "faculty"})
    zone, other = f.make_zone(), f.make_zone()
    req = f.make_visit_request(status="awaiting_admin")
    req.requested_zones.add(other)
    alert = f.make_alert(detail={"zone_id": other.pk})
    old = roles.assign(actor=super_actor, user_id=10, role="admin", scope_type="zone",
                       scope_id=zone.pk, ends_at=_ends())
    _, counts = roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=11)
    assert counts.total == 0
    assert not Notification.objects.filter(topic="role.handoff").exists()
    req.refresh_from_db()
    alert.refresh_from_db()
    assert req.status == "awaiting_admin" and alert.status == "open"


def test_br_182_reassign_moves_role_immediately(directory, super_actor):
    """VMS-BR-182: old holder loses the role now, new holder has it now."""
    directory.update({10: "staff", 11: "faculty"})
    old = roles.assign(actor=super_actor, user_id=10, role="security",
                       starts_at=timezone.now() - timedelta(minutes=1), ends_at=_ends())
    new, _ = roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=11)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=10), "security")
    assert authz.require_role(f.make_actor(user_id=11), "security") == new


def test_br_184_security_cannot_assign_roles(api_as):
    """VMS-BR-184: a Security holder (no vms.role.assign) gets 403."""
    f.make_role_assignment(user_id=50, role="security")
    client = api_as(user_id=50, permissions=["vms.gate.scan"])
    r = client.post(BASE + "roles", {"user_id": 9, "role": "security",
                                     "ends_at": _ends().isoformat()}, format="json")
    assert r.status_code == 403


def test_br_185_implicit_host_role_not_listed_in_assignments(super_actor):
    """VMS-BR-185: hosts need no row yet still resolve as hosts."""
    faculty = f.make_actor(kind="faculty", user_id=60)
    assert authz.is_host(faculty)
    assert not roles.my_roles(faculty).exists()
    assert not RoleAssignment.objects.filter(user_id=60).exists()
    assert not roles.list_active(actor=super_actor).exists()


# --- VIP ----------------------------------------------------------------------------

def test_uc_003_vip_list_filters_active_expired_revoked(super_actor):
    """VMS-UC-003: active_only excludes expired and revoked grants."""
    now = timezone.now()
    live = f.make_vip_permission()
    f.make_vip_permission(valid_from=now - timedelta(days=9), valid_until=now - timedelta(days=1))
    f.make_vip_permission(revoked_at=now)
    assert vip.list_permissions(actor=super_actor).count() == 3
    assert list(vip.list_permissions(actor=super_actor, active_only=True)) == [live]


def test_uc_003_vip_grant_for_blacklisted_visitor_rejected(super_actor):
    """VMS-UC-003: blacklist beats VIP at grant time."""
    ver = f.make_blacklist_version(status="published", published_at=timezone.now())
    f.make_blacklist_entry(version=ver, id_doc_number="BAD1")
    visitor = f.make_visitor(id_doc_number="BAD1")
    with pytest.raises(BadRequestError):
        vip.grant(actor=super_actor, visitor_id=visitor.pk, valid_until=_ends())


def test_br_196_vip_grant_by_admin_without_super_admin_forbidden(admin_actor):
    """VMS-BR-196: an Admin (no vms.vip.manage) cannot create or revoke VIP."""
    row = f.make_vip_permission()
    with pytest.raises(PermissionDeniedError):
        vip.grant(actor=admin_actor, visitor_id=row.visitor_id, valid_until=_ends(90))
    with pytest.raises(PermissionDeniedError):
        vip.revoke(actor=admin_actor, vip_id=row.pk)
    row.refresh_from_db()
    assert row.revoked_at is None


def test_br_196_vip_grant_audit_actor_is_super_admin(super_actor):
    """VMS-BR-196: the audit row names the granting Super Admin."""
    row = vip.grant(actor=super_actor, visitor_id=f.make_visitor().pk, valid_until=_ends())
    log = AuditLog.objects.get(action="vms.vip.granted", entity_id=str(row.pk))
    assert log.actor_user_id == super_actor.user_id
    assert row.granted_by_user_id == super_actor.user_id
