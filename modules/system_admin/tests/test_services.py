"""Unit tests for Phase 5 services."""
from unittest.mock import MagicMock, patch
import pytest
from datetime import date, timedelta
from django.utils import timezone

from modules.system_admin.domain.dataclasses import (
    RoleAssignmentSpec,
    RoleReassignmentSpec,
    RoleRevocationSpec,
    UserCreationSpec,
)
from modules.system_admin.domain.exceptions import (
    BulkLimitExceededError,
    ConfigurationBoundaryViolationError,
    DomainError,
    IdentityValidationError,
    ImmutabilityViolationError,
    PurgeDualAuthRequiredError,
    ReversibilityExpiredError,
    SingularRoleOccupiedError,
)
from modules.system_admin.services import (
    archive_historical_data,
    archive_user,
    assign_role,
    authorize_permanent_purge,
    create_basic_user,
    deactivate_user,
    execute_bulk_status_update,
    execute_bulk_user_creation,
    extend_role_validity,
    finalize_expired_reversible_users,
    queue_notification,
    reactivate_user,
    reassign_role,
    record_failed_login,
    request_permanent_purge,
    restore_archived_user,
    restore_historical_data,
    revoke_role,
    switch_active_role,
    update_basic_user_profile,
    update_system_parameter,
)


def test_bulk_size_limit_in_service():
    # 1001 records rejected
    lines = ["user_kind,name,institute_email,institute_id,contact_number,department,programme,discipline,batch_year,employee_id"]
    for i in range(1001):
        lines.append(f"student,Student {i},stu{i}@iiitdmj.ac.in,ID{i},9999999999,,B.Tech,CSE,2026,")
    csv_content = "\n".join(lines)

    with pytest.raises(BulkLimitExceededError, match="exceeds the limit of 1000"):
        execute_bulk_user_creation(csv_content, performed_by_id=1)


def test_config_parameter_boundary_violation():
    with pytest.raises(ConfigurationBoundaryViolationError):
        update_system_parameter("financial.tuition_fee", "50000", performed_by_id=1)


@patch("modules.system_admin.models.BasicUser.objects")
def test_update_profile_immutable_id(mock_users):
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.institute_id = "2026BCS001"
    mock_users.select_related.return_value.get.return_value = mock_user

    with pytest.raises(ImmutabilityViolationError):
        update_basic_user_profile(
            user_id=1,
            updates={"institute_id": "MODIFIED_ID"},
            performed_by_id=1,
        )


@patch("modules.system_admin.models.PurgeRequest.objects")
@patch("modules.system_admin.models.HistoricalDataArchive.objects")
def test_purge_dual_auth_prevent_self_authorization(mock_arch, mock_purge):
    req = MagicMock()
    req.status = "pending_it_head"
    req.requested_by = 42
    mock_purge.select_related.return_value.get.return_value = req

    # Requester attempting to authorize own request
    with pytest.raises(PurgeDualAuthRequiredError):
        authorize_permanent_purge(
            request_id=1,
            it_head_id=42,
            approved=True,
        )


@patch("modules.system_admin.models.RoleAssignment.objects")
def test_switch_active_role_unassigned(mock_assign):
    mock_assign.filter.return_value.exists.return_value = False
    with pytest.raises(DomainError, match="does not hold an active assignment"):
        switch_active_role(user_id=10, target_role_code="dean_academic")
