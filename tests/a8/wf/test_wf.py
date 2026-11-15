"""Automated backend test suite for Workflow (WF) specifications.

Generated from frozen a8_design/WF_DESIGN.json.
Rules:
- Tests are automated using pytest/pytest-django.
- Every test contains test_id and source_id.
- Uses Django isolated test database.
- Does not mock the behavior being tested.
"""
from __future__ import annotations

import datetime

import pytest
from django.utils import timezone

from modules.system_admin.constants import (
    PurgeRequestStatus,
    RoleAssignmentState,
    RoleCategory,
    UserArchivalStatus,
    UserKind,
    UserLifecycleStatus,
)
from modules.system_admin.domain.dataclasses import RoleAssignmentSpec
from modules.system_admin.models import (
    ArchivedUserRecord,
    BasicUser,
    HistoricalDataArchive,
    PurgeRequest,
    RoleAssignment,
    RoleDefinition,
    UserProfile,
)
from modules.system_admin.services import archival as archival_service
from modules.system_admin.services import purge as purge_service
from modules.system_admin.services import role_management as role_service
from modules.system_admin.services import user_lifecycle as user_service
from modules.system_admin.tasks import (
    sweep_expired_archived_user_windows,
    sweep_expired_roles,
    sweep_scheduled_role_activations,
)


@pytest.fixture
def base_user(db) -> BasicUser:
    user = BasicUser.objects.create(
        username="wf_user_1",
        institute_id="WF2026001",
        email="wf_user_1@iiitdmj.ac.in",
        kind=UserKind.STUDENT,
        status=UserLifecycleStatus.ACTIVE,
        is_active=True,
    )
    UserProfile.objects.create(
        user=user,
        display_name="WF User One",
        department="CSE",
    )
    return user


@pytest.fixture
def role_def(db) -> RoleDefinition:
    role, _ = RoleDefinition.objects.get_or_create(
        code="wf_warden",
        defaults={
            "label": "Hostel Warden",
            "category": RoleCategory.OFFICE,
            "allowed_kinds": "faculty,staff",
            "is_singular": False,
            "is_time_bound": True,
            "default_lead_time_days": 7,
            "is_active": True,
        },
    )
    return role


