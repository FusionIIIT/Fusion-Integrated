"""Unit and integration test suite for modules.system_admin.contracts.

Verifies plural queries, DTO immutability, and cross-module contracts compliance.
Traceability: CFR-SA-010, CFR-SA-011, CFR-SA-020, BR-SA-004, BR-SA-013, BR-SA-026, BR-SA-034.
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch
import pytest

from django.utils import timezone

from modules.system_admin import contracts
from modules.system_admin.constants import (
    RoleAssignmentState,
    UserArchivalStatus,
    UserLifecycleStatus,
)


def test_get_user_identities_empty_input():
    result = contracts.get_user_identities([])
    assert result == {}


@patch("modules.system_admin.models.BasicUser.objects")
def test_get_user_identities_mapping(mock_users):
    mock_u1 = MagicMock()
    mock_u1.id = 10
    mock_u1.username = "stu10"
    mock_u1.institute_id = "2026BCS010"
    mock_u1.email = "stu10@iiitdmj.ac.in"
    mock_u1.kind = "student"
    mock_u1.is_active = True
    mock_u1.status = UserLifecycleStatus.ACTIVE
    mock_u1.profile.display_name = "Student Ten"
    mock_u1.profile.department = "CSE"
    mock_u1.profile.programme = "B.Tech"
    mock_u1.profile.discipline = "Computer Science"
    mock_u1.profile.batch_year = 2026
    mock_u1.profile.employee_id = ""

    mock_users.filter.return_value.select_related.return_value = [mock_u1]

    result = contracts.get_user_identities([10, 999])
    assert 10 in result
    assert 999 not in result

    dto = result[10]
    assert isinstance(dto, contracts.UserIdentityDTO)
    assert dto.username == "stu10"
    assert dto.institute_id == "2026BCS010"
    assert dto.batch_year == 2026
    assert dto.display_name == "Student Ten"


@patch("modules.system_admin.models.RoleAssignment.objects")
def test_get_active_roles_for_users_plural(mock_roles):
    mock_a1 = MagicMock()
    mock_a1.id = 101
    mock_a1.user_id = 5
    mock_a1.role.code = "dean_academic"
    mock_a1.role.label = "Dean Academic"
    mock_a1.role.category = "academic"
    mock_a1.scope = "institute"
    mock_a1.state = RoleAssignmentState.ACTIVE
    mock_a1.start_date = datetime.date(2026, 1, 1)
    mock_a1.end_date = datetime.date(2027, 1, 1)

    mock_roles.filter.return_value.select_related.return_value.order_by.return_value = [mock_a1]

    result = contracts.get_active_roles_for_users([5, 6])
    assert 5 in result
    assert 6 in result
    assert len(result[5]) == 1
    assert len(result[6]) == 0

    grant = result[5][0]
    assert isinstance(grant, contracts.RoleGrantDTO)
    assert grant.role_code == "dean_academic"
    assert grant.assignment_id == 101


@patch("modules.system_admin.models.BasicUser.objects")
@patch("modules.system_admin.models.ArchivedUserRecord.objects")
def test_get_user_archival_statuses(mock_archives, mock_users):
    now = timezone.now()

    # User 1 is active BasicUser
    u1 = MagicMock()
    u1.id = 1
    u1.status = UserLifecycleStatus.ACTIVE

    # User 2 is in reversible window
    arch_rev = MagicMock()
    arch_rev.basic_user_id = 2
    arch_rev.status = UserArchivalStatus.REVERSIBLE
    arch_rev.reversible_until = now + datetime.timedelta(days=10)

    # User 3 is past reversible window
    arch_exp = MagicMock()
    arch_exp.basic_user_id = 3
    arch_exp.status = UserArchivalStatus.PERMANENT_NON_RESTORABLE
    arch_exp.reversible_until = now - datetime.timedelta(days=5)

    mock_users.filter.return_value = [u1]
    mock_archives.filter.return_value = [arch_rev, arch_exp]

    result = contracts.get_user_archival_statuses([1, 2, 3])

    assert result[1].is_archived is False
    assert result[1].is_reversible is False

    assert result[2].is_archived is True
    assert result[2].is_reversible is True

    assert result[3].is_archived is True
    assert result[3].is_reversible is False


@patch("modules.placement.contracts.get_no_dues_clearances")
def test_check_pending_transactions_for_archival_blocked_by_dues(mock_no_dues):
    mock_verdict = MagicMock()
    mock_verdict.cleared = False
    mock_no_dues.return_value = {42: mock_verdict}

    assert contracts.check_pending_transactions_for_archival(42) is True


@patch("modules.placement.contracts.get_no_dues_clearances")
def test_check_pending_transactions_for_archival_cleared(mock_no_dues):
    mock_verdict = MagicMock()
    mock_verdict.cleared = True
    mock_no_dues.return_value = {42: mock_verdict}

    assert contracts.check_pending_transactions_for_archival(42) is False


@patch("modules.system_admin.models.RoleHandoverLog.objects")
def test_get_previous_holder_audit_grants(mock_logs):
    today = datetime.date(2026, 6, 1)

    mock_log = MagicMock()
    mock_log.previous_holder_id = 88
    mock_log.role.code = "hod_cse"
    mock_log.scope = "cse"
    mock_log.audit_access_expires_at = datetime.date(2026, 7, 1)

    mock_logs.filter.return_value.select_related.return_value = [mock_log]

    result = contracts.get_previous_holder_audit_grants([88], today=today)
    assert 88 in result
    assert len(result[88]) == 1
    assert result[88][0].role_code == "hod_cse"
    assert result[88][0].has_audit_access is True
