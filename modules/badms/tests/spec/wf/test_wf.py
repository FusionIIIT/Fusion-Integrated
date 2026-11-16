# Generated automated specification tests for BADMS - Strategy: WF (Workflows)
import uuid
import pytest
from django.utils import timezone
from modules.badms.domain import (
    CLASS_ARCHIVAL,
    CLASS_CRITICAL,
    CLASS_ROUTINE,
    CLASS_SENSITIVE,
    ARCHIVAL_CLASSIFIED_NON_SENSITIVE,
    ARCHIVAL_CLASSIFIED_SENSITIVE,
    ARCHIVAL_ENCRYPTED,
    ARCHIVAL_HOD_APPROVED,
    ARCHIVAL_NOT_SUBMITTED,
    ARCHIVAL_REJECTED,
    ARCHIVAL_SPECIAL,
    ARCHIVAL_SUBMITTED,
    EXT_APPROVED,
    EXT_NOT_SUBMITTED,
    EXT_REJECTED,
    EXT_SUBMITTED,
    RESTORE_APPROVED_FOR_EXECUTION,
    RESTORE_COMPLETED,
    RESTORE_NOT_REQUESTED,
    RESTORE_REJECTED,
    RESTORE_SENSITIVE_PENDING,
    RESTORE_STANDARD_PENDING,
    ArchivalWorkflowEngine,
    RestorationWorkflowEngine,
    StorageExtensionWorkflowEngine,
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


def test_tc_badms_301_archival_hod_rejection_path(make_quota):
    """TC-BADMS-301 | CW-BA-01 Path 1 / BW-BA-01: User submit -> HoD reject."""
    make_quota(user_id="user_301", quota_mb=1000, department_id="CS")
    # Step 1: Submit
    req = submit_secure_archival_request(
        requester_user_id="user_301",
        department_id="CS",
        file_name="research_dataset_2026.tar.gz",
        file_size_mb=10.0,
        reason="Research archive",
    )
    assert req.status in [ARCHIVAL_SUBMITTED, "SUBMITTED"]

    # Step 2: HoD Reject
    dec = decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cs",
        hod_role="hod",
        hod_department="CS",
        approved=False,
        remarks="Insufficient justification",
    )
    assert dec.status in [ARCHIVAL_REJECTED, "REJECTED"]


def test_tc_badms_302_archival_hod_approval_non_sensitive(make_quota):
    """TC-BADMS-302 | CW-BA-01 Path 2 / BW-BA-02: User submit -> HoD approve -> SysAdmin Non-Sensitive."""
    make_quota(user_id="user_302", quota_mb=1000, department_id="EE")
    req = submit_secure_archival_request(
        requester_user_id="user_302",
        department_id="EE",
        file_name="lab_measurements.csv",
        file_size_mb=5.0,
        reason="Lab data",
    )
    assert req.status in [ARCHIVAL_SUBMITTED, "SUBMITTED"]

    dec = decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_ee",
        hod_role="hod",
        hod_department="EE",
        approved=True,
    )
    assert dec.status in [ARCHIVAL_HOD_APPROVED, "HOD_APPROVED", "APPROVED"]

    classified = classify_archival_sysadmin(
        request_id=str(req.id),
        sysadmin_user_id="admin_302",
        sysadmin_role="sysadmin",
        authoritative_classification=CLASS_ROUTINE,
    )
    assert classified.status in [ARCHIVAL_CLASSIFIED_NON_SENSITIVE, "CLASSIFIED_NON_SENSITIVE"]


