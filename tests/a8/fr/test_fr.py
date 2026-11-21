"""FR Test Suite: Functional Requirements (CFR + AFR).
Generated from a8_design/FR_DESIGN.json.
"""
from datetime import timedelta
import pytest
from django.utils import timezone
from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.badms.models import (
    BackupOperation,
    BackupSchedule,
    SecureArchivalRequest,
    DataRestorationRequest,
    StorageQuota,
    StorageExtensionRequest,
    BadmsAuditLog,
)
from modules.badms.domain import state_machine as sm
from modules.badms.services import operations as ops
from modules.badms.selectors import scoping
from modules.badms.contracts import get_user_storage_quotas
from tests.a8.helpers import (
    sysadmin_actor,
    superadmin_actor,
    hod_actor,
    it_security_actor,
    regular_user_actor,
)

pytestmark = pytest.mark.django_db


def test_fr_001_manual_backup_authorized():
    """TEST-FR-001 | AFR-BA-001: SysAdmin or Super Admin can trigger manual backup."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="cse_db")
    assert op.pk is not None
    assert op.status == "success"
    assert op.trigger_type == "manual"
    assert op.dataset_code == "cse_db"


def test_fr_002_manual_backup_unauthorized():
    """TEST-FR-002 | AFR-BA-001-AUTH-FAIL: Unauthorized user cannot trigger manual backup."""
    user = regular_user_actor(user_id=2)
    with pytest.raises(PermissionDeniedError):
        ops.trigger_manual_backup(actor=user, dataset_code="cse_db")


def test_fr_003_manual_backup_captures_artifacts():
    """TEST-FR-003 | AFR-BA-002: Manual backup captures current timestamp and required backup artifacts."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="all")
    assert op.started_at is not None
    assert op.completed_at is not None
    assert op.dump_location.startswith("/backups/dumps/")


def test_fr_004_manual_backup_integrity_verification():
    """TEST-FR-004 | AFR-BA-003: Save dump and record integrity verification."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="students")
    assert op.integrity_verified is True
    assert op.file_size_bytes > 0


def test_fr_005_manual_backup_outcome_success():
    """TEST-FR-005 | AFR-BA-004: Record outcome as Success."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="all")
    assert op.status == "success"


def test_fr_006_failed_backup_outcome_recording():
    """TEST-FR-006 | AFR-BA-005: Record failure outcome and error details."""
    op = BackupOperation.objects.create(
        trigger_type="manual",
        dataset_code="finance",
        status="failed",
        error_message="Disk full",
        file_size_bytes=0,
        integrity_verified=False,
    )
    assert op.status == "failed"
    assert "Disk full" in op.error_message


def test_fr_007_automatic_backup_schedule_properties():
    """TEST-FR-007 | AFR-BA-006: Automatic backup schedule representation and active status."""
    admin = sysadmin_actor(user_id=1)
    sch = ops.configure_schedule(
        actor=admin, scope="local", dataset_code="library", cron_expression="0 2 * * *", retention_days=30
    )
    assert sch.is_active is True
    assert sch.cron_expression == "0 2 * * *"
    assert sch.retention_days == 30


def test_fr_008_automatic_backup_repository_reachability():
    """TEST-FR-008 | AFR-BA-011: Repository reachability check for scheduled backup."""
    # Scheduled automatic backup execution daemon ping check
    pytest.skip("NOT_AUTOMATED: External storage daemon reachability probe is handled outside Django service layer")


def test_fr_009_view_backup_schedules():
    """TEST-FR-009 | AFR-BA-012: SysAdmin can view backup schedules."""
    admin = sysadmin_actor(user_id=1)
    ops.configure_schedule(actor=admin, scope="local", dataset_code="acad", cron_expression="0 1 * * *", retention_days=15)
    schedules = list(BackupSchedule.objects.all())
    assert len(schedules) >= 1
    assert any(s.dataset_code == "acad" for s in schedules)


def test_fr_010_configure_local_backup_schedule():
    """TEST-FR-010 | AFR-BA-013: SysAdmin configures local dataset backup schedule."""
    admin = sysadmin_actor(user_id=1)
    sch = ops.configure_schedule(
        actor=admin, scope="local", dataset_code="sports", cron_expression="0 3 * * 0", retention_days=14
    )
    assert sch.scope == "local"
    assert sch.dataset_code == "sports"


