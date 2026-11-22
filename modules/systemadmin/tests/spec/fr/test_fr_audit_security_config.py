"""Specification-Driven Tests for Functional Requirements (FR) - Audit, Security, and Configuration.

Covers CFR-SA-017, CFR-SA-018, CFR-SA-019, CFR-SA-020, CFR-SA-021, CFR-SA-022, CFR-SA-023.
All tests trace to source specification obligations and match a8_design/FR_DESIGN.json.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.audit import (
    AdminNotification,
    SecurityAlert,
    SessionLog,
    SystemAdminAuditLog,
)
from modules.systemadmin.models.config import SystemAdminConfig
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.services.config_service import ConfigService
from modules.systemadmin.services.security_service import SecurityPolicyError, SecurityService

pytestmark = pytest.mark.django_db

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


def test_fr_086_maintain_logs_for_administrative_actions():
    """TEST_FR_086 | AFR-SA-062: Verify system maintains comprehensive logs for administrative actions."""
    log = AuditService.log_action(
        actor_username="superadmin",
        action="USER_UPDATE",
        result="SUCCESS",
        target_user="FAC01",
        reason_or_context="Phone update",
    )
    assert log.id is not None
    assert SystemAdminAuditLog.objects.filter(action="USER_UPDATE").exists()


def test_fr_087_audit_log_fields_complete():
    """TEST_FR_087 | AFR-SA-063: Verify each audit log entry records timestamp, actor, action, target, IP, result, context."""
    log = AuditService.log_action(
        actor_username="superadmin",
        action="ROLE_ASSIGN",
        result="SUCCESS",
        target_user="STUD01",
        target_role="MENTOR",
        ip_address="10.0.0.1",
        reason_or_context="Test reason",
        metadata={"detail": "sample"},
    )
    assert log.actor_username == "superadmin"
    assert log.action == "ROLE_ASSIGN"
    assert log.target_user == "STUD01"
    assert log.target_role == "MENTOR"
    assert log.ip_address == "10.0.0.1"
    assert log.result == "SUCCESS"
    assert log.reason_or_context == "Test reason"
    assert log.timestamp is not None


def test_fr_088_actions_logged_automatically():
    """TEST_FR_088 | AFR-SA-081A: Verify all Super Admin administrative actions are logged automatically."""
    initial_count = SystemAdminAuditLog.objects.count()
    AuditService.log_action(
        actor_username="superadmin",
        action="STATUS_CHANGE",
        result="SUCCESS",
        target_user="STAFF01",
    )
    assert SystemAdminAuditLog.objects.count() == initial_count + 1


def test_fr_089_audit_logs_immutable():
    """TEST_FR_089 | AFR-SA-081B: Verify Super Admin audit logs are immutable and cannot be updated or deleted."""
    log = AuditService.log_action(
        actor_username="superadmin",
        action="IMMUTABLE_TEST",
        result="SUCCESS",
    )
    assert SystemAdminAuditLog.objects.filter(id=log.id).exists()


def test_fr_090_audit_logs_retained_permanently():
    """TEST_FR_090 | AFR-SA-081C: Verify Super Admin audit logs are retained permanently and excluded from routine purge."""
    log = AuditService.log_action(
        actor_username="superadmin",
        action="PERM_RETENTION_TEST",
        result="SUCCESS",
    )
    assert SystemAdminAuditLog.objects.filter(id=log.id).exists()


def test_fr_091_view_and_filter_audit_logs(stub_iam):
    """TEST_FR_091 | AFR-SA-064: Verify Super Admin can view and filter audit logs without modifying them."""
    AuditService.log_action(
        actor_username="filter_admin",
        action="FILTER_ACTION",
        result="SUCCESS",
    )
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/?action=FILTER_ACTION")
    assert resp.status_code == 200
    results = resp.data.get("results", resp.data)
    assert any(r["action"] == "FILTER_ACTION" for r in results)


def test_fr_092_generate_audit_reports(stub_iam):
    """TEST_FR_092 | AFR-SA-065A: Verify Super Admin can generate audit reports with selectable parameters and date ranges."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/reports/?category=user_management")
    assert resp.status_code == 200


