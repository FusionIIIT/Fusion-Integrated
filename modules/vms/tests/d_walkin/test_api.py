"""Endpoint auth matrix and end-to-end workflows (BW-VMS-06/07/08/15..18)."""
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from core.api import csrf
from modules.vms import auth
from modules.vms.models import VisitPass, VisitRequest
from modules.vms.tests import factories as f

from .conftest import ADMIN, HOST, SEC, on_site_pass, walkin_data

pytestmark = pytest.mark.django_db
BASE = "/api/v1/vms/"

ENDPOINTS = [
    ("post", "walkin/registrations", "vms.walkin.register"),
    ("get", "walkin/registrations", "vms.walkin.register"),
    ("post", "walkin/registrations/1/host-decision", "vms.request.decide"),
    ("post", "walkin/registrations/1/contingency", "vms.walkin.contingency_decide"),
    ("post", "visit/check-out", "vms.gate.operate"),
    ("post", "visit/passes/1/terminate", "vms.pass.terminate"),
    ("get", "visit/on-site", "vms.monitor.view"),
]


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_anonymous_is_401(api_as, method, path, perm):
    assert getattr(api_as(anonymous=True), method)(BASE + path, {}, format="json").status_code == 401


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_wrong_role_is_403(api_as, method, path, perm):
    client = api_as(permissions=["vms.report.view"])
    assert getattr(client, method)(BASE + path, {}, format="json").status_code == 403


def test_self_checkout_anonymous_is_401():
    assert APIClient().post(BASE + "visit/self-check-out", {}, format="json").status_code == 401


def test_self_checkout_iam_principal_is_403(api_as):
    client = api_as(permissions=["vms.gate.operate"])
    assert client.post(BASE + "visit/self-check-out", {}, format="json").status_code in (401, 403)


def _visitor_client(session, raw="tok-1"):
    session.token_hash = auth.hash_token(raw)
    session.verified_at = timezone.now()
    session.save()
    c = APIClient()
    c.cookies[auth.COOKIE_NAME] = raw
    c.defaults["HTTP_X_CSRF_TOKEN"] = csrf.token_for(raw)
    return c


def test_self_checkout_endpoint():
    f.make_integration_setting(key="kiosk_enabled", value=True)
    vp = on_site_pass()
    client = _visitor_client(f.make_visitor_session(visitor=vp.visit_request.visitor))
    r = client.post(BASE + "visit/self-check-out", {"pass_token": vp.qr_token}, format="json")
    assert r.status_code == 200
    vp.visit_request.refresh_from_db()
    assert vp.visit_request.status == "completed"


def test_self_checkout_endpoint_disabled_is_403():
    vp = on_site_pass()
    client = _visitor_client(f.make_visitor_session(visitor=vp.visit_request.visitor))
    r = client.post(BASE + "visit/self-check-out", {"pass_token": vp.qr_token}, format="json")
    assert r.status_code == 403 and r.json()["error"]["code"] == "self_checkout_disabled"


def test_wrong_owner_is_404(api_as):
    vp = on_site_pass(host_id=555)
    client = api_as(user_id=HOST, permissions=["vms.pass.terminate"], kind="faculty")
    r = client.post(BASE + f"visit/passes/{vp.pk}/terminate", {"reason": "x"}, format="json")
    assert r.status_code == 404


def test_host_decision_wrong_owner_404(api_as):
    vr = f.make_visit_request(source="walk_in", host_user_id=555)
    client = api_as(user_id=HOST, permissions=["vms.request.decide"], kind="faculty")
    r = client.post(BASE + f"walkin/registrations/{vr.pk}/host-decision",
                    {"decision": "approve"}, format="json")
    assert r.status_code == 404


def test_terminate_reason_required_400(api_as):
    vp = on_site_pass()
    client = api_as(user_id=HOST, permissions=["vms.pass.terminate"], kind="faculty")
    assert client.post(BASE + f"visit/passes/{vp.pk}/terminate", {}, format="json").status_code == 400


def test_blacklisted_walkin_400(api_as):
    from modules.vms.services import blacklist
    f.make_blacklist_version(version=1, status="published", published_at=timezone.now())
    blacklist.add_entry(actor=None, name="x", id_doc_number="WK123456", reason="r")
    f.make_role_assignment(user_id=SEC, role="security")
    client = api_as(user_id=SEC, permissions=["vms.walkin.register"])
    r = client.post(BASE + "walkin/registrations", {**walkin_data(), "host_user_id": HOST},
                    format="json")
    assert r.status_code == 400 and r.json()["error"]["code"] == "visitor_blacklisted"