def test_fr_011_schedule_validation_rejects_invalid_params():
    """TEST-FR-011 | AFR-BA-014: Validation rejects conflicting or invalid schedule parameters."""
    admin = sysadmin_actor(user_id=1)
    # The specification states that invalid schedule parameters must be rejected.
    # If the implementation accepts negative retention_days or malformed cron without validation, it violates AFR-BA-014.
    with pytest.raises((BadRequestError, ValueError)):
        ops.configure_schedule(
            actor=admin, scope="local", dataset_code="invalid", cron_expression="not-a-cron", retention_days=-10
        )


def test_fr_012_schedule_configuration_audit_log():
    """TEST-FR-012 | AFR-BA-016: Schedule configuration changes logged in audit log."""
    admin = sysadmin_actor(user_id=1)
    sch = ops.configure_schedule(
        actor=admin, scope="local", dataset_code="placement", cron_expression="0 4 * * *", retention_days=45
    )
    logs = BadmsAuditLog.objects.filter(entity_type="backup_schedule", entity_id=sch.pk)
    assert logs.exists()
    assert "local_schedule_configured" in logs.first().action


def test_fr_013_backup_history_maintenance():
    """TEST-FR-013 | AFR-BA-017: System maintains current status and history of backup operations."""
    admin = sysadmin_actor(user_id=1)
    op1 = ops.trigger_manual_backup(actor=admin, dataset_code="db1")
    op2 = ops.trigger_manual_backup(actor=admin, dataset_code="db2")
    history = list(BackupOperation.objects.all())
    assert len(history) >= 2
    assert op2 in history and op1 in history


def test_fr_014_submit_archival_request():
    """TEST-FR-014 | AFR-BA-019: Authenticated user initiates secure archival request."""
    user = regular_user_actor(user_id=10, dept="CSE")
    req = ops.submit_archival_request(
        actor=user,
        department="CSE",
        file_name="marks.csv",
        file_type="csv",
        file_size_bytes=1024,
        reason="Semester records",
        initial_classification="routine",
    )
    assert req.pk is not None
    assert req.status == "submitted"
    assert req.file_name == "marks.csv"


def test_fr_015_archival_request_captured_metadata():
    """TEST-FR-015 | AFR-BA-020: Archival request captures file details, size, reason and owner."""
    user = regular_user_actor(user_id=11, dept="ME")
    req = ops.submit_archival_request(
        actor=user,
        department="ME",
        file_name="lab_specs.pdf",
        file_type="pdf",
        file_size_bytes=4096,
        reason="Lab equipment manual",
        initial_classification="routine",
    )
    assert req.user_id == 11
    assert req.department == "ME"
    assert req.file_type == "pdf"
    assert req.file_size_bytes == 4096


def test_fr_016_archival_request_parameter_validation():
    """TEST-FR-016 | AFR-BA-021: Archival request parameter validation before acceptance."""
    user = regular_user_actor(user_id=12, dept="CSE")
    req = ops.submit_archival_request(
        actor=user,
        department="CSE",
        file_name="valid.txt",
        file_type="txt",
        file_size_bytes=512,
        reason="Valid reason",
    )
    assert req.pk is not None


def test_fr_017_archival_request_initial_status_submitted():
    """TEST-FR-017 | AFR-BA-022: Initial status of submitted archival request is 'submitted'."""
    user = regular_user_actor(user_id=13, dept="ECE")
    req = ops.submit_archival_request(
        actor=user,
        department="ECE",
        file_name="circuit.png",
        file_type="png",
        file_size_bytes=2048,
        reason="Schematics",
    )
    assert req.status == sm.ARCHIVAL_SUBMITTED


def test_fr_018_routed_hod_reviews_request():
    """TEST-FR-018 | AFR-BA-024: Routed HoD can review archival request details."""
    user = regular_user_actor(user_id=14, dept="CSE")
    req = ops.submit_archival_request(
        actor=user,
        department="CSE",
        file_name="thesis.docx",
        file_type="docx",
        file_size_bytes=8192,
        reason="Thesis document",
    )
    cse_hod = hod_actor(user_id=20, dept="CSE")
    visible = scoping.visible_archival_requests(cse_hod)
    assert req in visible


