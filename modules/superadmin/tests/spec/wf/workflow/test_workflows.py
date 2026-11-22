from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from modules.superadmin.models.archival import ArchivedUserRecord, HistoricalDataArchive

pytestmark = pytest.mark.django_db


def _eligible_archive(sa_principal):
    today = date.today()
    return HistoricalDataArchive.objects.create(
        dataset_category="examination",
        title="Workflow retention archive",
        date_range_start=today - timedelta(days=800),
        date_range_end=today - timedelta(days=400),
        record_count=5,
        backup_file_path="/archive/workflow.tar",
        backup_checksum="sha256-workflow",
        retention_expires_at=today - timedelta(days=1),
        archived_by=sa_principal.user_id,
    )


def test_wf_01_approved_permanent_purge(sa_principal, it_principal):
    """WF-01; source_id: BW-SA-01 / STT rows 1-2."""
    from modules.superadmin.services.purge import (
        create_purge_request,
        decide_purge_request,
        execute_purge,
    )

    archive = _eligible_archive(sa_principal)
    request = create_purge_request(
        sa_principal, archive_id=archive.pk, request_reason="Retention period elapsed."
    )
    assert request.status == "pending_it_head"
    request = decide_purge_request(
        it_principal, request_id=request.pk, approve=True, comments="Approved."
    )
    assert request.status == "approved"
    request = execute_purge(sa_principal, request_id=request.pk)
    archive.refresh_from_db()
    assert request.status == "purged"
    assert archive.is_purged is True


def test_wf_02_rejected_permanent_purge(sa_principal, it_principal):
    """WF-02; source_id: BW-SA-02 / STT row 2."""
    from modules.superadmin.services.purge import create_purge_request, decide_purge_request

    archive = _eligible_archive(sa_principal)
    request = create_purge_request(
        sa_principal, archive_id=archive.pk, request_reason="Retention period elapsed."
    )
    assert request.status == "pending_it_head"
    request = decide_purge_request(it_principal, request_id=request.pk, approve=False)
    archive.refresh_from_db()
    assert request.status == "rejected"
    assert archive.is_purged is False


@pytest.mark.skip(reason="NOT_AUTOMATED: no role-assignment lifecycle interface exists in this checkout.")
def test_wf_03_immediate_role_activation_and_expiry():
    """WF-03; source_id: BW-SA-03 / STT rows 1-2."""


@pytest.mark.skip(reason="NOT_AUTOMATED: no role-assignment lifecycle interface exists in this checkout.")
def test_wf_04_scheduled_role_activation_and_expiry():
    """WF-04; source_id: BW-SA-04 / STT rows 1-3."""


@pytest.mark.skip(reason="NOT_AUTOMATED: no role-assignment lifecycle interface exists in this checkout.")
def test_wf_05_time_bound_role_extension_and_expiry():
    """WF-05; source_id: BW-SA-05 / STT rows 1-2."""


@pytest.mark.skip(reason="NOT_AUTOMATED: no account reactivation service or endpoint exists in this checkout.")
def test_wf_06_reactivate_deactivated_user():
    """WF-06; source_id: BW-SA-06 / STT row 1."""


def test_wf_07_archive_and_restore_user(sa_principal):
    """WF-07; source_id: BW-SA-07 / STT rows 1-2."""
    from modules.superadmin.services.archival import archive_user, restore_archived_user

    record = archive_user(
        sa_principal,
        user_id=71007,
        institute_id="2021BCS007",
        username="wf007",
        email="wf007@iiitdmj.ac.in",
        user_kind="student",
        is_deactivated=True,
        deactivated_at=timezone.now() - timedelta(days=45),
        has_pending_transactions=False,
        archival_reason="Graduated.",
    )
    assert record.status == "reversible"
    record = restore_archived_user(
        sa_principal, user_id=record.user_id, restoration_reason="Eligible restoration."
    )
    assert record.status == "restored"


def test_wf_08_expire_archival_and_reject_restore(sa_principal):
    """WF-08; source_id: BW-SA-08 / STT rows 1-2; Problem Statement §5, ISS-SA-004."""
    from core.api.exceptions import ConflictError
    from modules.superadmin.services.archival import (
        expire_reversibility_sweep,
        restore_archived_user,
    )

    record = ArchivedUserRecord.objects.create(
        user_id=71008,
        institute_id="2021BCS008",
        username="wf008",
        email="wf008@iiitdmj.ac.in",
        user_kind="student",
        status="reversible",
        archived_at=timezone.now() - timedelta(days=40),
        reversible_until=timezone.now() - timedelta(days=1),
        authorized_by=sa_principal.user_id,
        archival_reason="Archival eligible user.",
    )
    assert expire_reversibility_sweep() == 1
    record.refresh_from_db()
    assert record.status == "finalized_permanent"
    with pytest.raises(ConflictError):
        restore_archived_user(
            sa_principal, user_id=record.user_id, restoration_reason="Late restoration."
        )
    record.refresh_from_db()
    assert record.status == "finalized_permanent"
    assert record.restored_at is None


def test_wf_09_archive_and_restore_historical_data(sa_principal):
    """WF-09; source_id: BW-SA-09 / STT rows 1-2."""
    from modules.superadmin.services.historical_archive import (
        create_historical_archive,
        restore_historical_archive,
    )

    today = date.today()
    archive = create_historical_archive(
        sa_principal,
        dataset_category="examination",
        title="WF-09 historical data",
        date_range_start=today - timedelta(days=400),
        date_range_end=today - timedelta(days=300),
        record_count=12,
        backup_file_path="/archive/wf-09.tar",
        backup_checksum="sha256-wf-09",
        retention_expires_at=today + timedelta(days=365),
    )
    assert archive.pk is not None
    assert archive.is_restored is False
    archive = restore_historical_archive(sa_principal, archive_id=archive.pk)
    assert archive.is_restored is True
    assert archive.restored_at is not None
