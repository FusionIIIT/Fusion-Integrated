"""Edge cases in role scoping, role assignment, VIP grants and policy validation
(BR-181..185, BR-197, CFR-002, CFR-004, CFR-006)."""
from datetime import time, timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.services import policy_admin, roles, vip
from modules.vms.services.common import authz
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


def _end(days=10):
    return timezone.now() + timedelta(days=days)


# --- authz: hosts and role scoping ------------------------------------------------------

def test_is_host_none_student_and_role_based_host():
    assert authz.is_host(None) is False
    assert authz.is_host(f.make_actor(kind="student")) is False
    assert authz.is_host(f.make_actor(kind="staff")) is True
    assert authz.is_host(f.make_actor(kind="student", roles=("faculty", "student"))) is True


def test_require_role_without_an_actor_or_user_id_is_denied():
    with pytest.raises(PermissionDeniedError):
        authz.require_role(None, "security")


def test_zone_scoped_assignment_only_covers_that_zone():
    zone, other = f.make_zone(), f.make_zone()
    f.make_role_assignment(user_id=70, role="security", scope_type="zone", scope_id=zone.pk)
    actor = f.make_actor(user_id=70)
    assert authz.require_role(actor, "security", zone_id=zone.pk)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(actor, "security", zone_id=other.pk)


def test_gate_scoped_assignment_covers_its_gate_and_a_zone_assignment_covers_its_gates():
    gate, other_gate = f.make_gate(), f.make_gate()
    f.make_role_assignment(user_id=71, role="security", scope_type="gate", scope_id=gate.pk)
    f.make_role_assignment(user_id=72, role="security", scope_type="zone",
                           scope_id=other_gate.zone_id)
    assert authz.require_role(f.make_actor(user_id=71), "security", gate_id=gate.pk)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=71), "security", gate_id=other_gate.pk)
    assert authz.require_role(f.make_actor(user_id=72), "security", gate_id=other_gate.pk)


def test_a_gate_id_that_does_not_exist_only_matches_campus_wide_assignments():
    f.make_role_assignment(user_id=73, role="security", scope_type="campus")
    f.make_role_assignment(user_id=74, role="security", scope_type="gate", scope_id=1)
    assert authz.require_role(f.make_actor(user_id=73), "security", gate_id=987654)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=74), "security", gate_id=987654)


def test_admin_satisfies_security_but_security_does_not_satisfy_admin():
    f.make_role_assignment(user_id=75, role="admin")
    f.make_role_assignment(user_id=76, role="security")
    assert authz.require_role(f.make_actor(user_id=75), "security")
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=76), "admin")


# --- roles.assign / reassign --------------------------------------------------------------

def test_assign_rejects_unknown_role_missing_end_and_bad_windows(directory, super_actor):
    directory[10] = "staff"
    with pytest.raises(BadRequestError):
        roles.assign(actor=super_actor, user_id=10, role="janitor", ends_at=_end())
    with pytest.raises(BadRequestError) as e:
        roles.assign(actor=super_actor, user_id=10, role="security")
    assert "end" in e.value.message.lower()
    now = timezone.now()
    with pytest.raises(BadRequestError):                                   # end before start
        roles.assign(actor=super_actor, user_id=10, role="security",
                     starts_at=now + timedelta(days=2), ends_at=now + timedelta(days=1))
    with pytest.raises(BadRequestError):                                   # already over
        roles.assign(actor=super_actor, user_id=10, role="security",
                     starts_at=now - timedelta(days=2), ends_at=now - timedelta(days=1))


def test_assign_requires_a_known_eligible_assignee(directory, super_actor):
    directory[11] = "student"
    with pytest.raises(BadRequestError) as unknown:
        roles.assign(actor=super_actor, user_id=999, role="security", ends_at=_end())
    assert unknown.value.code == "unknown_user"
    with pytest.raises(BadRequestError) as ineligible:
        roles.assign(actor=super_actor, user_id=11, role="security", ends_at=_end())
    assert ineligible.value.code == "ineligible_user"


@pytest.mark.parametrize("kwargs, code", [
    ({"scope_type": "planet"}, "validation_error"),
    ({"scope_type": "campus", "scope_id": 5}, "validation_error"),
    ({"scope_type": "zone"}, "validation_error"),
    ({"scope_type": "gate", "scope_id": 987654}, "unknown_scope"),
])
def test_assign_validates_the_scope(directory, super_actor, kwargs, code):
    directory[10] = "staff"
    with pytest.raises(BadRequestError) as e:
        roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_end(), **kwargs)
    assert e.value.code == code


def test_assign_to_an_inactive_zone_is_an_unknown_scope(directory, super_actor):
    directory[10] = "staff"
    zone = f.make_zone(is_active=False)
    with pytest.raises(BadRequestError) as e:
        roles.assign(actor=super_actor, user_id=10, role="security", scope_type="zone",
                     scope_id=zone.pk, ends_at=_end())
    assert e.value.code == "unknown_scope"


def test_reassign_rejects_same_holder_past_end_and_duplicate_holder(directory, super_actor):
    directory.update({10: "staff", 11: "faculty"})
    old = roles.assign(actor=super_actor, user_id=10, role="security", ends_at=_end())
    with pytest.raises(BadRequestError):
        roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=10)
    with pytest.raises(BadRequestError):
        roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=11,
                       ends_at=timezone.now() - timedelta(minutes=1))
    roles.assign(actor=super_actor, user_id=11, role="security", ends_at=_end())
    with pytest.raises(ConflictError) as e:
        roles.reassign(actor=super_actor, assignment_id=old.pk, new_user_id=11)
    assert e.value.code == "overlapping_assignment"
    old.refresh_from_db()
    assert old.revoked_at is None                  # nothing changed on refusal


