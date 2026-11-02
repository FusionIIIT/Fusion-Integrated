"""The ported legacy endpoints: auth matrix and behaviour parity."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import (
    AuditLog,
    Notification,
    VisitLog,
    Visitor,
    VisitPass,
    VisitRequest,
)
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db

BASE = "/api/v1/vms/"


@pytest.fixture(autouse=True)
def _policy():
    f.make_published_policy(version=1)


def _payload(host=2001, **over):
    start = timezone.now() + timedelta(days=1)
    body = {"full_name": "Ravi", "phone": "9876543210", "email": "ravi@example.com",
            "id_doc_type": "passport", "id_doc_number": "P1234567", "host_user_id": host,
            "purpose": "Interview", "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(hours=2)).isoformat()}
    body.update(over)
    return body


# --- auth matrix ---------------------------------------------------------------------

ENDPOINTS = [
    ("get", "host/pending", "vms.request.decide"),
    ("post", "host/requests/1/decision", "vms.request.decide"),
    ("post", "gate/validate", "vms.gate.operate"),
    ("post", "gate/checkout", "vms.gate.operate"),
    ("get", "blacklist", "vms.blacklist.manage"),
    ("post", "blacklist", "vms.blacklist.manage"),
    ("get", "policies", "vms.policy.publish"),
    ("post", "policies/1/publish", "vms.policy.publish"),
]


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_anonymous_is_401(api_as, method, path, perm):
    assert getattr(api_as(anonymous=True), method)(BASE + path, {}, format="json").status_code == 401


@pytest.mark.parametrize("method,path,perm", ENDPOINTS)
def test_wrong_role_is_403(api_as, method, path, perm):
    client = api_as(permissions=["vms.report.view"])
    assert getattr(client, method)(BASE + path, {}, format="json").status_code == 403


@pytest.mark.parametrize("method", ["get", "post"])
def test_pre_registration_requires_authentication(api_as, method):
    client = api_as(anonymous=True)
    assert getattr(client, method)(BASE + "pre-registrations", {}, format="json").status_code == 401


def test_pre_registration_is_open_to_any_authenticated_principal(api_as):
    # TODO lane A (D-1): replaced by visitor sessions.
    client = api_as(permissions=[], kind="student")
    assert client.post(BASE + "pre-registrations", _payload(), format="json").status_code == 201


# --- pre-registration ----------------------------------------------------------------

def test_pre_registration_creates_a_pending_request_with_audit_and_host_notice(api_as):
    r = api_as().post(BASE + "pre-registrations", _payload(), format="json")
    assert r.status_code == 201
    vr = VisitRequest.objects.get()
    assert (vr.status, vr.source, vr.host_user_id) == ("pending", "pre_registered", 2001)
    assert r.json()["visitor_name"] == "Ravi" and r.json()["status"] == "pending"
    assert AuditLog.objects.filter(action="vms.request.submitted").count() == 1
    assert Notification.objects.filter(recipient_user_id=2001,
                                       topic="request.submitted").count() == 2


def test_br_051_blacklisted_visitor_is_rejected_at_pre_registration(api_as):
    f.make_blacklist_version(version=1, status="published", published_at=timezone.now())
    from modules.vms.services import blacklist
    blacklist.add_entry(actor=None, name="Ravi", id_doc_number="P1234567", reason="x")
    r = api_as().post(BASE + "pre-registrations", _payload(), format="json")
    assert r.status_code == 400 and r.json()["error"]["code"] == "visitor_blacklisted"
    assert not VisitRequest.objects.exists()


def test_br_038_duplicate_pending_request_is_rejected(api_as):
    client = api_as()
    body = _payload()
    assert client.post(BASE + "pre-registrations", body, format="json").status_code == 201
    r = client.post(BASE + "pre-registrations", body, format="json")
    assert r.status_code == 400 and r.json()["error"]["code"] == "duplicate_request"
    assert VisitRequest.objects.count() == 1 and Visitor.objects.count() == 1


def test_pre_registration_validates_the_window(api_as):
    now = timezone.now()
    r = api_as().post(BASE + "pre-registrations", _payload(
        scheduled_start=now.isoformat(), scheduled_end=(now - timedelta(hours=1)).isoformat()),
        format="json")
    assert r.status_code in (400, 422)
    assert not VisitRequest.objects.exists()


def test_pre_registration_list_is_scoped_to_the_callers_email(api_as):
    mine = f.make_visit_request(visitor=f.make_visitor(email="me@example.com"))
    f.make_visit_request(visitor=f.make_visitor(email="other@example.com"))
    rows = api_as(email="Me@Example.com").get(BASE + "pre-registrations").json()["results"]
    assert [r["id"] for r in rows] == [mine.pk]


def test_pre_registration_list_is_empty_without_an_email(api_as):
    f.make_visit_request()
    assert api_as().get(BASE + "pre-registrations").json()["results"] == []


# --- host ----------------------------------------------------------------------------

def test_host_pending_lists_only_own_pending_requests(api_as):
    mine = f.make_visit_request(host_user_id=2001)
    f.make_visit_request(host_user_id=2001, status="approved")
    f.make_visit_request(host_user_id=9999)
    rows = api_as(permissions=["vms.request.decide"]).get(BASE + "host/pending").json()["results"]
    assert [r["id"] for r in rows] == [mine.pk]


def test_host_approval_issues_a_pass(api_as):
    vr = f.make_visit_request(host_user_id=2001)
    vr.requested_zones.add(f.make_zone())
    r = api_as(permissions=["vms.request.decide"]).post(
        BASE + f"host/requests/{vr.pk}/decision",
        {"decision": "approve", "note": "ok"}, format="json")
    assert r.status_code == 201
    vr.refresh_from_db()
    assert vr.status == "approved" and vr.decision_note == "ok" and vr.decided_at
    vp = VisitPass.objects.get()
    body = r.json()
    assert body["qr_token"] == vp.qr_token and len(body["otp"]) == 6
    assert body["pass_type"] == "PRE_REGISTERED" and body["is_active"] is True
    assert body["allowed_zones"] == list(vp.allowed_zones.values_list("pk", flat=True))
    assert vp.issued_by_user_id == 2001
    assert AuditLog.objects.filter(action="vms.pass.issued").exists()
    assert AuditLog.objects.filter(action="vms.request.approved").exists()
    assert Notification.objects.filter(topic="request.decided", recipient_visitor=vr.visitor)


def test_host_rejection_issues_no_pass(api_as):
    vr = f.make_visit_request(host_user_id=2001)
    r = api_as(permissions=["vms.request.decide"]).post(
        BASE + f"host/requests/{vr.pk}/decision", {"decision": "reject"}, format="json")
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert not VisitPass.objects.exists()


def test_pass_validity_is_capped_by_policy(api_as):
    start = timezone.now() + timedelta(days=1)
    vr = f.make_visit_request(host_user_id=2001, scheduled_start=start,
                              scheduled_end=start + timedelta(hours=12))
    r = api_as(permissions=["vms.request.decide"]).post(
        BASE + f"host/requests/{vr.pk}/decision", {"decision": "approve"}, format="json")
    assert r.status_code == 201
    assert VisitPass.objects.get().valid_until == start + timedelta(hours=8)


def test_only_the_host_may_decide_and_a_stranger_gets_404(api_as):
    vr = f.make_visit_request(host_user_id=2001)
    r = api_as(user_id=3333, permissions=["vms.request.decide"]).post(
        BASE + f"host/requests/{vr.pk}/decision", {"decision": "approve"}, format="json")
    assert r.status_code == 404
    vr.refresh_from_db()
    assert vr.status == "pending" and not VisitPass.objects.exists()


def test_unknown_request_decision_is_404(api_as):
    r = api_as(permissions=["vms.request.decide"]).post(
        BASE + "host/requests/999999/decision", {"decision": "approve"}, format="json")
    assert r.status_code == 404


def test_deciding_twice_is_a_409(api_as):
    vr = f.make_visit_request(host_user_id=2001)
    client = api_as(permissions=["vms.request.decide"])
    url = BASE + f"host/requests/{vr.pk}/decision"
    assert client.post(url, {"decision": "reject"}, format="json").status_code == 200
    assert client.post(url, {"decision": "approve"}, format="json").status_code == 409


def test_invalid_decision_value_is_rejected(api_as):
    vr = f.make_visit_request(host_user_id=2001)
    r = api_as(permissions=["vms.request.decide"]).post(
        BASE + f"host/requests/{vr.pk}/decision", {"decision": "maybe"}, format="json")
    assert r.status_code in (400, 422)


# --- gate ----------------------------------------------------------------------------

@pytest.fixture
def gate_pass():
    vr = f.make_visit_request(status="approved")
    now = timezone.now()
    return f.make_visit_pass(visit_request=vr, valid_from=now - timedelta(hours=1),
                             valid_until=now + timedelta(hours=1))


def _gate(api_as):
    return api_as(user_id=3001, permissions=["vms.gate.operate"])


def _events(vp):
    return list(vp.logs.order_by("id").values_list("event", "reason"))


def test_gate_valid_pass_checks_in(api_as, gate_pass):
    r = _gate(api_as).post(BASE + "gate/validate", {"qr_token": gate_pass.qr_token}, format="json")
    assert r.status_code == 200
    assert r.json() == {"detail": "Checked in.", "visit_request_id": gate_pass.visit_request_id}
    log = gate_pass.logs.get()
    assert log.event == "check_in" and log.logged_by_user_id == 3001


def test_gate_accepts_otp_for_active_pass(api_as, gate_pass):
    r = _gate(api_as).post(BASE + "gate/validate", {"otp": gate_pass.otp}, format="json")
    assert r.status_code == 200


def test_gate_otp_ignores_inactive_pass(api_as, gate_pass):
    gate_pass.is_active = False
    gate_pass.save()
    r = _gate(api_as).post(BASE + "gate/validate", {"otp": gate_pass.otp}, format="json")
    assert r.status_code == 403 and r.json() == {"detail": "Pass not found."}


def test_gate_unknown_pass_is_403_and_not_logged(api_as):
    r = _gate(api_as).post(BASE + "gate/validate", {"qr_token": "nope"}, format="json")
    assert r.status_code == 403 and r.json() == {"detail": "Pass not found."}
    assert not VisitLog.objects.exists()


def test_gate_needs_a_credential(api_as):
    r = _gate(api_as).post(BASE + "gate/validate", {}, format="json")
    assert r.status_code == 400


def test_br_077_inactive_pass_is_denied_and_logged(api_as, gate_pass):
    gate_pass.is_active = False
    gate_pass.save()
    r = _gate(api_as).post(BASE + "gate/validate", {"qr_token": gate_pass.qr_token}, format="json")
    assert r.status_code == 403 and r.json() == {"detail": "Pass is not active."}
    assert _events(gate_pass) == [("denied", "Pass is not active.")]


def test_br_190_outside_validity_is_denied_and_logged(api_as, gate_pass):
    gate_pass.valid_until = timezone.now() - timedelta(minutes=1)
    gate_pass.save()
    r = _gate(api_as).post(BASE + "gate/validate", {"qr_token": gate_pass.qr_token}, format="json")
    assert r.json() == {"detail": "Pass is outside its validity window."}
    assert _events(gate_pass) == [("denied", "Pass is outside its validity window.")]


def test_br_112_blacklisted_visitor_is_denied_at_the_gate(api_as, gate_pass):
    from modules.vms.services import blacklist
    visitor = gate_pass.visit_request.visitor
    blacklist.add_entry(actor=None, name=visitor.full_name,
                        id_doc_number=visitor.id_doc_number, reason="x")
    r = _gate(api_as).post(BASE + "gate/validate", {"qr_token": gate_pass.qr_token}, format="json")
    assert r.status_code == 403 and r.json() == {"detail": "Visitor is blacklisted."}
    assert _events(gate_pass) == [("denied", "Visitor is blacklisted.")]


def test_br_191_zone_not_on_the_pass_is_denied(api_as, gate_pass):
    allowed, other = f.make_zone(), f.make_zone()
    gate_pass.allowed_zones.add(allowed)
    r = _gate(api_as).post(BASE + "gate/validate",
                           {"qr_token": gate_pass.qr_token, "zone_id": other.pk}, format="json")
    assert r.json() == {"detail": "Zone not permitted for this pass."}
    log = gate_pass.logs.get()
    assert log.event == "denied" and log.zone is None


def test_permitted_zone_is_recorded_on_check_in(api_as, gate_pass):
    z = f.make_zone()
    gate_pass.allowed_zones.add(z)
    r = _gate(api_as).post(BASE + "gate/validate",
                           {"qr_token": gate_pass.qr_token, "zone_id": z.pk}, format="json")
    assert r.status_code == 200 and gate_pass.logs.get().zone_id == z.pk


def test_br_082_second_check_in_is_denied(api_as, gate_pass):
    client = _gate(api_as)
    body = {"qr_token": gate_pass.qr_token}
    assert client.post(BASE + "gate/validate", body, format="json").status_code == 200
    r = client.post(BASE + "gate/validate", body, format="json")
    assert r.status_code == 403 and r.json() == {"detail": "Already checked in."}
    assert _events(gate_pass) == [("check_in", ""), ("denied", "Already checked in.")]


def test_gate_validation_order_inactive_before_window_before_blacklist(api_as, gate_pass):
    """Failures are reported in the order of the old endpoint."""
    from modules.vms.services import blacklist
    v = gate_pass.visit_request.visitor
    blacklist.add_entry(actor=None, name="n", id_doc_number=v.id_doc_number, reason="x")
    gate_pass.valid_until = timezone.now() - timedelta(minutes=1)
    gate_pass.save()
    body = {"qr_token": gate_pass.qr_token}
    assert _gate(api_as).post(BASE + "gate/validate", body, format="json").json() == {
        "detail": "Pass is outside its validity window."}
    gate_pass.is_active = False
    gate_pass.save()
    assert _gate(api_as).post(BASE + "gate/validate", body, format="json").json() == {
        "detail": "Pass is not active."}
    gate_pass.is_active = True
    gate_pass.valid_until = timezone.now() + timedelta(hours=1)
    gate_pass.save()
    assert _gate(api_as).post(BASE + "gate/validate", body, format="json").json() == {
        "detail": "Visitor is blacklisted."}


def test_terminated_pass_is_denied(api_as, gate_pass):
    gate_pass.is_active = False
    gate_pass.terminated_at = timezone.now()
    gate_pass.save()
    r = _gate(api_as).post(BASE + "gate/validate", {"qr_token": gate_pass.qr_token}, format="json")
    assert r.status_code == 403 and r.json() == {"detail": "Pass was terminated."}


def test_checkout_completes_the_visit(api_as, gate_pass):
    client = _gate(api_as)
    client.post(BASE + "gate/validate", {"qr_token": gate_pass.qr_token}, format="json")
    r = client.post(BASE + "gate/checkout", {"qr_token": gate_pass.qr_token}, format="json")
    assert r.status_code == 200 and r.json() == {"detail": "Checked out."}
    gate_pass.visit_request.refresh_from_db()
    assert gate_pass.visit_request.status == "completed"
    assert [e for e, _ in _events(gate_pass)] == ["check_in", "check_out"]
    assert AuditLog.objects.filter(action="vms.visit.completed").exists()


def test_checkout_without_check_in_is_400(api_as, gate_pass):
    r = _gate(api_as).post(BASE + "gate/checkout", {"qr_token": gate_pass.qr_token}, format="json")
    assert r.status_code == 400
    gate_pass.visit_request.refresh_from_db()
    assert gate_pass.visit_request.status == "approved"


def test_checkout_unknown_pass_is_404(api_as):
    r = _gate(api_as).post(BASE + "gate/checkout", {"qr_token": "nope"}, format="json")
    assert r.status_code == 404


def test_checkout_twice_is_400(api_as, gate_pass):
    client = _gate(api_as)
    client.post(BASE + "gate/validate", {"qr_token": gate_pass.qr_token}, format="json")
    client.post(BASE + "gate/checkout", {"qr_token": gate_pass.qr_token}, format="json")
    assert client.post(BASE + "gate/checkout", {"qr_token": gate_pass.qr_token},
                       format="json").status_code == 400


# --- blacklist and policies ----------------------------------------------------------

def test_blacklist_post_then_list(api_as):
    client = api_as(permissions=["vms.blacklist.manage"])
    r = client.post(BASE + "blacklist", {"name": "Bad", "id_doc_number": "B1",
                                         "reason": "Fraud"}, format="json")
    assert r.status_code == 201 and r.json()["id_doc_number"] == "B1"
    rows = client.get(BASE + "blacklist").json()
    assert [x["id_doc_number"] for x in rows] == ["B1"]


def test_blacklist_post_cannot_choose_a_version(api_as):
    draft = f.make_blacklist_version()
    client = api_as(permissions=["vms.blacklist.manage"])
    client.post(BASE + "blacklist", {"name": "Bad", "id_doc_number": "B2", "reason": "x",
                                     "version": draft.pk}, format="json")
    from modules.vms.models import BlacklistEntry
    assert BlacklistEntry.objects.get().version.status == "published"


def test_blacklist_post_validates(api_as):
    r = api_as(permissions=["vms.blacklist.manage"]).post(
        BASE + "blacklist", {"name": "Bad"}, format="json")
    assert r.status_code in (400, 422)


def test_policy_list_newest_first_and_publish(api_as):
    draft = f.make_access_policy(version=50)
    client = api_as(permissions=["vms.policy.publish"])
    assert client.get(BASE + "policies").json()[0]["version"] == 50
    r = client.post(BASE + f"policies/{draft.pk}/publish")
    assert r.status_code == 200 and r.json()["status"] == "published"
    draft.refresh_from_db()
    assert draft.published_at is not None
    from modules.vms.services import policy
    assert policy.effective().version == 50


def test_policy_publish_unknown_is_404(api_as):
    r = api_as(permissions=["vms.policy.publish"]).post(BASE + "policies/999999/publish")
    assert r.status_code == 404


def test_removed_legacy_modules_are_gone():
    import importlib
    for name in ("requests", "legacy_gate"):
        with pytest.raises(ImportError):
            importlib.import_module(f"modules.vms.api.{name}")
