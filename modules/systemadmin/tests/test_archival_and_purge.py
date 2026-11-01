"""Tests for User Archival, Historical Data Archival, and Dual-Authorization Purge."""
import pytest
from datetime import date, timedelta
from django.utils import timezone

from modules.systemadmin.models.user_mgmt import BasicUserProfile
from modules.systemadmin.models.archival import (
    ArchivedUser,
    ArchivedHistoricalData,
    PermanentPurgeRequest,
)
from modules.systemadmin.models.audit import SystemAdminAuditLog
from modules.systemadmin.services.user_service import UserService
from modules.systemadmin.services.archival_service import ArchivalService, ArchivalError

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_user():
    user = UserService.create_basic_user(
        institute_id="ARCH_U1",
        user_type="student",
        full_name="Graduated Student",
        institute_email="graduated@iiitdmj.ac.in",
        date_of_joining=date(2020, 8, 1),
        department="Computer Science and Engineering",
        programme="B.Tech",
        batch_year=2020,
    )
    return user


def test_reject_archive_active_user(test_user):
    """Verify active user cannot be archived directly (BR-SA-004)."""
    with pytest.raises(ArchivalError) as exc_info:
        ArchivalService.archive_user(
            user_id=test_user.id,
            reason="Graduated",
            actor_username="superadmin",
        )
    assert "Only deactivated users are eligible for archival" in str(exc_info.value)


def test_archive_deactivated_user_and_snapshot(test_user):
    """Verify deactivated user archival snapshots profile and sets reversibility window (CFR-SA-011, BR-SA-004)."""
    UserService.deactivate_user(
        user_id=test_user.id,
        reason="Degree conferred; account closed",
        actor_username="superadmin",
    )

    archived = ArchivalService.archive_user(
        user_id=test_user.id,
        reason="Routine graduation archival",
        retention_option="standard_institutional",
        actor_username="superadmin",
        bypass_interval=True,
    )

    test_user.refresh_from_db()
    assert test_user.status == "archived"
    assert archived.status == "reversible"
    assert archived.reversibility_deadline > timezone.now()
    assert archived.retained_profile_snapshot["institute_id"] == "ARCH_U1"


def test_restore_archived_user_within_reversibility_window(test_user):
    """Verify restoration of archived user within deadline succeeds (CFR-SA-012, BW-SA-08)."""
    UserService.deactivate_user(user_id=test_user.id, reason="Graduated", actor_username="superadmin")
    archived = ArchivalService.archive_user(
        user_id=test_user.id, reason="Archived", actor_username="superadmin", bypass_interval=True
    )

    restored_user = ArchivalService.restore_archived_user(
        user_id=test_user.id,
        restoration_authorization_ref="DIR/RESTORE/2026/01",
        actor_username="superadmin",
    )

    restored_user.refresh_from_db()
    archived.refresh_from_db()
    assert restored_user.status == "active"
    assert archived.status == "restored"
    assert archived.restoration_authorization_ref == "DIR/RESTORE/2026/01"


def test_reject_restore_after_reversibility_window_elapsed(test_user):
    """Verify expired reversibility deadline transitions to permanent_non_restorable and blocks restore (BR-SA-005, ISS-SA-004)."""
    UserService.deactivate_user(user_id=test_user.id, reason="Graduated", actor_username="superadmin")
    archived = ArchivalService.archive_user(
        user_id=test_user.id, reason="Archived", actor_username="superadmin", bypass_interval=True
    )

    # Manually backdate deadline to past
    archived.reversibility_deadline = timezone.now() - timedelta(days=5)
    archived.save()

    # Process transition
    ArchivalService.finalize_non_restorable_archived_users()
    archived.refresh_from_db()
    assert archived.status == "permanent_non_restorable"

    # Restoration attempt must now fail
    with pytest.raises(ArchivalError) as exc_info:
        ArchivalService.restore_archived_user(
            user_id=test_user.id,
            restoration_authorization_ref="DIR/LATE/01",
            actor_username="superadmin",
        )
    assert "permanently non-restorable" in str(exc_info.value) or exc_info.value.code == "reversibility_window_expired"


def test_archive_and_restore_historical_data():
    """Verify historical dataset archival and restoration with reference (CFR-SA-013, CFR-SA-014)."""
    record = ArchivalService.archive_historical_data(
        category="system_logs_2022",
        date_range_start=date(2022, 1, 1),
        date_range_end=date(2022, 12, 31),
        record_count=15000,
        storage_size_kb=45000,
        backup_reference="S3://fusion-cold-storage/logs/2022.tar.gz",
        retention_years=7,
        actor_username="superadmin",
    )
    assert record.id is not None
    assert record.status == "archived"
    assert record.retention_expiry_date > date.today()

    restored = ArchivalService.restore_historical_data(
        data_id=record.id,
        approval_ref="AUDIT/REQ/2026/99",
        actor_username="superadmin",
    )
    assert restored.status == "restored"
    assert restored.restoration_approval_ref == "AUDIT/REQ/2026/99"


def test_dual_authorization_purge_approved_workflow():
    """Verify full dual-auth workflow: Super Admin requests, IT Head approves, data permanently purged (BR-SA-022, BW-SA-01, CW-SA-01)."""
    batch = ArchivalService.archive_historical_data(
        category="expired_temp_data",
        date_range_start=date(2015, 1, 1),
        date_range_end=date(2015, 12, 31),
        record_count=5000,
        storage_size_kb=10000,
        backup_reference="BK_2015",
        actor_username="superadmin",
    )

    # 1. Super Admin submits purge request
    purge_req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=batch.id,
        reason="Statutory retention expired beyond 10 years",
        regulatory_authorization_ref="REG/PURGE/2026/01",
        requester_username="superadmin",
    )
    assert purge_req.status == "pending_it_head"

    # 2. IT Head authorizes purge
    decided = ArchivalService.authorize_permanent_purge(
        purge_request_id=purge_req.id,
        it_head_username="it_head_officer",
        decision="approve",
        comments="Statutory clearance verified. Permanent purge approved.",
    )
    assert decided.status == "approved"
    assert decided.purge_executed_at is not None

    batch.refresh_from_db()
    assert batch.status == "purged"


def test_dual_authorization_purge_rejected_workflow():
    """Verify IT Head rejection leaves data safely archived (BW-SA-02)."""
    batch = ArchivalService.archive_historical_data(
        category="contested_archive_data",
        date_range_start=date(2018, 1, 1),
        date_range_end=date(2018, 12, 31),
        record_count=2000,
        storage_size_kb=5000,
        backup_reference="BK_2018",
        actor_username="superadmin",
    )

    purge_req = ArchivalService.request_permanent_purge(
        target_type="historical_data",
        target_id=batch.id,
        reason="Routine cleanup request",
        regulatory_authorization_ref="CLEAN/REQ/01",
        requester_username="superadmin",
    )

    decided = ArchivalService.authorize_permanent_purge(
        purge_request_id=purge_req.id,
        it_head_username="it_head_officer",
        decision="reject",
        comments="Rejected: legal hold still applies to 2018 datasets.",
    )
    assert decided.status == "rejected"

    batch.refresh_from_db()
    assert batch.status == "archived"  # Remains safely archived
