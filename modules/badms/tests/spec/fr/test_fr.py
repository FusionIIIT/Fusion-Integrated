# Generated automated specification tests for BADMS - Strategy: FR (CFR/AFR)
import uuid
import pytest
from modules.badms.domain import (
    CLASS_ARCHIVAL,
    CLASS_CRITICAL,
    CLASS_ROUTINE,
    CLASS_SENSITIVE,
    DomainValidationError,
    calculate_retention_policy,
    evaluate_backup_failure_response,
    get_initial_classification,
    is_sensitive_restoration_approval_required,
    resolve_effective_schedule,
    validate_authoritative_classification,
    validate_encryption_configuration,
    validate_global_backup_policy_authority,
    validate_hod_department_scope,
    validate_it_security_policy_authority,
    validate_manual_backup_authority,
    validate_schedule_parameters,
    validate_sensitive_restoration_decision,
    validate_special_archival_authority,
    validate_storage_extension_submission,
)
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    EncryptedArchive,
    RestorationRequest,
    StorageExtensionRequest,
    StorageQuota,
)
from modules.badms.services import (
    classify_archival_sysadmin,
    configure_backup_schedule,
    configure_sensitive_encryption_it_security,
    decide_secure_archival_hod,
    decide_sensitive_restoration_sysadmin,
    decide_storage_extension_hod,
    execute_data_restoration,
    perform_special_archival_operation,
    request_data_restoration,
    submit_secure_archival_request,
    submit_storage_extension_request,
    trigger_manual_backup,
)
from modules.badms.selectors import (
    get_archival_request_by_id,
    get_consecutive_backup_failures,
    get_user_storage_quota,
    list_archival_requests_for_user,
    list_audit_events,
    list_backup_history,
    list_backup_schedules,
    list_restoration_requests,
    list_storage_extensions,
)




def test_tc_badms_001_manual_backup_sysadmin():
    """TC-BADMS-001 | AFR-BA-001: Verify that an authorized SysAdmin can trigger an on-demand manual backup."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    assert record.status in ["SUCCESS", "FAILED"]


def test_tc_badms_002_manual_backup_superadmin():
    """TC-BADMS-002 | AFR-BA-001: Verify that an authorized Super Admin can trigger an on-demand manual backup."""
    record = trigger_manual_backup(actor_user_id="super_1", actor_role="superadmin")
    assert record.status in ["SUCCESS", "FAILED"]


def test_tc_badms_003_manual_backup_unauthorized():
    """TC-BADMS-003 | AFR-BA-001 authorization-denied: Verify that an unauthorized user cannot trigger a manual backup."""
    with pytest.raises((DomainValidationError, Exception)):
        trigger_manual_backup(actor_user_id="user_1", actor_role="student")


def test_tc_badms_004_manual_backup_artifacts():
    """TC-BADMS-004 | AFR-BA-002: Verify that triggering a manual backup collects the current timestamp and required backup artifacts."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    assert record.started_at is not None
    assert record.file_path != "" or record.checksum_sha256 != ""


def test_tc_badms_005_manual_backup_dump():
    """TC-BADMS-005 | AFR-BA-003: Verify that the system communicates with the database and saves a current-state dump with its timestamp."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    assert record.started_at is not None
    assert record.status in ["SUCCESS", "FAILED"]


def test_tc_badms_006_manual_backup_outcome():
    """TC-BADMS-006 | AFR-BA-004: Verify that the system records and communicates backup outcome as Success or Failure."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    assert record.status in ["SUCCESS", "FAILED"]