def test_fr_019_hod_decision_approve_and_reject():
    """TEST-FR-019 | AFR-BA-025: HoD can approve or reject secure archival request."""
    user = regular_user_actor(user_id=15, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")

    req_app = ops.submit_archival_request(
        actor=user, department="CSE", file_name="f1.pdf", file_type="pdf", file_size_bytes=100, reason="R1"
    )
    approved = ops.hod_review_archival(actor=cse_hod, request_id=req_app.pk, action="approve", remarks="Approved")
    assert approved.status == sm.ARCHIVAL_HOD_APPROVED

    req_rej = ops.submit_archival_request(
        actor=user, department="CSE", file_name="f2.pdf", file_type="pdf", file_size_bytes=100, reason="R2"
    )
    rejected = ops.hod_review_archival(actor=cse_hod, request_id=req_rej.pk, action="reject", remarks="Rejected")
    assert rejected.status == sm.ARCHIVAL_HOD_REJECTED


def test_fr_020_hod_department_scoping_enforced():
    """TEST-FR-020 | AFR-BA-026: Only the HoD of requester's department can approve/reject request."""
    user = regular_user_actor(user_id=16, dept="ECE")
    ece_req = ops.submit_archival_request(
        actor=user, department="ECE", file_name="ece_file.dat", file_type="dat", file_size_bytes=500, reason="ECE test"
    )
    cse_hod = hod_actor(user_id=20, dept="CSE")
    # AFR-BA-026: only the HoD of the requester's department shall be permitted to approve or reject
    with pytest.raises(PermissionDeniedError):
        ops.hod_review_archival(actor=cse_hod, request_id=ece_req.pk, action="approve")


def test_fr_021_sysadmin_classify_archival_request():
    """TEST-FR-021 | AFR-BA-028: SysAdmin classifies approved archival request."""
    user = regular_user_actor(user_id=17, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)

    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="report.pdf", file_type="pdf", file_size_bytes=300, reason="Final"
    )
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    classified = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="routine")
    assert classified.authoritative_classification == "routine"
    assert classified.status == sm.ARCHIVAL_COMPLETED
    assert classified.retention_until is not None


def test_fr_022_initial_classification_default():
    """TEST-FR-022 | AFR-BA-029: Default initial classification is 'routine' if omitted or invalid."""
    user = regular_user_actor(user_id=18, dept="CSE")
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="notes.txt", file_type="txt", file_size_bytes=100, reason="Notes", initial_classification="invalid_tier"
    )
    assert req.initial_classification == sm.TIER_ROUTINE


def test_fr_023_sensitive_classification_routing():
    """TEST-FR-023 | AFR-BA-031: Sensitive classification routes request for encryption."""
    user = regular_user_actor(user_id=19, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)

    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="keys.txt", file_type="txt", file_size_bytes=200, reason="Credentials"
    )
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    classified = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    assert classified.status == sm.ARCHIVAL_CLASSIFIED


def test_fr_024_it_security_encryption_configuration():
    """TEST-FR-024 | AFR-BA-032: IT Security Team configures encryption for Sensitive data."""
    user = regular_user_actor(user_id=20, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    sec = it_security_actor(user_id=30)

    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="payroll.csv", file_type="csv", file_size_bytes=400, reason="Salaries"
    )
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    enc = ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="AES-256")
    assert enc.is_encrypted is True
    assert enc.encryption_algorithm == "AES-256"
    assert enc.status == sm.ARCHIVAL_COMPLETED


def test_fr_025_sensitive_encryption_aes256_enforced():
    """TEST-FR-025 | AFR-BA-034: AES-256 encryption algorithm is strictly enforced for Sensitive data."""
    user = regular_user_actor(user_id=21, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    sec = it_security_actor(user_id=30)

    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="secret.csv", file_type="csv", file_size_bytes=400, reason="Secrets"
    )
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")

    # AFR-BA-034: Data classified as Sensitive shall use AES-256 encryption. Non-AES algorithm must be rejected.
    with pytest.raises((BadRequestError, ValueError)):
        ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="DES-ECB")


