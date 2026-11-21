"""Comprehensive unit and API test suite for Phase 7 REST API layer.

Tests permissions, serializers, viewsets, and compliance boundaries.
Traceability: CFR-SA-001..023, BR-SA-001, BR-SA-022, BR-SA-026, BR-SA-028, BR-SA-029.
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch
import pytest

from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIRequestFactory

from fusion_auth.principal import Principal
from modules.system_admin.api import permissions, serializers as s, views
from modules.system_admin.domain.exceptions import (
    IdentityValidationError,
    ReversibilityExpiredError,
)
from modules.system_admin.models import BasicUser, RoleAssignment, RoleDefinition


@pytest.fixture
def super_admin_principal():
    return Principal(
        user_id=1,
        username="superadmin",
        display_name="Super Admin",
        kind="staff",
        active_role="super_admin",
        roles=("super_admin",),
        permissions=frozenset(["system_admin.access", "admin:access"]),
        modules=("system_admin",),
    )


@pytest.fixture
def it_head_principal():
    return Principal(
        user_id=2,
        username="ithead",
        display_name="IT Head",
        kind="faculty",
        active_role="it_head",
        roles=("it_head",),
        permissions=frozenset(["it_head:access", "system_admin:purge_authorize"]),
        modules=("system_admin",),
    )


@pytest.fixture
def standard_student_principal():
    return Principal(
        user_id=10,
        username="student1",
        display_name="Student One",
        kind="student",
        active_role="student",
        roles=("student",),
        permissions=frozenset(),
        modules=(),
    )


@pytest.fixture
def rf():
    return APIRequestFactory()


# ==============================================================================
# 1. PERMISSIONS TESTS
# ==============================================================================


def test_is_super_admin_principal_permits_super_admin(rf, super_admin_principal):
    perm = permissions.IsSuperAdminPrincipal()
    req = rf.get("/api/v1/system_admin/users/")
    req.principal = super_admin_principal
    assert perm.has_permission(req, None) is True


def test_is_super_admin_principal_denies_standard_user(rf, standard_student_principal):
    perm = permissions.IsSuperAdminPrincipal()
    req = rf.get("/api/v1/system_admin/users/")
    req.principal = standard_student_principal
    assert perm.has_permission(req, None) is False


def test_is_super_admin_principal_denies_anonymous(rf):
    perm = permissions.IsSuperAdminPrincipal()
    req = rf.get("/api/v1/system_admin/users/")
    req.principal = None
    assert perm.has_permission(req, None) is False


def test_is_it_head_principal_permits_it_head(rf, it_head_principal):
    perm = permissions.IsITHeadPrincipal()
    req = rf.post("/api/v1/system_admin/purge/1/authorize/")
    req.principal = it_head_principal
    assert perm.has_permission(req, None) is True


def test_is_it_head_principal_denies_super_admin(rf, super_admin_principal):
    perm = permissions.IsITHeadPrincipal()
    req = rf.post("/api/v1/system_admin/purge/1/authorize/")
    req.principal = super_admin_principal
    assert perm.has_permission(req, None) is False


def test_deny_self_modification_blocks_same_user_id(rf, super_admin_principal):
    perm = permissions.DenySelfModification()
    view = MagicMock()
    view.kwargs = {"pk": "1"}
    req = rf.post("/api/v1/system_admin/users/1/deactivate/")
    req.principal = super_admin_principal

    with pytest.raises(PermissionDenied, match="cannot self-modify their own account"):
        perm.has_permission(req, view)


def test_deny_self_modification_permits_other_user_id(rf, super_admin_principal):
    perm = permissions.DenySelfModification()
    view = MagicMock()
    view.kwargs = {"pk": "42"}
    req = rf.post("/api/v1/system_admin/users/42/deactivate/")
    req.principal = super_admin_principal
    assert perm.has_permission(req, view) is True


def test_deny_self_modification_object_permission(rf, super_admin_principal):
    perm = permissions.DenySelfModification()
    view = MagicMock()
    req = rf.patch("/api/v1/system_admin/users/1/")
    req.principal = super_admin_principal

    mock_target = MagicMock(spec=BasicUser)
    mock_target.id = 1
    with pytest.raises(PermissionDenied, match="cannot self-modify their own account"):
        perm.has_object_permission(req, view, mock_target)

    mock_other = MagicMock(spec=BasicUser)
    mock_other.id = 99
    assert perm.has_object_permission(req, view, mock_other) is True


@patch("modules.system_admin.services.security.verify_critical_action_reauth")
def test_requires_critical_action_confirmation_validates_credentials(mock_reauth, rf, super_admin_principal):
    mock_reauth.return_value = True
    perm = permissions.RequiresCriticalActionConfirmation()

    req = rf.post(
        "/api/v1/system_admin/archival/1/archive_user/",
        HTTP_X_CONFIRM_PASSWORD="ValidSuperSecret123!",
    )
    req.principal = super_admin_principal
    assert perm.has_permission(req, None) is True
    mock_reauth.assert_called_once_with(
        admin_user_id=1, password="ValidSuperSecret123!", totp_code=""
    )


def test_requires_critical_action_confirmation_missing_header_raises(rf, super_admin_principal):
    perm = permissions.RequiresCriticalActionConfirmation()
    req = rf.post("/api/v1/system_admin/archival/1/archive_user/")
    req.principal = super_admin_principal

    with pytest.raises(PermissionDenied, match="Missing required re-authentication header"):
        perm.has_permission(req, None)


def test_enforce_data_isolation_boundary_blocks_operational_keywords(rf):
    perm = permissions.EnforceDataIsolationBoundary()

    req_grades = rf.get("/api/v1/system_admin/users/?grades=all")
    with pytest.raises(PermissionDenied, match="Operational domain query parameter 'grades' is prohibited"):
        perm.has_permission(req_grades, None)

    req_payroll = rf.get("/api/v1/system_admin/payroll/")
    with pytest.raises(PermissionDenied, match="Operational domain data access 'payroll' is prohibited"):
        perm.has_permission(req_payroll, None)

    req_safe = rf.get("/api/v1/system_admin/users/?department=CSE")
    assert perm.has_permission(req_safe, None) is True


# ==============================================================================
# 2. SERIALIZERS TESTS
# ==============================================================================


def test_basic_user_create_serializer_valid_student():
    payload = {
        "user_kind": "student",
        "name": "Jane Student",
        "institute_email": "jane@iiitdmj.ac.in",
        "institute_id": "2026BCS099",
        "contact_number": "9876543210",
        "department": "CSE",
        "programme": "B.Tech",
        "discipline": "Computer Science",
        "batch_year": 2026,
    }
    serializer = s.BasicUserCreateSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors


def test_basic_user_create_serializer_missing_student_batch_year_fails():
    payload = {
        "user_kind": "student",
        "name": "Jane Student",
        "institute_email": "jane@iiitdmj.ac.in",
        "institute_id": "2026BCS099",
        "programme": "B.Tech",
        "discipline": "CSE",
        # missing batch_year
    }
    serializer = s.BasicUserCreateSerializer(data=payload)
    assert not serializer.is_valid()
    assert any("batch" in str(err).lower() for err in serializer.errors.get("non_field_errors", []))


def test_basic_user_profile_update_serializer_prohibits_institute_id():
    payload = {
        "display_name": "Jane Doe Updated",
        "institute_id": "2026BCS999",  # Attempting to mutate immutable ID
    }
    serializer = s.BasicUserProfileUpdateSerializer(data=payload)
    assert not serializer.is_valid()
    assert "institute_id" in serializer.errors
    assert "immutable" in str(serializer.errors["institute_id"])


def test_bulk_status_update_serializer_caps_at_1000():
    payload = {
        "user_ids": list(range(1001)),
        "action": "deactivate",
        "reason": "Graduated batch",
    }
    serializer = s.BulkStatusUpdateSerializer(data=payload)
    assert not serializer.is_valid()
    assert "user_ids" in serializer.errors


def test_role_assignment_create_serializer_ordering_validation():
    payload = {
        "role_code": "dean_academic",
        "target_user_id": 5,
        "start_date": "2026-06-01",
        "end_date": "2026-05-01",  # End before start
        "reason": "Test role",
    }
    serializer = s.RoleAssignmentCreateSerializer(data=payload)
    assert not serializer.is_valid()
    assert "end_date" in serializer.errors


def test_role_reassignment_serializer_past_effective_date_rejected():
    past_date = datetime.date.today() - datetime.timedelta(days=1)
    payload = {
        "new_holder_id": 7,
        "effective_date": str(past_date),
        "reason": "Handover to new HOD",
    }
    serializer = s.RoleReassignmentSerializer(data=payload)
    assert not serializer.is_valid()
    assert "effective_date" in serializer.errors


# ==============================================================================
# 3. VIEWSET WORKFLOW & INTEGRATION TESTS
# ==============================================================================


@patch("modules.system_admin.services.user_lifecycle.create_basic_user")
def test_user_viewset_create(mock_create, rf, super_admin_principal):
    mock_user = MagicMock(spec=BasicUser)
    mock_user.id = 100
    mock_user.username = "jane"
    mock_user.institute_id = "2026BCS100"
    mock_user.email = "jane@iiitdmj.ac.in"
    mock_user.kind = "student"
    mock_user.is_active = True
    mock_user.status = "active"
    mock_user.deactivated_at = None
    mock_user.date_of_joining = None
    mock_user.expected_completion_date = None
    mock_user.created_at = datetime.datetime.now()
    mock_user.updated_at = datetime.datetime.now()
    mock_user.profile = None
    mock_create.return_value = mock_user

    payload = {
        "user_kind": "student",
        "name": "Jane Student",
        "institute_email": "jane@iiitdmj.ac.in",
        "institute_id": "2026BCS100",
        "programme": "B.Tech",
        "discipline": "CSE",
        "batch_year": 2026,
    }

    view = views.UserViewSet.as_view({"post": "create"})
    req = rf.post("/api/v1/system_admin/users/", data=payload, format="json")
    req.principal = super_admin_principal

    resp = view(req)
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["id"] == 100
    mock_create.assert_called_once()


@patch("modules.system_admin.selectors.users.get_user_by_id")
@patch("modules.system_admin.services.user_lifecycle.deactivate_user")
def test_user_viewset_deactivate(mock_deact, mock_get_user, rf, super_admin_principal):
    target_user = MagicMock(spec=BasicUser)
    target_user.id = 55
    mock_get_user.return_value = target_user

    updated_user = MagicMock(spec=BasicUser)
    updated_user.id = 55
    updated_user.username = "student55"
    updated_user.institute_id = "2026BCS055"
    updated_user.email = "student55@iiitdmj.ac.in"
    updated_user.kind = "student"
    updated_user.is_active = False
    updated_user.status = "deactivated"
    updated_user.deactivated_at = datetime.datetime.now()
    updated_user.date_of_joining = None
    updated_user.expected_completion_date = None
    updated_user.created_at = datetime.datetime.now()
    updated_user.updated_at = datetime.datetime.now()
    updated_user.profile = None
    mock_deact.return_value = updated_user

    view = views.UserViewSet.as_view({"post": "deactivate"})
    req = rf.post(
        "/api/v1/system_admin/users/55/deactivate/",
        data={"reason": "Disciplinary suspension"},
        format="json",
    )
    req.principal = super_admin_principal

    resp = view(req, pk="55")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == "deactivated"
    mock_deact.assert_called_once_with(
        user_id=55,
        reason="Disciplinary suspension",
        performed_by_id=1,
    )


@patch("modules.system_admin.services.archival.restore_archived_user")
def test_archival_viewset_restore_expired_window_returns_409(mock_restore, rf, super_admin_principal):
    mock_restore.side_effect = ReversibilityExpiredError(expired_at="2026-01-01T00:00:00Z")

    view = views.ArchivalViewSet.as_view({"post": "restore_user"})
    req = rf.post(
        "/api/v1/system_admin/archival/33/restore_user/",
        data={"reason": "Re-admission", "confirm_password": "ValidPassword123!"},
        format="json",
        HTTP_X_CONFIRM_PASSWORD="ValidPassword123!",
    )
    req.principal = super_admin_principal

    with patch("modules.system_admin.services.security.verify_critical_action_reauth", return_value=True):
        resp = view(req, pk="33")

    assert resp.status_code == status.HTTP_409_CONFLICT
    assert resp.data["error"]["code"] == "reversibility_expired"


@patch("modules.system_admin.services.purge.authorize_permanent_purge")
def test_purge_request_viewset_authorize_by_it_head(mock_auth, rf, it_head_principal):
    mock_req = MagicMock()
    mock_req.id = 8
    mock_req.archive_id = 12
    mock_req.status = "purged"
    mock_req.requested_by = 1
    mock_req.requested_at = datetime.datetime.now()
    mock_req.request_reason = "Retention expired 5 years"
    mock_req.it_head_id = 2
    mock_req.it_head_decision_at = datetime.datetime.now()
    mock_req.it_head_comments = "Approved permanent purge"
    mock_req.purged_at = datetime.datetime.now()
    mock_auth.return_value = mock_req

    view = views.PurgeRequestViewSet.as_view({"post": "authorize"})
    req = rf.post(
        "/api/v1/system_admin/purge/8/authorize/",
        data={"approved": True, "comments": "Approved permanent purge"},
        format="json",
        HTTP_X_CONFIRM_PASSWORD="ValidITHeadPassword123!",
    )
    req.principal = it_head_principal

    with patch("modules.system_admin.services.security.verify_critical_action_reauth", return_value=True):
        resp = view(req, pk="8")

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == "purged"
    mock_auth.assert_called_once_with(
        request_id=8,
        it_head_id=2,
        approved=True,
        comments="Approved permanent purge",
    )


@patch("modules.system_admin.selectors.dashboard.get_super_admin_dashboard_metrics")
def test_dashboard_view(mock_metrics, rf, super_admin_principal):
    mock_metrics.return_value = {
        "users": {"total": 500, "active": 480, "deactivated": 20},
        "roles": {"total_definitions": 25, "active_assignments": 45},
        "archival": {"archived_users": 15, "historical_archives": 3},
        "security": {"active_sessions": 2, "failed_logins_24h": 0},
        "timestamp": datetime.datetime.now().isoformat(),
    }

    view = views.DashboardView.as_view()
    req = rf.get("/api/v1/system_admin/dashboard/metrics/")
    req.principal = super_admin_principal

    resp = view(req)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["users"]["total"] == 500