def test_bw06_end_to_end_host_approved(api_as):
    f.make_role_assignment(user_id=SEC, role="security")
    sec = api_as(user_id=SEC, permissions=["vms.walkin.register", "vms.gate.operate",
                                           "vms.monitor.view"])
    r = sec.post(BASE + "walkin/registrations", {**walkin_data(), "host_user_id": HOST},
                 format="json")
    assert r.status_code == 201 and r.json()["status"] == "pending"
    rid = r.json()["id"]
    assert sec.get(BASE + "walkin/registrations?status=pending").json()[0]["id"] == rid

    host = api_as(user_id=HOST, permissions=["vms.request.decide"], kind="faculty")
    r = host.post(BASE + f"walkin/registrations/{rid}/host-decision",
                  {"decision": "approve"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "approved"
    vp = VisitPass.objects.get(visit_request_id=rid)
    assert vp.pass_type == "WALK_IN"

    f.make_visit_log(visit_pass=vp, event="check_in")
    sec = api_as(user_id=SEC, permissions=["vms.gate.operate", "vms.monitor.view"])
    on_site = sec.get(BASE + "visit/on-site").json()
    assert [row["pass_id"] for row in on_site] == [vp.pk]
    r = sec.post(BASE + "visit/check-out", {"credential": vp.qr_token}, format="json")
    assert r.status_code == 200
    assert VisitRequest.objects.get(pk=rid).status == "completed"
    assert sec.get(BASE + "visit/on-site").json() == []


def test_bw07_end_to_end_contingency(api_as):
    f.make_role_assignment(user_id=SEC, role="security")
    f.make_role_assignment(user_id=ADMIN, role="admin")
    sec = api_as(user_id=SEC, permissions=["vms.walkin.register"])
    r = sec.post(BASE + "walkin/registrations",
                 {**walkin_data(), "host_user_id": HOST, "host_available": False}, format="json")
    assert r.json()["status"] == "awaiting_admin"
    admin = api_as(user_id=ADMIN, permissions=["vms.walkin.contingency_decide"])
    r = admin.post(BASE + f"walkin/registrations/{r.json()['id']}/contingency",
                   {"decision": "approve", "note": "host away"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "approved"


def test_bw08_end_to_end_host_rejected(api_as):
    f.make_role_assignment(user_id=SEC, role="security")
    sec = api_as(user_id=SEC, permissions=["vms.walkin.register"])
    rid = sec.post(BASE + "walkin/registrations", {**walkin_data(), "host_user_id": HOST},
                   format="json").json()["id"]
    host = api_as(user_id=HOST, permissions=["vms.request.decide"], kind="faculty")
    r = host.post(BASE + f"walkin/registrations/{rid}/host-decision",
                  {"decision": "reject"}, format="json")
    assert r.json()["status"] == "rejected" and not VisitPass.objects.exists()


def test_bw16_end_to_end_host_terminates_on_site(api_as):
    f.make_role_assignment(user_id=SEC, role="security")
    vp = on_site_pass()
    host = api_as(user_id=HOST, permissions=["vms.pass.terminate"], kind="faculty")
    assert host.post(BASE + f"visit/passes/{vp.pk}/terminate", {"reason": "breach"},
                     format="json").status_code == 200
    sec = api_as(user_id=SEC, permissions=["vms.gate.operate"])
    assert sec.post(BASE + "visit/check-out", {"credential": vp.qr_token},
                    format="json").status_code == 200
    assert VisitRequest.objects.get(pk=vp.visit_request_id).status == "completed"


def test_bw17_end_to_end_admin_terminates_before_checkin(api_as):
    f.make_role_assignment(user_id=ADMIN, role="admin")
    vp = f.make_visit_pass(visit_request=f.make_visit_request(status="approved"))
    admin = api_as(user_id=ADMIN, permissions=["vms.pass.terminate"])
    assert admin.post(BASE + f"visit/passes/{vp.pk}/terminate", {"reason": "breach"},
                      format="json").status_code == 200
    vp.refresh_from_db()
    assert not vp.is_active