def test_tc_badms_303_archival_sensitive_encrypted_path(make_quota):
    """TC-BADMS-303 | CW-BA-01 Path 3 / BW-BA-03: User submit -> HoD approve -> SysAdmin Sensitive -> IT Security AES-256."""
    make_quota(user_id="user_303", quota_mb=1000, department_id="ME")
    req = submit_secure_archival_request(
        requester_user_id="user_303",
        department_id="ME",
        file_name="turbine_design.cad",
        file_size_mb=25.0,
        reason="Proprietary design",
    )
    dec = decide_secure_archival_hod(str(req.id), "hod_me", "hod", "ME", True)
    classified = classify_archival_sysadmin(str(req.id), "admin_303", "sysadmin", CLASS_SENSITIVE)
    assert classified.status in [ARCHIVAL_CLASSIFIED_SENSITIVE, "CLASSIFIED_SENSITIVE", "PENDING_ENCRYPTION_CONFIG"]

    archive = configure_sensitive_encryption_it_security(
        request_id=str(req.id),
        security_user_id="sec_303",
        security_role="it_security",
        encryption_algorithm="AES-256",
    )
    assert archive.encryption_algorithm == "AES-256"
    assert archive.checksum_sha256 != ""
    req.refresh_from_db()
    assert req.status in [ARCHIVAL_ENCRYPTED, "ENCRYPTED"]


def test_tc_badms_304_archival_submission_validation_guard(make_quota):
    """TC-BADMS-304 | CW-BA-01 Transition 1 Guard Unsatisfied: Missing metadata or quota exceeded."""
    make_quota(user_id="user_304", quota_mb=50, used_mb=45)
    with pytest.raises(DomainValidationError):
        submit_secure_archival_request(
            requester_user_id="user_304",
            department_id="CS",
            file_name="large_file.zip",
            file_size_mb=100.0,
            reason="Exceeds quota",
        )


def test_tc_badms_305_archival_submission_default_routine(make_quota):
    """TC-BADMS-305 | CW-BA-01 Transition 1 Guard Default: Omitted initial classification defaults to Routine."""
    make_quota(user_id="user_305", quota_mb=1000, department_id="Math")
    req = submit_secure_archival_request(
        requester_user_id="user_305",
        department_id="Math",
        file_name="topology.pdf",
        file_size_mb=2.0,
        reason="Lecture notes",
        initial_classification="",
    )
    assert req.initial_classification == CLASS_ROUTINE
    assert req.status in [ARCHIVAL_SUBMITTED, "SUBMITTED"]


def test_tc_badms_306_archival_decision_cross_department_guard(make_quota):
    """TC-BADMS-306 | CW-BA-01 Decision Point HoD Authorization Guard: Cross-department HoD rejected."""
    make_quota(user_id="user_306", quota_mb=1000, department_id="CS")
    req = submit_secure_archival_request("user_306", "CS", "file_306.pdf", 1.0, "Reason")
    with pytest.raises(DomainValidationError):
        decide_secure_archival_hod(str(req.id), "hod_physics", "hod", "Physics", True)


def test_tc_badms_307_archival_classification_role_guard(make_quota):
    """TC-BADMS-307 | CW-BA-01 Decision Point SysAdmin Authorization Guard: Non-SysAdmin cannot classify."""
    make_quota(user_id="user_307", quota_mb=1000, department_id="CS")
    req = submit_secure_archival_request("user_307", "CS", "file_307.pdf", 1.0, "Reason")
    decide_secure_archival_hod(str(req.id), "hod_cs", "hod", "CS", True)
    with pytest.raises(DomainValidationError):
        classify_archival_sysadmin(str(req.id), "student_307", "student", CLASS_CRITICAL)


def test_tc_badms_308_archival_encryption_algorithm_guard():
    """TC-BADMS-308 | CW-BA-01 Transition 6 Guard Unsatisfied: Weak or invalid encryption rejected."""
    with pytest.raises(DomainValidationError):
        validate_encryption_configuration(actor_role="it_security", classification=CLASS_SENSITIVE, algorithm="DES-WEAK")


def test_tc_badms_309_archival_encryption_role_guard(make_quota):
    """TC-BADMS-309 | CW-BA-01 Transition 6 Authorization Guard: SysAdmin cannot configure encryption."""
    make_quota(user_id="user_309", quota_mb=1000, department_id="ME")
    req = submit_secure_archival_request("user_309", "ME", "file_309.pdf", 1.0, "Reason")
    decide_secure_archival_hod(str(req.id), "hod_me", "hod", "ME", True)
    classify_archival_sysadmin(str(req.id), "admin_309", "sysadmin", CLASS_SENSITIVE)
    with pytest.raises(DomainValidationError):
        configure_sensitive_encryption_it_security(str(req.id), "admin_309", "sysadmin", "AES-256")