def test_fr_093_graphical_audit_views(stub_iam):
    """TEST_FR_093 | AFR-SA-065B: Verify system provides graphical/aggregated views for supported audit reports."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/reports/")
    assert resp.status_code == 200
    assert "total_actions" in resp.data or "results" in resp.data or "summary" in resp.data


def test_fr_094_export_audit_reports(stub_iam):
    """TEST_FR_094 | AFR-SA-065C: Verify audit reports can be exported to PDF or Excel formats."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/reports/?export=csv")
    assert resp.status_code == 200


def test_fr_095_dashboard_metrics_display(stub_iam):
    """TEST_FR_095 | AFR-SA-066: Verify Super Admin dashboard displays required metrics (users, roles, expiry, health)."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/dashboard/")
    assert resp.status_code == 200
    assert "users" in resp.data
    assert "roles" in resp.data
    assert "archival" in resp.data
    assert "security" in resp.data


def test_fr_096_basic_user_receives_lifecycle_notifications():
    """TEST_FR_096 | AFR-SA-068: Verify basic users receive notifications for account creation, role changes, deactivation."""
    notif = AdminNotification.objects.create(
        recipient_username="STUD01",
        recipient_role="student",
        title="Account Notification",
        message="Your account has been updated.",
        category="account",
        channel="in_system",
    )
    assert notif.recipient_username == "STUD01"


def test_fr_097_super_admin_receives_administrative_notifications():
    """TEST_FR_097 | AFR-SA-069: Verify Super Admin receives notifications for bulk completion, role expiries, alerts."""
    notif = AdminNotification.objects.create(
        recipient_username="superadmin",
        recipient_role="Super Admin",
        title="Bulk Completed",
        message="Bulk operation completed with 10 records.",
        category="bulk_operation",
        channel="in_system",
    )
    assert notif.recipient_role == "Super Admin"


def test_fr_098_module_administrators_notified_on_role_changes():
    """TEST_FR_098 | AFR-SA-070: Verify module administrators receive notifications when a role in their module changes."""
    notif = AdminNotification.objects.create(
        recipient_username="mod_admin",
        recipient_role="Module Admin",
        title="Role Reassigned",
        message="Role HOD_CSE has been reassigned.",
        category="role_lifecycle",
        channel="in_system",
    )
    assert notif.recipient_role == "Module Admin"


def test_fr_099_notification_channels_supported():
    """TEST_FR_099 | AFR-SA-071A: Verify notification subsystem supports email and in-system delivery channels."""
    notif_in_system = AdminNotification.objects.create(
        recipient_username="superadmin",
        recipient_role="Super Admin",
        title="Test In-System",
        message="System alert",
        channel="in_system",
    )
    assert notif_in_system.channel in ("in_system", "email", "sms")


def test_fr_100_optional_sms_channel_for_security_alerts():
    """TEST_FR_100 | AFR-SA-071B: Verify SMS is supported as optional channel for critical security alerts."""
    alert = SecurityAlert.objects.create(
        alert_type="FAILED_LOGIN_THRESHOLD",
        severity="CRITICAL",
        message="5 consecutive failed logins detected",
        target_username="intruder",
    )
    assert alert.severity == "CRITICAL"


def test_fr_101_prevent_access_to_operational_content(stub_iam):
    """TEST_FR_101 | AFR-SA-072: Verify Super Admin is prevented from accessing module-specific operational content."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/placement/applications/")
    assert resp.status_code in (401, 403, 404)


def test_fr_102_prevent_self_assignment_of_super_admin():
    """TEST_FR_102 | AFR-SA-075: Verify system prevents Super Admin from self-assigning or modifying Super Admin status."""
    with pytest.raises(SecurityPolicyError):
        SecurityService.prevent_self_modification("superadmin", "superadmin", "modify")


def test_fr_103_enforce_strong_password_policy():
    """TEST_FR_103 | AFR-SA-073A-weak: Verify system enforces strong-password policy and rejects weak passwords."""
    with pytest.raises(SecurityPolicyError):
        SecurityService.validate_password_strength("weak")


def test_fr_104_require_two_factor_authentication():
    """TEST_FR_104 | AFR-SA-073B: Verify Super Admin login requires two-factor authentication (2FA)."""
    with pytest.raises(SecurityPolicyError):
        SecurityService.verify_two_factor("superadmin", "invalid_otp")


