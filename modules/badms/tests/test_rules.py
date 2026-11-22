"""Comprehensive unit tests for BADMS pure business rules (BR-BA-001 through BR-BA-021).

Tests run in pure Python without database overhead.
"""

import pytest

from modules.badms.domain.entities import (
    ActorRole,
    DataClassification,
)
from modules.badms.domain.errors import (
    ActorNotAllowed,
    DepartmentScopeViolation,
    QuotaExceededError,
    RepositoryUnreachableError,
    RuleViolation,
    StorageNotFullError,
)
from modules.badms.domain.rules import (
    check_global_backup_auth,
    check_hod_department_scope,
    check_hod_storage_extension_auth,
    check_it_security_encryption_auth,
    check_it_security_rbac_auth,
    check_manual_backup_auth,
    check_repository_reachability,
    check_sensitive_restoration_approval_requirement,
    check_special_archival_auth,
    check_sysadmin_classification_auth,
    evaluate_failure_alerts,
    resolve_effective_schedule,
    resolve_initial_classification,
    validate_infrastructure_capacity,
    validate_retention_classification,
    validate_schedule_parameters,
    validate_sensitive_encryption_algorithm,
    validate_storage_extension_eligibility,
)


def test_br_ba_001_manual_backup_auth():
    # Permitted roles
    check_manual_backup_auth(ActorRole.SYSADMIN)
    check_manual_backup_auth(ActorRole.SUPER_ADMIN)

    # Denied roles
    for role in (ActorRole.USER, ActorRole.HOD, ActorRole.IT_SECURITY):
        with pytest.raises(RuleViolation) as exc:
            check_manual_backup_auth(role)
        assert exc.value.rule_id == "BR-BA-001"


def test_br_ba_002_and_010_hod_department_scope():
    # Matching department allowed
    check_hod_department_scope(ActorRole.HOD, hod_dept_id=1, target_dept_id=1)

    # Mismatched department denied
    with pytest.raises(DepartmentScopeViolation):
        check_hod_department_scope(ActorRole.HOD, hod_dept_id=1, target_dept_id=2)

    # Non-HoD actor denied
    with pytest.raises(ActorNotAllowed):
        check_hod_department_scope(ActorRole.USER, hod_dept_id=1, target_dept_id=1)


def test_br_ba_003_it_security_encryption_auth():
    check_it_security_encryption_auth(ActorRole.IT_SECURITY)

    for role in (ActorRole.USER, ActorRole.HOD, ActorRole.SYSADMIN, ActorRole.SUPER_ADMIN):
        with pytest.raises(RuleViolation) as exc:
            check_it_security_encryption_auth(role)
        assert exc.value.rule_id == "BR-BA-003"


def test_br_ba_004_sysadmin_classification_auth():
    check_sysadmin_classification_auth(ActorRole.SYSADMIN)

    for role in (ActorRole.USER, ActorRole.HOD, ActorRole.IT_SECURITY, ActorRole.SUPER_ADMIN):
        with pytest.raises(RuleViolation) as exc:
            check_sysadmin_classification_auth(role)
        assert exc.value.rule_id == "BR-BA-004"


def test_br_ba_005_sensitive_restoration_approval():
    # Sensitive without approval must fail
    with pytest.raises(RuleViolation) as exc:
        check_sensitive_restoration_approval_requirement(
            DataClassification.SENSITIVE, ActorRole.SYSADMIN, is_approved=False
        )
    assert exc.value.rule_id == "BR-BA-005"

    # Sensitive with approval succeeds
    check_sensitive_restoration_approval_requirement(
        DataClassification.SENSITIVE, ActorRole.SYSADMIN, is_approved=True
    )

    # Non-sensitive does not require approval
    check_sensitive_restoration_approval_requirement(
        DataClassification.ROUTINE, ActorRole.SYSADMIN, is_approved=False
    )


def test_br_ba_006_initial_classification_default():
    assert resolve_initial_classification(None) == DataClassification.ROUTINE
    assert resolve_initial_classification("") == DataClassification.ROUTINE
    assert resolve_initial_classification("sensitive") == DataClassification.SENSITIVE
    assert resolve_initial_classification("critical") == DataClassification.CRITICAL
    assert resolve_initial_classification("invalid_val") == DataClassification.ROUTINE


def test_br_ba_007_sensitive_data_encryption_algorithm():
    validate_sensitive_encryption_algorithm("AES-256")
    validate_sensitive_encryption_algorithm("aes-256-gcm")

    with pytest.raises(RuleViolation) as exc:
        validate_sensitive_encryption_algorithm("DES")
    assert exc.value.rule_id == "BR-BA-007"


