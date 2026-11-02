from datetime import time, timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.vms.models import AccessPolicy
from modules.vms.services import policy, policy_admin
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db


def test_br_125_publish_makes_new_version_runtime_source(admin_actor, published_policy):
    draft = policy_admin.create_draft(actor=admin_actor)
    assert draft.status == "draft" and draft.version == 2
    assert policy.effective().version == 1                 # a draft is never enforced
    policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk,
                              changes={"max_visit_hours": 6})
    policy_admin.publish(actor=admin_actor, policy_id=draft.pk)
    eff = policy.effective()
    assert eff.version == draft.version and eff.max_visit_hours == 6
    assert AccessPolicy.objects.get(pk=published_policy.pk).status == "published"  # BR-126


def test_publish_is_audited(admin_actor, published_policy):
    from modules.vms.models import AuditLog
    draft = policy_admin.create_draft(actor=admin_actor)
    policy_admin.publish(actor=admin_actor, policy_id=draft.pk)
    assert AuditLog.objects.filter(action="vms.policy.published",
                                   entity_id=str(draft.pk)).exists()


def test_br_128_edit_creates_draft(admin_actor, published_policy):
    published_policy.restricted_zones.add(f.make_zone())
    draft = policy_admin.create_draft(actor=admin_actor)
    assert draft.pk != published_policy.pk
    assert list(draft.restricted_zones.all()) == list(published_policy.restricted_zones.all())
    with pytest.raises(ConflictError):
        policy_admin.update_draft(actor=admin_actor, policy_id=published_policy.pk,
                                  changes={"max_visit_hours": 3})
    with pytest.raises(ConflictError):                     # one open draft at a time
        policy_admin.create_draft(actor=admin_actor)


def test_published_policy_cannot_be_published_twice(admin_actor, published_policy):
    with pytest.raises(ConflictError):
        policy_admin.publish(actor=admin_actor, policy_id=published_policy.pk)


def test_br_129_active_visit_unaffected_by_new_policy(admin_actor):
    f.make_published_policy(version=1, published_at=timezone.now() - timedelta(days=2),
                            max_visit_hours=8)
    vr = f.make_visit_request()
    draft = policy_admin.create_draft(actor=admin_actor)
    policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk,
                              changes={"max_visit_hours": 2, "walk_in_pass_hours": 2})
    policy_admin.publish(actor=admin_actor, policy_id=draft.pk)
    assert policy.effective().max_visit_hours == 2
    assert policy.snapshot_for(vr).max_visit_hours == 8


@pytest.mark.parametrize("changes", [
    {"walk_in_pass_hours": 9},                                  # > max_visit_hours (8)
    {"visiting_hours_start": time(20, 0), "visiting_hours_end": time(8, 0)},
    {"approval_timeout_hours": 0},
    {"contingency_sla_minutes": -5},
    {"reminder_after_hours": 24},                               # not before timeout
    {"max_visit_hours": 30},
])
def test_policy_validation_rejects_inconsistent_values(admin_actor, published_policy, changes):
    draft = policy_admin.create_draft(actor=admin_actor)
    with pytest.raises(BadRequestError) as e:
        policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk, changes=changes)
    assert e.value.details


def test_unknown_field_rejected(admin_actor, published_policy):
    draft = policy_admin.create_draft(actor=admin_actor)
    with pytest.raises(BadRequestError):
        policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk,
                                  changes={"version": 99})


def test_manage_and_publish_are_separate_permissions(published_policy):
    manager = f.make_actor(permissions=["vms.policy.manage"])
    publisher = f.make_actor(permissions=["vms.policy.publish"])
    draft = policy_admin.create_draft(actor=manager)
    with pytest.raises(PermissionDeniedError):
        policy_admin.publish(actor=manager, policy_id=draft.pk)
    with pytest.raises(PermissionDeniedError):
        policy_admin.create_draft(actor=publisher)
    policy_admin.publish(actor=publisher, policy_id=draft.pk)


def test_diff_lists_changed_fields(admin_actor, published_policy):
    zone = f.make_zone()
    draft = policy_admin.create_draft(actor=admin_actor)
    policy_admin.update_draft(actor=admin_actor, policy_id=draft.pk,
                              changes={"max_visit_hours": 5}, restricted_zone_ids=[zone.pk])
    d = policy_admin.diff(actor=admin_actor, a_id=published_policy.pk, b_id=draft.pk)
    assert d["changes"]["max_visit_hours"] == {"a": 8, "b": 5}
    assert d["changes"]["restricted_zones"] == {"a": [], "b": [zone.pk]}


def test_acceptance_admin_publishes_via_api_and_effective_policy_changes(
        api_as, published_policy):
    client = api_as(permissions=["vms.policy.manage", "vms.policy.publish"])
    r = client.post("/api/v1/vms/policies", {}, format="json")
    assert r.status_code == 201
    pid = r.json()["id"]
    r = client.patch(f"/api/v1/vms/policies/{pid}", {"max_visit_hours": 5,
                     "visiting_hours_start": "09:00"}, format="json")
    assert r.status_code == 200 and r.json()["max_visit_hours"] == 5
    assert client.patch(f"/api/v1/vms/policies/{pid}", {"walk_in_pass_hours": 9},
                        format="json").status_code == 400
    assert client.post(f"/api/v1/vms/policies/{pid}/publish").status_code == 200
    assert policy.effective().visiting_hours_start == time(9, 0)
    assert client.patch(f"/api/v1/vms/policies/{pid}", {"max_visit_hours": 4},
                        format="json").status_code == 409
    r = client.get(f"/api/v1/vms/policies/{published_policy.pk}/diff/{pid}")
    assert r.status_code == 200 and "max_visit_hours" in r.json()["changes"]