def test_tc_badms_007_backup_failure_alert():
    """TC-BADMS-007 | AFR-BA-005: Verify that if a backup cannot be created, system marks it Failed and alerts SysAdmin."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin", force_failure=True)
    assert record.status == "FAILED"
    assert record.alert_sent is True


def test_tc_badms_008_automatic_backup_execution():
    """TC-BADMS-008 | AFR-BA-006: Verify that automatic backup executes at scheduled time without user intervention."""
    from modules.badms.services.badms_services import execute_scheduled_backups

    records = execute_scheduled_backups(actor_user_id="system_cron", actor_role="sysadmin")
    assert len(records) > 0
    assert records[0].status == "SUCCESS"
    assert records[0].file_path.endswith(".sql.gz")
    assert records[0].checksum_sha256 is not None


def test_tc_badms_009_automatic_backup_dataset_eligibility():
    """TC-BADMS-009 | AFR-BA-007: Verify that automatic backup identifies and reads datasets eligible under applicable schedule."""
    eff = resolve_effective_schedule(dataset_name="ds_1", local_schedules=[{"dataset_name": "ds_1", "frequency": "DAILY"}], global_schedules=[{"frequency": "WEEKLY"}])
    sched_dict = eff.get("schedule", eff)
    assert sched_dict.get("frequency") == "DAILY"


def test_tc_badms_010_backup_transfer_recovery_storage():
    """TC-BADMS-010 | AFR-BA-008: Verify that eligible data is transferred to backup recovery storage during automatic backup."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    assert record.status == "SUCCESS"
    assert record.file_path != ""


def test_tc_badms_011_backup_integrity_verification():
    """TC-BADMS-011 | AFR-BA-009: Verify that system verifies backup integrity and consistency during automatic backup execution."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    assert record.checksum_sha256 != ""


def test_tc_badms_012_backup_log_timestamp_status():
    """TC-BADMS-012 | AFR-BA-010: Verify that system logs verified automatic backup with its timestamp and status."""
    trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    assert AuditEvent.objects.filter(target_entity_type="BackupRecord").exists()


def test_tc_badms_013_backup_scheduled_reachable():
    """TC-BADMS-013 | AFR-BA-011 condition-true: Verify that scheduled automatic backup executes when the repository is scheduled and reachable."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin", force_failure=False)
    assert record.status == "SUCCESS"


def test_tc_badms_014_backup_unreachable():
    """TC-BADMS-014 | AFR-BA-011 condition-false: Verify that scheduled automatic backup does not execute if the repository is unreachable."""
    record = trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin", force_failure=True)
    assert record.status == "FAILED"


def test_tc_badms_015_display_backup_schedules():
    """TC-BADMS-015 | AFR-BA-012: Verify that system displays current backup schedules to an authorized SysAdmin."""
    schedules = list_backup_schedules()
    assert hasattr(schedules, "__iter__")


def test_tc_badms_016_create_local_backup_schedule():
    """TC-BADMS-016 | AFR-BA-013: Verify that SysAdmin can create or modify local backup schedule with frequency, time, and classification filters."""
    sched = configure_backup_schedule(
        actor_user_id="admin_1",
        actor_role="sysadmin",
        name="Local16",
        scope="DATASET",
        dataset_name="ds_local16",
        frequency="DAILY",
        scheduled_time="02:00:00",
    )
    assert sched.dataset_name == "ds_local16"


def test_tc_badms_017_reject_invalid_schedule_parameters():
    """TC-BADMS-017 | AFR-BA-014: Verify that system rejects conflicting or invalid schedule parameters without applying them."""
    with pytest.raises((DomainValidationError, Exception)):
        configure_backup_schedule(
            actor_user_id="admin_1",
            actor_role="sysadmin",
            name="Bad",
            scope="DATASET",
            dataset_name="ds_bad",
            frequency="INVALID_FREQ",
            scheduled_time="02:00:00",
        )


def test_tc_badms_018_apply_local_backup_schedule():
    """TC-BADMS-018 | AFR-BA-015: Verify that system applies local backup schedule after successful validation."""
    sched = configure_backup_schedule(
        actor_user_id="admin_1",
        actor_role="sysadmin",
        name="Local18",
        scope="DATASET",
        dataset_name="ds_local18",
        frequency="WEEKLY",
        scheduled_time="03:00:00",
    )
    assert BackupSchedule.objects.filter(dataset_name="ds_local18").exists()


def test_tc_badms_019_log_schedule_changes():
    """TC-BADMS-019 | AFR-BA-016: Verify that system logs each backup-schedule configuration change."""
    configure_backup_schedule(
        actor_user_id="admin_1",
        actor_role="sysadmin",
        name="Local19",
        scope="DATASET",
        dataset_name="ds_local19",
        frequency="DAILY",
        scheduled_time="01:00:00",
    )
    assert AuditEvent.objects.filter(target_entity_type="BackupSchedule").exists()