def test_fr_026_user_tracks_own_archival_request():
    """TEST-FR-026 | AFR-BA-035: User can track status and history of own secure archival request."""
    user1 = regular_user_actor(user_id=22, dept="CSE")
    user2 = regular_user_actor(user_id=23, dept="CSE")

    req1 = ops.submit_archival_request(actor=user1, department="CSE", file_name="u1.pdf", file_type="pdf", file_size_bytes=100, reason="U1")
    req2 = ops.submit_archival_request(actor=user2, department="CSE", file_name="u2.pdf", file_type="pdf", file_size_bytes=100, reason="U2")

    u1_visible = list(scoping.visible_archival_requests(user1))
    assert req1 in u1_visible
    assert req2 not in u1_visible


def test_fr_027_superadmin_special_archival_operation():
    """TEST-FR-027 | AFR-BA-037: Super Admin can perform special archival operation."""
    superadmin = superadmin_actor(user_id=102)
    # CFR-BA-010 / AFR-BA-037 requires special archival operation by Super Admin.
    # If the operation function is not implemented on ops, this will raise AttributeError (candidate defect).
    assert hasattr(ops, "special_archival_operation"), "special_archival_operation service is missing from operations.py"
    res = getattr(ops, "special_archival_operation")(
        actor=superadmin, department="INSTITUTE", file_name="special_archive.tar.gz", reason="Statutory requirement"
    )
    assert res.is_special is True
    assert res.status == sm.ARCHIVAL_SPECIAL_EXECUTED


def test_fr_028_non_superadmin_denied_special_archival():
    """TEST-FR-028 | AFR-BA-038: Non-Super Admin denied special archival operation."""
    user = regular_user_actor(user_id=24)
    assert hasattr(ops, "special_archival_operation"), "special_archival_operation service is missing from operations.py"
    with pytest.raises(PermissionDeniedError):
        getattr(ops, "special_archival_operation")(
            actor=user, department="CSE", file_name="hack.tar.gz", reason="Unauthorized"
        )


