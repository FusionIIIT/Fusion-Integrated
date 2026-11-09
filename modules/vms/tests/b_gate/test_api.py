"""Endpoint auth matrix and response shapes for gate/* and zones/*."""
import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import GateOverride, VisitLog
from modules.vms.tests import factories as f
from modules.vms.tests.b_gate.conftest import ADMIN_PERMS, SECURITY_PERMS, blacklist

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"

# (method, path, permission that opens the view)
ENDPOINTS = [
    ("post", "gate/validate", "vms.gate.operate"),
    ("post", "gate/override", "vms.gate.override"),
    ("post", "gate/escalations", "vms.gate.escalate"),
    ("post", "gate/escalations/1/resolve", "vms.gate.override"),
    ("post", "gate/manual-entries", "vms.gate.operate"),
    ("get", "gate/denials", "vms.gate.operate"),
    ("get", "gate/alerts", "vms.monitor.view"),
    ("post", "gate/alerts/1/handle", "vms.gate.operate"),
    ("post", "gate/sync", "vms.gate.sync"),
    ("get", "gate/cached-roster", "vms.gate.sync"),
    ("post", "zones/access-check", "vms.gate.operate"),
    ("post", "zones/elevations", "vms.zone.elevate"),
    ("get", "zones/elevations", "vms.zone.elevate"),
    ("post", "zones/elevations/1/revoke", "vms.zone.elevate"),
]


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_anonymous_is_401(api_as, method, path, perm):
    r = getattr(api_as(anonymous=True), method)(BASE + path, {}, format="json")
    assert r.status_code == 401


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_wrong_permission_is_403(api_as, method, path, perm):
    r = getattr(api_as(permissions=["vms.report.view"]), method)(BASE + path, {}, format="json")
    assert r.status_code == 403


@pytest.mark.parametrize("method,path,perm", [e for e in ENDPOINTS if e[1] != "gate/validate"])
def test_permission_without_role_assignment_is_403_or_400(api_as, method, path, perm):
    """Holding the IAM permission is not enough: the time-bound role decides (BR-181)."""
    r = getattr(api_as(user_id=8123, permissions=[perm]), method)(BASE + path, {}, format="json")
    assert r.status_code in (400, 403)
    assert r.status_code != 200


def test_validate_checks_in(api_as, sec, gate, vpass):
    client = api_as(user_id=3001, permissions=SECURITY_PERMS)
    r = client.post(BASE + "gate/validate", {"qr_token": vpass.qr_token, "gate_id": gate.pk,
                                             "device_id": "d1"}, format="json")
    assert r.status_code == 200
    body = r.json()
    assert body["detail"] == "Checked in." and body["visit_request_id"] == vpass.visit_request_id
    assert vpass.logs.get().device_id == "d1"


def test_validate_denial_returns_failures_and_override_flag(api_as, sec, gate, vpass):
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    r = api_as(user_id=3001, permissions=SECURITY_PERMS).post(
        BASE + "gate/validate", {"otp": vpass.otp, "gate_id": gate.pk}, format="json")
    assert r.status_code == 403
    body = r.json()
    assert body["code"] == "outside_validity" and body["override_eligible"] is True
    assert body["failures"][0]["rule"] == "VMS-BR-190" and body["visit_log_id"]


def test_validate_blacklist_not_override_eligible(api_as, sec, gate, vpass):
    blacklist(vpass.visit_request.visitor)
    r = api_as(user_id=3001, permissions=SECURITY_PERMS).post(
        BASE + "gate/validate", {"qr_token": vpass.qr_token, "gate_id": gate.pk}, format="json")
    assert r.status_code == 403 and r.json()["override_eligible"] is False


def test_validate_unknown_pass_is_403(api_as, sec, gate):
    r = api_as(user_id=3001, permissions=SECURITY_PERMS).post(
        BASE + "gate/validate", {"qr_token": "nope", "gate_id": gate.pk}, format="json")
    assert r.status_code == 403 and r.json()["code"] == "unknown_credential"
    assert VisitLog.objects.count() == 0


def test_validate_needs_credential_and_gate(api_as, sec, gate):
    client = api_as(user_id=3001, permissions=SECURITY_PERMS)
    assert client.post(BASE + "gate/validate", {"gate_id": gate.pk}, format="json").status_code == 400
    assert client.post(BASE + "gate/validate", {"otp": "1"}, format="json").status_code == 400


