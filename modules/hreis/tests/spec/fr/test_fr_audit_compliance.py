import pytest
from django.core.exceptions import PermissionDenied
from modules.hreis.models import HrAuditLog
from modules.hreis.services.audit import log_hr_action

pytestmark = pytest.mark.django_db


def test_fr_095_log_every_hr_transaction():
    """TEST-FR-095 [HR-AFR-083]: Verify HR-EIS logs every HR transaction."""
    log = log_hr_action(
        actor_id=101,
        actor_username="faculty1",
        actor_role="faculty",
        action="submit_test_request",
        entity_type="test_entity",
        entity_id=1,
    )
    assert log.id is not None
    assert HrAuditLog.objects.filter(id=log.id).exists()


def test_fr_096_audit_log_includes_actor_identity():
    """TEST-FR-096 [HR-AFR-084]: Verify HR-EIS audit logs include actor identity."""
    log = log_hr_action(
        actor_id=102,
        actor_username="faculty_actor",
        actor_role="faculty",
        action="action_check",
        entity_type="test_entity",
        entity_id=2,
    )
    assert log.actor_id == 102
    assert log.actor_username == "faculty_actor"


def test_fr_097_audit_log_includes_timestamp():
    """TEST-FR-097 [HR-AFR-085]: Verify HR-EIS audit logs include timestamp."""
    log = log_hr_action(
        actor_id=103,
        actor_username="actor3",
        actor_role="faculty",
        action="action_ts",
        entity_type="test_entity",
        entity_id=3,
    )
    assert log.timestamp is not None


def test_fr_098_audit_log_includes_action_performed():
    """TEST-FR-098 [HR-AFR-086]: Verify HR-EIS audit logs include action performed."""
    log = log_hr_action(
        actor_id=104,
        actor_username="actor4",
        actor_role="faculty",
        action="verify_documents",
        entity_type="test_entity",
        entity_id=4,
    )
    assert log.action == "verify_documents"


def test_fr_099_audit_logs_are_immutable():
    """TEST-FR-099 [HR-AFR-087]: Verify HR-EIS audit logs are immutable."""
    log = log_hr_action(
        actor_id=105,
        actor_username="actor5",
        actor_role="faculty",
        action="immutable_action",
        entity_type="test_entity",
        entity_id=5,
    )
    with pytest.raises(PermissionDenied):
        log.action = "tampered_action"
        log.save()

    with pytest.raises(PermissionDenied):
        log.delete()


def test_fr_100_restrict_audit_log_access(auth_client_factory):
    """TEST-FR-100 [HR-AFR-088]: Verify HR-EIS restricts audit log access to authorized roles only."""
    client_faculty, _ = auth_client_factory(user_id=106, role="faculty")
    resp_faculty = client_faculty.get("/api/v1/hreis/audit-logs/")
    assert resp_faculty.status_code == 403

    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp_admin = client_admin.get("/api/v1/hreis/audit-logs/")
    assert resp_admin.status_code == 200


def test_fr_101_compliance_reporting_support(auth_client_factory):
    """TEST-FR-101 [HR-AFR-089]: Verify HR-EIS supports compliance reporting through logged transactions."""
    log_hr_action(
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
        action="compliance_check",
        entity_type="service_record",
        entity_id=99,
        details={"audit": "annual_review"},
    )
    client_admin, _ = auth_client_factory(user_id=201, role="hr_admin")
    resp = client_admin.get("/api/v1/hreis/audit-logs/?action=compliance_check")
    assert resp.status_code == 200
    results = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
    assert any(item["action"] == "compliance_check" for item in results)
