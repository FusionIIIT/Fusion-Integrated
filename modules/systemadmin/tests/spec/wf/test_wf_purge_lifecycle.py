"""WF Test Suite 1: Permanent Data Purge Lifecycle (BW-SA-01, BW-SA-02, CW-SA-01)."""

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.systemadmin.models import ArchivedHistoricalData
from modules.systemadmin.services.archival_service import ArchivalService

ALL_PERMISSIONS = (
    "systemadmin.dashboard.view",
    "systemadmin.user.view",
    "systemadmin.user.create",
    "systemadmin.user.edit",
    "systemadmin.user.status",
    "systemadmin.user.bulk",
    "systemadmin.role.view",
    "systemadmin.role.assign",
    "systemadmin.role.reassign",
    "systemadmin.role.revoke",
    "systemadmin.role.extend",
    "systemadmin.archive.view",
    "systemadmin.archive.execute",
    "systemadmin.archive.restore",
    "systemadmin.purge.request",
    "systemadmin.purge.authorize",
    "systemadmin.audit.view",
    "systemadmin.audit.report",
    "systemadmin.config.manage",
)


def get_sa_client(stub_iam, permissions=ALL_PERMISSIONS):
    session = make_session(
        user_id=1,
        kind="staff",
        modules=("systemadmin",),
        permissions=permissions,
        roles=("Super Admin",),
        active_role="Super Admin",
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token token-sa-1")
    return client


pytestmark = pytest.mark.django_db

# --- BW-SA-01: Permanent Data Purge — Approved Path ---


def test_wf_001_purge_approved_basis_path(stub_iam):
    """TEST_WF_001 | BW-SA-01: Verify complete approved purge basis path: retention expired -> request -> IT Head approves -> permanently purged."""
    rec = ArchivalService.archive_historical_data(
        category="purge_wf_appr",
        date_range_start=date(2000, 1, 1),
        date_range_end=date(2000, 12, 31),
    )
    rec.retention_expiry_date = date.today() - timedelta(days=1)
    rec.save()

    req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Statutory period over",
        regulatory_authorization_ref="REG-AUTH-WF-001",
    )
    assert req.status == "pending_it_head"

    authorized = ArchivalService.authorize_permanent_purge(
        request_id=req.id,
        decision="approve",
        comments="Approved by IT Head",
    )
    assert authorized.status in ["approved", "completed"]
    # BW-SA-01: Approved permanent purge permanently deletes data from database
    assert not ArchivedHistoricalData.objects.filter(id=rec.id).exists()


# --- BW-SA-02: Permanent Data Purge — Rejected Path ---


def test_wf_002_purge_rejected_basis_path(stub_iam):
    """TEST_WF_002 | BW-SA-02: Verify complete rejected purge basis path: retention expired -> request -> IT Head rejects -> data remains archived."""
    rec = ArchivalService.archive_historical_data(
        category="purge_wf_rej",
        date_range_start=date(2001, 1, 1),
        date_range_end=date(2001, 12, 31),
    )
    rec.retention_expiry_date = date.today() - timedelta(days=1)
    rec.save()

    req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Testing purge rejection",
        regulatory_authorization_ref="REG-AUTH-WF-002",
    )
    assert req.status == "pending_it_head"

    authorized = ArchivalService.authorize_permanent_purge(
        request_id=req.id,
        decision="reject",
        comments="Rejected due to pending audit hold",
    )
    assert authorized.status == "rejected"
    assert ArchivedHistoricalData.objects.filter(id=rec.id).exists()


# --- CW-SA-01: Permanent Data Purge Authorization Lifecycle ---


def test_wf_003_composite_purge_lifecycle_approve_branch(stub_iam):
    """TEST_WF_003 | CW-SA-01: Verify composite purge lifecycle decision branch 2A (Approve path traversal)."""
    rec = ArchivalService.archive_historical_data(
        category="cw_purge_appr",
        date_range_start=date(2002, 1, 1),
        date_range_end=date(2002, 12, 31),
    )
    rec.retention_expiry_date = date.today() - timedelta(days=1)
    rec.save()

    req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Composite test approve",
        regulatory_authorization_ref="REG-AUTH-CW-001",
    )
    authorized = ArchivalService.authorize_permanent_purge(
        request_id=req.id,
        decision="approve",
        comments="Approved in composite flow",
    )
    assert authorized.status in ["approved", "completed"]


def test_wf_004_composite_purge_lifecycle_reject_branch(stub_iam):
    """TEST_WF_004 | CW-SA-01: Verify composite purge lifecycle decision branch 2B (Reject path traversal)."""
    rec = ArchivalService.archive_historical_data(
        category="cw_purge_rej",
        date_range_start=date(2003, 1, 1),
        date_range_end=date(2003, 12, 31),
    )
    rec.retention_expiry_date = date.today() - timedelta(days=1)
    rec.save()

    req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=rec.id,
        reason="Composite test reject",
        regulatory_authorization_ref="REG-AUTH-CW-002",
    )
    authorized = ArchivalService.authorize_permanent_purge(
        request_id=req.id,
        decision="reject",
        comments="Rejected in composite flow",
    )
    assert authorized.status == "rejected"
    assert ArchivedHistoricalData.objects.filter(id=rec.id).exists()