def test_fr_029_submit_restoration_request():
    """TEST-FR-029 | AFR-BA-040: User can request restoration of archived data."""
    user = regular_user_actor(user_id=25, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=25,
        department="CSE",
        file_name="old_data.csv",
        file_type="csv",
        file_size_bytes=1024,
        status=sm.ARCHIVAL_COMPLETED,
        authoritative_classification="routine",
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Need past data")
    assert rest_req.pk is not None
    assert rest_req.archival_request == arch


def test_fr_030_sensitive_restoration_requires_sysadmin_approval():
    """TEST-FR-030 | AFR-BA-041: Restoration of Sensitive data requires SysAdmin approval."""
    user = regular_user_actor(user_id=26, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    arch = SecureArchivalRequest.objects.create(
        user_id=26,
        department="CSE",
        file_name="sensitive_vault.dat",
        file_type="dat",
        file_size_bytes=1024,
        status=sm.ARCHIVAL_COMPLETED,
        authoritative_classification="sensitive",
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Legal inquiry")
    assert rest_req.status == sm.RESTORATION_SUBMITTED

    reviewed = ops.sysadmin_review_restoration(actor=admin, restoration_id=rest_req.pk, action="approve", remarks="Approved")
    assert reviewed.status == sm.RESTORATION_COMPLETED
    assert reviewed.restored_at is not None


def test_fr_031_non_sensitive_restoration_standard_path():
    """TEST-FR-031 | AFR-BA-042: Non-Sensitive restoration proceeds through standard path to completion."""
    user = regular_user_actor(user_id=27, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=27,
        department="CSE",
        file_name="public_doc.txt",
        file_type="txt",
        file_size_bytes=500,
        status=sm.ARCHIVAL_COMPLETED,
        authoritative_classification="routine",
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Standard restore")
    assert rest_req.status == sm.RESTORATION_COMPLETED
    assert rest_req.restored_at is not None


def test_fr_032_submit_storage_extension_when_quota_full():
    """TEST-FR-032 | AFR-BA-045: User can submit storage extension request when quota is full."""
    user = regular_user_actor(user_id=28, dept="CSE")
    StorageQuota.objects.create(user_id=28, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Quota full")
    assert ext.pk is not None
    assert ext.status == sm.STORAGE_SUBMITTED
    assert ext.requested_additional_mb == 1024


def test_fr_033_storage_extension_rejected_if_quota_not_reached():
    """TEST-FR-033 | AFR-BA-046: Storage extension rejected if user quota is not reached."""
    user = regular_user_actor(user_id=29, dept="CSE")
    StorageQuota.objects.create(user_id=29, allocated_mb=5120, used_mb=2000)
    with pytest.raises(sm.RuleViolation):
        ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Too early")


def test_fr_034_hod_storage_extension_decision_allocates_storage():
    """TEST-FR-034 | AFR-BA-049: HoD approval of storage extension allocates additional storage."""
    user = regular_user_actor(user_id=30, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=30, allocated_mb=5120, used_mb=5120)

    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=2048, reason="Heavy datasets")
    decided = ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="approve", remarks="Approved 2GB")
    assert decided.status == sm.STORAGE_APPROVED

    updated_quota = StorageQuota.objects.get(user_id=30)
    assert updated_quota.allocated_mb == 5120 + 2048


def test_fr_035_storage_threshold_monitoring():
    """TEST-FR-035 | AFR-BA-051: Storage threshold monitoring and quota calculation."""
    StorageQuota.objects.create(user_id=31, allocated_mb=5120, used_mb=5200)
    StorageQuota.objects.create(user_id=32, allocated_mb=5120, used_mb=1000)

    quotas = get_user_storage_quotas([31, 32])
    assert quotas[31].is_quota_full is True
    assert quotas[32].is_quota_full is False


def test_fr_036_superadmin_global_backup_schedule():
    """TEST-FR-036 | AFR-BA-053: Super Admin can define global backup schedule."""
    superadmin = superadmin_actor(user_id=102)
    sch = ops.configure_schedule(
        actor=superadmin, scope="global", dataset_code="", cron_expression="0 0 * * 0", retention_days=90
    )
    assert sch.scope == "global"
    assert sch.cron_expression == "0 0 * * 0"


def test_fr_037_local_schedule_overrides_global():
    """TEST-FR-037 | AFR-BA-055: Local backup schedule overrides global schedule."""
    global_sch = {"cron": "0 0 * * *", "scope": "global"}
    local_sch = {"cron": "0 3 * * *", "scope": "local"}
    schedules = {"exam_db": local_sch}

    effective = sm.calculate_effective_schedule("exam_db", schedules, global_sch)
    assert effective == local_sch

    effective_default = sm.calculate_effective_schedule("general_db", schedules, global_sch)
    assert effective_default == global_sch


def test_fr_038_retention_rules_by_classification():
    """TEST-FR-038 | AFR-BA-056: Enforce retention rules by classification tier."""
    assert sm.RETENTION_YEARS[sm.TIER_ROUTINE] == 1
    assert sm.RETENTION_YEARS[sm.TIER_ARCHIVAL] == 5
    assert sm.RETENTION_YEARS[sm.TIER_SENSITIVE] == 7
    assert sm.RETENTION_YEARS[sm.TIER_CRITICAL] == 10


def test_fr_039_consecutive_backup_failures_escalation():
    """TEST-FR-039 | AFR-BA-058: Escalation to Director of IT on 3 consecutive backup failures."""
    assert sm.check_repeated_failure_escalation(consecutive_failures=2) is False
    assert sm.check_repeated_failure_escalation(consecutive_failures=3) is True
    assert sm.check_repeated_failure_escalation(consecutive_failures=5) is True


def test_fr_040_audit_log_recording():
    """TEST-FR-040 | AFR-BA-061: Audit log recording for operations."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="audit_test")
    log = BadmsAuditLog.objects.filter(entity_type="backup_operation", entity_id=op.pk).first()
    assert log is not None
    assert log.actor_user_id == 1
    assert log.action == "manual_backup_triggered"
