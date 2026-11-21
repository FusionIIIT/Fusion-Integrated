"""Verification tests for BR-SA-012 and BR-SA-013: Role Handover and Previous Holder Audit Access.

Traceability: CFR-SA-007, AFR-SA-032..037, BR-SA-012, BR-SA-013, UC-SA-009, CW-SA-02.
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch
import pytest

from modules.system_admin.constants import RoleAssignmentState
from modules.system_admin.domain.dataclasses import RoleReassignmentSpec
from modules.system_admin.services import role_management as role_service


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.BasicUser.objects")
@patch("modules.system_admin.models.RoleAssignment.objects")
@patch("modules.system_admin.models.RoleHandoverLog.objects")
@patch("modules.system_admin.models.RoleAssignmentHistory.objects")
@patch("modules.system_admin.models.SuperAdminAuditLog.objects")
@patch("modules.system_admin.models.NotificationOutbox.objects")
def test_role_reassignment_transfers_work_and_grants_audit_access(
    mock_notif, mock_audit, mock_hist, mock_handover, mock_assign, mock_users, mock_atomic
):
    """BR-SA-012 / BR-SA-013: Reassigning a role revokes previous grant, creates new grant, and sets handover log."""
    mock_prev_user = MagicMock()
    mock_prev_user.id = 11
    mock_prev_user.email = "prev@iiitdmj.ac.in"
    mock_new_user = MagicMock()
    mock_new_user.id = 12
    mock_new_user.email = "new@iiitdmj.ac.in"
    mock_users.get.side_effect = lambda id: mock_prev_user if id == 11 else mock_new_user

    mock_curr = MagicMock()
    mock_curr.id = 50
    mock_curr.user_id = 11
    mock_curr.state = RoleAssignmentState.ACTIVE
    mock_curr.role.code = "dean_academic"
    mock_curr.role.label = "Dean Academic"
    mock_curr.role.get_allowed_kinds_set.return_value = {"faculty"}
    mock_curr.scope = "institute"

    mock_assign.select_related.return_value.get.return_value = mock_curr

    mock_new_assign = MagicMock()
    mock_new_assign.id = 51
    mock_new_assign.user_id = 12
    mock_new_assign.state = RoleAssignmentState.ACTIVE
    mock_assign.create.return_value = mock_new_assign

    today = datetime.date.today()
    spec = RoleReassignmentSpec(
        role_assignment_id=50,
        role_code="dean_academic",
        previous_holder_id=11,
        new_holder_id=12,
        new_holder_kind="faculty",
        effective_date=today,
        handover_tasks=True,
        audit_access_days=90,
        reason="Annual rotation",
    )

    result = role_service.reassign_role(spec=spec, performed_by_id=1)

    # Current assignment is revoked
    assert mock_curr.state == RoleAssignmentState.REVOKED
    mock_curr.save.assert_called_once()

    # Handover log created with 90 days audit access
    mock_handover.create.assert_called_once()
    call_kwargs = mock_handover.create.call_args[1]
    assert call_kwargs["previous_holder_id"] == 11
    assert call_kwargs["new_holder_id"] == 12
    assert call_kwargs["audit_access_expires_at"] == today + datetime.timedelta(days=90)
