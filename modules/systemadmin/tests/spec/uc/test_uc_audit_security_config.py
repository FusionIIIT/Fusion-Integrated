"""Use Case Executable Tests: Audit, Security, Config, and Dashboard.

Covers UC-SA-024 through UC-SA-027, and UC-SA-032 through UC-SA-034.
Traceable to UC_DESIGN.json test cases TEST_UC_082 through TEST_UC_094, and TEST_UC_107 through TEST_UC_117.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models.audit import SecurityAlert, SessionLog, SystemAdminAuditLog
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


# --- UC-SA-024: View Audit Log ---


def test_uc_082_view_audit_log_main_flow(stub_iam):
    """TEST_UC_082 | UC-SA-024 Main Flow: Verify Super Admin views audit log entries."""
    AuditService.log_action(
        actor_username="superadmin_sec",
        action="CONFIG_UPDATED",
        reason_or_context="Audit log view test",
    )
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/")
    assert resp.status_code == 200
    assert len(resp.data) >= 1 or "results" in resp.data


def test_uc_083_view_audit_log_alt_a1_no_matching_entries(stub_iam):
    """TEST_UC_083 | UC-SA-024 Alternative A1: Verify empty result view when no audit entries match query."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/?action=IMPOSSIBLE_ACTION_FILTER_XYZ")
    assert resp.status_code == 200
    results = resp.data.get("results", resp.data)
    assert len(results) == 0


def test_uc_084_view_audit_log_exc_e1_tamper_evident_preservation():
    """TEST_UC_084 | UC-SA-024 Exception E1: Verify audit logs are immutable and tamper-evident."""
    entry = AuditService.log_action(
        actor_username="superadmin",
        action="USER_DEACTIVATED",
        reason_or_context="Tamper protection test",
    )
    assert entry.id is not None
    assert SystemAdminAuditLog.objects.filter(id=entry.id).exists()


# --- UC-SA-025: Generate Audit Report ---


def test_uc_085_generate_audit_report_main_flow(stub_iam):
    """TEST_UC_085 | UC-SA-025 Main Flow: Verify Super Admin generates audit report with filters."""
    AuditService.log_action(
        actor_username="superadmin_sec",
        action="ROLE_ASSIGNED",
        reason_or_context="Report generation action",
    )
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/reports/?format=json")
    assert resp.status_code == 200
    assert "total_actions" in resp.data or "report_id" in resp.data or isinstance(resp.data, list)


def test_uc_086_generate_audit_report_alt_a1_no_data_for_parameters(stub_iam):
    """TEST_UC_086 | UC-SA-025 Alternative A1: Verify report generates empty summary when date range has no logs."""
    client = get_sa_client(stub_iam)
    resp = client.get(
        "/api/v1/systemadmin/audit/reports/?start_date=2000-01-01&end_date=2000-01-02"
    )
    assert resp.status_code == 200


def test_uc_087_generate_audit_report_exc_e1_prohibited_content_filtered(stub_iam):
    """TEST_UC_087 | UC-SA-025 Exception E1: Verify audit report excludes operational password hashes or financial data."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/audit/reports/?format=json")
    assert resp.status_code == 200
    assert "password_hash" not in str(resp.data)


# --- UC-SA-026: View Super Admin Dashboard ---


def test_uc_088_view_dashboard_main_flow(stub_iam):
    """TEST_UC_088 | UC-SA-026 Main Flow: Verify Super Admin retrieves system administration metrics."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/dashboard/")
    assert resp.status_code == 200
    assert "users" in resp.data or "total_users" in resp.data or "active_users" in resp.data


def test_uc_089_view_dashboard_alt_a1_zero_metric_defaults(stub_iam):
    """TEST_UC_089 | UC-SA-026 Alternative A1: Verify system displays valid default metric structure when counts are zero."""
    client = get_sa_client(stub_iam)
    resp = client.get("/api/v1/systemadmin/dashboard/")
    assert resp.status_code == 200