def test_br_ba_008_retention_classification():
    assert "PERMANENT" in validate_retention_classification(DataClassification.CRITICAL)
    assert "7_YEARS" in validate_retention_classification(DataClassification.SENSITIVE)
    assert "3_YEARS" in validate_retention_classification(DataClassification.ROUTINE)
    assert "EXTENDED" in validate_retention_classification(DataClassification.ARCHIVAL)


def test_br_ba_009_hod_storage_extension_auth():
    check_hod_storage_extension_auth(ActorRole.HOD)

    with pytest.raises(RuleViolation) as exc:
        check_hod_storage_extension_auth(ActorRole.USER)
    assert exc.value.rule_id == "BR-BA-009"


def test_br_ba_011_local_schedule_overrides_global():
    local = {"scope": "local", "is_active": True, "dataset": "finance"}
    global_sched = {"scope": "global", "is_active": True, "dataset": "all"}

    # Local overrides global
    assert resolve_effective_schedule(local, global_sched) == local

    # Inactive local falls back to global
    inactive_local = {"scope": "local", "is_active": False}
    assert resolve_effective_schedule(inactive_local, global_sched) == global_sched

    # No local falls back to global
    assert resolve_effective_schedule(None, global_sched) == global_sched


def test_br_ba_012_schedule_parameter_validation():
    valid, _ = validate_schedule_parameters("daily", "02:00", "academics")
    assert valid is True

    valid, _ = validate_schedule_parameters("invalid_freq", "02:00", "academics")
    assert valid is False

    valid, _ = validate_schedule_parameters("daily", "25:00", "academics")
    assert valid is False

    valid, _ = validate_schedule_parameters("daily", "02:00", "")
    assert valid is False


def test_br_ba_013_repository_reachability():
    check_repository_reachability(True, "/var/backups")

    with pytest.raises(RepositoryUnreachableError):
        check_repository_reachability(False, "/var/backups")


def test_br_ba_014_and_015_failure_alerts_and_escalation():
    # Single failure
    alerts1 = evaluate_failure_alerts(1)
    assert alerts1["alert_sysadmin"] is True
    assert alerts1["escalate_director_it"] is False

    # Two failures
    alerts2 = evaluate_failure_alerts(2)
    assert alerts2["escalate_director_it"] is False

    # Three consecutive failures -> escalate
    alerts3 = evaluate_failure_alerts(3)
    assert alerts3["alert_sysadmin"] is True
    assert alerts3["escalate_director_it"] is True


def test_br_ba_016_storage_extension_eligibility():
    # Quota full
    validate_storage_extension_eligibility(current_usage_bytes=1000, quota_bytes=1000)
    validate_storage_extension_eligibility(current_usage_bytes=1100, quota_bytes=1000)

    # Quota not full -> raises
    with pytest.raises(StorageNotFullError):
        validate_storage_extension_eligibility(current_usage_bytes=500, quota_bytes=1000)


def test_br_ba_017_infrastructure_capacity():
    validate_infrastructure_capacity(requested_bytes=500, available_infra_bytes=1000)

    with pytest.raises(QuotaExceededError):
        validate_infrastructure_capacity(requested_bytes=1500, available_infra_bytes=1000)

    with pytest.raises(RuleViolation):
        validate_infrastructure_capacity(requested_bytes=-5, available_infra_bytes=1000)


def test_br_ba_018_special_archival_super_admin_auth():
    check_special_archival_auth(ActorRole.SUPER_ADMIN)

    for role in (ActorRole.USER, ActorRole.HOD, ActorRole.SYSADMIN, ActorRole.IT_SECURITY):
        with pytest.raises(RuleViolation) as exc:
            check_special_archival_auth(role)
        assert exc.value.rule_id == "BR-BA-018"


def test_br_ba_019_super_admin_global_backup_auth():
    check_global_backup_auth(ActorRole.SUPER_ADMIN)

    for role in (ActorRole.USER, ActorRole.HOD, ActorRole.SYSADMIN, ActorRole.IT_SECURITY):
        with pytest.raises(RuleViolation) as exc:
            check_global_backup_auth(role)
        assert exc.value.rule_id == "BR-BA-019"


def test_br_ba_021_it_security_rbac_auth():
    check_it_security_rbac_auth(ActorRole.IT_SECURITY)

    for role in (ActorRole.USER, ActorRole.HOD, ActorRole.SYSADMIN, ActorRole.SUPER_ADMIN):
        with pytest.raises(RuleViolation) as exc:
            check_it_security_rbac_auth(role)
        assert exc.value.rule_id == "BR-BA-021"
