"""Unit and service verification for bulk user operations.

Traceability: CFR-SA-004, AFR-SA-015..020, BR-SA-030, UC-SA-002, UC-SA-003.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from modules.system_admin.domain.exceptions import BulkLimitExceededError
from modules.system_admin.models import BasicUser, UserProfile
from modules.system_admin.services import user_lifecycle


def test_bulk_user_creation_enforces_1000_limit():
    """BR-SA-030: Bulk operations strictly capped at 1000 records."""
    header = "user_kind,name,institute_email,institute_id,contact_number,department,programme,discipline,batch_year,employee_id"
    rows = [
        f"student,Student {i},stu{i}@iiitdmj.ac.in,ID{i},9999999999,,B.Tech,CSE,2026,"
        for i in range(1001)
    ]
    csv_content = header + "\n" + "\n".join(rows)

    with pytest.raises(BulkLimitExceededError, match="exceeds the limit of 1000"):
        user_lifecycle.execute_bulk_user_creation(csv_content, performed_by_id=1)


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.BasicUser.objects")
@patch("modules.system_admin.models.UserProfile.objects")
@patch("modules.system_admin.models.SuperAdminAuditLog.objects")
@patch("modules.system_admin.models.UserStatusHistory.objects")
@patch("modules.system_admin.models.NotificationOutbox.objects")
def test_bulk_user_creation_reports_line_errors(
    mock_notif, mock_status_hist, mock_audit, mock_profiles, mock_users, mock_atomic
):
    """Validates line-by-line reporting of valid and malformed rows."""
    mock_users.filter.return_value.exists.return_value = False

    def fake_create(**kwargs):
        u = BasicUser(
            id=99,
            username=kwargs.get("username", "test"),
            institute_id=kwargs.get("institute_id", "2026BCS099"),
            email=kwargs.get("email", "test@iiitdmj.ac.in"),
            kind="student",
        )
        return u

    mock_users.create.side_effect = fake_create

    csv_content = (
        "user_kind,name,institute_email,institute_id,contact_number,department,programme,discipline,batch_year,employee_id\n"
        "student,Valid Student,valid@iiitdmj.ac.in,2026BCS099,9999999999,,B.Tech,CSE,2026,\n"
        "student,Bad Email,invalid-email@gmail.com,2026BCS100,9999999999,,B.Tech,CSE,2026,\n"
    )

    report = user_lifecycle.execute_bulk_user_creation(csv_content, performed_by_id=1)
    assert report["total"] == 2
    assert report["processed"] == 1
    assert report["failed"] == 1
    assert len(report["error_details"]) == 1
    assert report["error_details"][0]["line"] == 3
    assert "@iiitdmj.ac.in" in str(report["error_details"][0]["errors"])


def test_bulk_status_update_enforces_1000_limit():
    """BR-SA-030: Bulk status update capped at 1000 IDs."""
    ids = list(range(1001))
    with pytest.raises(BulkLimitExceededError, match="exceeds the limit of 1000"):
        user_lifecycle.execute_bulk_status_update(
            user_ids=ids,
            action="deactivate",
            reason="Graduation",
            performed_by_id=1,
        )


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.BasicUser.objects")
@patch("modules.system_admin.models.RoleAssignment.objects")
@patch("modules.system_admin.models.UserStatusHistory.objects")
@patch("modules.system_admin.models.SuperAdminAuditLog.objects")
@patch("modules.system_admin.models.NotificationOutbox.objects")
def test_bulk_status_update_deactivation_success(
    mock_notif, mock_audit, mock_hist, mock_assign, mock_users, mock_atomic
):
    u1 = BasicUser(id=1, status="active", is_active=True, username="u1")
    u2 = BasicUser(id=2, status="active", is_active=True, username="u2")

    mock_users.get.side_effect = lambda id: u1 if id == 1 else u2
    mock_assign.filter.return_value = []

    with patch.object(u1, "save"), patch.object(u2, "save"):
        report = user_lifecycle.execute_bulk_status_update(
            user_ids=[1, 2],
            action="deactivate",
            reason="Academic suspension",
            performed_by_id=1,
        )

    assert report["total"] == 2
    assert report["succeeded"] == 2
    assert report["failed"] == 0
    assert u1.status == "deactivated"
    assert u1.is_active is False
    assert u2.status == "deactivated"
    assert u2.is_active is False