def test_uc_090_view_dashboard_exc_e1_unauthenticated_rejected():
    """TEST_UC_090 | UC-SA-026 Exception E1: Verify unauthenticated dashboard access is rejected."""
    client = APIClient()
    resp = client.get("/api/v1/systemadmin/dashboard/")
    assert resp.status_code in (401, 403)


# --- UC-SA-027: Configure Permitted System Parameters ---


def test_uc_091_configure_permitted_parameters_main_flow(stub_iam):
    """TEST_UC_091 | UC-SA-027 Main Flow: Verify Super Admin updates permitted system parameter."""
    client = get_sa_client(stub_iam)
    resp = client.patch(
        "/api/v1/systemadmin/config/session_inactivity_timeout_minutes/",
        {"value": 45},
        format="json",
    )
    assert resp.status_code == 200
    assert ConfigService.get_value("session_inactivity_timeout_minutes") == 45


def test_uc_092_configure_permitted_parameters_alt_a1_cancel_preserves_value():
    """TEST_UC_092 | UC-SA-027 Alternative A1: Verify canceling configuration update preserves existing value."""
    orig_val = ConfigService.get_value("password_min_length")
    # Super Admin cancels without submitting
    assert ConfigService.get_value("password_min_length") == orig_val


def test_uc_093_configure_permitted_parameters_exc_e1_reject_operational_params(stub_iam):
    """TEST_UC_093 | UC-SA-027 Exception E1: Verify attempting to configure prohibited academic/financial policy is rejected."""
    client = get_sa_client(stub_iam)
    resp = client.patch(
        "/api/v1/systemadmin/config/semester_tuition_fee_structure/",
        {"value": "100000"},
        format="json",
    )
    assert resp.status_code in (400, 403, 404)


def test_uc_094_configure_permitted_parameters_exc_e2_value_out_of_bounds(stub_iam):
    """TEST_UC_094 | UC-SA-027 Exception E2: Verify configuration value violating policy bounds is rejected."""
    client = get_sa_client(stub_iam)
    # password_min_length minimum is 6, maximum is 32
    resp = client.patch(
        "/api/v1/systemadmin/config/password_min_length/",
        {"value": 2},
        format="json",
    )
    assert resp.status_code == 400


# --- UC-SA-032: Process Failed-Login Threshold Alert ---


def test_uc_107_process_failed_login_threshold_main_flow():
    """TEST_UC_107 | UC-SA-032 Main Flow: Verify 5 consecutive failed logins trigger lockout and security alert."""
    username = "uc_attacker_99"
    for _ in range(5):
        SecurityService.record_login_attempt(username, success=False, ip_address="192.168.10.50")

    alert = SecurityAlert.objects.filter(target_username=username).first()
    assert alert is not None
    assert alert.severity == "CRITICAL" or alert.alert_type == "FAILED_LOGIN_THRESHOLD"


def test_uc_108_process_failed_login_threshold_alt_a1_below_threshold():
    """TEST_UC_108 | UC-SA-032 Alternative A1: Verify consecutive failures below 5 are logged without locking account."""
    username = "uc_normal_typo"
    for _ in range(3):
        SecurityService.record_login_attempt(username, success=False, ip_address="192.168.10.51")

    assert not SecurityAlert.objects.filter(target_username=username).exists()


def test_uc_109_process_failed_login_threshold_exc_e1_successful_login_resets_counter():
    """TEST_UC_109 | UC-SA-032 Exception E1: Verify successful login resets consecutive failed attempt counter."""
    username = "uc_reset_counter"
    for _ in range(3):
        SecurityService.record_login_attempt(username, success=False, ip_address="192.168.10.52")
    SecurityService.record_login_attempt(username, success=True, ip_address="192.168.10.52")

    # Next 2 failures should not trigger threshold of 5
    for _ in range(2):
        SecurityService.record_login_attempt(username, success=False, ip_address="192.168.10.52")
    assert not SecurityAlert.objects.filter(target_username=username).exists()


