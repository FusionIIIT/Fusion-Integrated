import csv
import io
from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.vms.models import AuditLog, IntegrationSetting, Visitor
from modules.vms.models.base import AppendOnlyError
from modules.vms.services import audit_review, integration, vip, zones_admin
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db
BASE = "/api/v1/vms/"


# --- integration ------------------------------------------------------------------

def test_integration_secret_masked(super_actor):
    out = integration.set_value(actor=super_actor, key="sms_gateway", value={
        "enabled": True, "provider": "acme", "endpoint": "https://sms.example/send",
        "api_key": "s3cret"})
    assert out["value"]["api_key"] == "***"
    assert integration.get(actor=super_actor, key="sms_gateway")["value"]["api_key"] == "***"
    assert IntegrationSetting.objects.get(key="sms_gateway").value["api_key"] == "s3cret"
    # resending the mask (or omitting it) keeps the stored secret
    integration.set_value(actor=super_actor, key="sms_gateway",
                          value={"enabled": False, "api_key": "***"})
    assert IntegrationSetting.objects.get(key="sms_gateway").value["api_key"] == "s3cret"
    log = AuditLog.objects.filter(action="vms.integration.updated").latest("id")
    assert "s3cret" not in str(log.detail) and "api_key" not in log.detail.get("key", "")


def test_integration_validates_keys_and_shapes(super_actor):
    with pytest.raises(NotFoundError):
        integration.get(actor=super_actor, key="nope")
    with pytest.raises(BadRequestError):
        integration.set_value(actor=super_actor, key="sms_gateway", value={"bogus": 1})
    with pytest.raises(BadRequestError):
        integration.set_value(actor=super_actor, key="sms_gateway", value={"enabled": "yes"})
    with pytest.raises(BadRequestError):
        integration.set_value(actor=super_actor, key="campus_directory",
                              value={"enabled": True, "base_url": "ftp://x"})
    with pytest.raises(BadRequestError):
        integration.set_value(actor=super_actor, key="max_elevation_minutes",
                              value={"minutes": 0})


def test_max_elevation_minutes_default_and_override(super_actor):
    assert integration.max_elevation_minutes() == 120
    integration.set_value(actor=super_actor, key="max_elevation_minutes",
                          value={"minutes": 45})
    assert integration.max_elevation_minutes() == 45


def test_integration_requires_permission():
    with pytest.raises(PermissionDeniedError):
        integration.set_value(actor=f.make_actor(), key="sms_gateway", value={})


# --- vip --------------------------------------------------------------------------

def _vip_args(**kw):
    base = {"id_doc_type": "passport", "id_doc_number": "V1", "full_name": "Vee",
            "valid_until": timezone.now() + timedelta(days=5)}
    base.update(kw)
    return base


def test_vip_grant_creates_visitor_and_audits(super_actor):
    zone = f.make_zone()
    row = vip.grant(actor=super_actor, zone_ids=[zone.pk], **_vip_args())
    assert Visitor.objects.get(id_doc_number="V1") == row.visitor
    assert list(row.zones.all()) == [zone]
    assert AuditLog.objects.filter(action="vms.vip.granted").exists()


def test_vip_expiry_is_mandatory(super_actor):
    with pytest.raises(BadRequestError):
        vip.grant(actor=super_actor, **_vip_args(valid_until=None))
    with pytest.raises(BadRequestError):
        vip.grant(actor=super_actor, **_vip_args(
            valid_until=timezone.now() - timedelta(days=1)))


def test_vip_restricted_zone_must_be_listed_explicitly(super_actor):
    zone = f.make_zone(is_restricted=True)
    with pytest.raises(BadRequestError) as e:
        vip.grant(actor=super_actor, zone_ids=[zone.pk], **_vip_args())
    assert e.value.code == "restricted_zone_not_confirmed"
    row = vip.grant(actor=super_actor, zone_ids=[zone.pk],
                    restricted_zone_ids=[zone.pk], **_vip_args())
    assert zone in row.zones.all()


def test_vip_revoke_and_overlap(super_actor):
    row = vip.grant(actor=super_actor, **_vip_args())
    with pytest.raises(ConflictError):
        vip.grant(actor=super_actor, **_vip_args())
    vip.revoke(actor=super_actor, vip_id=row.pk)
    with pytest.raises(ConflictError):
        vip.revoke(actor=super_actor, vip_id=row.pk)
    assert vip.list_permissions(actor=super_actor, active_only=True).count() == 0
    vip.grant(actor=super_actor, **_vip_args())


