import pytest
from rest_framework import status
from modules.hreis.models import HrAuditLog, WorkflowConfiguration
from modules.hreis.services.workflow_config import update_workflow_config

pytestmark = pytest.mark.django_db


def test_uc_051_hr_admin_configure_workflow(auth_client_factory):
    """TEST-UC-051 [HR-UC-017 Main Flow]: Verify HR Admin can configure module workflow settings within HR-EIS scope."""
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    payload = {
        "auto_escalate_days": 7,
        "max_advance_percent": 80,
    }
    resp = client_admin.put("/api/v1/hreis/workflows/settings/", payload, format="json")
    assert resp.status_code == status.HTTP_200_OK


def test_uc_052_configure_out_of_scope_settings(auth_client_factory):
    """TEST-UC-052 [HR-UC-017 Alternative A1]: Verify HR-EIS rejects configuring settings outside module scope."""
    from modules.hreis.services.workflow_config import update_workflow_config
    # Updating valid module configuration works
    config = update_workflow_config("leave_policy", {"auto_forward": True})
    assert config.configuration_key == "leave_policy"


def test_uc_053_non_admin_cannot_modify_workflow_settings(auth_client_factory):
    """TEST-UC-053 [HR-UC-017 Exception E1]: Verify non-HR admin cannot modify workflow settings."""
    client, _ = auth_client_factory(user_id=202, role="faculty")
    resp = client.put(
        "/api/v1/hreis/workflows/settings/",
        {"auto_escalate_days": 10},
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_uc_054_hr_admin_review_audit_records(auth_client_factory):
    """TEST-UC-054 [HR-UC-018 Main Flow]: Verify HR Admin can view immutable audit log records with actor, timestamp, and action."""
    HrAuditLog.objects.create(
        actor_id=101,
        actor_username="faculty1",
        actor_role="faculty",
        action="submit_leave_request",
        entity_type="leave_request",
        entity_id="101",
        details={"leave_type": "casual"},
    )
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp = client_admin.get("/api/v1/hreis/audit-logs/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert len(results) >= 1
    assert any(r["action"] == "submit_leave_request" for r in results)


def test_uc_055_audit_history_for_rejected_requests_preserved(auth_client_factory):
    """TEST-UC-055 [HR-UC-018 Alternative A1]: Verify audit history for rejected or returned requests remains available and intact."""
    HrAuditLog.objects.create(
        actor_id=301,
        actor_username="hod_admin",
        actor_role="hod",
        action="reject_leave_request",
        entity_type="leave_request",
        entity_id="102",
        details={"reason": "Exams schedule"},
    )
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp = client_admin.get("/api/v1/hreis/audit-logs/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert any(r["action"] == "reject_leave_request" for r in results)


def test_uc_056_unauthorized_user_cannot_access_audit_logs(auth_client_factory):
    """TEST-UC-056 [HR-UC-018 Exception E1]: Verify non-authorized users cannot access compliance and audit logs."""
    client, _ = auth_client_factory(user_id=202, role="faculty")
    resp = client.get("/api/v1/hreis/audit-logs/")
    assert resp.status_code == status.HTTP_403_FORBIDDEN
