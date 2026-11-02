from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.vms.models import AuditLog, BlacklistEntry
from modules.vms.services import blacklist, blacklist_admin
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


def _probe(**kw):
    return blacklist.check(checkpoint="gate", **kw)


def test_br_120_unpublished_blacklist_not_enforced(admin_actor):
    draft = blacklist_admin.create_version(actor=admin_actor)
    blacklist_admin.add_entry(actor=admin_actor, version_id=draft.pk, name="Bad",
                              id_doc_number="X1", reason="Fraud")
    assert _probe(id_doc_number="X1") is None
    blacklist_admin.publish(actor=admin_actor, version_id=draft.pk)
    hit = _probe(id_doc_number="X1")
    assert hit is not None and hit.version == draft.version


def test_new_draft_carries_published_entries_forward(admin_actor):
    d1 = blacklist_admin.create_version(actor=admin_actor)
    blacklist_admin.add_entry(actor=admin_actor, version_id=d1.pk, name="A",
                              id_doc_number="A1", reason="r", severity="critical")
    blacklist_admin.publish(actor=admin_actor, version_id=d1.pk)
    d2 = blacklist_admin.create_version(actor=admin_actor)
    blacklist_admin.add_entry(actor=admin_actor, version_id=d2.pk, name="B",
                              phone="9876543210", reason="r")
    assert _probe(phone="9876543210") is None          # d2 not yet published
    blacklist_admin.publish(actor=admin_actor, version_id=d2.pk)
    assert _probe(id_doc_number="A1").severity == "critical"
    assert _probe(phone="9876543210") is not None


def test_published_version_is_immutable(admin_actor):
    d = blacklist_admin.create_version(actor=admin_actor)
    e = blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="A",
                                  id_doc_number="A1", reason="r")
    blacklist_admin.publish(actor=admin_actor, version_id=d.pk)
    with pytest.raises(ConflictError):
        blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="B",
                                  id_doc_number="B1", reason="r")
    with pytest.raises(ConflictError):
        blacklist_admin.update_entry(actor=admin_actor, version_id=d.pk, entry_id=e.pk,
                                     severity="low")
    with pytest.raises(ConflictError):
        blacklist_admin.publish(actor=admin_actor, version_id=d.pk)


def test_deactivate_keeps_the_row_and_lifts_the_block_after_publish(admin_actor):
    d1 = blacklist_admin.create_version(actor=admin_actor)
    blacklist_admin.add_entry(actor=admin_actor, version_id=d1.pk, name="A",
                              id_doc_number="A1", reason="r")
    blacklist_admin.publish(actor=admin_actor, version_id=d1.pk)
    d2 = blacklist_admin.create_version(actor=admin_actor)
    copy = d2.entries.get()
    blacklist_admin.deactivate_entry(actor=admin_actor, version_id=d2.pk, entry_id=copy.pk)
    assert _probe(id_doc_number="A1") is not None      # still enforced until publish
    blacklist_admin.publish(actor=admin_actor, version_id=d2.pk)
    assert _probe(id_doc_number="A1") is None
    assert BlacklistEntry.objects.filter(pk=copy.pk, is_active=False).exists()


def test_publish_writes_a_changelog_to_the_audit_log(admin_actor):
    d1 = blacklist_admin.create_version(actor=admin_actor)
    a = blacklist_admin.add_entry(actor=admin_actor, version_id=d1.pk, name="A",
                                  id_doc_number="A1", reason="r")
    blacklist_admin.publish(actor=admin_actor, version_id=d1.pk)
    d2 = blacklist_admin.create_version(actor=admin_actor)
    old_copy = d2.entries.get()
    blacklist_admin.update_entry(actor=admin_actor, version_id=d2.pk, entry_id=old_copy.pk,
                                 severity="low")
    b = blacklist_admin.add_entry(actor=admin_actor, version_id=d2.pk, name="B",
                                  id_doc_number="B1", reason="r")
    blacklist_admin.publish(actor=admin_actor, version_id=d2.pk)
    log = AuditLog.objects.get(action="vms.blacklist.published", entity_id=str(d2.pk))
    assert log.detail["changelog"] == {"added": [b.pk], "removed": [],
                                       "changed": [old_copy.pk]}
    assert a.pk != old_copy.pk