@pytest.mark.django_db
def test_tc_sa_001_purge_request_approved():
    """TC-SA-001 | BW-SA-01 path-approved
    Verify retention-expired archived dataset requested for purge by Super Admin
    and subsequently approved by IT Head.
    """
    admin_user = BasicUser.objects.create(
        username="superadmin_wf",
        institute_id="SAWF001",
        email="sawf@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )
    it_head_user = BasicUser.objects.create(
        username="ithead_wf",
        institute_id="ITWF001",
        email="itwf@iiitdmj.ac.in",
        kind=UserKind.FACULTY,
        status=UserLifecycleStatus.ACTIVE,
    )

    archive = HistoricalDataArchive.objects.create(
        dataset_category="academic_records",
        date_range_start=datetime.date(2015, 1, 1),
        date_range_end=datetime.date(2018, 12, 31),
        record_count=150,
        archived_by=admin_user.id,
        retention_expires_at=timezone.now().date() - datetime.timedelta(days=10),
    )

    purge_req = purge_service.request_permanent_purge(
        archive_id=archive.id,
        reason="Statutory retention expired, eligible for permanent destruction.",
        super_admin_id=admin_user.id,
    )

    assert purge_req.status == PurgeRequestStatus.PENDING_IT_HEAD

    decision_req = purge_service.authorize_permanent_purge(
        request_id=purge_req.id,
        it_head_id=it_head_user.id,
        approved=True,
        comments="Approved by IT Head per institutional policy.",
    )

    assert decision_req.status == PurgeRequestStatus.PURGED
    archive.refresh_from_db()
    assert archive.is_purged is True


@pytest.mark.django_db
def test_tc_sa_002_purge_request_rejected():
    """TC-SA-002 | BW-SA-02 path-rejected
    Verify retention-expired archived dataset purge request rejected by IT Head.
    """
    admin_user = BasicUser.objects.create(
        username="superadmin_wf2",
        institute_id="SAWF002",
        email="sawf2@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )
    it_head_user = BasicUser.objects.create(
        username="ithead_wf2",
        institute_id="ITWF002",
        email="itwf2@iiitdmj.ac.in",
        kind=UserKind.FACULTY,
        status=UserLifecycleStatus.ACTIVE,
    )

    archive = HistoricalDataArchive.objects.create(
        dataset_category="audit_logs",
        date_range_start=datetime.date(2016, 1, 1),
        date_range_end=datetime.date(2019, 12, 31),
        record_count=500,
        archived_by=admin_user.id,
        retention_expires_at=timezone.now().date() - datetime.timedelta(days=5),
    )

    purge_req = purge_service.request_permanent_purge(
        archive_id=archive.id,
        reason="Requesting purge of historical audit logs.",
        super_admin_id=admin_user.id,
    )

    assert purge_req.status == PurgeRequestStatus.PENDING_IT_HEAD

    decision_req = purge_service.authorize_permanent_purge(
        request_id=purge_req.id,
        it_head_id=it_head_user.id,
        approved=False,
        comments="Rejected: audit inquiry pending.",
    )

    assert decision_req.status == PurgeRequestStatus.REJECTED
    archive.refresh_from_db()
    assert archive.is_purged is False


@pytest.mark.django_db
def test_tc_sa_003_immediate_assignment_to_expiry(role_def):
    """TC-SA-003 | BW-SA-03 immediate-assignment-to-expiry
    Verify assignment of immediate time-bound role and auto transition to expired upon reaching end date.
    """
    faculty = BasicUser.objects.create(
        username="faculty_wf3",
        institute_id="FACWF003",
        email="facwf3@iiitdmj.ac.in",
        kind=UserKind.FACULTY,
        status=UserLifecycleStatus.ACTIVE,
    )
    admin = BasicUser.objects.create(
        username="admin_wf3",
        institute_id="ADWF003",
        email="adwf3@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )

    today = timezone.now().date()
    spec = RoleAssignmentSpec(
        role_code=role_def.code,
        target_user_id=faculty.id,
        target_user_kind=faculty.kind,
        start_date=today,
        end_date=today + datetime.timedelta(days=30),
        scope="Hall 1",
        reason="Appointed Warden for Hall 1",
        is_time_bound=True,
    )
    assignment = role_service.assign_role(
        spec=spec,
        performed_by_id=admin.id,
    )

    assert assignment.state == RoleAssignmentState.ACTIVE

    # Simulate passing end date by shifting both dates backward to preserve start <= end constraint
    assignment.start_date = today - datetime.timedelta(days=30)
    assignment.end_date = today - datetime.timedelta(days=1)
    assignment.save(update_fields=["start_date", "end_date"])

    expired_count = sweep_expired_roles()
    assert expired_count >= 1

    assignment.refresh_from_db()
    assert assignment.state == RoleAssignmentState.EXPIRED
    assert assignment.expired_at is not None


@pytest.mark.django_db
def test_tc_sa_004_future_dated_assignment_to_expiry(role_def):
    """TC-SA-004 | BW-SA-04 future-dated-assignment-to-expiry
    Verify scheduled role assignment, auto activation on start date, and expiry on end date.
    """
    faculty = BasicUser.objects.create(
        username="faculty_wf4",
        institute_id="FACWF004",
        email="facwf4@iiitdmj.ac.in",
        kind=UserKind.FACULTY,
        status=UserLifecycleStatus.ACTIVE,
    )
    admin = BasicUser.objects.create(
        username="admin_wf4",
        institute_id="ADWF004",
        email="adwf4@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )

    today = timezone.now().date()
    future_start = today + datetime.timedelta(days=7)
    future_end = today + datetime.timedelta(days=60)

    spec = RoleAssignmentSpec(
        role_code=role_def.code,
        target_user_id=faculty.id,
        target_user_kind=faculty.kind,
        start_date=future_start,
        end_date=future_end,
        scope="Hall 2",
        reason="Scheduled appointment as Warden Hall 2",
        is_time_bound=True,
    )
    assignment = role_service.assign_role(
        spec=spec,
        performed_by_id=admin.id,
    )

    assert assignment.state == RoleAssignmentState.SCHEDULED

    # Simulate reaching start date
    assignment.start_date = today
    assignment.save(update_fields=["start_date"])

    activated_count = sweep_scheduled_role_activations()
    assert activated_count >= 1

    assignment.refresh_from_db()
    assert assignment.state == RoleAssignmentState.ACTIVE
    assert assignment.activated_at is not None

    # Simulate reaching end date preserving start <= end
    assignment.start_date = today - datetime.timedelta(days=30)
    assignment.end_date = today - datetime.timedelta(days=1)
    assignment.save(update_fields=["start_date", "end_date"])

    expired_count = sweep_expired_roles()
    assert expired_count >= 1

    assignment.refresh_from_db()
    assert assignment.state == RoleAssignmentState.EXPIRED


@pytest.mark.django_db
def test_tc_sa_005_role_validity_extension(role_def):
    """TC-SA-005 | BW-SA-05 role-validity-extension
    Verify extending validity of an active time-bound role prior to expiry and expiry at revised end date.
    """
    faculty = BasicUser.objects.create(
        username="faculty_wf5",
        institute_id="FACWF005",
        email="facwf5@iiitdmj.ac.in",
        kind=UserKind.FACULTY,
        status=UserLifecycleStatus.ACTIVE,
    )
    admin = BasicUser.objects.create(
        username="admin_wf5",
        institute_id="ADWF005",
        email="adwf5@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )

    today = timezone.now().date()
    spec = RoleAssignmentSpec(
        role_code=role_def.code,
        target_user_id=faculty.id,
        target_user_kind=faculty.kind,
        start_date=today,
        end_date=today + datetime.timedelta(days=30),
        scope="Hall 3",
        reason="Warden Hall 3",
        is_time_bound=True,
    )
    assignment = role_service.assign_role(
        spec=spec,
        performed_by_id=admin.id,
    )
    assert assignment.state == RoleAssignmentState.ACTIVE

    revised_end = today + datetime.timedelta(days=90)
    extended = role_service.extend_role_validity(
        assignment_id=assignment.id,
        new_end_date=revised_end,
        reason="Extended tenure by committee recommendation",
        performed_by_id=admin.id,
    )

    assert extended.state == RoleAssignmentState.EXTENDED
    assert extended.end_date == revised_end

    # Simulate reaching revised end date preserving start <= end
    extended.start_date = today - datetime.timedelta(days=30)
    extended.end_date = today - datetime.timedelta(days=1)
    extended.save(update_fields=["start_date", "end_date"])

    sweep_expired_roles()
    extended.refresh_from_db()
    assert extended.state == RoleAssignmentState.EXPIRED


@pytest.mark.django_db
def test_tc_sa_006_deactivated_user_reactivation(base_user):
    """TC-SA-006 | BW-SA-06 deactivated-user-reactivation
    Verify reactivation of a deactivated basic user account.
    """
    admin = BasicUser.objects.create(
        username="admin_wf6",
        institute_id="ADWF006",
        email="adwf6@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )

    deactivated = user_service.deactivate_user(
        user_id=base_user.id,
        reason="Leave of absence",
        performed_by_id=admin.id,
    )
    assert deactivated.status == UserLifecycleStatus.DEACTIVATED

    reactivated = user_service.reactivate_user(
        user_id=base_user.id,
        reason="Returned from leave",
        performed_by_id=admin.id,
    )
    assert reactivated.status == UserLifecycleStatus.ACTIVE
    assert reactivated.is_active is True


@pytest.mark.django_db
def test_tc_sa_007_archived_user_restoration_within_window(base_user):
    """TC-SA-007 | BW-SA-07 archived-user-restoration-within-window
    Verify archival of an eligible deactivated user and restoration within reversible window.
    """
    admin = BasicUser.objects.create(
        username="admin_wf7",
        institute_id="ADWF007",
        email="adwf7@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )

    # Precondition: deactivation interval elapsed (>=30 days)
    base_user.status = UserLifecycleStatus.DEACTIVATED
    base_user.deactivated_at = timezone.now() - datetime.timedelta(days=35)
    base_user.save(update_fields=["status", "deactivated_at"])

    archived_record = archival_service.archive_user(
        user_id=base_user.id,
        reason="Graduation archival",
        performed_by_id=admin.id,
    )
    assert archived_record.status == UserArchivalStatus.REVERSIBLE
    base_user.refresh_from_db()
    assert base_user.status == UserLifecycleStatus.ARCHIVED

    # Restore within reversible window
    restored = archival_service.restore_archived_user(
        user_id=base_user.id,
        reason="Restoring for higher studies enrolment",
        performed_by_id=admin.id,
    )
    assert restored.status == UserLifecycleStatus.ACTIVE
    archived_record.refresh_from_db()
    assert archived_record.status == UserArchivalStatus.RESTORED


@pytest.mark.django_db
def test_tc_sa_008_archived_user_reversibility_window_expiry(base_user):
    """TC-SA-008 | BW-SA-08 archived-user-reversibility-window-expiry
    Verify automatic transition of archived user to permanently non-restorable status when window expires.
    """
    admin = BasicUser.objects.create(
        username="admin_wf8",
        institute_id="ADWF008",
        email="adwf8@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )

    base_user.status = UserLifecycleStatus.DEACTIVATED
    base_user.deactivated_at = timezone.now() - datetime.timedelta(days=35)
    base_user.save(update_fields=["status", "deactivated_at"])

    archived_record = archival_service.archive_user(
        user_id=base_user.id,
        reason="Alumnus departure",
        performed_by_id=admin.id,
    )

    # Simulate reversible period expiration
    archived_record.reversible_until = timezone.now() - datetime.timedelta(days=1)
    archived_record.save(update_fields=["reversible_until"])

    finalized_count = sweep_expired_archived_user_windows()
    assert finalized_count >= 1

    archived_record.refresh_from_db()
    assert archived_record.status == UserArchivalStatus.PERMANENT_NON_RESTORABLE


@pytest.mark.django_db
def test_tc_sa_009_historical_data_archive_and_restore():
    """TC-SA-009 | BW-SA-09 historical-data-archive-and-restore
    Verify archiving eligible historical data after backup and subsequently restoring it.
    """
    admin = BasicUser.objects.create(
        username="admin_wf9",
        institute_id="ADWF009",
        email="adwf9@iiitdmj.ac.in",
        kind=UserKind.STAFF,
        status=UserLifecycleStatus.ACTIVE,
    )

    archive = archival_service.archive_historical_data(
        category="library_transactions",
        date_start=datetime.date(2017, 1, 1),
        date_end=datetime.date(2020, 12, 31),
        record_count=3200,
        backup_file_path="/var/backups/fusion/library_2017_2020.tar.gz",
        backup_checksum="a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
        retention_years=7,
        performed_by_id=admin.id,
    )

    assert archive.dataset_category == "library_transactions"
    assert archive.is_restored is False

    restored = archival_service.restore_historical_data(
        archive_id=archive.id,
        reason="Accreditation historical data audit request",
        performed_by_id=admin.id,
    )

    assert restored.is_restored is True
