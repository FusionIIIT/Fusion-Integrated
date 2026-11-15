"""Unit tests for Phase 4 selectors with mocked queries."""
from unittest.mock import MagicMock, patch
import pytest
from datetime import date, timedelta
from django.utils import timezone

from modules.system_admin.constants import (
    RoleAssignmentState,
    RoleCategory,
    UserArchivalStatus,
    UserKind,
    UserLifecycleStatus,
)
from modules.system_admin.selectors import (
    get_all_permitted_parameters,
    get_archived_user,
    get_assignments_pending_activation,
    get_assignments_pending_expiry,
    get_deactivated_users_eligible_for_archival,
    get_expired_reversible_user_records,
    get_role_availability,
    get_role_definition,
    get_super_admin_dashboard_metrics,
    get_system_parameter,
    get_user_active_assignments,
    get_user_by_id,
    get_user_by_institute_id,
    get_user_by_username,
    get_user_status_history,
    list_archived_users,
    list_historical_archives,
    list_purge_requests,
    list_role_definitions,
    list_users,
    query_audit_logs,
)


@patch("modules.system_admin.models.BasicUser.objects")
def test_user_selectors(mock_users):
    mock_qs = MagicMock()
    mock_qs.first.return_value = None
    mock_qs.select_related.return_value = mock_qs
    mock_qs.order_by.return_value = mock_qs
    mock_qs.count.return_value = 0
    mock_qs.__getitem__.return_value = []
    mock_users.filter.return_value = mock_qs
    mock_users.select_related.return_value = mock_qs

    assert get_user_by_id(99999) is None
    assert get_user_by_institute_id("NONEXISTENT") is None
    assert get_user_by_username("nonexistent") is None
    users, total = list_users()
    assert total == 0
    assert users == []


@patch("modules.system_admin.models.RoleDefinition.objects")
@patch("modules.system_admin.models.RoleAssignment.objects")
def test_role_selectors(mock_assigns, mock_defs):
    mock_defs.filter.return_value.first.return_value = None
    mock_defs.all.return_value.order_by.return_value.filter.return_value = []

    assert get_role_definition("nonexistent") is None
    avail = get_role_availability("nonexistent")
    assert avail["is_available"] is False


@patch("modules.system_admin.models.ArchivedUserRecord.objects")
def test_archival_selectors(mock_arch):
    mock_qs = MagicMock()
    mock_qs.first.return_value = None
    mock_qs.__iter__.return_value = iter([])
    mock_arch.filter.return_value = mock_qs

    assert get_archived_user(99999) is None
    assert get_expired_reversible_user_records(timezone.now()) == []


@patch("modules.system_admin.models.BasicUser.objects")
@patch("modules.system_admin.models.RoleAssignment.objects")
@patch("modules.system_admin.models.ArchivedUserRecord.objects")
@patch("modules.system_admin.models.HistoricalDataArchive.objects")
@patch("modules.system_admin.models.PurgeRequest.objects")
@patch("modules.system_admin.models.SuperAdminSession.objects")
def test_dashboard_metrics(m_sess, m_purge, m_hist, m_arch, m_role, m_user):
    m_user.all.return_value.filter.return_value.count.return_value = 10
    m_role.filter.return_value.count.return_value = 5
    m_arch.filter.return_value.count.return_value = 2
    m_hist.filter.return_value.count.return_value = 3
    m_purge.filter.return_value.count.return_value = 1
    m_sess.filter.return_value.count.return_value = 1

    metrics = get_super_admin_dashboard_metrics()
    assert "users" in metrics
    assert "roles" in metrics
    assert "archival" in metrics
    assert "security" in metrics
    assert metrics["users"]["total_active"] == 30


@patch("modules.system_admin.models.SystemParameter.objects")
def test_system_parameter_selector(mock_param):
    mock_qs = MagicMock()
    mock_qs.first.return_value = None
    mock_qs.__iter__.return_value = iter([])
    mock_param.filter.return_value = mock_qs

    assert get_system_parameter("nonexistent.param", default=42) == 42
    params = get_all_permitted_parameters()
    assert isinstance(params, dict)