def test_entry_needs_an_identifier_and_valid_severity(admin_actor):
    d = blacklist_admin.create_version(actor=admin_actor)
    with pytest.raises(BadRequestError):
        blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="Only Name",
                                  reason="r")
    with pytest.raises(BadRequestError):
        blacklist_admin.add_entry(actor=admin_actor, version_id=d.pk, name="A",
                                  id_doc_number="A1", reason="r", severity="extreme")


def test_manage_and_publish_are_separate(admin_actor):
    manager = f.make_actor(permissions=["vms.blacklist.manage"])
    d = blacklist_admin.create_version(actor=manager)
    with pytest.raises(PermissionDeniedError):
        blacklist_admin.publish(actor=manager, version_id=d.pk)


def test_only_one_open_draft(admin_actor):
    blacklist_admin.create_version(actor=admin_actor)
    with pytest.raises(ConflictError):
        blacklist_admin.create_version(actor=admin_actor)
    assert blacklist_admin.open_draft(actor=admin_actor).status == "draft"


# --- safe list ---------------------------------------------------------------------

def test_br_119_safelist_expiry_respected(admin_actor):
    f.make_blacklist_version(version=1, status="published", published_at=timezone.now())
    blacklist.add_entry(actor=None, name="A", id_doc_number="S1", reason="r")
    assert _probe(id_doc_number="S1") is not None
    entry = blacklist_admin.add_safelist(
        actor=admin_actor, id_doc_number="S1", reason="Cleared",
        expires_at=timezone.now() + timedelta(days=10))
    assert _probe(id_doc_number="S1") is None
    assert _probe(id_doc_number="S1", at=timezone.now() + timedelta(days=11)) is not None
    blacklist_admin.revoke_safelist(actor=admin_actor, entry_id=entry.pk)
    assert _probe(id_doc_number="S1") is not None


def test_br_118_safelist_expiry_is_mandatory_and_capped_at_90_days(admin_actor):
    now = timezone.now()
    for bad in (None, now - timedelta(days=1), now + timedelta(days=91)):
        with pytest.raises(BadRequestError):
            blacklist_admin.add_safelist(actor=admin_actor, id_doc_number="S1",
                                         reason="r", expires_at=bad)
    blacklist_admin.add_safelist(actor=admin_actor, id_doc_number="S1", reason="r",
                                 expires_at=now + timedelta(days=89))


def test_safelist_needs_its_own_permission():
    actor = f.make_actor(permissions=["vms.blacklist.manage"])
    with pytest.raises(PermissionDeniedError):
        blacklist_admin.add_safelist(actor=actor, id_doc_number="S1", reason="r",
                                     expires_at=timezone.now() + timedelta(days=5))


# --- endpoints ---------------------------------------------------------------------

def test_endpoint_flow_draft_entry_publish(api_as):
    client = api_as(permissions=["vms.blacklist.manage", "vms.blacklist.publish"])
    v = client.post("/api/v1/vms/blacklist/versions", {}, format="json").json()
    r = client.post(f"/api/v1/vms/blacklist/versions/{v['id']}/entries",
                    {"name": "Bad", "id_doc_number": "Z9", "reason": "r",
                     "severity": "high"}, format="json")
    assert r.status_code == 201
    eid = r.json()["id"]
    assert client.patch(f"/api/v1/vms/blacklist/versions/{v['id']}/entries/{eid}",
                        {"severity": "low"}, format="json").json()["severity"] == "low"
    assert _probe(id_doc_number="Z9") is None
    assert client.post(f"/api/v1/vms/blacklist/versions/{v['id']}/publish").status_code == 200
    assert _probe(id_doc_number="Z9") is not None
    # published: edits and deactivation are refused
    assert client.delete(
        f"/api/v1/vms/blacklist/versions/{v['id']}/entries/{eid}").status_code == 409
    assert client.get(
        f"/api/v1/vms/blacklist/versions/{v['id']}/entries").json()[0]["id"] == eid
    assert client.get("/api/v1/vms/blacklist/versions/99999/entries").status_code == 404