def test_validate_unknown_gate_is_404(api_as, sec):
    r = api_as(user_id=3001, permissions=SECURITY_PERMS).post(
        BASE + "gate/validate", {"otp": "123456", "gate_id": 99999}, format="json")
    assert r.status_code == 404


def test_validate_role_scoped_to_other_gate_is_403(api_as, sec, vpass):
    other = f.make_gate()
    r = api_as(user_id=3001, permissions=SECURITY_PERMS).post(
        BASE + "gate/validate", {"qr_token": vpass.qr_token, "gate_id": other.pk}, format="json")
    assert r.status_code == 403


def test_override_endpoint_and_wrong_denial_is_404(api_as, sec, admin, gate, vpass):
    vpass.valid_until = timezone.now() - timedelta(minutes=1)
    vpass.save()
    sec_client = api_as(user_id=3001, permissions=SECURITY_PERMS)
    log_id = sec_client.post(BASE + "gate/validate", {"qr_token": vpass.qr_token,
                                                      "gate_id": gate.pk},
                             format="json").json()["visit_log_id"]
    adm = api_as(user_id=4001, permissions=ADMIN_PERMS)
    body = {"denial_log_id": log_id, "justification": "Escorted by the Dean personally"}
    assert adm.post(BASE + "gate/override", {**body, "denial_log_id": 987654},
                    format="json").status_code == 404
    assert adm.post(BASE + "gate/override", {**body, "justification": "short"},
                    format="json").status_code == 400
    r = adm.post(BASE + "gate/override", body, format="json")
    assert r.status_code == 200 and GateOverride.objects.count() == 1
    assert adm.post(BASE + "gate/override", body, format="json").status_code == 409


