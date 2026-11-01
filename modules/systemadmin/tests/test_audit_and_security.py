"""Tests for Audit Logging, Security Constraints, and System Parameter Boundaries."""
import pytest
from datetime import date
from django.utils import timezone

from modules.systemadmin.models.audit import SystemAdminAuditLog, SecurityAlert, AdminNotification
from modules.systemadmin.models.config import SystemAdminConfig
from modules.systemadmin.services.audit_service import AuditService
from modules.systemadmin.services.config_service import ConfigService, ConfigurationError
from modules.systemadmin.services.security_service import SecurityService, SecurityPolicyError

pytestmark = pytest.mark.django_db


def test_immutable_audit_logging():
    """Verify audit logging records action details accurately (BR-SA-025, CFR-SA-017)."""
    entry = AuditService.log_action(
        actor_username="superadmin",
        action="TEST_ACTION",
        result="SUCCESS",
        target_user="STU001",
        target_role="STUDENT_SENATE",
        reason_or_context="Testing immutable audit recording",
        metadata={"key": "val"},
    )
    assert entry.id is not None
    assert entry.actor_username == "superadmin"
    assert entry.action == "TEST_ACTION"
    assert entry.result == "SUCCESS"
    assert entry.metadata["key"] == "val"


def test_audit_summary_metrics():
    """Verify audit aggregation metrics for reports (CFR-SA-018)."""
    AuditService.log_action("admin1", "USER_CREATE", "SUCCESS", target_user="U1")
    AuditService.log_action("admin1", "ROLE_ASSIGN", "SUCCESS", target_role="R1")
    AuditService.log_action("admin2", "USER_DEACTIVATE", "FAILURE", reason_or_context="Self modification")

    summary = AuditService.aggregate_audit_summary()
    assert summary["total_actions"] >= 3
    assert summary["success_count"] >= 2
    assert summary["failure_count"] >= 1
    assert "USER_CREATE" in summary["actions_by_type"]


def test_strictly_reject_operational_configuration(monkeypatch):
    """Verify prohibited operational, academic, or financial configuration is rejected (BR-SA-035)."""
    with pytest.raises(ConfigurationError) as exc_info:
        ConfigService.update_configuration(
            key="academic_calendar_fall_dates",
            value="2026-08-01",
            actor_username="superadmin",
        )
    assert "prohibited from modifying" in str(exc_info.value)

    with pytest.raises(ConfigurationError) as exc_info:
        ConfigService.update_configuration(
            key="course_grading_formula",
            value="relative",
            actor_username="superadmin",
        )
    assert "prohibited from modifying" in str(exc_info.value)


def test_permitted_configuration_update():
    """Verify permitted system parameters update cleanly (AFR-SA-077)."""
    cfg = ConfigService.update_configuration(
        key="password_min_length",
        value=12,
        actor_username="superadmin",
    )
    assert cfg.value == 12

    val = ConfigService.get_value("password_min_length")
    assert val == 12


def test_password_strength_enforcement():
    """Verify password policy adheres to length and character composition (BR-SA-024)."""
    # Too short
    with pytest.raises(SecurityPolicyError):
        SecurityService.validate_password_strength("Short1!")

    # Missing special char
    with pytest.raises(SecurityPolicyError):
        SecurityService.validate_password_strength("StrongPass1234")

    # Valid
    SecurityService.validate_password_strength("Fusion@Secure2026")


def test_prevent_self_modification():
    """Verify administrator cannot deactivate or modify their own account (BR-SA-028)."""
    with pytest.raises(SecurityPolicyError) as exc_info:
        SecurityService.prevent_self_modification(
            actor_username="admin_user",
            target_username="admin_user",
            action="DEACTIVATE",
        )
    assert "cannot perform destructive or status-altering" in str(exc_info.value)