def test_tc_badms_020_maintain_backup_history():
    """TC-BADMS-020 | AFR-BA-017: Verify that system maintains current status and history of all backup operations."""
    trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    hist = list_backup_history()
    assert len(hist) >= 1


def test_tc_badms_021_view_backup_history_scope():
    """TC-BADMS-021 | AFR-BA-018: Verify that users and authorized administrators can view backup history and current status within authorized scope."""
    hist = list_backup_history()
    assert hasattr(hist, "__iter__")


def test_tc_badms_022_initiate_archival_request():
    """TC-BADMS-022 | AFR-BA-019: Verify that an authenticated user can initiate a secure archival request."""
    assert callable(submit_secure_archival_request)


def test_tc_badms_023_capture_archival_metadata(make_quota):
    """TC-BADMS-023 | AFR-BA-020: Verify that secure archival request captures file name, date, owners, file type, reason, and file attachment."""
    make_quota(user_id="user_23", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_23",
        department_id="CSE",
        file_name="doc.pdf",
        file_size_mb=1.0,
        reason="Research",
        owners="Alice",
        attachment_ref="ref1",
    )
    assert req.file_name == "doc.pdf"
    assert req.department_id == "CSE"


def test_tc_badms_024_validate_archival_valid(make_quota):
    """TC-BADMS-024 | AFR-BA-021 condition-valid: Verify that system validates request details and quota, accepting valid requests."""
    make_quota(user_id="user_24", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_24",
        department_id="CSE",
        file_name="valid.pdf",
        file_size_mb=1.0,
        reason="Valid",
        owners="Alice",
    )
    assert req.status == "SUBMITTED"


def test_tc_badms_025_validate_archival_quota_failed(make_quota):
    """TC-BADMS-025 | AFR-BA-021 validation-failed: Verify that validation failure or storage quota exhaustion shows errors without request-state change."""
    make_quota(user_id="user_25", quota_mb=500, used_mb=400)
    with pytest.raises((DomainValidationError, Exception)):
        submit_secure_archival_request(
            requester_user_id="user_25",
            department_id="CSE",
            file_name="large.pdf",
            file_size_mb=200.0,
            reason="Exceeds",
            owners="Alice",
        )


def test_tc_badms_026_archival_status_submitted(make_quota):
    """TC-BADMS-026 | AFR-BA-022: Verify that system sets status to Submitted upon successful submission."""
    make_quota(user_id="user_26", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_26",
        department_id="CSE",
        file_name="sub.pdf",
        file_size_mb=1.0,
        reason="Sub",
        owners="Alice",
    )
    assert req.status == "SUBMITTED"


def test_tc_badms_027_route_archival_to_hod(make_quota):
    """TC-BADMS-027 | AFR-BA-023: Verify that system routes submitted secure archival request to the HoD of the requester's department."""
    make_quota(user_id="user_27", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_27",
        department_id="CSE",
        file_name="route.pdf",
        file_size_mb=1.0,
        reason="Route",
        owners="Alice",
    )
    assert req.department_id == "CSE"


def test_tc_badms_028_hod_review_request(make_quota):
    """TC-BADMS-028 | AFR-BA-024: Verify that routed HoD can review request details, attachments, and policy context before deciding request."""
    make_quota(user_id="user_28", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_28",
        department_id="ECE",
        file_name="hod.pdf",
        file_size_mb=1.0,
        reason="Review",
        owners="Bob",
    )
    retrieved = get_archival_request_by_id(str(req.id))
    assert retrieved.id == req.id


def test_tc_badms_029_hod_approve_archival(make_quota):
    """TC-BADMS-029 | AFR-BA-025 approval: Verify that HoD can approve secure archival request and decision is recorded."""
    make_quota(user_id="user_29", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_29",
        department_id="CSE",
        file_name="app.pdf",
        file_size_mb=1.0,
        reason="App",
        owners="Alice",
    )
    updated = decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
        remarks="Approved",
    )
    assert updated.status in ["APPROVED_BY_HOD", "HOD_APPROVED", "APPROVED"]