def test_escalation_endpoints(api_as, sec, admin, gate, vpass):
    vpass.is_active = False
    vpass.save()
    c = api_as(user_id=3001, permissions=SECURITY_PERMS)
    log_id = c.post(BASE + "gate/validate", {"qr_token": vpass.qr_token, "gate_id": gate.pk},
                    format="json").json()["visit_log_id"]
    r = c.post(BASE + "gate/escalations", {"visit_log_id": log_id, "note": "odd"}, format="json")
    assert r.status_code == 201
    adm = api_as(user_id=4001, permissions=ADMIN_PERMS)
    r = adm.post(BASE + f"gate/escalations/{r.json()['id']}/resolve", {"note": "ok"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    assert adm.post(BASE + "gate/escalations/9999/resolve", {"note": "ok"},
                    format="json").status_code == 404


def test_denials_list_is_scoped_to_the_callers_gates(api_as, sec, gate, vpass):
    other = f.make_gate()
    vpass.is_active = False
    vpass.save()
    c = api_as(user_id=3001, permissions=SECURITY_PERMS)
    c.post(BASE + "gate/validate", {"qr_token": vpass.qr_token, "gate_id": gate.pk}, format="json")
    # a denial at a gate this officer does not cover must not be listed
    f.make_visit_log(event="denied", gate=other, reason="pass_inactive")
    rows = c.get(BASE + "gate/denials").json()["results"]
    assert len(rows) == 1 and rows[0]["failures"] == ["pass_inactive"]
    assert rows[0]["gate_id"] == gate.pk
    assert c.get(BASE + "gate/denials?status=overridden").json()["results"] == []


def test_alerts_list_and_handle(api_as, sec, gate, vpass):
    vpass.is_active = False
    vpass.save()
    c = api_as(user_id=3001, permissions=SECURITY_PERMS)
    c.post(BASE + "gate/validate", {"qr_token": vpass.qr_token, "gate_id": gate.pk}, format="json")
    alerts = c.get(BASE + "gate/alerts?status=open").json()["results"]
    assert len(alerts) == 1 and alerts[0]["kind"] == "gate_failure"
    r = c.post(BASE + f"gate/alerts/{alerts[0]['id']}/handle", {"outcome": "resolved"},
               format="json")
    assert r.status_code == 200 and r.json()["status"] == "handled"
    assert c.get(BASE + "gate/alerts?status=open").json()["results"] == []
    assert c.post(BASE + "gate/alerts/99999/handle", {"outcome": "resolved"},
                  format="json").status_code == 404


def test_manual_entry_endpoint(api_as, sec, gate, vpass):
    c = api_as(user_id=3001, permissions=SECURITY_PERMS)
    body = {"pass_id": vpass.pk, "gate_id": gate.pk, "event": "check_in", "reason": "Reader down"}
    assert c.post(BASE + "gate/manual-entries", {**body, "reason": ""},
                  format="json").status_code == 400
    r = c.post(BASE + "gate/manual-entries", body, format="json")
    assert r.status_code == 200
    r = c.post(BASE + "gate/manual-entries", {**body, "event": "check_out"}, format="json")
    assert r.status_code == 200 and r.json()["detail"] == "Checked out."


def test_sync_and_roster_endpoints(api_as, sec, gate, vpass):
    c = api_as(user_id=3001, permissions=SECURITY_PERMS)
    event = {"client_event_id": str(uuid.uuid4()), "event": "check_in",
             "qr_token": vpass.qr_token,
             "occurred_at": (timezone.now() - timedelta(minutes=5)).isoformat()}
    r = c.post(BASE + "gate/sync", {"gate_id": gate.pk, "events": [event]}, format="json")
    assert r.status_code == 200 and r.json()["applied"] == 1
    r = c.post(BASE + "gate/sync", {"gate_id": gate.pk, "events": [event]}, format="json")
    assert r.json()["results"][0]["status"] == "duplicate"
    assert c.get(BASE + f"gate/cached-roster?gate_id={gate.pk}").json()["results"][0][
        "pass_id"] == vpass.pk
    assert c.get(BASE + "gate/cached-roster").status_code == 400
    assert c.get(BASE + "gate/cached-roster?gate_id=99999").status_code == 404


def test_access_check_endpoint(api_as, sec, gate, vpass):
    zone = f.make_zone(is_restricted=True)
    c = api_as(user_id=3001, permissions=SECURITY_PERMS)
    r = c.post(BASE + "zones/access-check", {"pass_id": vpass.pk, "zone_id": zone.pk,
                                             "gate_id": gate.pk}, format="json")
    assert r.status_code == 403 and r.json()["allowed"] is False
    assert c.post(BASE + "zones/access-check", {"pass_id": 99999, "zone_id": zone.pk,
                                                "gate_id": gate.pk},
                  format="json").status_code == 404
    vpass.allowed_zones.add(zone)
    r = c.post(BASE + "zones/access-check", {"pass_id": vpass.pk, "zone_id": zone.pk,
                                             "gate_id": gate.pk}, format="json")
    assert r.status_code == 200 and r.json()["allowed"] is True


def test_elevation_endpoints(api_as, admin, vpass):
    zone = f.make_zone(is_restricted=True)
    adm = api_as(user_id=4001, permissions=ADMIN_PERMS)
    soon = (timezone.now() + timedelta(minutes=30)).isoformat()
    far = (timezone.now() + timedelta(hours=5)).isoformat()
    body = {"pass_id": vpass.pk, "zone_id": zone.pk, "ends_at": soon, "reason": "Escort"}
    assert adm.post(BASE + "zones/elevations", {**body, "ends_at": far},
                    format="json").status_code == 400
    assert adm.post(BASE + "zones/elevations", {k: v for k, v in body.items() if k != "ends_at"},
                    format="json").status_code == 400
    r = adm.post(BASE + "zones/elevations", body, format="json")
    assert r.status_code == 201
    eid = r.json()["id"]
    assert len(adm.get(BASE + f"zones/elevations?pass_id={vpass.pk}&active=1")
               .json()["results"]) == 1
    assert adm.post(BASE + f"zones/elevations/{eid}/revoke").status_code == 200
    assert adm.post(BASE + "zones/elevations/99999/revoke").status_code == 404
    assert adm.get(BASE + "zones/elevations?active=1").json()["results"] == []


def test_validate_then_visit_check_out(api_as, sec, gate, vpass):
    c = api_as(user_id=3001, permissions=SECURITY_PERMS)
    c.post(BASE + "gate/validate", {"qr_token": vpass.qr_token, "gate_id": gate.pk}, format="json")
    r = c.post(BASE + "visit/check-out", {"credential": vpass.qr_token}, format="json")
    assert r.status_code == 200
    vpass.visit_request.refresh_from_db()
    assert vpass.visit_request.status == "completed"
    assert c.post(BASE + "visit/check-out", {"credential": vpass.qr_token},
                  format="json").status_code in (400, 409)
    assert c.post(BASE + "gate/checkout", {"qr_token": vpass.qr_token},
                  format="json").status_code == 404        # legacy route is gone
