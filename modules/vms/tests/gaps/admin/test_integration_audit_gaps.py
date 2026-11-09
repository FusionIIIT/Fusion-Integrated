from datetime import timedelta

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError
from modules.vms.models import AuditLog, Notification
from modules.vms.services import audit_review, integration
from modules.vms.services.common import notify
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db
BASE = "/api/v1/vms/"


def test_uc_002_integration_change_is_audited_with_old_and_new_masked(super_actor):
    """VMS-UC-002: audit lists changed field names only, never secret values."""
    integration.set_value(actor=super_actor, key="sms_gateway",
                          value={"enabled": False, "provider": "acme", "api_key": "old-secret"})
    integration.set_value(actor=super_actor, key="sms_gateway",
                          value={"enabled": False, "provider": "beta", "api_key": "new-secret"})
    log = AuditLog.objects.filter(action="vms.integration.updated").latest("id")
    assert log.detail["key"] == "sms_gateway"
    assert log.detail["changed_fields"] == ["api_key", "provider"]
    assert "old-secret" not in str(log.detail) and "new-secret" not in str(log.detail)
    assert integration.get(actor=super_actor, key="sms_gateway")["value"]["api_key"] == "***"


def test_uc_002_integration_unsupported_integration_key_rejected(super_actor, api_as):
    """VMS-UC-002: an unknown integration key is not stored."""
    with pytest.raises(NotFoundError):
        integration.set_value(actor=super_actor, key="telepathy", value={"enabled": True})
    assert not AuditLog.objects.filter(action="vms.integration.updated").exists()
    client = api_as(permissions=["vms.integration.manage"])
    assert client.get(BASE + "integrations/telepathy").status_code == 404


def test_uc_002_integration_notification_channels_setting_roundtrip(super_actor):
    """VMS-UC-002: channel switches are stored and returned."""
    value = {"inapp": True, "email": False, "sms": False, "push": True}
    out = integration.set_value(actor=super_actor, key="notification_channels", value=value)
    assert out["value"] == value
    assert integration.get(actor=super_actor, key="notification_channels")["value"] == value
    keys = [r["key"] for r in integration.list_all(actor=super_actor)]
    assert "notification_channels" in keys


@pytest.mark.xfail(strict=True,
                   reason="BUG: notify.enqueue ignores the notification_channels setting")
def test_br_174_disabled_channel_in_setting_not_enqueued(super_actor):
    """VMS-BR-174: a disabled email channel produces no email row."""
    integration.set_value(actor=super_actor, key="notification_channels",
                          value={"inapp": True, "email": False})
    notify.enqueue(topic="t", dedupe_key="k1", subject="s", body="b", user_id=5,
                   channels=("inapp", "email"))
    assert not Notification.objects.filter(channel="email").exists()


@pytest.mark.xfail(strict=True,
                   reason="BUG: notify.enqueue ignores the notification_channels setting")
def test_br_174_channel_setting_per_event_type_selects_channels(super_actor):
    """VMS-BR-174: configured channels decide which rows a host notice gets."""
    integration.set_value(actor=super_actor, key="notification_channels",
                          value={"inapp": False, "email": True})
    notify.enqueue(topic="host.notice", dedupe_key="k2", subject="s", body="b", user_id=5,
                   channels=("inapp", "email"))
    assert set(Notification.objects.values_list("channel", flat=True)) == {"email"}


def test_br_174_invalid_channel_in_setting_rejected(super_actor):
    """VMS-BR-174: unknown channel names and non-boolean flags are a 400."""
    with pytest.raises(BadRequestError):
        integration.set_value(actor=super_actor, key="notification_channels",
                              value={"fax": True})
    with pytest.raises(BadRequestError):
        integration.set_value(actor=super_actor, key="notification_channels",
                              value={"email": "yes"})


# --- audit ----------------------------------------------------------------------------

def test_uc_004_audit_trail_denies_security_role(api_as):
    """VMS-UC-004: a Security holder without vms.audit.view gets 403."""
    f.make_role_assignment(user_id=70, role="security")
    client = api_as(user_id=70, permissions=["vms.gate.scan"])
    assert client.get(BASE + "audit").status_code == 403
    assert client.get(BASE + "audit/export.csv").status_code == 403


def test_uc_004_audit_filter_by_visitor_and_action_combined(super_actor):
    """VMS-UC-004: filters AND together."""
    f.make_audit_log(actor_user_id=5, action="vms.vip.granted", entity_type="vippermission",
                     entity_id="9")
    f.make_audit_log(actor_user_id=5, action="vms.vip.revoked", entity_type="vippermission",
                     entity_id="9")
    f.make_audit_log(actor_user_id=6, action="vms.vip.granted", entity_type="vippermission",
                     entity_id="10")
    rows = audit_review.search(actor=super_actor, actor_user_id=5, action="vms.vip.granted",
                               entity_type="vippermission", entity_id="9")
    assert [r.action for r in rows] == ["vms.vip.granted"]
    assert rows[0].actor_user_id == 5 and rows[0].entity_id == "9"


@pytest.mark.xfail(strict=True,
                   reason="BUG: inverted audit date range returns 200/empty, not 400")
def test_uc_004_audit_date_range_inverted_rejected(api_as):
    """VMS-UC-004: date_from after date_to is a 400."""
    client = api_as(permissions=["vms.audit.view"])
    now = timezone.now()
    r = client.get(BASE + "audit", {"date_from": (now + timedelta(days=1)).isoformat(),
                                    "date_to": now.isoformat()})
    assert r.status_code == 400


def test_uc_004_audit_rows_cannot_be_updated_via_api(api_as):
    """VMS-UC-004: PATCH/PUT/DELETE on an audit row URL never succeed."""
    row = f.make_audit_log(action="vms.keep")
    client = api_as(permissions=["vms.audit.view", "vms.integration.manage"])
    for method in ("patch", "put", "delete"):
        r = getattr(client, method)(f"{BASE}audit/{row.pk}", {"action": "x"}, format="json")
        assert r.status_code in (404, 405)
    row.refresh_from_db()
    assert row.action == "vms.keep"


def test_uc_004_audit_export_requires_permission_before_streaming(super_actor):
    """VMS-UC-004: export authorises eagerly, so a denied caller never gets a generator."""
    with pytest.raises(Exception) as e:
        audit_review.export_rows(actor=f.make_actor())
    assert e.value.__class__.__name__ == "PermissionDeniedError"
    f.make_audit_log(actor_user_id=1)
    assert len(list(audit_review.export_rows(actor=super_actor))) == 1