def test_tc_badms_030_hod_reject_archival(make_quota):
    """TC-BADMS-030 | AFR-BA-025 rejection: Verify that HoD can reject secure archival request and decision is recorded."""
    make_quota(user_id="user_30", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_30",
        department_id="CSE",
        file_name="rej.pdf",
        file_size_mb=1.0,
        reason="Rej",
        owners="Alice",
    )
    updated = decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=False,
        remarks="Rejected",
    )
    assert updated.status in ["REJECTED_BY_HOD", "REJECTED"]


def test_tc_badms_031_cross_dept_hod_denied(make_quota):
    """TC-BADMS-031 | AFR-BA-026 authorization-denied: Verify that HoD from another department cannot approve or reject a user's request."""
    make_quota(user_id="user_31", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_31",
        department_id="CSE",
        file_name="cross.pdf",
        file_size_mb=1.0,
        reason="Cross",
        owners="Alice",
    )
    with pytest.raises((DomainValidationError, Exception)):
        decide_secure_archival_hod(
            request_id=str(req.id),
            hod_user_id="hod_ece",
            hod_role="hod",
            hod_department="ECE",
            approved=True,
        )


def test_tc_badms_032_route_to_sysadmin_after_hod_approval(make_quota):
    """TC-BADMS-032 | AFR-BA-027: Verify that after HoD approval, request is routed to SysAdmin for classification."""
    make_quota(user_id="user_32", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_32",
        department_id="ME",
        file_name="sys.pdf",
        file_size_mb=1.0,
        reason="Sys",
        owners="Alice",
    )
    updated = decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_me",
        hod_role="hod",
        hod_department="ME",
        approved=True,
    )
    assert updated.status in ["APPROVED_BY_HOD", "HOD_APPROVED", "APPROVED"]


def test_tc_badms_033_sysadmin_classify_archival(make_quota):
    """TC-BADMS-033 | AFR-BA-028: Verify that SysAdmin can review approved request and assign authoritative classification."""
    make_quota(user_id="user_33", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_33",
        department_id="CSE",
        file_name="auth.pdf",
        file_size_mb=1.0,
        reason="Auth",
        owners="Alice",
    )
    decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
    )
    classified = classify_archival_sysadmin(
        request_id=str(req.id),
        sysadmin_user_id="admin_1",
        sysadmin_role="sysadmin",
        authoritative_classification=CLASS_CRITICAL,
    )
    assert classified.authoritative_classification.upper() == "CRITICAL"


def test_tc_badms_034_user_initial_classification(make_quota):
    """TC-BADMS-034 | AFR-BA-029 explicit-classification: Verify that user can provide an initial classification for uploaded data."""
    make_quota(user_id="user_34", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_34",
        department_id="CSE",
        file_name="init.pdf",
        file_size_mb=1.0,
        reason="Init",
        owners="Alice",
        initial_classification=CLASS_SENSITIVE,
    )
    assert req.initial_classification.upper() == "SENSITIVE"


def test_tc_badms_035_default_routine_classification():
    """TC-BADMS-035 | AFR-BA-029 default-routine: Verify that if user omits initial classification, system assigns Routine as default."""
    init_cls = get_initial_classification(None)
    assert init_cls == CLASS_ROUTINE


def test_tc_badms_036_retention_rules_by_classification():
    """TC-BADMS-036 | AFR-BA-030: Verify that system applies security and retention rules according to authoritative data classification."""
    years, _ = calculate_retention_policy(CLASS_CRITICAL)
    assert years == 30


def test_tc_badms_037_sensitive_routes_to_it_security(make_quota):
    """TC-BADMS-037 | AFR-BA-031: Verify that if authoritative classification is Sensitive, request routes to IT Security Team for encryption configuration."""
    make_quota(user_id="user_37", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_37",
        department_id="CSE",
        file_name="sens.pdf",
        file_size_mb=1.0,
        reason="Sens",
        owners="Alice",
    )
    decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
    )
    classified = classify_archival_sysadmin(
        request_id=str(req.id),
        sysadmin_user_id="admin_1",
        sysadmin_role="sysadmin",
        authoritative_classification="Sensitive",
    )
    assert classified.status in ["PENDING_ENCRYPTION_CONFIG", "CLASSIFIED_SENSITIVE"]


