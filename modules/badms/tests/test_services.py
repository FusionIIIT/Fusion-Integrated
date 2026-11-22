"""Service-layer tests for BADMS core workflows."""
from dataclasses import dataclass

import pytest

from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    UserStorageQuota,
)
from modules.badms.services import (
    archival as arch_svc,
)
from modules.badms.services import (
    backups as bkup_svc,
)
from modules.badms.services import (
    restoration as rest_svc,
)
from modules.badms.services import (
    storage as stor_svc,
)

pytestmark = pytest.mark.django_db


@dataclass
class SimpleActor:
    user_id: int
    department: str = "CSE"
    role: str = "student"


def test_backup_service_manual_and_job_execution():
    actor = SimpleActor(user_id=101, department="CSE", role="SysAdmin")
    rec = bkup_svc.trigger_manual_backup(actor=actor, dataset_name="academic_db")
    assert rec.status == BackupRecord.STATUS_SUCCESS
    assert rec.backup_type == BackupRecord.TYPE_MANUAL
    assert rec.checksum_sha256 != ""
    assert rec.file_size_bytes > 0
    assert rec.completed_at is not None

    # Verify audit event emitted
    audit = AuditEvent.objects.filter(target_model="BackupRecord", target_id=rec.id).first()
    assert audit is not None
    assert audit.event_type == "manual_backup_created"


def test_backup_service_failure_handling():
    failed_rec = bkup_svc.execute_scheduled_backup(
        dataset_name="failing_db",
        simulate_failure=True,
    )
    assert failed_rec.status == BackupRecord.STATUS_FAILURE
    assert failed_rec.consecutive_failure_count == 1
    assert "unreachable" in failed_rec.error_message


def test_archival_service_full_workflow():
    actor_user = SimpleActor(user_id=1001, department="CSE", role="student")
    actor_hod = SimpleActor(user_id=5001, department="CSE", role="HOD")
    actor_sys = SimpleActor(user_id=6001, department="CSE", role="SysAdmin")
    actor_sec = SimpleActor(user_id=7001, department="CSE", role="IT Security")

    # 1. Submit
    req = arch_svc.submit_archival_request(
        actor=actor_user,
        file_name="course_eval.csv",
        file_type="csv",
        file_size_bytes=4096,
        reason="Semester end archival",
        file_storage_path="/storage/cse/eval.csv",
        initial_classification="Sensitive",
    )
    assert req.status == "submitted"

    # 2. HOD Review (Approve)
    req_hod = arch_svc.decide_archival_request(
        actor=actor_hod,
        request_id=req.id,
        decision="approve",
        remarks="Approved by HOD CSE",
    )
    assert req_hod.status == "hod_approved"

    # 3. SysAdmin Classification
    req_class = arch_svc.classify_archival_request(
        actor=actor_sys,
        request_id=req.id,
        classification="Sensitive",
    )
    assert req_class.status == "classified_sensitive"
    assert req_class.authoritative_classification == "Sensitive"

    # 4. IT Security Encryption
    req_enc = arch_svc.configure_sensitive_encryption(
        actor=actor_sec,
        request_id=req.id,
        encryption_algorithm="AES-256-GCM",
    )
    assert req_enc.status == "sensitive_archive_encrypted"
    assert req_enc.is_encrypted is True
    assert req_enc.encryption_algorithm == "AES-256-GCM"


def test_archival_special_by_super_admin():
    actor_admin = SimpleActor(user_id=1, department="Institute", role="Super Admin")
    req = arch_svc.perform_special_archival(
        actor=actor_admin,
        file_name="board_resolution.pdf",
        file_type="pdf",
        file_size_bytes=10000,
        reason="Board of Governors resolution",
        file_storage_path="/secure/board.pdf",
    )
    assert req.status == "special_archived"
    assert req.is_special_archival is True


def test_storage_service_quota_and_extension_flow():
    user_id = 2002
    actor_user = SimpleActor(user_id=user_id, department="ME", role="student")
    actor_hod = SimpleActor(user_id=5002, department="ME", role="HOD")

    # Initialize quota at 1000 bytes with 1000 bytes used (quota full)
    quota = UserStorageQuota.objects.create(
        user_id=user_id,
        allocated_quota_bytes=1000,
        used_storage_bytes=1000,
        is_full=True,
    )

    # 1. Submit extension request
    req = stor_svc.submit_storage_extension(
        actor=actor_user,
        requested_extension_bytes=500,
        justification="Large ANSYS mesh output files",
    )
    assert req.status == "submitted"
    assert req.current_quota_bytes == 1000
    assert req.current_usage_bytes == 1000

    # 2. HOD Review (Approve)
    approved_req = stor_svc.decide_storage_extension(
        actor=actor_hod,
        request_id=req.id,
        decision="approve",
        remarks="Approved 500 bytes expansion",
    )
    assert approved_req.status == "approved"

    # Check that UserStorageQuota was updated atomically
    quota.refresh_from_db()
    assert quota.allocated_quota_bytes == 1500
    assert quota.is_full is False