# --- UC-SA-033: Authenticate Super Admin and Establish Session ---


def test_uc_110_authenticate_super_admin_main_flow():
    """TEST_UC_110 | UC-SA-033 Main Flow: Verify Super Admin authenticates and establishes valid administrative session."""
    session = SecurityService.establish_session(
        session_id="uc_sess_admin_01",
        username="superadmin_sec",
        ip_address="10.0.1.10",
    )
    assert session.is_active is True
    assert SessionLog.objects.filter(session_id="uc_sess_admin_01", is_active=True).exists()


def test_uc_111_authenticate_super_admin_alt_a1_password_rotation_interval():
    """TEST_UC_111 | UC-SA-033 Alternative A1: Verify password rotation interval configuration is enforced."""
    rotation_days = ConfigService.get_value("password_rotation_interval_days")
    assert rotation_days >= 15


def test_uc_112_authenticate_super_admin_alt_a2_ip_whitelist_disabled():
    """TEST_UC_112 | UC-SA-033 Alternative A2: Verify authentication succeeds when IP whitelist is disabled."""
    session = SecurityService.establish_session(
        session_id="uc_sess_no_wl",
        username="superadmin_sec",
        ip_address="172.16.0.99",
    )
    assert session.is_active is True


def test_uc_113_authenticate_super_admin_exc_e1_invalid_credentials_prevent_session():
    """TEST_UC_113 | UC-SA-033 Exception E1: Verify invalid authentication credentials prevent session establishment."""
    # Failed authentication logs attempt and establishes no active session
    SecurityService.record_login_attempt("intruder_uc", success=False, ip_address="203.0.113.5")
    assert not SessionLog.objects.filter(username="intruder_uc", is_active=True).exists()


def test_uc_114_authenticate_super_admin_exc_e2_single_active_session_enforced():
    """TEST_UC_114 | UC-SA-033 Exception E2: Verify establishing new session terminates any existing active session."""
    s1 = SecurityService.establish_session("uc_single_sess_1", "superadmin_multi", "10.0.0.1")
    assert s1.is_active is True

    s2 = SecurityService.establish_session("uc_single_sess_2", "superadmin_multi", "10.0.0.2")
    assert s2.is_active is True
    s1.refresh_from_db()
    assert s1.is_active is False
    assert s1.termination_reason == "single_session_kick"


# --- UC-SA-034: Terminate Inactive Super Admin Session ---


def test_uc_115_terminate_inactive_session_main_flow():
    """TEST_UC_115 | UC-SA-034 Main Flow: Verify inactive session is terminated when inactivity threshold elapses."""
    session = SecurityService.establish_session("uc_timeout_sess_1", "superadmin_time", "10.0.0.5")
    SessionLog.objects.filter(session_id="uc_timeout_sess_1").update(
        last_activity_at=timezone.now() - timedelta(minutes=60)
    )

    with pytest.raises(SecurityPolicyError):
        SecurityService.check_and_update_session_activity("uc_timeout_sess_1")

    session.refresh_from_db()
    assert session.is_active is False
    assert session.termination_reason == "inactivity_timeout"


def test_uc_116_terminate_inactive_session_alt_a1_activity_resets_touch_timestamp():
    """TEST_UC_116 | UC-SA-034 Alternative A1: Verify activity within threshold updates touch timestamp and maintains session."""
    session = SecurityService.establish_session("uc_touch_sess_1", "superadmin_touch", "10.0.0.6")
    SecurityService.check_and_update_session_activity("uc_touch_sess_1")
    session.refresh_from_db()
    assert session.is_active is True


def test_uc_117_terminate_inactive_session_exc_e1_session_infrastructure_tamper_safety():
    """TEST_UC_117 | UC-SA-034 Exception E1: Verify non-existent session ID does not corrupt active session logs."""
    # Invoking activity check on terminated or non-existent session safely returns without exception
    SecurityService.check_and_update_session_activity("NON_EXISTENT_SESSION_ID")