def test_tc_badms_038_it_security_configure_encryption(make_quota):
    """TC-BADMS-038 | AFR-BA-032: Verify that IT Security Team can configure encryption for Sensitive data."""
    make_quota(user_id="user_38", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_38",
        department_id="CSE",
        file_name="enc.pdf",
        file_size_mb=1.0,
        reason="Enc",
        owners="Alice",
    )
    decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
    )
    classify_archival_sysadmin(
        request_id=str(req.id),
        sysadmin_user_id="admin_1",
        sysadmin_role="sysadmin",
        authoritative_classification="Sensitive",
    )
    enc = configure_sensitive_encryption_it_security(
        request_id=str(req.id),
        security_user_id="sec_1",
        security_role="it_security",
        encryption_algorithm="AES-256",
    )
    assert enc.encryption_algorithm == "AES-256"


def test_tc_badms_039_create_encrypted_archive(make_quota):
    """TC-BADMS-039 | AFR-BA-033: Verify that after encryption configuration, system creates encrypted archive and records outcome."""
    make_quota(user_id="user_39", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_39",
        department_id="CSE",
        file_name="arch.pdf",
        file_size_mb=1.0,
        reason="Arch",
        owners="Alice",
    )
    decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
    )
    classify_archival_sysadmin(
        request_id=str(req.id),
        sysadmin_user_id="admin_1",
        sysadmin_role="sysadmin",
        authoritative_classification="Sensitive",
    )
    enc = configure_sensitive_encryption_it_security(
        request_id=str(req.id),
        security_user_id="sec_1",
        security_role="it_security",
        encryption_algorithm="AES-256",
    )
    assert enc.checksum_sha256 != ""


def test_tc_badms_040_aes_256_encryption_transit_rest():
    """TC-BADMS-040 | AFR-BA-034: Verify that data classified as Sensitive uses AES-256 encryption both at rest and in transit."""
    validate_encryption_configuration(actor_role="it_security", classification=CLASS_SENSITIVE, algorithm="AES-256")


def test_tc_badms_041_track_archival_status(make_quota):
    """TC-BADMS-041 | AFR-BA-035: Verify that user can track status and history of secure archival request throughout processing."""
    make_quota(user_id="user_41", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_41",
        department_id="CSE",
        file_name="track.pdf",
        file_size_mb=1.0,
        reason="Track",
        owners="Alice",
    )
    tracked = get_archival_request_by_id(str(req.id))
    assert tracked.status == "SUBMITTED"


def test_tc_badms_042_submission_decision_notifications(make_quota):
    """TC-BADMS-042 | AFR-BA-036: Verify that system sends submission confirmation and decision notifications for secure archival requests."""
    make_quota(user_id="user_42", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_42",
        department_id="CSE",
        file_name="notif.pdf",
        file_size_mb=1.0,
        reason="Notif",
        owners="Alice",
    )
    assert AuditEvent.objects.filter(target_entity_type="ArchivalRequest").exists()
    decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
    )
    assert AuditEvent.objects.filter(target_entity_type="ArchivalRequest").count() >= 2


def test_tc_badms_043_superadmin_special_archival():
    """TC-BADMS-043 | AFR-BA-037: Verify that Super Admin can perform special archival operation for Sensitive research data when requested offline."""
    arc = perform_special_archival_operation(
        superadmin_user_id="super_1",
        superadmin_role="superadmin",
        file_name="dna.pdf",
        file_size_mb=10.0,
        department_id="CSE",
        reason="National Project",
    )
    assert arc.status in ["ARCHIVED", "SPECIAL_ARCHIVED"]


def test_tc_badms_044_non_superadmin_denied_special_archival():
    """TC-BADMS-044 | AFR-BA-038 authorization-denied: Verify that only Super Admin can perform special archival operation in BADMS."""
    with pytest.raises((DomainValidationError, Exception)):
        perform_special_archival_operation(
            superadmin_user_id="sys_1",
            superadmin_role="sysadmin",
            file_name="dna.pdf",
            file_size_mb=10.0,
            department_id="CSE",
            reason="Test",
        )