def test_storage_service_rejects_extension_when_quota_not_full():
    user_id = 3003
    actor_user = SimpleActor(user_id=user_id, department="Design", role="student")
    UserStorageQuota.objects.create(
        user_id=user_id,
        allocated_quota_bytes=1000,
        used_storage_bytes=500,  # Only half used
        is_full=False,
    )
    with pytest.raises(Exception) as exc_info:
        stor_svc.submit_storage_extension(
            actor=actor_user,
            requested_extension_bytes=500,
            justification="Premature extension request",
        )
    assert "not full" in str(exc_info.value).lower()


def test_restoration_service_flow():
    actor_user = SimpleActor(user_id=1001, department="CSE", role="student")
    actor_sys = SimpleActor(user_id=6001, department="CSE", role="SysAdmin")

    # Setup sensitive archive
    arch = ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="cse_records.tar",
        file_type="tar",
        file_size_bytes=5000,
        file_storage_path="/archive/cse_records.tar",
        status="sensitive_archive_encrypted",
        authoritative_classification="Sensitive",
        is_encrypted=True,
    )

    # Submit restoration request (sensitive archive requires approval)
    rest_req = rest_svc.request_data_restoration(
        actor=actor_user,
        archival_request_id=arch.id,
        target_destination="/restored/cse_records/",
    )
    assert rest_req.status == "sensitive_pending_approval"
    assert rest_req.classification == "Sensitive"

    # Review (Approve by sysadmin)
    app_req = rest_svc.approve_sensitive_restoration(
        actor=actor_sys,
        restoration_id=rest_req.id,
        decision="approve",
    )
    assert app_req.status == "approved"

    # Execute technical restore
    done_req = rest_svc.execute_data_restoration(
        actor=actor_sys,
        restoration_id=app_req.id,
    )
    assert done_req.status == "restored"
    assert done_req.restored_at is not None


def test_restoration_execution_refuses_unapproved_or_rejected_state():
    from core.api.exceptions import ConflictError

    actor_user = SimpleActor(user_id=1001, department="CSE", role="student")
    actor_sys = SimpleActor(user_id=6001, department="CSE", role="SysAdmin")

    arch = ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="unapproved.tar",
        file_type="tar",
        file_size_bytes=5000,
        file_storage_path="/archive/unapproved.tar",
        status="sensitive_archive_encrypted",
        authoritative_classification="Sensitive",
        is_encrypted=True,
    )
    rest_req = rest_svc.request_data_restoration(
        actor=actor_user,
        archival_request_id=arch.id,
        target_destination="/restored/unapproved/",
    )
    # 1. Refuse execution while still pending approval
    with pytest.raises(ConflictError):
        rest_svc.execute_data_restoration(actor=actor_sys, restoration_id=rest_req.id)

    # 2. Refuse execution when rejected
    rest_svc.approve_sensitive_restoration(
        actor=actor_sys, restoration_id=rest_req.id, decision="reject"
    )
    with pytest.raises(ConflictError):
        rest_svc.execute_data_restoration(actor=actor_sys, restoration_id=rest_req.id)


def test_schedule_service_flow():
    from core.api.exceptions import BadRequestError, NotFoundError
    from modules.badms.services import schedules as sched_svc

    actor = SimpleActor(user_id=1, department="Central", role="SysAdmin")

    # 1. Invalid cron
    with pytest.raises(BadRequestError):
        sched_svc.create_backup_schedule(
            actor, name="bad", scope_type="global", dataset_name="d1", cron_expression="invalid"
        )

    # 2. Invalid scope
    with pytest.raises(BadRequestError):
        sched_svc.create_backup_schedule(
            actor, name="bad", scope_type="unknown_scope", dataset_name="d1", cron_expression="* * * * *"
        )

    # 3. Create schedule
    s1 = sched_svc.create_backup_schedule(
        actor, name="Nightly", scope_type="global", dataset_name="d1", cron_expression="0 2 * * *"
    )
    assert s1.version == 1
    assert s1.is_active is True

    # 4. Create another schedule superseding s1
    s2 = sched_svc.create_backup_schedule(
        actor, name="Nightly v2", scope_type="global", dataset_name="d1", cron_expression="0 3 * * *"
    )
    assert s2.version == 2
    s1.refresh_from_db()
    assert s1.is_active is False
    assert s1.effective_to is not None

    # 5. Update schedule
    s2_up = sched_svc.update_backup_schedule(
        actor, schedule_id=s2.id, name="Nightly Final", cron_expression="0 4 * * *"
    )
    assert s2_up.name == "Nightly Final"

    # 6. Update invalid cron
    with pytest.raises(BadRequestError):
        sched_svc.update_backup_schedule(actor, schedule_id=s2.id, cron_expression="invalid")

    # 7. Update nonexistent schedule
    with pytest.raises(NotFoundError):
        sched_svc.update_backup_schedule(actor, schedule_id=99999, name="None")


def test_policies_service_flow():
    from modules.badms.services import policies as pol_svc

    actor = SimpleActor(user_id=7001, department="Central", role="IT Security")

    p1 = pol_svc.save_security_policy(actor, "enc_std", {"algo": "AES-128"})
    assert p1.is_active is True

    # Save same key supersedes p1
    p2 = pol_svc.save_security_policy(actor, "enc_std", {"algo": "AES-256-GCM"})
    assert p2.is_active is True
    p1.refresh_from_db()
    assert p1.is_active is False
    assert p1.effective_to is not None

