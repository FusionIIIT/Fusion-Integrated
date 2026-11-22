import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import AuditEvent, SecurityPolicy

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions):
    stub_iam(make_session(modules=("badms",), permissions=permissions,
                          roles=("IT Security Team",),
                          active_role="IT Security Team", kind="staff"))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_security_policy_is_visible_to_it_security(stub_iam):
    client = _client(stub_iam, ("badms.security_policy.manage",))

    response = client.get("/api/v1/badms/security_policies")

    assert response.status_code == 200
    assert response.json()["sensitive_at_rest"] == "AES-256"
    assert response.json()["sensitive_in_transit"] == "AES-256"
    assert response.json()["configured"] is False


def test_policy_update_requires_all_classification_values_and_audits(stub_iam):
    client = _client(stub_iam, ("badms.security_policy.manage",))
    policy = {"Critical": 90, "Sensitive": 365, "Routine": 30, "Archival": 730}

    response = client.put("/api/v1/badms/security_policies",
                          {"retention_days": policy}, format="json")

    assert response.status_code == 200
    assert response.json()["retention_days"] == policy
    assert SecurityPolicy.objects.get(pk=1).retention_days == policy
    audit = AuditEvent.objects.get(action="security_policy.update")
    assert audit.actor_user_id == 1001
    assert audit.details["retention_days"] == policy


def test_policy_update_rejects_missing_or_nonpositive_durations(stub_iam):
    client = _client(stub_iam, ("badms.security_policy.manage",))

    missing = client.put("/api/v1/badms/security_policies",
                         {"retention_days": {"Sensitive": 1}}, format="json")
    nonpositive = client.put("/api/v1/badms/security_policies", {
        "retention_days": {"Critical": 1, "Sensitive": 0,
                           "Routine": 1, "Archival": 1},
    }, format="json")

    assert missing.status_code == 400
    assert nonpositive.status_code == 400
    assert not SecurityPolicy.objects.exists()


def test_policy_management_is_forbidden_without_it_security_permission(stub_iam):
    client = _client(stub_iam, ("badms.backup.view",))

    response = client.get("/api/v1/badms/security_policies")

    assert response.status_code == 403