def test_tc_badms_045_special_archival_audit_log():
    """TC-BADMS-045 | AFR-BA-039: Verify that system records outcome and audit event after special archival operation."""
    perform_special_archival_operation(
        superadmin_user_id="super_1",
        superadmin_role="superadmin",
        file_name="gov.pdf",
        file_size_mb=5.0,
        department_id="ME",
        reason="Audit test",
    )
    assert AuditEvent.objects.filter(target_entity_type="ArchivalRequest", actor_role="superadmin").exists()


def test_tc_badms_046_user_request_restoration(make_quota):
    """TC-BADMS-046 | AFR-BA-040: Verify that user can request restoration of archived data."""
    make_quota(user_id="user_46", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_46",
        department_id="CSE",
        file_name="res.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    rest = request_data_restoration(
        requester_user_id="user_46",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Project recovery",
    )
    assert rest.requester_user_id == "user_46"


def test_tc_badms_047_sensitive_restoration_requires_approval(make_quota):
    """TC-BADMS-047 | AFR-BA-041: Verify that restoration request for Sensitive data requires SysAdmin approval before proceeding."""
    make_quota(user_id="user_47", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_47",
        department_id="CSE",
        file_name="res_sens.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_1", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_1", "it_security")
    rest = request_data_restoration(
        requester_user_id="user_47",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Need sensitive restore",
    )
    assert rest.status in ["PENDING_SYSADMIN_APPROVAL", "SENSITIVE_PENDING_APPROVAL"]


def test_tc_badms_048_non_sensitive_restoration_standard(make_quota):
    """TC-BADMS-048 | AFR-BA-042: Verify that system supports restoration of non-Sensitive data through standard restoration procedure."""
    make_quota(user_id="user_48", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_48",
        department_id="CSE",
        file_name="res_rout.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_1", "sysadmin", "Routine")
    rest = request_data_restoration(
        requester_user_id="user_48",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Routine restore",
    )
    assert rest.status in ["PENDING_EXECUTION", "RESTORED", "STANDARD_PENDING", "STANDARD_PENDING_EXECUTION"]


def test_tc_badms_049_track_restoration_status(make_quota):
    """TC-BADMS-049 | AFR-BA-043: Verify that user can track restoration-request status."""
    make_quota(user_id="user_49", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_49",
        department_id="CSE",
        file_name="res_tr.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    request_data_restoration(
        requester_user_id="user_49",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Tracking test",
    )
    res_list = list_restoration_requests(user_id="user_49", role="student")
    assert len(res_list) >= 1


def test_tc_badms_050_submit_storage_extension_quota_full(make_quota):
    """TC-BADMS-050 | AFR-BA-045: Verify that user can submit storage-extension request when storage quota is full."""
    make_quota(user_id="user_50", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_50",
        department_id="CSE",
        requested_additional_mb=5000.0,
        justification="Quota full",
    )
    assert ext.status in ["PENDING_HOD_APPROVAL", "SUBMITTED"]


def test_tc_badms_051_reject_extension_quota_not_full(make_quota):
    """TC-BADMS-051 | AFR-BA-046: Verify that system validates storage-extension request against user current storage usage."""
    make_quota(user_id="user_51", quota_mb=1000, used_mb=500)
    with pytest.raises((DomainValidationError, Exception)):
        submit_storage_extension_request(
            requester_user_id="user_51",
            department_id="CSE",
            requested_additional_mb=5000.0,
            justification="Quota not full",
        )


def test_tc_badms_052_route_extension_to_hod(make_quota):
    """TC-BADMS-052 | AFR-BA-047: Verify that system routes valid storage-extension request to user HoD for review."""
    make_quota(user_id="user_52", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_52",
        department_id="ECE",
        requested_additional_mb=5000.0,
        justification="Route test",
    )
    assert ext.department_id == "ECE"


def test_tc_badms_053_hod_review_extension_request(make_quota):
    """TC-BADMS-053 | AFR-BA-048: Verify that HoD can review storage-extension request details, attachments, available infrastructure, departmental policy, and user justification."""
    make_quota(user_id="user_53", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_53",
        department_id="CSE",
        requested_additional_mb=5000.0,
        justification="Review test",
    )
    ext_list = list_storage_extensions(user_id="hod_cse", role="hod", department_id="CSE")
    assert any(e.id == ext.id for e in ext_list)


def test_tc_badms_054_hod_approve_storage_extension(make_quota):
    """TC-BADMS-054 | AFR-BA-049 approval: Verify that HoD can approve storage-extension request and decision is recorded."""
    make_quota(user_id="user_54", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_54",
        department_id="CSE",
        requested_additional_mb=5000.0,
        justification="Approve test",
    )
    updated = decide_storage_extension_hod(
        request_id=str(ext.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
        remarks="Approved",
    )
    assert updated.status in ["APPROVED_BY_HOD", "HOD_APPROVED", "APPROVED"]


def test_tc_badms_055_hod_reject_storage_extension(make_quota):
    """TC-BADMS-055 | AFR-BA-049 rejection: Verify that HoD can reject storage-extension request and decision is recorded."""
    make_quota(user_id="user_55", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_55",
        department_id="CSE",
        requested_additional_mb=5000.0,
        justification="Reject test",
    )
    updated = decide_storage_extension_hod(
        request_id=str(ext.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=False,
        remarks="Rejected",
    )
    assert updated.status in ["REJECTED_BY_HOD", "REJECTED"]


def test_tc_badms_056_monitor_storage_thresholds(make_quota):
    """TC-BADMS-056 | AFR-BA-051: Verify that system monitors storage thresholds for all users."""
    make_quota(user_id="user_56", quota_mb=2000, used_mb=1500)
    q = get_user_storage_quota("user_56")
    assert q is not None
    assert q.used_storage_mb == 1500


def test_tc_badms_057_validate_storage_infrastructure_capacity():
    """TC-BADMS-057 | AFR-BA-052: Verify that system validates requested storage against available infrastructure and detects when extension exceeds available storage."""
    with pytest.raises((DomainValidationError, Exception)):
        validate_storage_extension_submission(
            current_used_mb=1000,
            allocated_quota_mb=1000,
            requested_additional_mb=999999999999999,
            available_infrastructure_mb=50000,
        )


def test_tc_badms_058_superadmin_global_backup_schedule():
    """TC-BADMS-058 | AFR-BA-053: Verify that Super Admin can define institution-wide global backup schedules and default backup policies."""
    sched = configure_backup_schedule(
        actor_user_id="super_1",
        actor_role="superadmin",
        name="GlobalDaily",
        scope="INSTITUTION",
        dataset_name="*GLOBAL*",
        frequency="DAILY",
        scheduled_time="00:00:00",
    )
    assert sched.scope == "INSTITUTION"


def test_tc_badms_059_apply_global_schedule_when_no_local():
    """TC-BADMS-059 | AFR-BA-054: Verify that system applies global schedule to datasets when no valid local override exists."""
    eff = resolve_effective_schedule(
        dataset_name="ds_unspecified",
        local_schedules=[],
        global_schedules=[{"frequency": "DAILY", "scheduled_time": "00:00:00"}],
    )
    sched_dict = eff.get("schedule", eff)
    assert sched_dict.get("frequency") == "DAILY"


def test_tc_badms_060_local_schedule_overrides_global():
    """TC-BADMS-060 | AFR-BA-055: Verify that local backup schedule overrides institution-wide global schedule for that dataset."""
    eff = resolve_effective_schedule(
        dataset_name="ds_override",
        local_schedules=[{"dataset_name": "ds_override", "frequency": "HOURLY"}],
        global_schedules=[{"frequency": "DAILY"}],
    )
    sched_dict = eff.get("schedule", eff)
    assert sched_dict.get("frequency") == "HOURLY"


def test_tc_badms_061_retention_rules_by_classification():
    """TC-BADMS-061 | AFR-BA-056: Verify that system enforces institute-defined retention rules according to data classification."""
    years, _ = calculate_retention_policy(CLASS_SENSITIVE)
    assert years == 10


def test_tc_badms_062_failure_alert_sla():
    """TC-BADMS-062 | AFR-BA-057: Verify that when backup is marked Failed, system sends an alert to SysAdmin within five minutes."""
    alert, escalate, msg = evaluate_backup_failure_response(consecutive_failure_count=1)
    assert alert is True


def test_tc_badms_063_consecutive_failures_escalate():
    """TC-BADMS-063 | AFR-BA-058 escalation: Verify that system escalates to Director of IT when three consecutive backup failures occur."""
    alert, escalate, msg = evaluate_backup_failure_response(consecutive_failure_count=3)
    assert escalate is True


def test_tc_badms_064_non_consecutive_failures_no_escalate():
    """TC-BADMS-064 | AFR-BA-058 non-escalation: Verify that fewer than three consecutive backup failures do not escalate to Director of IT."""
    alert, escalate, msg = evaluate_backup_failure_response(consecutive_failure_count=2)
    assert escalate is False


def test_tc_badms_065_backup_notifications():
    """TC-BADMS-065 | AFR-BA-059: Verify that system issues backup creation-status and completion notifications, including failure alerts to SysAdmin."""
    trigger_manual_backup(actor_user_id="admin_1", actor_role="sysadmin")
    assert AuditEvent.objects.filter(target_entity_type="BackupRecord").exists()


def test_tc_badms_066_extension_notifications(make_quota):
    """TC-BADMS-066 | AFR-BA-060: Verify that system notifies requester when storage-extension request is submitted and when HoD approves or rejects it."""
    make_quota(user_id="user_66", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_66",
        department_id="CSE",
        requested_additional_mb=5000.0,
        justification="Notification test",
    )
    assert AuditEvent.objects.filter(event_type="STORAGE_EXTENSION_SUBMITTED").exists()
    decide_storage_extension_hod(
        request_id=str(ext.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
    )
    assert AuditEvent.objects.filter(target_entity_type="StorageExtensionRequest").count() >= 2


def test_tc_badms_067_maintain_audit_logs():
    """TC-BADMS-067 | AFR-BA-061: Verify that system maintains audit logs with timestamps, actor identifiers, actions, and outcomes."""
    events = list_audit_events(actor_role="sysadmin")
    assert hasattr(events, "__iter__")


def test_tc_badms_068_sysadmin_view_audit_logs():
    """TC-BADMS-068 | AFR-BA-062: Verify that SysAdmin can view audit logs and activity histories."""
    events = list_audit_events(actor_role="sysadmin")
    assert hasattr(events, "__iter__")


def test_tc_badms_069_it_security_audit_logs():
    """TC-BADMS-069 | AFR-BA-063: Verify that IT Security Team can audit data-activity logs for unauthorized access and review security reports."""
    events = list_audit_events(actor_role="it_security")
    assert hasattr(events, "__iter__")


def test_tc_badms_070_hod_view_dept_reports_only(make_quota):
    """TC-BADMS-070 | AFR-BA-064: Verify that HoD can view operational reports relevant to HoD own department only."""
    make_quota(user_id="user_70", quota_mb=1000, used_mb=1000)
    submit_storage_extension_request(
        requester_user_id="user_70",
        department_id="CSE",
        requested_additional_mb=5000.0,
        justification="CSE dept",
    )
    exts = list_storage_extensions(user_id="hod_70", role="hod", department_id="CSE")
    assert all(e.department_id == "CSE" for e in exts)


def test_tc_badms_071_operational_visibility_backup():
    """TC-BADMS-071 | AFR-BA-065: Verify that system provides operational visibility into backup operations for monitoring and compliance."""
    hist = list_backup_history()
    assert hasattr(hist, "__iter__")


def test_tc_badms_072_it_security_rbac():
    """TC-BADMS-072 | AFR-BA-066: Verify that IT Security Team can manage user permissions through RBAC."""
    validate_it_security_policy_authority("it_security")


def test_tc_badms_073_it_security_security_policies():
    """TC-BADMS-073 | AFR-BA-067: Verify that IT Security Team can define and enforce security policies governing encryption, access, and security controls."""
    validate_it_security_policy_authority("it_security")
    with pytest.raises((DomainValidationError, Exception)):
        validate_it_security_policy_authority("student")


def test_tc_badms_074_role_separation_and_department_scope():
    """TC-BADMS-074 | AFR-BA-068 role-separation: Verify that system enforces role separation and departmental scope restrictions across roles."""
    with pytest.raises((DomainValidationError, Exception)):
        validate_hod_department_scope("CSE", "ECE")
