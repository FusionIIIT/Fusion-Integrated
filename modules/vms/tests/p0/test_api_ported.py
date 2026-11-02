"""The ported legacy endpoints: auth matrix and behaviour parity."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import (
    AuditLog,
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


# gate/validate behaviour moved to modules/vms/tests/b_gate (lane B).


def test_checkout_completes_the_visit(api_as, gate_pass):
    client = _gate(api_as)
    f.make_visit_log(visit_pass=gate_pass, event="check_in")
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
    f.make_visit_log(visit_pass=gate_pass, event="check_in")
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


def test_blacklist_post_goes_to_the_open_draft_not_the_published_version(api_as):
    # Lane C: BR-120, a new entry is not enforced until its version is published.
    f.make_blacklist_version(version=1, status="published", published_at=timezone.now())
    other = f.make_blacklist_version(version=2)
    client = api_as(permissions=["vms.blacklist.manage"])
    client.post(BASE + "blacklist", {"name": "Bad", "id_doc_number": "B2", "reason": "x",
                                     "version": 1}, format="json")
    from modules.vms.models import BlacklistEntry
    assert BlacklistEntry.objects.get().version_id == other.pk


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
