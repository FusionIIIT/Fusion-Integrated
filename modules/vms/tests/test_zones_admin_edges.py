"""Zone and gate maintenance edge cases: validation, cycles, in-use deactivation, no-op
updates, duplicate names and permissions (CFR-026 CRUD half, CFR-001)."""
import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import AuditLog
from modules.vms.services import zones_admin as za
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin():
    return f.make_actor(kind="staff", permissions=["vms.zone.manage"])


def _audits(action):
    return AuditLog.objects.filter(action=action).count()


# --- create ------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["", "   ", None])
def test_create_zone_requires_a_name(admin, name):
    with pytest.raises(BadRequestError) as e:
        za.create_zone(actor=admin, name=name)
    assert e.value.code == "validation_error"


def test_create_zone_with_a_parent_and_unknown_or_inactive_parent(admin):
    parent = za.create_zone(actor=admin, name="Campus")
    child = za.create_zone(actor=admin, name="Block A", parent_zone_id=parent.pk)
    assert child.parent_zone_id == parent.pk
    for bad in (987654, f.make_zone(is_active=False).pk):
        with pytest.raises(BadRequestError) as e:
            za.create_zone(actor=admin, name=f"x{bad}", parent_zone_id=bad)
        assert e.value.code == "unknown_zone"


def test_create_zone_needs_the_permission():
    with pytest.raises(PermissionDeniedError):
        za.create_zone(actor=f.make_actor(kind="staff", permissions=[]), name="Z")


# --- update zone -------------------------------------------------------------------------

def test_update_unknown_zone_is_not_found(admin):
    with pytest.raises(NotFoundError):
        za.update_zone(actor=admin, zone_id=987654, name="x")


def test_update_zone_with_nothing_changed_writes_no_audit_row(admin):
    z = za.create_zone(actor=admin, name="Lab")
    before = _audits("vms.zone.updated")
    za.update_zone(actor=admin, zone_id=z.pk, name="Lab", is_restricted=False, is_active=True)
    assert _audits("vms.zone.updated") == before


def test_update_zone_records_each_changed_field(admin):
    z = za.create_zone(actor=admin, name="Lab")
    p = za.create_zone(actor=admin, name="Campus")
    za.update_zone(actor=admin, zone_id=z.pk, name="Lab 2", is_restricted=True,
                   parent_zone_id=p.pk)
    z.refresh_from_db()
    assert (z.name, z.is_restricted, z.parent_zone_id) == ("Lab 2", True, p.pk)
    detail = AuditLog.objects.filter(action="vms.zone.updated").latest("id").detail
    assert set(detail) == {"renamed", "is_restricted", "parent_zone_id"}


def test_update_zone_cannot_become_its_own_ancestor(admin):
    a = za.create_zone(actor=admin, name="A")
    b = za.create_zone(actor=admin, name="B", parent_zone_id=a.pk)
    c = za.create_zone(actor=admin, name="C", parent_zone_id=b.pk)
    with pytest.raises(BadRequestError):
        za.update_zone(actor=admin, zone_id=a.pk, parent_zone_id=c.pk)
    with pytest.raises(BadRequestError):
        za.update_zone(actor=admin, zone_id=a.pk, parent_zone_id=a.pk)


def test_update_zone_can_be_moved_back_to_the_top_level(admin):
    p = za.create_zone(actor=admin, name="Campus")
    z = za.create_zone(actor=admin, name="Lab", parent_zone_id=p.pk)
    za.update_zone(actor=admin, zone_id=z.pk, parent_zone_id=None)
    z.refresh_from_db()
    assert z.parent_zone_id is None


def test_update_zone_rename_to_an_existing_name_conflicts(admin):
    za.create_zone(actor=admin, name="Taken")
    z = za.create_zone(actor=admin, name="Free")
    with pytest.raises(ConflictError) as e:
        za.update_zone(actor=admin, zone_id=z.pk, name="Taken")
    assert e.value.code == "duplicate_name"


def test_zone_in_use_cannot_be_deactivated_until_gates_and_children_are(admin):
    z = za.create_zone(actor=admin, name="Block")
    child = za.create_zone(actor=admin, name="Wing", parent_zone_id=z.pk)
    gate = za.create_gate(actor=admin, name="G1", zone_id=z.pk)
    with pytest.raises(ConflictError) as e:
        za.update_zone(actor=admin, zone_id=z.pk, is_active=False)
    assert e.value.code == "zone_in_use"
    za.update_gate(actor=admin, gate_id=gate.pk, is_active=False)
    with pytest.raises(ConflictError):
        za.update_zone(actor=admin, zone_id=z.pk, is_active=False)       # child still active
    za.update_zone(actor=admin, zone_id=child.pk, is_active=False)
    za.update_zone(actor=admin, zone_id=z.pk, is_active=False)
    z.refresh_from_db()
    assert z.is_active is False
    za.update_zone(actor=admin, zone_id=z.pk, is_active=True)             # and back
    z.refresh_from_db()
    assert z.is_active is True


# --- gates -------------------------------------------------------------------------------

def test_create_gate_validates_name_and_zone(admin):
    z = za.create_zone(actor=admin, name="Block")
    with pytest.raises(BadRequestError):
        za.create_gate(actor=admin, name=" ", zone_id=z.pk)
    for bad in (987654, f.make_zone(is_active=False).pk):
        with pytest.raises(BadRequestError) as e:
            za.create_gate(actor=admin, name="G", zone_id=bad)
        assert e.value.code == "unknown_zone"
    g = za.create_gate(actor=admin, name="North", zone_id=z.pk)
    assert g.device_id == ""
    with pytest.raises(ConflictError):
        za.create_gate(actor=admin, name="North", zone_id=z.pk)


def test_update_unknown_gate_is_not_found(admin):
    with pytest.raises(NotFoundError):
        za.update_gate(actor=admin, gate_id=987654, name="x")


def test_update_gate_changes_are_audited_and_noops_are_not(admin):
    z1, z2 = za.create_zone(actor=admin, name="A"), za.create_zone(actor=admin, name="B")
    g = za.create_gate(actor=admin, name="G1", zone_id=z1.pk, device_id="d1")
    before = _audits("vms.gate.updated")
    za.update_gate(actor=admin, gate_id=g.pk, name="G1", zone_id=z1.pk, device_id="d1",
                   is_active=True)
    assert _audits("vms.gate.updated") == before
    za.update_gate(actor=admin, gate_id=g.pk, name="G2", zone_id=z2.pk, device_id="d2",
                   is_active=False)
    g.refresh_from_db()
    assert (g.name, g.zone_id, g.device_id, g.is_active) == ("G2", z2.pk, "d2", False)
    detail = AuditLog.objects.filter(action="vms.gate.updated").latest("id").detail
    assert set(detail) == {"renamed", "zone_id", "device_id", "is_active"}


def test_update_gate_to_an_unknown_zone_or_duplicate_name_is_refused(admin):
    z = za.create_zone(actor=admin, name="A")
    za.create_gate(actor=admin, name="Taken", zone_id=z.pk)
    g = za.create_gate(actor=admin, name="Free", zone_id=z.pk)
    with pytest.raises(BadRequestError) as e:
        za.update_gate(actor=admin, gate_id=g.pk, zone_id=987654)
    assert e.value.code == "unknown_zone"
    with pytest.raises(ConflictError):
        za.update_gate(actor=admin, gate_id=g.pk, name="Taken")