def test_vip_requires_permission():
    with pytest.raises(PermissionDeniedError):
        vip.grant(actor=f.make_actor(), **_vip_args())


# --- zones and gates --------------------------------------------------------------

def test_zone_crud_rename_is_audited(admin_actor):
    z = zones_admin.create_zone(actor=admin_actor, name="Lab", is_restricted=True)
    zones_admin.update_zone(actor=admin_actor, zone_id=z.pk, name="Lab 2")
    log = AuditLog.objects.get(action="vms.zone.updated", entity_id=str(z.pk))
    assert log.detail["renamed"] == ["Lab", "Lab 2"]
    with pytest.raises(ConflictError):
        zones_admin.create_zone(actor=admin_actor, name="Lab 2")


def test_zone_in_use_cannot_be_deactivated_and_parent_cycles_rejected(admin_actor):
    z = zones_admin.create_zone(actor=admin_actor, name="Block")
    g = zones_admin.create_gate(actor=admin_actor, name="Main", zone_id=z.pk)
    with pytest.raises(ConflictError):
        zones_admin.update_zone(actor=admin_actor, zone_id=z.pk, is_active=False)
    zones_admin.update_gate(actor=admin_actor, gate_id=g.pk, is_active=False)
    zones_admin.update_zone(actor=admin_actor, zone_id=z.pk, is_active=False)
    child = zones_admin.create_zone(actor=admin_actor, name="Child")
    parent = zones_admin.create_zone(actor=admin_actor, name="Parent",
                                     parent_zone_id=child.pk)
    with pytest.raises(BadRequestError):
        zones_admin.update_zone(actor=admin_actor, zone_id=child.pk,
                                parent_zone_id=parent.pk)


def test_gate_needs_active_zone(admin_actor):
    z = f.make_zone(is_active=False)
    with pytest.raises(BadRequestError):
        zones_admin.create_gate(actor=admin_actor, name="G", zone_id=z.pk)


def test_zones_have_no_delete_route(api_as):
    z = f.make_zone()
    client = api_as(permissions=["vms.zone.manage"])
    assert client.delete(f"{BASE}zones/{z.pk}").status_code == 405
    assert client.delete(f"{BASE}gates/1").status_code == 405


# --- audit ------------------------------------------------------------------------

def test_audit_has_no_write_path(api_as, super_actor):
    row = f.make_audit_log()
    with pytest.raises(AppendOnlyError):
        row.action = "x"
        row.save()
    with pytest.raises(AppendOnlyError):
        row.delete()
    assert not [n for n in dir(audit_review)
                if n.startswith(("update", "delete", "remove", "edit", "purge"))]
    client = api_as(permissions=["vms.audit.view"])
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)(BASE + "audit", {}, format="json").status_code == 405
        assert getattr(client, method)(BASE + "audit/export.csv", {},
                                       format="json").status_code == 405


def test_audit_search_filters(super_actor):
    f.make_audit_log(actor_user_id=5, action="vms.policy.published",
                     entity_type="accesspolicy", entity_id="3")
    f.make_audit_log(actor_user_id=6, action="vms.zone.created",
                     entity_type="zone", entity_id="4")
    s = audit_review.search
    assert s(actor=super_actor, actor_user_id=5).count() == 1
    assert s(actor=super_actor, action="vms.policy.").count() == 1
    assert s(actor=super_actor, entity_type="zone", entity_id="4").count() == 1
    assert s(actor=super_actor, date_from=timezone.now() + timedelta(days=1)).count() == 0
    with pytest.raises(PermissionDeniedError):
        s(actor=f.make_actor())


def test_audit_endpoint_paginates_and_filters(api_as):
    for i in range(3):
        f.make_audit_log(actor_user_id=9, action=f"vms.a.{i}")
    client = api_as(permissions=["vms.audit.view"])
    body = client.get(BASE + "audit", {"actor": 9, "limit": 2}).json()
    assert len(body["results"]) == 2 and body["next"]
    assert client.get(BASE + "audit", {"date_from": "garbage"}).status_code == 400


def test_audit_export_csv_has_ids_only_and_neutralises_formulas(api_as):
    f.make_audit_log(actor_user_id=9, action="=cmd", detail={"name": "Secret Person"})
    client = api_as(permissions=["vms.audit.view"])
    r = client.get(BASE + "audit/export.csv", {"actor": 9})
    assert r.status_code == 200 and r["Content-Type"].startswith("text/csv")
    text = b"".join(r.streaming_content).decode()
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == audit_review.EXPORT_HEADER
    assert "Secret Person" not in text
    assert "'=cmd" in rows[1]
