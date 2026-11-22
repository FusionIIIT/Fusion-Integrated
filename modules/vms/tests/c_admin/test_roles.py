from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.vms.models import AuditLog, Notification, RoleAssignment
from modules.vms.services import roles
from modules.vms.services.common import authz
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


def _ends(days=30):
    return timezone.now() + timedelta(days=days)


def test_br_184_admin_cannot_assign_admin(directory):
    directory[10] = "faculty"
    admin = f.make_actor(permissions=[
        "vms.policy.manage", "vms.policy.publish", "vms.blacklist.manage", "vms.zone.manage"])
    for role in ("admin", "security"):
        with pytest.raises(PermissionDeniedError):
            roles.assign(actor=admin, user_id=10, role=role, ends_at=_ends())
    assert not RoleAssignment.objects.exists()


def test_super_admin_assigns_and_audits(directory, super_actor):
    directory[10] = "staff"
    row = roles.assign(actor=super_actor, user_id=10, role="admin", ends_at=_ends())
    assert row.assigned_by_user_id == super_actor.user_id
    assert AuditLog.objects.filter(action="vms.role.assigned", entity_id=str(row.pk)).exists()


def test_assignee_must_be_faculty_or_staff_in_directory(directory, super_actor):
    directory[11] = "student"
    with pytest.raises(BadRequestError) as e:
        roles.assign(actor=super_actor, user_id=11, role="security", ends_at=_ends())
    assert e.value.code == "ineligible_user"
    with pytest.raises(BadRequestError) as e:
        roles.assign(actor=super_actor, user_id=99, role="security", ends_at=_ends())
    assert e.value.code == "unknown_user"


def test_br_181_assignment_requires_an_end(directory, super_actor):
    directory[10] = "staff"
    with pytest.raises(BadRequestError):
        roles.assign(actor=super_actor, user_id=10, role="security", ends_at=None)


def test_br_181_assignment_expires(directory, super_actor):
    directory[10] = "staff"
    row = roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_ends(1))
    holder = f.make_actor(user_id=10)
    assert authz.require_role(holder, "security") == row
    later = timezone.now() + timedelta(days=2)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(holder, "security", at=later)
    assert not roles.my_roles(holder, at=later).exists()


def test_no_overlapping_identical_scope(directory, super_actor):
    directory[10] = "staff"
    roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_ends())
    with pytest.raises(ConflictError):
        roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_ends(5))
    zone = f.make_zone()
    roles.assign(actor=super_actor, user_id=10, role="security", scope_type="zone",
                 scope_id=zone.pk, ends_at=_ends())          # different scope is fine


def test_scope_must_exist(directory, super_actor):
    directory[10] = "staff"
    with pytest.raises(BadRequestError):
        roles.assign(actor=super_actor, user_id=10, role="security", scope_type="gate",
                     scope_id=424242, ends_at=_ends())


def test_br_182_reassign_effective_immediately(directory, super_actor):
    directory.update({10: "staff", 11: "faculty"})
    old = roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_ends())
    new, _ = roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=11)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=10), "security")
    assert authz.require_role(f.make_actor(user_id=11), "security") == new
    assert new.ends_at == old.ends_at
    old.refresh_from_db()
    assert old.revoked_at is not None


def test_br_183_handoff_moves_open_items(directory, super_actor):
    directory.update({10: "staff", 11: "faculty"})
    zone = f.make_zone()
    gate = f.make_gate(zone=zone)
    log = f.make_visit_log(event="denied", gate=gate, zone=zone)
    f.make_escalation(visit_log=log)
    f.make_alert(detail={"zone_id": zone.pk})
    f.make_alert(detail={"zone_id": zone.pk + 1000})            # out of scope
    req = f.make_visit_request(status="awaiting_admin")
    req.requested_zones.add(zone)
    old = roles.assign(actor=super_actor, user_id=10, role="admin", scope_type="zone",
                       scope_id=zone.pk, ends_at=_ends())
    _, counts = roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=11)
    assert counts.as_dict() == {"contingency_decisions": 1, "escalations": 1, "alerts": 1}
    note = Notification.objects.get(topic="role.handoff", channel="inapp")
    assert note.recipient_user_id == 11
    assert AuditLog.objects.get(action="vms.role.reassigned").detail["handoff"]["alerts"] == 1


def test_handoff_for_gate_scope_counts_only_that_gate(directory, super_actor):
    directory.update({10: "staff", 11: "faculty"})
    gate, other = f.make_gate(), f.make_gate()
    f.make_escalation(visit_log=f.make_visit_log(event="denied", gate=gate))
    f.make_escalation(visit_log=f.make_visit_log(event="denied", gate=other))
    old = roles.assign(actor=super_actor, user_id=10, role="security", scope_type="gate",
                       scope_id=gate.pk, ends_at=_ends())
    _, counts = roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=11)
    assert counts.escalations == 1


def test_revoke_then_second_revoke_conflicts(directory, super_actor):
    directory[10] = "staff"
    row = roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_ends())
    roles.revoke(actor=super_actor, assignment_id=row.pk)
    with pytest.raises(ConflictError):
        roles.revoke(actor=super_actor, assignment_id=row.pk)
    assert not roles.list_active(actor=super_actor).exists()


def test_my_roles_endpoint_any_signed_in_user(api_as):
    f.make_role_assignment(user_id=77)
    r = api_as(user_id=77, permissions=()).get("/api/v1/vms/roles/me")
    assert r.status_code == 200 and len(r.json()) == 1
    assert api_as(user_id=78).get("/api/v1/vms/roles/me").json() == []
