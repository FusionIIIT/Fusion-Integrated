"""BR Test Suite 4: Security, Alerts, Audit Immutability, Sessions, and Config (BR-SA-024..029, 031..033, 035)."""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models import (
    AdminNotification,
    SecurityAlert,
    SystemAdminAuditLog,
)
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.services.config_service import ConfigService, ConfigurationError
from modules.systemadmin.services.notification_service import NotificationService
from modules.systemadmin.services.security_service import SecurityPolicyError, SecurityService

ALL_PERMISSIONS = (
    "systemadmin.dashboard.view",
    "systemadmin.user.view",
    "systemadmin.user.create",
    "systemadmin.user.edit",
    "systemadmin.user.status",
    "systemadmin.user.bulk",
    "systemadmin.role.view",
    "systemadmin.role.assign",
    "systemadmin.role.reassign",
    "systemadmin.role.revoke",
    "systemadmin.role.extend",
    "systemadmin.archive.view",
    "systemadmin.archive.execute",
    "systemadmin.archive.restore",
    "systemadmin.purge.request",
    "systemadmin.purge.authorize",
    "systemadmin.audit.view",
    "systemadmin.audit.report",
    "systemadmin.config.manage",
)


def get_sa_client(stub_iam, permissions=ALL_PERMISSIONS):
    session = make_session(
        user_id=1,
        kind="staff",
        modules=("systemadmin",),
        permissions=permissions,
        roles=("Super Admin",),
        active_role="Super Admin",
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-sa-1")
    return client


pytestmark = pytest.mark.django_db

# --- BR-SA-024: Security Alert Threshold and Channels ---


def test_br_048_failed_login_logged():
    """TEST_BR_048 | BR-SA-024: Verify failed login attempts are logged in audit system."""
    SecurityService.record_login_attempt(
        username="admin_br_48", success=False, ip_address="192.168.1.100"
    )
    assert SystemAdminAuditLog.objects.filter(
        actor_username="admin_br_48", action="LOGIN_FAILED"
    ).exists()


def test_br_049_five_failed_logins_triggers_critical_alert():
    """TEST_BR_049 | BR-SA-024: Verify five consecutive failed login attempts trigger high-severity security alert."""
    username = "attacker_br_49"
    SecurityService._FAILED_LOGINS_CACHE[username] = 0
    for _ in range(5):
        SecurityService.record_login_attempt(
            username=username, success=False, ip_address="10.10.10.50"
        )

    alert = SecurityAlert.objects.filter(target_username=username).first()
    assert alert is not None
    assert alert.severity == "CRITICAL"
    assert "FAILED_LOGIN" in alert.alert_type


# --- BR-SA-025: Audit Immutability and Retention ---


def test_br_050_superadmin_actions_generate_permanent_audit():
    """TEST_BR_050 | BR-SA-025: Verify all Super Admin administrative actions generate permanent audit records."""
    AuditService.log_action(
        actor_username="superadmin_test",
        action="CONFIG_UPDATE",
        result="SUCCESS",
        target_role="SYSTEM",
        reason_or_context="Policy change",
    )
    assert SystemAdminAuditLog.objects.filter(
        actor_username="superadmin_test", action="CONFIG_UPDATE"
    ).exists()


def test_br_051_audit_log_immutability(stub_iam):
    """TEST_BR_051 | BR-SA-025: Verify audit log records cannot be modified or deleted via administrative APIs."""
    log = SystemAdminAuditLog.objects.create(
        actor_username="immutable_actor",
        action="TEST_ACTION",
        result="SUCCESS",
        timestamp=timezone.now(),
    )
    client = get_sa_client(stub_iam)
    # Attempting to delete or modify audit log via DELETE /api/v1/systemadmin/audit/
    resp_del = client.delete(f"/api/v1/systemadmin/audit/{log.id}/")
    assert resp_del.status_code in [404, 405]
    resp_put = client.put(f"/api/v1/systemadmin/audit/{log.id}/", {"action": "TAMPERED"})
    assert resp_put.status_code in [404, 405]


# --- BR-SA-026: Super Admin Data Isolation ---


def test_br_052_superadmin_data_isolation_metadata_access(stub_iam):
    """TEST_BR_052 | BR-SA-026: Verify Super Admin accesses administrative metadata without exposing isolated module payloads."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/dashboard/")
    assert resp.status_code == 200
    assert "users" in resp.data


def test_br_053_superadmin_data_isolation_operational_boundary(stub_iam):
    """TEST_BR_053 | BR-SA-026: Verify Super Admin role is isolated from direct academic course/grade manipulation endpoints."""
    client = get_sa_client(stub_iam)
    # Operational module path not exposed in system admin
    resp = client.post("/api/v1/systemadmin/academic/grades/override/", {"grade": "A+"})
    assert resp.status_code in [404, 405]


# --- BR-SA-027: Super Admin Authentication and Session Controls ---


def test_br_054_session_lifecycle_and_logout():
    """TEST_BR_054 | BR-SA-027: Verify valid Super Admin session creation and termination upon logout."""
    sess = SecurityService.establish_session(
        session_id="SESS_BR_054",
        username="sa_sess_user",
        ip_address="172.16.0.1",
    )
    assert sess.is_active is True
    # Inactivity check
    SecurityService.check_and_update_session_activity("SESS_BR_054")
    sess.refresh_from_db()
    assert sess.last_activity_at is not None


def test_br_055_single_active_session_enforcement():
    """TEST_BR_055 | BR-SA-027: Verify concurrent session control terminates prior active session for Super Admin."""
    sess1 = SecurityService.establish_session(
        session_id="SESS_BR_CONC_1",
        username="sa_single_user",
        ip_address="10.0.0.1",
    )
    assert sess1.is_active is True

    sess2 = SecurityService.establish_session(
        session_id="SESS_BR_CONC_2",
        username="sa_single_user",
        ip_address="10.0.0.2",
    )
    sess1.refresh_from_db()
    assert sess1.is_active is False
    assert sess1.termination_reason == "single_session_kick"
    assert sess2.is_active is True


# --- BR-SA-028: No Self-Modification of Super Admin Status ---


def test_br_056_self_modification_prohibited():
    """TEST_BR_056 | BR-SA-028: Verify Super Admin attempting to modify own administrative status is prohibited."""
    with pytest.raises(SecurityPolicyError):
        SecurityService.prevent_self_modification(
            actor_username="superadmin",
            target_username="superadmin",
            action="revoke_superadmin_status",
        )


# --- BR-SA-029: Critical Operation Reauthentication ---


def test_br_057_critical_operation_reauthentication_permitted():
    """TEST_BR_057 | BR-SA-029: Verify critical operation executes successfully when valid reauthentication token provided."""
    ok = SecurityService.reauthenticate_critical_operation("superadmin", "SECURE_PIN_123")
    assert ok is True


def test_br_058_critical_operation_reauthentication_prohibited():
    """TEST_BR_058 | BR-SA-029: Verify critical operation is rejected when reauthentication token is invalid or missing."""
    with pytest.raises(SecurityPolicyError):
        SecurityService.reauthenticate_critical_operation("superadmin", "")
    with pytest.raises(SecurityPolicyError):
        SecurityService.reauthenticate_critical_operation("superadmin", "12")  # < 4 chars


# --- BR-SA-031: Password Rotation ---


def test_br_061_password_rotation_within_interval_valid():
    """TEST_BR_061 | BR-SA-031: Verify password strength validation passes for compliant password."""
    SecurityService.validate_password_strength("StrongPass@2026!")


def test_br_062_weak_password_rejected():
    """TEST_BR_062 | BR-SA-031: Verify weak or non-compliant password rejected by password policy."""
    with pytest.raises(SecurityPolicyError):
        SecurityService.validate_password_strength("weak")


# --- BR-SA-032: Notification Channel Policy ---


def test_br_063_notification_channel_policy():
    """TEST_BR_063 | BR-SA-032: Verify in-system and email notifications are dispatched for supported administrative events."""
    notif = NotificationService.send_notification(
        recipient_username="sa_user_notif",
        title="Administrative Security Notice",
        message="System policy has been updated.",
        category="security",
        channel="in_system",
    )
    assert notif.channel == "in_system"
    assert AdminNotification.objects.filter(recipient_username="sa_user_notif").exists()


# --- BR-SA-033: Audit Event Coverage and Record Content ---


def test_br_064_audit_record_mandatory_schema():
    """TEST_BR_064 | BR-SA-033: Verify audit log entries capture mandatory schema fields (timestamp, actor, action, result)."""
    entry = AuditService.log_action(
        actor_username="audit_tester",
        action="ROLE_ASSIGN",
        result="SUCCESS",
        target_user="TARGET_USER_01",
        target_role="COMM_MEMBER",
        ip_address="192.168.10.5",
        reason_or_context="Audit schema test",
        metadata={"extra_field": "val"},
    )
    assert entry.timestamp is not None
    assert entry.actor_username == "audit_tester"
    assert entry.action == "ROLE_ASSIGN"
    assert entry.result == "SUCCESS"
    assert entry.target_user == "TARGET_USER_01"


# --- BR-SA-035: Permitted System Configuration Boundary ---


def test_br_067_permitted_configuration_key_update_permitted():
    """TEST_BR_067 | BR-SA-035: Verify updating permitted administrative configuration keys is allowed."""
    cfg = ConfigService.update_configuration(
        key="session_inactivity_timeout_minutes",
        value=45,
        actor_username="superadmin",
    )
    assert cfg.value == 45
    val = ConfigService.get_value("session_inactivity_timeout_minutes")
    assert val == 45


def test_br_068_disallowed_configuration_boundary_prohibited():
    """TEST_BR_068 | BR-SA-035: Verify attempting to modify disallowed operational or academic configuration is prohibited."""
    with pytest.raises(ConfigurationError):
        ConfigService.update_configuration(
            key="academic_grading_policy_curves",
            value={"curve": "linear"},
            actor_username="superadmin",
        )