def test_tc_badms_310_storage_extension_hod_rejection(make_quota):
    """TC-BADMS-310 | CW-BA-02 Path 1 / BW-BA-04: User submit -> HoD reject."""
    make_quota(user_id="user_310", quota_mb=1000, used_mb=1000, department_id="Civil")
    ext = submit_storage_extension_request(
        requester_user_id="user_310",
        department_id="Civil",
        requested_additional_mb=500.0,
        justification="Structural modeling simulation output",
    )
    assert ext.status in [EXT_SUBMITTED, "SUBMITTED"]

    dec = decide_storage_extension_hod(
        request_id=str(ext.id),
        hod_user_id="hod_civil",
        hod_role="hod",
        hod_department="Civil",
        approved=False,
        remarks="Exceeds department allocated infrastructure",
    )
    assert dec.status in [EXT_REJECTED, "REJECTED"]


def test_tc_badms_311_storage_extension_hod_approval(make_quota):
    """TC-BADMS-311 | CW-BA-02 Path 2 / BW-BA-05: User submit -> HoD approve."""
    make_quota(user_id="user_311", quota_mb=1000, used_mb=1000, department_id="Aero")
    ext = submit_storage_extension_request(
        requester_user_id="user_311",
        department_id="Aero",
        requested_additional_mb=500.0,
        justification="Wind tunnel telemetry",
    )
    assert ext.status in [EXT_SUBMITTED, "SUBMITTED"]

    dec = decide_storage_extension_hod(
        request_id=str(ext.id),
        hod_user_id="hod_aero",
        hod_role="hod",
        hod_department="Aero",
        approved=True,
    )
    assert dec.status in [EXT_APPROVED, "APPROVED"]


def test_tc_badms_312_storage_extension_submission_quota_not_full(make_quota):
    """TC-BADMS-312 | CW-BA-02 Transition 1 Guard Unsatisfied: Quota not full rejected."""
    make_quota(user_id="user_312", quota_mb=1000, used_mb=300, department_id="CS")
    with pytest.raises(DomainValidationError):
        submit_storage_extension_request("user_312", "CS", 500.0, "Future needs")


def test_tc_badms_313_storage_extension_decision_role_guard(make_quota):
    """TC-BADMS-313 | CW-BA-02 Decision Point HoD Authorization Guard: SysAdmin cannot approve extension."""
    make_quota(user_id="user_313", quota_mb=1000, used_mb=1000, department_id="CS")
    ext = submit_storage_extension_request("user_313", "CS", 500.0, "Research quota")
    with pytest.raises(DomainValidationError):
        decide_storage_extension_hod(str(ext.id), "admin_313", "sysadmin", "CS", True)


def test_tc_badms_314_restoration_standard_path(make_quota):
    """TC-BADMS-314 | CW-BA-03 Path 1 / BW-BA-06: Non-Sensitive standard restoration path."""
    make_quota(user_id="user_314", quota_mb=1000, department_id="CS")
    req = submit_secure_archival_request("user_314", "CS", "data_314.tar", 5.0, "Archive")
    decide_secure_archival_hod(str(req.id), "hod_cs", "hod", "CS", True)
    classify_archival_sysadmin(str(req.id), "admin_314", "sysadmin", CLASS_ROUTINE)

    rest = request_data_restoration("user_314", "CS", str(req.id), "Recovery")
    assert rest.status in [RESTORE_STANDARD_PENDING, "STANDARD_PENDING", "PENDING_EXECUTION"]

    completed = execute_data_restoration(str(rest.id), "admin_314", "sysadmin")
    assert completed.status in [RESTORE_COMPLETED, "RESTORED", "COMPLETED"]


