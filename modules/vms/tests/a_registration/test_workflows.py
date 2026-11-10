"""End-to-end walk-throughs of BW-VMS-01, 02, 04, 05 and 22 over the HTTP API."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import PreAuthorization, VisitPass, VisitRequest
from modules.vms.tests import factories as f
from modules.vms.tests.a_registration.conftest import BASE, HOST_ID, payload

pytestmark = pytest.mark.django_db

PERMS = ["vms.request.decide", "vms.request.view_assigned", "vms.preauth.manage"]


@pytest.fixture
def host_api(api_as):
    return api_as(user_id=HOST_ID, permissions=PERMS, kind="staff")


def test_bw_vms_01_pre_registered_approved_visit(visitor_api, host_api):
    v, _ = visitor_api()
    r = v.post(BASE + "visitor/pre-registrations", payload(), format="json")
    assert r.status_code == 201 and r.json()["status"] == "pending"           # R1
    rid = r.json()["id"]
    assert [x["id"] for x in host_api.get(BASE + "host/requests?status=pending")
            .json()["results"]] == [rid]
    assert v.get(BASE + f"visitor/requests/{rid}/pass").status_code == 409     # BR-052
    d = host_api.post(BASE + f"host/requests/{rid}/decision",
                      {"decision": "approve", "note": "Welcome"}, format="json")
    assert d.status_code == 201                                                # R2
    got = v.get(BASE + f"visitor/requests/{rid}/pass").json()
    vp = VisitPass.objects.get()
    assert got["qr_token"] == vp.qr_token and got["pass_type"] == "PRE_REGISTERED"
    assert VisitRequest.objects.get().status == "approved"


def test_bw_vms_02_rejected_visit(visitor_api, host_api):
    v, _ = visitor_api()
    rid = v.post(BASE + "visitor/pre-registrations", payload(), format="json").json()["id"]
    assert host_api.post(BASE + f"host/requests/{rid}/decision",
                         {"decision": "reject"}, format="json").status_code == 400
    r = host_api.post(BASE + f"host/requests/{rid}/decision",
                      {"decision": "reject", "note": "Out of office"}, format="json")
    assert r.status_code == 200
    d = v.get(BASE + f"visitor/requests/{rid}").json()
    assert d["status"] == "rejected" and d["decision_note"] == "Out of office"
    assert not VisitPass.objects.exists()
    assert v.get(BASE + f"visitor/requests/{rid}/pass").status_code == 409


def test_bw_vms_04_pre_authorized_visit(visitor_api, host_api):
    host_api.post(BASE + "host/pre-authorizations", {
        "full_name": "Ravi Kumar", "phone": "9876543210", "id_doc_type": "passport",
        "id_doc_number": "P1234567", "max_visits": 1,
        "valid_until": (timezone.now() + timedelta(days=10)).isoformat()}, format="json")
    v, _ = visitor_api()
    r = v.post(BASE + "visitor/pre-registrations", payload(), format="json")
    assert r.status_code == 201 and r.json()["status"] == "approved"          # R2: no host step
    assert r.json()["source"] == "pre_authorized"
    assert VisitPass.objects.get().pass_type == "PRE_REGISTERED"
    assert PreAuthorization.objects.get().used_visits == 1
    # single-use grant is spent: the next visit needs the host
    start = timezone.localtime() + timedelta(days=3)
    start = start.replace(hour=10, minute=0, second=0, microsecond=0)
    r2 = v.post(BASE + "visitor/pre-registrations", payload(
        scheduled_start=start.isoformat(),
        scheduled_end=(start + timedelta(hours=1)).isoformat()), format="json")
    assert r2.json()["status"] == "pending"


def test_bw_vms_05_vip_visit(visitor_api):
    person = f.make_visitor(id_doc_type="passport", id_doc_number="P1234567",
                            full_name="Ravi Kumar")
    zone = f.make_zone()
    vip = f.make_vip_permission(visitor=person, granted_by_user_id=1)
    vip.zones.set([zone])
    v, _ = visitor_api()
    r = v.post(BASE + "visitor/pre-registrations", payload(requested_zones=[zone.pk]),
               format="json")
    assert r.status_code == 201 and r.json()["status"] == "approved"
    assert r.json()["source"] == "vip"
    vp = VisitPass.objects.get()
    assert vp.pass_type == "VIP" and set(vp.allowed_zones.all()) == {zone}


def test_bw_vms_22_same_day_urgent_exception(visitor_api, host_api, api_as, monkeypatch):
    fixed = timezone.localtime().replace(hour=9, minute=0, second=0, microsecond=0)
    monkeypatch.setattr("modules.vms.services.registration.timezone.now", lambda: fixed)
    start = fixed + timedelta(hours=1)
    v, _ = visitor_api()
    r = v.post(BASE + "visitor/pre-registrations", payload(
        scheduled_start=start.isoformat(),
        scheduled_end=(start + timedelta(hours=1)).isoformat()), format="json")
    assert r.status_code == 202 and r.json()["status"] == "awaiting_admin"     # R1
    rid = r.json()["id"]
    # the host cannot decide it yet
    assert host_api.post(BASE + f"host/requests/{rid}/decision", {"decision": "approve"},
                         format="json").status_code == 409
    f.make_role_assignment(user_id=4001, role="admin")
    admin = api_as(user_id=4001, permissions=["vms.urgent.decide"], kind="staff")
    assert admin.post(BASE + f"admin-requests/{rid}/urgent-decision",
                      {"decision": "approve"}, format="json").status_code == 200   # R2
    assert VisitRequest.objects.get().status == "pending"
    host = api_as(user_id=HOST_ID, permissions=PERMS, kind="staff")   # one stub session at a time
    assert host.post(BASE + f"host/requests/{rid}/decision", {"decision": "approve"},
                     format="json").status_code == 201                         # R3
    assert VisitPass.objects.get().pass_type == "PRE_REGISTERED"
    assert v.get(BASE + f"visitor/requests/{rid}/pass").status_code == 200
