"""audit, notify, authz and scope (build_sequence/13 section C)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import PermissionDeniedError
from modules.vms.models import AuditLog, Notification
from modules.vms.services.common import audit, authz, notify, scope
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


# --- audit ---------------------------------------------------------------------------

def test_audit_record_writes_actor_entity_and_detail():
    vr = f.make_visit_request()
    actor = f.make_actor(kind="staff", user_id=77)
    row = audit.record(actor=actor, action="vms.test", entity=vr, detail={"k": 1})
    assert (row.actor_user_id, row.actor_role) == (77, "staff")
    assert (row.entity_type, row.entity_id) == ("visitrequest", str(vr.pk))
    assert row.detail == {"k": 1} and row.action == "vms.test"


def test_audit_system_actor_has_no_user():
    row = audit.record(actor=None, action="vms.sys", entity=f.make_zone())
    assert row.actor_user_id is None and row.actor_role == "system"


def test_audit_accepts_a_plain_user_id():
    row = audit.record(actor=5, action="vms.x", entity=f.make_zone())
    assert row.actor_user_id == 5


def test_audit_rejects_unsaved_entity():
    from modules.vms.models import Zone
    with pytest.raises(ValueError):
        audit.record(actor=None, action="a", entity=Zone(name="x"))


def test_audit_rows_are_append_only():
    from modules.vms.models import AppendOnlyError
    row = audit.record(actor=None, action="a", entity=f.make_zone())
    row.action = "changed"
    with pytest.raises(AppendOnlyError):
        row.save()
    assert AuditLog.objects.count() == 1


# --- notify --------------------------------------------------------------------------

def test_notify_writes_one_pending_row_per_channel():
    rows = notify.enqueue(topic="t", dedupe_key="k1", subject="s", body="b", user_id=9)
    assert [r.channel for r in rows] == ["inapp", "email"]
    assert all(r.status == Notification.Status.PENDING and r.recipient_user_id == 9
               for r in rows)


def test_notify_is_idempotent_on_dedupe_key():
    a = notify.enqueue(topic="t", dedupe_key="k2", subject="s", body="b", user_id=9)
    b = notify.enqueue(topic="t", dedupe_key="k2", subject="other", body="b", user_id=9)
    assert [r.pk for r in a] == [r.pk for r in b]
    assert Notification.objects.count() == 2
    assert b[0].subject == "s"


def test_notify_to_a_visitor():
    v = f.make_visitor()
    (row,) = notify.enqueue(topic="t", dedupe_key="k3", subject="s", body="b",
                            visitor=v, channels=("email",))
    assert row.recipient_visitor_id == v.pk and row.recipient_user_id is None


def test_notify_needs_a_recipient():
    with pytest.raises(ValueError):
        notify.enqueue(topic="t", dedupe_key="k4", subject="s", body="b")


def test_notify_rejects_unknown_channel():
    with pytest.raises(ValueError):
        notify.enqueue(topic="t", dedupe_key="k5", subject="s", body="b",
                       user_id=1, channels=("pigeon",))


# --- authz.require / is_host ---------------------------------------------------------

def test_require_passes_only_with_every_code():
    actor = f.make_actor(permissions=["vms.a", "vms.b"])
    authz.require(actor, "vms.a", "vms.b")
    with pytest.raises(PermissionDeniedError):
        authz.require(actor, "vms.a", "vms.c")


def test_require_denies_anonymous():
    with pytest.raises(PermissionDeniedError):
        authz.require(None, "vms.a")


@pytest.mark.parametrize("kind,expected", [
    ("faculty", True), ("staff", True), ("student", False), ("operator", False)])
def test_br_185_faculty_and_staff_are_implicit_hosts(kind, expected):
    assert authz.is_host(f.make_actor(kind=kind)) is expected


# --- authz.require_role (BR-181, 182, 184) -------------------------------------------

def test_br_181_role_inside_window_is_granted():
    ra = f.make_role_assignment(user_id=31)
    assert authz.require_role(f.make_actor(user_id=31), "security") == ra


def test_br_181_role_outside_window_is_denied():
    now = timezone.now()
    f.make_role_assignment(user_id=32, starts_at=now + timedelta(hours=1),
                           ends_at=now + timedelta(hours=2))
    f.make_role_assignment(user_id=32, starts_at=now - timedelta(days=2),
                           ends_at=now - timedelta(days=1))
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=32), "security")


def test_br_181_at_parameter_evaluates_another_instant():
    now = timezone.now()
    f.make_role_assignment(user_id=33, starts_at=now + timedelta(hours=1),
                           ends_at=now + timedelta(hours=2))
    authz.require_role(f.make_actor(user_id=33), "security",
                       at=now + timedelta(minutes=90))


def test_br_182_revoked_role_is_denied_at_once():
    f.make_role_assignment(user_id=34, revoked_at=timezone.now())
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=34), "security")


def test_wrong_role_is_denied():
    f.make_role_assignment(user_id=35, role="security")
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=35), "admin")


def test_br_184_admin_satisfies_security():
    f.make_role_assignment(user_id=36, role="admin")
    authz.require_role(f.make_actor(user_id=36), "security")


def test_other_users_assignment_does_not_count():
    f.make_role_assignment(user_id=37)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(f.make_actor(user_id=38), "security")


def test_zone_scoped_role_only_applies_in_its_zone():
    z1, z2 = f.make_zone(), f.make_zone()
    f.make_role_assignment(user_id=39, scope_type="zone", scope_id=z1.pk)
    actor = f.make_actor(user_id=39)
    authz.require_role(actor, "security", zone_id=z1.pk)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(actor, "security", zone_id=z2.pk)


def test_gate_scoped_role_only_applies_at_its_gate():
    g1, g2 = f.make_gate(), f.make_gate()
    f.make_role_assignment(user_id=40, scope_type="gate", scope_id=g1.pk)
    actor = f.make_actor(user_id=40)
    authz.require_role(actor, "security", gate_id=g1.pk)
    with pytest.raises(PermissionDeniedError):
        authz.require_role(actor, "security", gate_id=g2.pk)


def test_zone_scoped_role_covers_a_gate_in_that_zone():
    gate = f.make_gate()
    f.make_role_assignment(user_id=41, scope_type="zone", scope_id=gate.zone_id)
    authz.require_role(f.make_actor(user_id=41), "security", gate_id=gate.pk)


def test_campus_role_applies_to_any_zone_or_gate():
    f.make_role_assignment(user_id=42)
    actor = f.make_actor(user_id=42)
    authz.require_role(actor, "security", zone_id=f.make_zone().pk)
    authz.require_role(actor, "security", gate_id=f.make_gate().pk)


# --- scope.visible_requests ----------------------------------------------------------

def test_visible_requests_host_sees_own_only():
    mine = f.make_visit_request(host_user_id=51)
    f.make_visit_request(host_user_id=52)
    qs = scope.visible_requests(f.make_actor(user_id=51))
    assert list(qs) == [mine]


def test_visible_requests_staff_principal_does_not_match_by_email():   # a-2: branch removed
    v = f.make_visitor(email="me@example.com")
    f.make_visit_request(visitor=v, host_user_id=99)
    actor = f.make_actor(user_id=53)
    object.__setattr__(actor, "email", "ME@example.com")
    assert list(scope.visible_requests(actor)) == []


def test_visible_requests_visitor_session_sees_own():
    v = f.make_visitor()
    mine = f.make_visit_request(visitor=v)
    f.make_visit_request()
    from modules.vms.auth import VisitorPrincipal
    p = VisitorPrincipal(visitor_id=v.pk, email=v.email, display_name=v.full_name)
    assert list(scope.visible_requests(p)) == [mine]


def test_visible_requests_campus_admin_sees_all():
    f.make_role_assignment(user_id=54, role="admin")
    a, b = f.make_visit_request(), f.make_visit_request()
    assert set(scope.visible_requests(f.make_actor(user_id=54))) == {a, b}


def test_visible_requests_zone_admin_sees_only_their_zone():
    z1, z2 = f.make_zone(), f.make_zone()
    f.make_role_assignment(user_id=55, role="admin", scope_type="zone", scope_id=z1.pk)
    inside, outside = f.make_visit_request(), f.make_visit_request()
    inside.requested_zones.add(z1)
    outside.requested_zones.add(z2)
    assert list(scope.visible_requests(f.make_actor(user_id=55))) == [inside]


def test_visible_requests_security_role_does_not_widen_scope():
    f.make_role_assignment(user_id=56, role="security")
    f.make_visit_request()
    assert not scope.visible_requests(f.make_actor(user_id=56)).exists()


def test_visible_requests_anonymous_sees_nothing():
    f.make_visit_request()
    assert not scope.visible_requests(None).exists()
