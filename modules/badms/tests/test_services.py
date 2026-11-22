"""Integration and transaction tests for BADMS services and contracts."""

import pytest

from modules.badms.contracts import get_user_archival_summaries, get_user_storage_quotas
from modules.badms.domain.errors import (
    DepartmentScopeViolation,
    RuleViolation,
)
from modules.badms.models import (
    ArchivalRequest,
    BackupSchedule,
    NotificationLog,
    SystemState,
    UserStorageQuota,
)
from modules.badms.services import (
    classify_archival_request_sysadmin,
    configure_sensitive_encryption,
    decide_archival_request_hod,
    decide_sensitive_restoration_sysadmin,
    decide_storage_extension_hod,
    execute_scheduled_backup,
    execute_special_archival,
    execute_technical_restoration,
    submit_archival_request,
    submit_restoration_request,
    submit_storage_extension,
    trigger_manual_backup,
)


@pytest.mark.django_db
def test_manual_backup_flow():
    record = trigger_manual_backup(
        actor_id=10,
        actor_username="admin1",
        actor_role="sysadmin",
        dataset="all",
    )
    assert record.status == "success"
    assert record.backup_type == "manual"
    assert record.checksum != ""
    assert record.is_consistent is True

    # User cannot trigger manual backup
    with pytest.raises(RuleViolation):
        trigger_manual_backup(
            actor_id=11,
            actor_username="student1",
            actor_role="user",
        )


@pytest.mark.django_db
def test_scheduled_backup_and_escalation():
    sched = BackupSchedule.objects.create(
        name="Nightly Full",
        scope="global",
        dataset="all",
        frequency="daily",
        execution_time="03:00",
        repository_path="/var/backups",
        is_active=True,
        created_by_id=1,
    )

    # Success run
    rec = execute_scheduled_backup(schedule=sched, is_reachable=True)
    assert rec.status == "success"

    # Unreachable repository fails and marks record as failure
    rec_fail = execute_scheduled_backup(schedule=sched, is_reachable=False)
    assert rec_fail.status == "failure"


@pytest.mark.django_db
def test_consecutive_backup_failures_escalate():
    SystemState.objects.filter(key="consecutive_backup_failures").delete()
    sched = BackupSchedule.objects.create(
        name="Critical DB",
        scope="local",
        dataset="finance",
        frequency="hourly",
        execution_time="00:00",
        repository_path="/invalid_path",
        is_active=True,
        created_by_id=1,
    )

    for _i in range(1, 4):
        rec = execute_scheduled_backup(schedule=sched, is_reachable=False)
        assert rec.status == "failure"

    # 3 consecutive failures trigger escalation notification
    escalations = NotificationLog.objects.filter(
        recipient_role="director_it",
        notification_type="repeated_failure_escalation",
    )
    assert escalations.count() >= 1


@pytest.mark.django_db
def test_archival_full_sensitive_lifecycle():
    # 1. User submits archival
    UserStorageQuota.objects.create(
        user_id=101,
        department_id=1,
        used_bytes=1000,
        quota_bytes=100000,
    )
    arch = submit_archival_request(
        user_id=101,
        username="scholar1",
        department_id=1,
        file_name="quantum_sim.dat",
        file_type="binary",
        file_size_bytes=5000,
        owners="scholar1",
        reason="Publication dataset",
        attachment_path="/tmp/qsim.dat",
        initial_classification="sensitive",
    )
    assert arch.status == "submitted"

    # 2. HoD from other department cannot decide
    with pytest.raises(DepartmentScopeViolation):
        decide_archival_request_hod(
            request_id=arch.id,
            hod_id=902,
            hod_username="hod_ece",
            hod_department_id=2,  # Mismatch!
            approve=True,
        )

    # HoD from same department approves
    arch = decide_archival_request_hod(
        request_id=arch.id,
        hod_id=901,
        hod_username="hod_cse",
        hod_department_id=1,
        approve=True,
    )
    assert arch.status == "hod_approved"

    # 3. SysAdmin classifies as Sensitive
    arch = classify_archival_request_sysadmin(
        request_id=arch.id,
        sysadmin_id=1,
        sysadmin_username="sysadmin",
        authoritative_classification="sensitive",
    )
    assert arch.status == "classified_sensitive"

    # 4. IT Security configures encryption
    arch = configure_sensitive_encryption(
        request_id=arch.id,
        security_officer_id=50,
        security_officer_username="sec_officer",
        encryption_algorithm="AES-256",
    )
    assert arch.status == "sensitive_archive_encrypted"
    assert "AES-256" in arch.encryption_algorithm


@pytest.mark.django_db
def test_storage_extension_lifecycle():
    # Quota full
    quota = UserStorageQuota.objects.create(
        user_id=202,
        department_id=3,
        used_bytes=10000,
        quota_bytes=10000,
        is_full=True,
        available_infra_bytes=500000,
    )

    req = submit_storage_extension(
        user_id=202,
        username="researcher2",
        department_id=3,
        requested_bytes=20000,
        justification="Large dataset requirements",
    )
    assert req.status == "submitted"

    # HoD approval increases quota
    decide_storage_extension_hod(
        request_id=req.id,
        hod_id=803,
        hod_username="hod_mech",
        hod_department_id=3,
        approve=True,
    )
    quota.refresh_from_db()
    assert quota.quota_bytes == 30000
    assert quota.is_full is False


@pytest.mark.django_db
def test_restoration_lifecycle():
    arch = ArchivalRequest.objects.create(
        user_id=303,
        department_id=1,
        file_name="project_repo.zip",
        file_type="zip",
        file_size_bytes=1000,
        owners="user303",
        reason="Historical backup",
        attachment_path="/tmp/p.zip",
        initial_classification="sensitive",
        authoritative_classification="sensitive",
        status="sensitive_archive_encrypted",
    )

    # 1. User submits restore
    restore = submit_restoration_request(
        user_id=303,
        username="user303",
        archival_request_id=arch.id,
        target_destination="/home/user303/restored",
        reason="Need code verification",
    )
    assert restore.status == "pending_approval"

    # 2. SysAdmin approves
    restore = decide_sensitive_restoration_sysadmin(
        restoration_id=restore.id,
        sysadmin_id=1,
        sysadmin_username="sysadmin",
        approve=True,
    )
    assert restore.status == "approved"

    # 3. SysAdmin executes technical restoration
    restore = execute_technical_restoration(
        restoration_id=restore.id,
        sysadmin_id=1,
        sysadmin_username="sysadmin",
    )
    assert restore.status == "restored"
    assert restore.restored_at is not None


@pytest.mark.django_db
def test_special_archival_super_admin():
    rec = execute_special_archival(
        super_admin_id=999,
        super_admin_username="superadmin",
        dataset_name="DRDO_Defense_Study",
        source_authority="Ministry of Defence",
        reason="Classified archive holding",
        archive_path="/secure/drdo.tar.gz",
        size_bytes=5000000,
    )
    assert rec.dataset_name == "DRDO_Defense_Study"
    assert rec.performed_by_id == 999


@pytest.mark.django_db
def test_public_contracts_plurality():
    UserStorageQuota.objects.create(
        user_id=401,
        department_id=1,
        used_bytes=5000,
        quota_bytes=10000,
        is_full=False,
    )
    quotas = get_user_storage_quotas([401, 402])
    assert 401 in quotas
    assert quotas[401].used_bytes == 5000
    assert 402 not in quotas  # Non-existent user absent from mapping

    summaries = get_user_archival_summaries([401])
    assert 401 in summaries
    assert summaries[401].total_archived_files == 0