def test_tc_badms_315_restoration_sensitive_rejection_path(make_quota):
    """TC-BADMS-315 | CW-BA-03 Path 2 / BW-BA-07: Sensitive restoration SysAdmin rejection."""
    make_quota(user_id="user_315", quota_mb=1000, department_id="Bio")
    req = submit_secure_archival_request("user_315", "Bio", "bio_315.tar", 5.0, "Archive")
    decide_secure_archival_hod(str(req.id), "hod_bio", "hod", "Bio", True)
    classify_archival_sysadmin(str(req.id), "admin_315", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_315", "it_security")

    rest = request_data_restoration("user_315", "Bio", str(req.id), "Restore sensitive")
    assert rest.status in [RESTORE_SENSITIVE_PENDING, "SENSITIVE_PENDING", "SENSITIVE_PENDING_APPROVAL"]

    rejected = decide_sensitive_restoration_sysadmin(
        request_id=str(rest.id),
        sysadmin_user_id="admin_315",
        sysadmin_role="sysadmin",
        approved=False,
        remarks="Lacks security clearance",
    )
    assert rejected.status in [RESTORE_REJECTED, "REJECTED"]


def test_tc_badms_316_restoration_sensitive_approval_and_execution(make_quota):
    """TC-BADMS-316 | CW-BA-03 Path 3 / BW-BA-07: Sensitive restoration SysAdmin approval and technical execution."""
    make_quota(user_id="user_316", quota_mb=1000, department_id="Chem")
    req = submit_secure_archival_request("user_316", "Chem", "chem_316.tar", 5.0, "Archive")
    decide_secure_archival_hod(str(req.id), "hod_chem", "hod", "Chem", True)
    classify_archival_sysadmin(str(req.id), "admin_316", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_316", "it_security")

    rest = request_data_restoration("user_316", "Chem", str(req.id), "Restore sensitive")
    approved = decide_sensitive_restoration_sysadmin(str(rest.id), "admin_316", "sysadmin", True)
    assert approved.status in [RESTORE_APPROVED_FOR_EXECUTION, "APPROVED_FOR_EXECUTION"]

    completed = execute_data_restoration(str(rest.id), "admin_316", "sysadmin")
    assert completed.status in [RESTORE_COMPLETED, "RESTORED", "COMPLETED"]


def test_tc_badms_317_restoration_request_missing_archive_guard():
    """TC-BADMS-317 | CW-BA-03 Transition 1 Guard Unsatisfied: Missing archive identifier rejected."""
    with pytest.raises(Exception):
        request_data_restoration("user_317", "CS", str(uuid.uuid4()), "Nonexistent")


def test_tc_badms_318_sensitive_restoration_hod_approval_blocked(make_quota):
    """TC-BADMS-318 | CW-BA-03 Decision Point SysAdmin Authorization Guard: HoD cannot approve sensitive restore."""
    make_quota(user_id="user_318", quota_mb=1000, department_id="CS")
    req = submit_secure_archival_request("user_318", "CS", "cs_318.tar", 5.0, "Archive")
    decide_secure_archival_hod(str(req.id), "hod_cs", "hod", "CS", True)
    classify_archival_sysadmin(str(req.id), "admin_318", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_318", "it_security")
    rest = request_data_restoration("user_318", "CS", str(req.id), "Restore")

    with pytest.raises(DomainValidationError):
        decide_sensitive_restoration_sysadmin(str(rest.id), "hod_cs", "hod", True)


def test_tc_badms_319_restoration_unapproved_sensitive_execution_blocked(make_quota):
    """TC-BADMS-319 | CW-BA-03 Transition 3/6 Guard Unsatisfied: Unapproved sensitive restore cannot execute."""
    make_quota(user_id="user_319", quota_mb=1000, department_id="CS")
    req = submit_secure_archival_request("user_319", "CS", "cs_319.tar", 5.0, "Archive")
    decide_secure_archival_hod(str(req.id), "hod_cs", "hod", "CS", True)
    classify_archival_sysadmin(str(req.id), "admin_319", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_319", "it_security")
    rest = request_data_restoration("user_319", "CS", str(req.id), "Restore")

    with pytest.raises(DomainValidationError):
        execute_data_restoration(str(rest.id), "admin_319", "sysadmin")


def test_tc_badms_320_state_transition_invariance_out_of_order_approval():
    """TC-BADMS-320 | CW-BA-01 State Transition Guard: Direct approval on unsubmitted request rejected."""
    with pytest.raises(DomainValidationError):
        ArchivalWorkflowEngine.transition_hod_decision(ARCHIVAL_NOT_SUBMITTED, approved=True)