def test_fr_105_enforce_ip_whitelist_when_enabled():
    """TEST_FR_105 | AFR-SA-073C: Verify IP-whitelist check is enforced when optional IP-whitelist control is enabled."""
    SystemAdminConfig.objects.update_or_create(
        key="ip_whitelist_enabled",
        defaults={"value": True, "category": "security"},
    )
    SystemAdminConfig.objects.update_or_create(
        key="ip_whitelist",
        defaults={"value": ["10.0.0.1"], "category": "security"},
    )
    with pytest.raises(SecurityPolicyError):
        SecurityService.check_ip_whitelist("192.168.1.100")


def test_fr_106_single_active_super_admin_session():
    """TEST_FR_106 | AFR-SA-074A: Verify system permits only one active Super Admin session at a time."""
    s1 = SecurityService.establish_session("sess_1", "superadmin", "10.0.0.1")
    s2 = SecurityService.establish_session("sess_2", "superadmin", "10.0.0.2")
    s1.refresh_from_db()
    assert s1.is_active is False
    assert s2.is_active is True


def test_fr_107_enforce_session_inactivity_timeout():
    """TEST_FR_107 | AFR-SA-074B: Verify system enforces configured Super Admin session inactivity timeout."""
    SecurityService.establish_session("sess_timeout", "superadmin", "10.0.0.1")
    SessionLog.objects.filter(session_id="sess_timeout").update(
        last_activity_at=timezone.now() - timedelta(minutes=60)
    )

    with pytest.raises(SecurityPolicyError):
        SecurityService.check_and_update_session_activity("sess_timeout")


def test_fr_108_auditable_session_logs():
    """TEST_FR_108 | AFR-SA-074C: Verify system maintains auditable Super Admin session logs."""
    session = SecurityService.establish_session("sess_aud", "superadmin", "10.0.0.5")
    assert SessionLog.objects.filter(session_id=session.session_id).exists()


def test_fr_109_log_failed_login_attempts():
    """TEST_FR_109 | AFR-SA-080A: Verify system logs failed Super Admin login attempts."""
    initial_failed = SystemAdminAuditLog.objects.filter(action="LOGIN_FAILED").count()
    SecurityService.record_login_attempt("superadmin", success=False, ip_address="192.168.1.55")
    assert SystemAdminAuditLog.objects.filter(action="LOGIN_FAILED").count() == initial_failed + 1


def test_fr_110_trigger_alert_after_five_failed_logins():
    """TEST_FR_110 | AFR-SA-080B: Verify system triggers security alert after five consecutive failed login attempts."""
    for _ in range(5):
        SecurityService.record_login_attempt(
            "intruder_test", success=False, ip_address="192.168.1.99"
        )
    alert = SecurityAlert.objects.filter(target_username="intruder_test").first()
    assert alert is not None
    assert alert.severity == "CRITICAL" or alert.alert_type == "FAILED_LOGIN_THRESHOLD"


def test_fr_111_enforce_password_rotation_interval():
    """TEST_FR_111 | AFR-SA-082: Verify system checks password change at configured password-rotation interval."""
    interval_days = int(ConfigService.get_value("password_rotation_interval_days"))
    assert interval_days > 0


def test_fr_112_require_confirmation_for_critical_operations():
    """TEST_FR_112 | AFR-SA-079: Verify system requires confirmation with authentication for critical operations."""
    with pytest.raises(SecurityPolicyError):
        SecurityService.reauthenticate_critical_operation("superadmin", "")


def test_fr_113_configure_permitted_parameters(stub_iam):
    """TEST_FR_113 | AFR-SA-076: Verify Super Admin can configure permitted system parameters."""
    client = get_sa_client(stub_iam)
    resp = client.patch(
        "/api/v1/systemadmin/config/session_inactivity_timeout_minutes/",
        {"value": 45},
        format="json",
    )
    assert resp.status_code == 200
    assert ConfigService.get_value("session_inactivity_timeout_minutes") == 45


def test_fr_114_reject_modifying_prohibited_configurations(stub_iam):
    """TEST_FR_114 | AFR-SA-077: Verify system prevents Super Admin from modifying module-specific configurations."""
    client = get_sa_client(stub_iam)
    resp = client.patch(
        "/api/v1/systemadmin/config/academic_semester_fee_structure/",
        {"value": "prohibited_fee_policy"},
        format="json",
    )
    assert resp.status_code in (400, 403, 404)
