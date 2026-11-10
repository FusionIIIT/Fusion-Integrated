"""Auth matrix and behaviour of the visitor and host endpoints."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import AuditLog, VisitRequest
from modules.vms.tests import factories as f
from modules.vms.tests.a_registration.conftest import BASE, HOST_ID, payload

pytestmark = pytest.mark.django_db

HOST_PERMS = ["vms.request.decide", "vms.request.view_assigned", "vms.preauth.manage"]

HOST_ENDPOINTS = [
    ("get", "host/requests", "vms.request.view_assigned"),
    ("post", "host/requests/1/decision", "vms.request.decide"),
    ("post", "host/requests/bulk-decision", "vms.request.decide"),
    ("get", "host/pre-authorizations", "vms.preauth.manage"),
    ("post", "host/pre-authorizations", "vms.preauth.manage"),
    ("post", "host/pre-authorizations/1/revoke", "vms.preauth.manage"),
    ("post", "admin-requests/1/urgent-decision", "vms.urgent.decide"),
]
VISITOR_ENDPOINTS = [
    ("post", "visitor/pre-registrations"),
    ("get", "visitor/requests"),
    ("get", "visitor/requests/1"),
    ("get", "visitor/requests/1/pass"),
]


@pytest.mark.parametrize("method,path,perm", HOST_ENDPOINTS)
def test_host_endpoint_anonymous_is_401(api_as, method, path, perm):
    r = getattr(api_as(anonymous=True), method)(BASE + path, {}, format="json")
    assert r.status_code == 401


@pytest.mark.parametrize("method,path,perm", HOST_ENDPOINTS)
def test_host_endpoint_wrong_role_is_403(api_as, method, path, perm):
    client = api_as(permissions=["vms.report.view"])
    assert getattr(client, method)(BASE + path, {}, format="json").status_code == 403


@pytest.mark.parametrize("method,path", VISITOR_ENDPOINTS)
def test_visitor_endpoint_anonymous_is_401(api_as, method, path):
    assert getattr(api_as(anonymous=True), method)(
        BASE + path, {}, format="json").status_code == 401


@pytest.mark.parametrize("method,path", VISITOR_ENDPOINTS)
def test_visitor_endpoint_rejects_an_iam_user(api_as, method, path):
    """A staff token is not a visitor session (D-1)."""
    client = api_as(permissions=HOST_PERMS)
    assert getattr(client, method)(BASE + path, {}, format="json").status_code == 401


def test_visitor_post_without_csrf_header_is_403(visitor_api):
    client, _ = visitor_api()
    client.credentials()   # drop the CSRF header, keep the cookie
    r = client.post(BASE + "visitor/pre-registrations", payload(), format="json")
    assert r.status_code == 403


def test_visitor_expired_session_is_401(visitor_api):
    from modules.vms.models import VisitorSession
    client, _ = visitor_api()
    VisitorSession.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    assert client.get(BASE + "visitor/requests").status_code == 401


# --- visitor reads -------------------------------------------------------------------------

def test_visitor_cannot_see_other_visitor(visitor_api):
    mine_client, mine = visitor_api()
    _, theirs = visitor_api(f.make_visitor())
    mine_vr = f.make_visit_request(visitor=mine)
    their_vr = f.make_visit_request(visitor=theirs, status="approved")
    f.make_visit_pass(visit_request=their_vr)
    rows = mine_client.get(BASE + "visitor/requests").json()["results"]
    assert [r["id"] for r in rows] == [mine_vr.pk]
    assert mine_client.get(BASE + f"visitor/requests/{their_vr.pk}").status_code == 404
    assert mine_client.get(BASE + f"visitor/requests/{their_vr.pk}/pass").status_code == 404


def test_visitor_request_detail_has_history_and_decision_note(visitor_api, host):
    client, _ = visitor_api()
    r = client.post(BASE + "visitor/pre-registrations", payload(), format="json")
    rid = r.json()["id"]
    from modules.vms.services import approval
    approval.decide(host_actor=host, request_id=rid, decision="reject", note="No slot")
    d = client.get(BASE + f"visitor/requests/{rid}").json()
    assert d["status"] == "rejected" and d["decision_note"] == "No slot"
    assert [h["action"] for h in d["history"]] == [
        "vms.request.submitted", "vms.request.rejected"]


def test_visitor_status_filter(visitor_api):
    client, me = visitor_api()
    f.make_visit_request(visitor=me, status="pending")
    f.make_visit_request(visitor=me, status="rejected")
    rows = client.get(BASE + "visitor/requests?status=rejected").json()["results"]
    assert [r["status"] for r in rows] == ["rejected"]


def test_pass_endpoint_returns_qr_and_marks_viewed(visitor_api):
    client, me = visitor_api()
    vr = f.make_visit_request(visitor=me, status="approved")
    vp = f.make_visit_pass(visit_request=vr, valid_until=timezone.now() + timedelta(hours=2))
    d = client.get(BASE + f"visitor/requests/{vr.pk}/pass").json()
    assert d["qr_token"] == vp.qr_token and d["otp"] == vp.otp
    assert AuditLog.objects.filter(action="vms.pass.viewed", entity_id=str(vp.pk)).exists()


def test_pass_not_available_until_approved_and_active(visitor_api):
    client, me = visitor_api()
    pending = f.make_visit_request(visitor=me, status="pending")
    assert client.get(BASE + f"visitor/requests/{pending.pk}/pass").status_code == 409
    vr = f.make_visit_request(visitor=me, status="approved")
    f.make_visit_pass(visit_request=vr, is_active=False)
    assert client.get(BASE + f"visitor/requests/{vr.pk}/pass").status_code == 409
    vr2 = f.make_visit_request(visitor=me, status="approved")
    f.make_visit_pass(visit_request=vr2, valid_until=timezone.now() - timedelta(minutes=1))
    assert client.get(BASE + f"visitor/requests/{vr2.pk}/pass").status_code == 409


# --- host ---------------------------------------------------------------------------------------

def test_host_list_only_assigned_with_status_filter(api_as):
    mine = f.make_visit_request(host_user_id=HOST_ID, status="pending")
    f.make_visit_request(host_user_id=HOST_ID, status="rejected")
    f.make_visit_request(host_user_id=2002, status="pending")
    c = api_as(user_id=HOST_ID, permissions=HOST_PERMS)
    all_rows = c.get(BASE + "host/requests").json()["results"]
    assert len(all_rows) == 2
    rows = c.get(BASE + "host/requests?status=pending").json()["results"]
    assert [r["id"] for r in rows] == [mine.pk]


def test_host_decision_wrong_owner_is_404(api_as):
    vr = f.make_visit_request(host_user_id=2002, status="pending")
    c = api_as(user_id=HOST_ID, permissions=HOST_PERMS)
    assert c.post(BASE + f"host/requests/{vr.pk}/decision", {"decision": "approve"},
                  format="json").status_code == 404


def test_host_decision_approve_201_reject_200_double_409(api_as):
    a = f.make_visit_request(host_user_id=HOST_ID, status="pending")
    b = f.make_visit_request(host_user_id=HOST_ID, status="pending")
    c = api_as(user_id=HOST_ID, permissions=HOST_PERMS, kind="staff")
    r = c.post(BASE + f"host/requests/{a.pk}/decision", {"decision": "approve"}, format="json")
    assert r.status_code == 201 and r.json()["pass_type"] == "PRE_REGISTERED"
    assert "qr_token" not in r.json()
    r = c.post(BASE + f"host/requests/{b.pk}/decision",
               {"decision": "reject", "note": "no"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert c.post(BASE + f"host/requests/{b.pk}/decision", {"decision": "approve"},
                  format="json").status_code == 409
    assert c.post(BASE + f"host/requests/{b.pk}/decision", {"decision": "maybe"},
                  format="json").status_code == 400
    assert c.post(BASE + f"host/requests/{a.pk}/decision", {"decision": "reject"},
                  format="json").status_code in (400, 409)


def test_host_bulk_decision_returns_per_id_results(api_as):
    a = f.make_visit_request(host_user_id=HOST_ID, status="pending")
    other = f.make_visit_request(host_user_id=2002, status="pending")
    c = api_as(user_id=HOST_ID, permissions=HOST_PERMS, kind="staff")
    r = c.post(BASE + "host/requests/bulk-decision",
               {"ids": [a.pk, other.pk], "decision": "approve"}, format="json")
    assert r.status_code == 200
    res = {x["id"]: x for x in r.json()["results"]}
    assert res[a.pk]["ok"] and not res[other.pk]["ok"]
    assert VisitRequest.objects.get(pk=other.pk).status == "pending"


def test_host_preauth_endpoints_and_wrong_owner_404(api_as):
    c = api_as(user_id=HOST_ID, permissions=HOST_PERMS, kind="staff")
    body = {"full_name": "Ravi", "phone": "9876543210", "id_doc_type": "passport",
            "id_doc_number": "P1234567",
            "valid_until": (timezone.now() + timedelta(days=30)).isoformat(),
            "max_visits": 2}
    r = c.post(BASE + "host/pre-authorizations", body, format="json")
    assert r.status_code == 201 and r.json()["max_visits"] == 2
    assert len(c.get(BASE + "host/pre-authorizations").json()["results"]) == 1
    pid = r.json()["id"]
    other = f.make_pre_authorization(host_user_id=2002)
    assert c.post(BASE + f"host/pre-authorizations/{other.pk}/revoke").status_code == 404
    assert c.post(BASE + f"host/pre-authorizations/{pid}/revoke").status_code == 200
    assert c.post(BASE + f"host/pre-authorizations/{pid}/revoke").status_code == 409
    body["valid_until"] = (timezone.now() + timedelta(days=500)).isoformat()
    assert c.post(BASE + "host/pre-authorizations", body, format="json").status_code == 400


def test_urgent_decision_needs_admin_role_not_just_permission(api_as):
    vr = f.make_visit_request(status="awaiting_admin", is_urgent=True,
                              urgent_decision="pending", source="pre_registered")
    c = api_as(user_id=4001, permissions=["vms.urgent.decide"], kind="staff")
    url = BASE + f"admin-requests/{vr.pk}/urgent-decision"
    assert c.post(url, {"decision": "approve"}, format="json").status_code == 403
    f.make_role_assignment(user_id=4001, role="admin")
    r = c.post(url, {"decision": "approve"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "pending"
    assert c.post(url, {"decision": "approve"}, format="json").status_code == 409
    assert c.post(BASE + "admin-requests/99999/urgent-decision", {"decision": "approve"},
                  format="json").status_code == 404