def test_reassign_an_unknown_assignment_is_not_found(directory, super_actor):
    directory[11] = "faculty"
    with pytest.raises(NotFoundError):
        roles.reassign(actor=super_actor, assignment_id=987654, new_user_id=11)


# --- VIP grants ----------------------------------------------------------------------------

def test_vip_grant_needs_a_future_expiry_after_its_start(super_actor):
    visitor = f.make_visitor()
    with pytest.raises(BadRequestError):
        vip.grant(actor=super_actor, valid_until=None, visitor_id=visitor.pk)
    with pytest.raises(BadRequestError):
        vip.grant(actor=super_actor, valid_until=timezone.now() - timedelta(hours=1),
                  visitor_id=visitor.pk)
    now = timezone.now()
    with pytest.raises(BadRequestError):
        vip.grant(actor=super_actor, valid_from=now + timedelta(days=3),
                  valid_until=now + timedelta(days=2), visitor_id=visitor.pk)


def test_vip_grant_zone_rules(super_actor):
    visitor = f.make_visitor()
    open_zone, restricted = f.make_zone(), f.make_zone(is_restricted=True)
    until = _end()
    with pytest.raises(BadRequestError) as e:
        vip.grant(actor=super_actor, valid_until=until, visitor_id=visitor.pk, zone_ids=[987654])
    assert e.value.code == "unknown_zone"
    with pytest.raises(BadRequestError) as e:
        vip.grant(actor=super_actor, valid_until=until, visitor_id=visitor.pk,
                  zone_ids=[restricted.pk])
    assert e.value.code == "restricted_zone_not_confirmed"
    with pytest.raises(BadRequestError) as e:
        vip.grant(actor=super_actor, valid_until=until, visitor_id=visitor.pk,
                  zone_ids=[open_zone.pk], restricted_zone_ids=[restricted.pk])
    assert e.value.code == "validation_error"
    ok = vip.grant(actor=super_actor, valid_until=until, visitor_id=visitor.pk,
                   zone_ids=[restricted.pk], restricted_zone_ids=[restricted.pk])
    assert ok.pk


def test_vip_grant_visitor_resolution(super_actor):
    until = _end()
    with pytest.raises(NotFoundError):
        vip.grant(actor=super_actor, valid_until=until, visitor_id=987654)
    with pytest.raises(BadRequestError):
        vip.grant(actor=super_actor, valid_until=until, full_name="No Document")
    with pytest.raises(BadRequestError):
        vip.grant(actor=super_actor, valid_until=until, id_doc_type="passport",
                  id_doc_number="V-NEW-1")                       # new visitor without a name
    created = vip.grant(actor=super_actor, valid_until=until, id_doc_type="passport",
                        id_doc_number="V-NEW-1", full_name="Dr New", email="n@example.com")
    # The same document resolves to the same person, so an overlapping grant conflicts.
    with pytest.raises(ConflictError) as e:
        vip.grant(actor=super_actor, valid_until=until + timedelta(days=1),
                  id_doc_type="passport", id_doc_number="V-NEW-1")
    assert e.value.code == "overlapping_vip" and created.visitor_id
    from modules.vms.models import Visitor
    assert Visitor.objects.filter(id_doc_number="V-NEW-1").count() == 1


# --- policy validation and permission paths --------------------------------------------------

def _values(**over):
    base = {"visiting_hours_start": time(8), "visiting_hours_end": time(18),
            "max_visit_hours": 8, "walk_in_pass_hours": 4, "approval_timeout_hours": 24,
            "reminder_after_hours": 12, "advance_registration_hours": 2,
            "contingency_sla_minutes": 15, "walkin_rate_limit_per_hour": 30}
    base.update(over)
    return base


def test_policy_validate_accepts_a_good_set_and_names_each_bad_field():
    assert policy_admin.validate(_values()) == []
    fields = {e["field"] for e in policy_admin.validate(_values(
        max_visit_hours=0, walk_in_pass_hours=-1, approval_timeout_hours="24",
        advance_registration_hours=-1))}
    assert fields == {"max_visit_hours", "walk_in_pass_hours", "approval_timeout_hours",
                      "advance_registration_hours"}


def test_policy_validate_visiting_hours_must_be_times_in_order():
    wrong_type = policy_admin.validate(_values(visiting_hours_start="08:00"))
    assert wrong_type == [{"field": "visiting_hours_start",
                           "message": "visiting hours must be times"}]
    backwards = policy_admin.validate(_values(visiting_hours_start=time(18),
                                              visiting_hours_end=time(8)))
    assert backwards[0]["field"] == "visiting_hours_end"
    equal = policy_admin.validate(_values(visiting_hours_end=time(8)))
    assert equal[0]["field"] == "visiting_hours_end"


def test_policy_read_paths_need_a_policy_permission():
    nobody = f.make_actor(kind="staff", permissions=[])
    with pytest.raises(PermissionDeniedError):
        policy_admin.list_policies(actor=nobody)
    a, b = f.make_published_policy(version=801), f.make_published_policy(version=802)
    with pytest.raises(PermissionDeniedError):
        policy_admin.diff(actor=nobody, a_id=a.pk, b_id=b.pk)
    publisher = f.make_actor(kind="staff", permissions=["vms.policy.publish"])
    assert policy_admin.list_policies(actor=publisher).count() >= 2
    assert isinstance(policy_admin.diff(actor=publisher, a_id=a.pk, b_id=b.pk), dict)
