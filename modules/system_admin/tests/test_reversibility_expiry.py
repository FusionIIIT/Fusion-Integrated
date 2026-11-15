"""Verification tests for BR-SA-005 and ISS-SA-004: Archival Reversibility Expiry.

Traceability: CFR-SA-012, AFR-SA-051A, AFR-SA-051B, BR-SA-005, ISS-SA-004, UC-SA-012, CW-SA-03.
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch
import pytest

from django.utils import timezone

from modules.system_admin.constants import (
    UserArchivalStatus,
    UserLifecycleStatus,
)
from modules.system_admin.domain.exceptions import ReversibilityExpiredError
from modules.system_admin.models import BasicUser
from modules.system_admin.services import archival as archival_service


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.BasicUser.objects")
@patch("modules.system_admin.models.ArchivedUserRecord.objects")
@patch("modules.system_admin.models.SuperAdminAuditLog.objects")
@patch("modules.system_admin.models.UserStatusHistory.objects")
def test_archived_user_restoration_within_window_succeeds(
    mock_status_hist, mock_audit, mock_archives, mock_users, mock_atomic
):
    """Within reversible window: restores user to ACTIVE and marks record RESTORED."""
    now = timezone.now()

    mock_record = MagicMock()
    mock_record.basic_user_id = 15
    mock_record.status = UserArchivalStatus.REVERSIBLE
    mock_record.reversible_until = now + datetime.timedelta(days=15)
    mock_archives.get.return_value = mock_record

    mock_user = BasicUser(
        id=15,
        username="u15",
        institute_id="2026BCS015",
        email="u15@iiitdmj.ac.in",
        kind="student",
        is_active=False,
        status=UserLifecycleStatus.DEACTIVATED,
    )
    mock_users.get.return_value = mock_user

    with patch.object(mock_user, "save") as mock_save:
        restored = archival_service.restore_archived_user(
            user_id=15,
            reason="Academic re-enrollment",
            performed_by_id=1,
        )

    assert restored.status == UserLifecycleStatus.ACTIVE
    assert restored.is_active is True
    assert mock_record.status == UserArchivalStatus.RESTORED


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.BasicUser.objects")
@patch("modules.system_admin.models.ArchivedUserRecord.objects")
def test_archived_user_restoration_past_window_permanently_rejected(
    mock_archives, mock_users, mock_atomic
):
    """ISS-SA-004 / BR-SA-005: Past reversible window, restoration MUST fail with ReversibilityExpiredError."""
    now = timezone.now()

    mock_record = MagicMock()
    mock_record.basic_user_id = 15
    mock_record.status = UserArchivalStatus.REVERSIBLE
    mock_record.reversible_until = now - datetime.timedelta(days=1)  # Expired yesterday!
    mock_archives.get.return_value = mock_record

    mock_user = MagicMock(spec=BasicUser)
    mock_user.id = 15
    mock_users.get.return_value = mock_user

    with pytest.raises(ReversibilityExpiredError, match="permanently non-restorable"):
        archival_service.restore_archived_user(
            user_id=15,
            reason="Late restore attempt",
            performed_by_id=1,
        )


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.ArchivedUserRecord.objects")
@patch("modules.system_admin.models.SuperAdminAuditLog.objects")
def test_finalize_expired_reversible_users_sweep(mock_audit, mock_archives, mock_atomic):
    """Sweep task transitions expired reversible records to PERMANENT_NON_RESTORABLE."""
    rec1 = MagicMock()
    rec1.basic_user_id = 21
    rec1.status = UserArchivalStatus.REVERSIBLE

    rec2 = MagicMock()
    rec2.basic_user_id = 22
    rec2.status = UserArchivalStatus.REVERSIBLE

    mock_archives.filter.return_value = [rec1, rec2]

    finalized_count = archival_service.finalize_expired_reversible_users()
    assert finalized_count == 2
    assert rec1.status == UserArchivalStatus.PERMANENT_NON_RESTORABLE
    assert rec2.status == UserArchivalStatus.PERMANENT_NON_RESTORABLE
