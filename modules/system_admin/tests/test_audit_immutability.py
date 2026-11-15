"""Unit tests for Phase 3 models: immutability, boundary validation, and role helpers."""
from unittest.mock import patch
import pytest

from modules.system_admin.constants import AuditAction, AuditResult, PermittedConfigKey, RoleCategory
from modules.system_admin.exceptions import (
    ConfigurationBoundaryViolationError,
    ImmutableFieldModificationError,
)
from modules.system_admin.models import (
    ArchivedUserRecord,
    BasicUser,
    FailedLoginAttempt,
    HistoricalDataArchive,
    NotificationOutbox,
    PurgeRequest,
    RoleAssignment,
    RoleAssignmentHistory,
    RoleDefinition,
    RoleHandoverLog,
    SuperAdminAuditLog,
    SuperAdminSession,
    SystemParameter,
    TwoFactorCredential,
    UserActivityLog,
    UserProfile,
    UserStatusHistory,
)


def test_models_exported():
    """Verify all 16 Phase 3 domain models are exported."""
    expected_models = [
        BasicUser,
        UserProfile,
        UserStatusHistory,
        RoleDefinition,
        RoleAssignment,
        RoleAssignmentHistory,
        RoleHandoverLog,
        ArchivedUserRecord,
        HistoricalDataArchive,
        PurgeRequest,
        SuperAdminAuditLog,
        UserActivityLog,
        SuperAdminSession,
        FailedLoginAttempt,
        TwoFactorCredential,
        SystemParameter,
        NotificationOutbox,
    ]
    for model in expected_models:
        assert model is not None


def test_super_admin_audit_log_delete_prevented():
    """BR-SA-025: Audit log entries must never be deletable."""
    log = SuperAdminAuditLog(
        id=1,
        actor_id=42,
        actor_username="admin_user",
        action=AuditAction.USER_CREATE,
        result=AuditResult.SUCCESS,
    )
    with pytest.raises(PermissionError, match="permanent and strictly immutable"):
        log.delete()


def test_super_admin_audit_log_update_prevented():
    """BR-SA-025: Existing audit log entries cannot be modified or updated."""
    log = SuperAdminAuditLog(
        id=10,
        actor_id=42,
        actor_username="admin_user",
        action=AuditAction.USER_CREATE,
        result=AuditResult.SUCCESS,
    )
    with pytest.raises(PermissionError, match="Existing audit log entries cannot be modified"):
        log.save()


def test_super_admin_audit_log_insert_allowed():
    """New audit log entries (pk is None) are allowed to save."""
    log = SuperAdminAuditLog(
        actor_id=42,
        actor_username="admin_user",
        action=AuditAction.USER_CREATE,
        result=AuditResult.SUCCESS,
    )
    assert log.pk is None
    with patch("django.db.models.Model.save") as mock_super_save:
        log.save()
        mock_super_save.assert_called_once()


def test_system_parameter_validates_key_whitelist():
    """BR-SA-035: Parameters outside PermittedConfigKey.ALL_KEYS must be rejected."""
    invalid_param = SystemParameter(
        key="unauthorized.param.key",
        value="value",
        updated_by=1,
    )
    with pytest.raises(ConfigurationBoundaryViolationError):
        invalid_param.save()

    valid_param = SystemParameter(
        key=PermittedConfigKey.PASSWORD_MIN_LENGTH,
        value="12",
        updated_by=1,
    )
    with patch("django.db.models.Model.save") as mock_super_save:
        valid_param.save()
        mock_super_save.assert_called_once()


def test_basic_user_institute_id_immutability():
    """BR-SA-001: institute_id cannot be changed once assigned."""
    user = BasicUser(
        id=100,
        username="student1",
        institute_id="2024CS01",
        email="student1@iiitdmj.ac.in",
        kind="student",
    )
    orig_mock = BasicUser(id=100, institute_id="2024CS01")

    with patch.object(BasicUser.objects, "only") as mock_only:
        mock_only.return_value.get.return_value = orig_mock

        # Saving with unaltered institute_id succeeds
        with patch("django.db.models.Model.save") as mock_super_save:
            user.save()
            mock_super_save.assert_called_once()

        # Changing institute_id raises ImmutableFieldModificationError
        user.institute_id = "2024CS99"
        with pytest.raises(ImmutableFieldModificationError):
            user.save()


def test_role_definition_helpers():
    """RoleDefinition helper methods for kind checking."""
    role = RoleDefinition(
        code="hod_cse",
        label="Head of Department CSE",
        category=RoleCategory.OFFICE,
        allowed_kinds="faculty, staff",
    )
    assert role.get_allowed_kinds_set() == {"faculty", "staff"}
    assert role.is_eligible_kind("faculty") is True
    assert role.is_eligible_kind("staff") is True
    assert role.is_eligible_kind("student") is False

    empty_role = RoleDefinition(code="empty", label="Empty", category=RoleCategory.BASIC, allowed_kinds="")
    assert empty_role.get_allowed_kinds_set() == set()
    assert empty_role.is_eligible_kind("faculty") is False
