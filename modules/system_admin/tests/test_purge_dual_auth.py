"""Verification tests for BR-SA-021, BR-SA-022, and CW-SA-01: Permanent Purge Dual-Authorization.

Traceability: CFR-SA-016, AFR-SA-061A, AFR-SA-061B, BR-SA-021, BR-SA-022, CW-SA-01, BW-SA-01, BW-SA-02.
"""
from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch
import pytest

from modules.system_admin.constants import PurgeRequestStatus
from modules.system_admin.domain.exceptions import DomainError, PurgeDualAuthRequiredError
from modules.system_admin.services import purge as purge_service


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.HistoricalDataArchive.objects")
@patch("modules.system_admin.models.PurgeRequest.objects")
@patch("modules.system_admin.models.SuperAdminAuditLog.objects")
@patch("modules.system_admin.models.NotificationOutbox.objects")
def test_permanent_purge_dual_auth_approved_workflow(
    mock_notif, mock_audit, mock_purge, mock_arch, mock_atomic
):
    """BW-SA-01 / CW-SA-01: Approved permanent purge by distinct IT Head."""
    mock_archive = MagicMock()
    mock_archive.id = 5
    mock_archive.is_purged = False
    mock_archive.retention_expires_at = datetime.date.today() - datetime.timedelta(days=1)
    mock_arch.get.return_value = mock_archive

    created_req = MagicMock()
    created_req.id = 100
    created_req.status = PurgeRequestStatus.PENDING_IT_HEAD
    created_req.requested_by = 1
    created_req.archive = mock_archive
    mock_purge.create.return_value = created_req

    req = purge_service.request_permanent_purge(
        archive_id=5,
        reason="Statutory 10-year retention expired",
        super_admin_id=1,
    )
    assert req.status == PurgeRequestStatus.PENDING_IT_HEAD

    mock_purge.select_related.return_value.get.return_value = created_req

    authorized_req = purge_service.authorize_permanent_purge(
        request_id=100,
        it_head_id=2,  # Distinct actor (BR-SA-022)
        approved=True,
        comments="Approved for disposal",
    )
    assert authorized_req.status == PurgeRequestStatus.PURGED
    assert mock_archive.is_purged is True


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.PurgeRequest.objects")
def test_permanent_purge_dual_auth_prevent_self_authorization(mock_purge, mock_atomic):
    """BR-SA-022: Requester cannot self-authorize their own purge request."""
    req = MagicMock()
    req.id = 100
    req.status = PurgeRequestStatus.PENDING_IT_HEAD
    req.requested_by = 42  # Initiated by user 42
    mock_purge.select_related.return_value.get.return_value = req

    with pytest.raises(PurgeDualAuthRequiredError, match="Distinct IT Head authorization required"):
        purge_service.authorize_permanent_purge(
            request_id=100,
            it_head_id=42,  # Same user!
            approved=True,
            comments="Self approval attempt",
        )


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.HistoricalDataArchive.objects")
def test_permanent_purge_request_before_retention_expiry_fails(mock_arch, mock_atomic):
    """BR-SA-021: Purge request cannot be initiated before retention period elapses."""
    mock_archive = MagicMock()
    mock_archive.id = 7
    mock_archive.is_purged = False
    mock_archive.retention_expires_at = datetime.date.today() + datetime.timedelta(days=300)
    mock_arch.get.return_value = mock_archive

    with pytest.raises(DomainError, match="Retention period has not yet elapsed"):
        purge_service.request_permanent_purge(
            archive_id=7,
            reason="Premature purge attempt",
            super_admin_id=1,
        )


@patch("django.db.transaction.atomic")
@patch("modules.system_admin.models.HistoricalDataArchive.objects")
@patch("modules.system_admin.models.PurgeRequest.objects")
@patch("modules.system_admin.models.SuperAdminAuditLog.objects")
@patch("modules.system_admin.models.NotificationOutbox.objects")
def test_permanent_purge_rejected_by_it_head_leaves_data_retained(
    mock_notif, mock_audit, mock_purge, mock_arch, mock_atomic
):
    """BW-SA-02: IT Head rejection keeps data retained and marks request REJECTED."""
    mock_archive = MagicMock()
    mock_archive.id = 8
    mock_archive.is_purged = False

    req = MagicMock()
    req.id = 102
    req.status = PurgeRequestStatus.PENDING_IT_HEAD
    req.requested_by = 1
    req.archive = mock_archive
    mock_purge.select_related.return_value.get.return_value = req

    rejected_req = purge_service.authorize_permanent_purge(
        request_id=102,
        it_head_id=2,
        approved=False,
        comments="Hold data for statutory audit",
    )
    assert rejected_req.status == PurgeRequestStatus.REJECTED
    assert mock_archive.is_purged is False
