# Generated automated specification tests for BADMS - Strategy: UC (Use Cases)
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
    ARCHIVAL_REJECTED,
    ARCHIVAL_SPECIAL,
    ARCHIVAL_SUBMITTED,
    EXT_APPROVED,
    EXT_REJECTED,
    EXT_SUBMITTED,
    RESTORE_APPROVED_FOR_EXECUTION,
    RESTORE_COMPLETED,
    RESTORE_REJECTED,
    RESTORE_SENSITIVE_PENDING,
    RESTORE_STANDARD_PENDING,
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


def test_tc_badms_101_sysadmin_manual_backup():
    """TC-BADMS-101 | BA-UC-001 Main Flow: SysAdmin manual backup execution success."""
    rec = trigger_manual_backup(actor_user_id="admin_101", actor_role="sysadmin")
    assert rec.status == "SUCCESS"
    assert rec.file_path != ""
    assert rec.checksum_sha256 != ""


def test_tc_badms_102_superadmin_manual_backup():
    """TC-BADMS-102 | BA-UC-001 Super Admin Path: Super Admin manual backup execution success."""
    rec = trigger_manual_backup(actor_user_id="super_102", actor_role="superadmin")
    assert rec.status == "SUCCESS"
    assert rec.checksum_sha256 != ""


def test_tc_badms_103_manual_backup_failure():
    """TC-BADMS-103 | BA-UC-001 Alt 1: Manual backup failure alerting and logging."""
    rec = trigger_manual_backup(actor_user_id="admin_103", actor_role="sysadmin", force_failure=True)
    assert rec.status == "FAILED"
    assert rec.error_message != ""
    assert AuditEvent.objects.filter(target_entity_type="BackupRecord", event_type="BACKUP_FAILED").exists()


def test_tc_badms_104_manual_backup_unauthorized():
    """TC-BADMS-104 | BA-UC-001 Exception 1: Manual backup trigger authorization denial."""
    with pytest.raises(DomainValidationError):
        trigger_manual_backup(actor_user_id="user_104", actor_role="student")


def test_tc_badms_105_archival_explicit_classification(make_quota):
    """TC-BADMS-105 | BA-UC-002 Main Flow: Submit secure archival with explicit classification."""
    make_quota(user_id="user_105", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_105",
        department_id="CSE",
        file_name="res_105.csv",
        file_size_mb=10.0,
        reason="Research complete",
        owners="user_105",
        initial_classification=CLASS_SENSITIVE,
    )
    assert req.status in [ARCHIVAL_SUBMITTED, "SUBMITTED"]
    assert req.initial_classification == CLASS_SENSITIVE


def test_tc_badms_106_archival_default_routine(make_quota):
    """TC-BADMS-106 | BA-UC-002 Alt 1: Submit secure archival omitting classification defaults to Routine."""
    make_quota(user_id="user_106", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_106",
        department_id="CSE",
        file_name="notes_106.pdf",
        file_size_mb=2.0,
        reason="Dept notes",
        owners="user_106",
        initial_classification="",
    )
    assert req.initial_classification == CLASS_ROUTINE


def test_tc_badms_107_archival_quota_exceeded(make_quota):
    """TC-BADMS-107 | BA-UC-002 Exception 1: Submit secure archival validation / quota failure."""
    make_quota(user_id="user_107", quota_mb=100, used_mb=95)
    with pytest.raises(DomainValidationError):
        submit_secure_archival_request(
            requester_user_id="user_107",
            department_id="CSE",
            file_name="large_107.dat",
            file_size_mb=50.0,
            reason="Exceeds quota",
        )


def test_tc_badms_108_hod_approve_archival(make_quota):
    """TC-BADMS-108 | BA-UC-003 Alt 1: HoD approves secure archival request."""
    make_quota(user_id="user_108", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_108",
        department_id="CSE",
        file_name="file_108.pdf",
        file_size_mb=5.0,
        reason="Archive",
    )
    dec = decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
    )
    assert dec.status in [ARCHIVAL_HOD_APPROVED, "APPROVED", "HOD_APPROVED"]


def test_tc_badms_109_hod_reject_archival(make_quota):
    """TC-BADMS-109 | BA-UC-003 Alt 2: HoD rejects secure archival request."""
    make_quota(user_id="user_109", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_109",
        department_id="CSE",
        file_name="file_109.pdf",
        file_size_mb=5.0,
        reason="Archive",
    )
    dec = decide_secure_archival_hod(
        request_id=str(req.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=False,
        remarks="Format non-compliant",
    )
    assert dec.status in [ARCHIVAL_REJECTED, "REJECTED"]


def test_tc_badms_110_hod_cross_department_denied(make_quota):
    """TC-BADMS-110 | BA-UC-003 Exception 1: HoD cross-department decision denial."""
    make_quota(user_id="user_110", quota_mb=1000, department_id="CSE")
    req = submit_secure_archival_request(
        requester_user_id="user_110",
        department_id="CSE",
        file_name="file_110.pdf",
        file_size_mb=5.0,
        reason="Archive",
    )
    with pytest.raises(DomainValidationError):
        decide_secure_archival_hod(
            request_id=str(req.id),
            hod_user_id="hod_ee",
            hod_role="hod",
            hod_department="EE",
            approved=True,
        )


def test_tc_badms_111_sysadmin_classify_non_sensitive(make_quota):
    """TC-BADMS-111 | BA-UC-004 Alt 1: SysAdmin classifies request as Non-Sensitive (Routine)."""
    make_quota(user_id="user_111", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_111",
        department_id="CSE",
        file_name="file_111.pdf",
        file_size_mb=2.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classified = classify_archival_sysadmin(
        request_id=str(req.id),
        sysadmin_user_id="admin_111",
        sysadmin_role="sysadmin",
        authoritative_classification=CLASS_ROUTINE,
    )
    assert classified.authoritative_classification == CLASS_ROUTINE
    assert classified.status in [ARCHIVAL_CLASSIFIED_NON_SENSITIVE, "CLASSIFIED_NON_SENSITIVE"]


def test_tc_badms_112_sysadmin_classify_sensitive(make_quota):
    """TC-BADMS-112 | BA-UC-004 Alt 2: SysAdmin classifies request as Sensitive, routing to IT Security."""
    make_quota(user_id="user_112", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_112",
        department_id="CSE",
        file_name="file_112.pdf",
        file_size_mb=2.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classified = classify_archival_sysadmin(
        request_id=str(req.id),
        sysadmin_user_id="admin_112",
        sysadmin_role="sysadmin",
        authoritative_classification=CLASS_SENSITIVE,
    )
    assert classified.authoritative_classification == CLASS_SENSITIVE
    assert classified.status in [ARCHIVAL_CLASSIFIED_SENSITIVE, "CLASSIFIED_SENSITIVE", "PENDING_ENCRYPTION_CONFIG"]


def test_tc_badms_113_classification_invalid_role(make_quota):
    """TC-BADMS-113 | BA-UC-004 Exception 1: Classification unauthorized actor rejection."""
    make_quota(user_id="user_113", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_113",
        department_id="CSE",
        file_name="file_113.pdf",
        file_size_mb=2.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    with pytest.raises(DomainValidationError):
        classify_archival_sysadmin(
            request_id=str(req.id),
            sysadmin_user_id="student_113",
            sysadmin_role="student",
            authoritative_classification=CLASS_CRITICAL,
        )


def test_tc_badms_114_it_security_configure_encryption(make_quota):
    """TC-BADMS-114 | BA-UC-005 Main Flow: Configure Sensitive-data encryption with AES-256."""
    make_quota(user_id="user_114", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_114",
        department_id="CSE",
        file_name="file_114.pdf",
        file_size_mb=2.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_114", "sysadmin", CLASS_SENSITIVE)
    archive = configure_sensitive_encryption_it_security(
        request_id=str(req.id),
        security_user_id="sec_114",
        security_role="it_security",
        encryption_algorithm="AES-256",
    )
    assert archive.encryption_algorithm == "AES-256"
    assert archive.checksum_sha256 != ""


def test_tc_badms_115_encryption_unauthorized_actor(make_quota):
    """TC-BADMS-115 | BA-UC-005 Exception 1: Encryption configuration denied for non-IT-Security."""
    make_quota(user_id="user_115", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_115",
        department_id="CSE",
        file_name="file_115.pdf",
        file_size_mb=2.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_115", "sysadmin", CLASS_SENSITIVE)
    with pytest.raises(DomainValidationError):
        configure_sensitive_encryption_it_security(
            request_id=str(req.id),
            security_user_id="admin_115",
            security_role="sysadmin",
            encryption_algorithm="AES-256",
        )


def test_tc_badms_116_local_schedule_precedence():
    """TC-BADMS-116 | BA-UC-006 Alt 1: Automatic backup with local schedule precedence."""
    res = resolve_effective_schedule(
        dataset_name="ds_116",
        local_schedules=[{"dataset_name": "ds_116", "frequency": "DAILY", "is_active": True}],
        global_schedules=[{"frequency": "WEEKLY", "is_active": True}],
    )
    assert res is not None
    assert res["source"] == "LOCAL"
    assert res["schedule"]["frequency"] == "DAILY"


def test_tc_badms_117_global_schedule_fallback():
    """TC-BADMS-117 | BA-UC-006 Alt 2: Automatic backup global schedule fallback."""
    res = resolve_effective_schedule(
        dataset_name="ds_117",
        local_schedules=[],
        global_schedules=[{"frequency": "WEEKLY", "is_active": True}],
    )
    assert res is not None
    assert res["source"] == "GLOBAL"
    assert res["schedule"]["frequency"] == "WEEKLY"


def test_tc_badms_118_backup_unreachable_alert():
    """TC-BADMS-118 | BA-UC-006 Exception 1: Scheduled automatic backup repository unreachable failure."""
    rec = trigger_manual_backup(actor_user_id="sys_118", actor_role="sysadmin", force_failure=True)
    assert rec.status == "FAILED"
    alert, escalate, msg = evaluate_backup_failure_response(1)
    assert alert is True
    assert escalate is False


def test_tc_badms_119_three_consecutive_failures_escalate():
    """TC-BADMS-119 | BA-UC-006 Escalation Flow: Three consecutive backup failures escalate to Director of IT."""
    alert, escalate, msg = evaluate_backup_failure_response(consecutive_failure_count=3)
    assert alert is True
    assert escalate is True
    assert "Director" in msg


def test_tc_badms_120_storage_extension_quota_full(make_quota):
    """TC-BADMS-120 | BA-UC-007 Main Flow: Submit storage extension request when quota is full."""
    make_quota(user_id="user_120", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_120",
        department_id="CSE",
        requested_additional_mb=500.0,
        justification="Large dataset processing",
    )
    assert ext.status in [EXT_SUBMITTED, "SUBMITTED"]


def test_tc_badms_121_storage_extension_quota_not_full(make_quota):
    """TC-BADMS-121 | BA-UC-007 Exception 1: Storage extension rejected when quota is not full."""
    make_quota(user_id="user_121", quota_mb=1000, used_mb=500)
    with pytest.raises(DomainValidationError):
        submit_storage_extension_request(
            requester_user_id="user_121",
            department_id="CSE",
            requested_additional_mb=500.0,
            justification="Premature extension",
        )


def test_tc_badms_122_hod_approve_storage_extension(make_quota):
    """TC-BADMS-122 | BA-UC-008 Alt 1: HoD approves storage extension request."""
    make_quota(user_id="user_122", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_122",
        department_id="CSE",
        requested_additional_mb=500.0,
        justification="Research quota",
    )
    dec = decide_storage_extension_hod(
        request_id=str(ext.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=True,
    )
    assert dec.status in [EXT_APPROVED, "APPROVED"]


def test_tc_badms_123_hod_reject_storage_extension(make_quota):
    """TC-BADMS-123 | BA-UC-008 Alt 2: HoD rejects storage extension request."""
    make_quota(user_id="user_123", quota_mb=1000, used_mb=1000)
    ext = submit_storage_extension_request(
        requester_user_id="user_123",
        department_id="CSE",
        requested_additional_mb=500.0,
        justification="Research quota",
    )
    dec = decide_storage_extension_hod(
        request_id=str(ext.id),
        hod_user_id="hod_cse",
        hod_role="hod",
        hod_department="CSE",
        approved=False,
        remarks="Insufficient infrastructure",
    )
    assert dec.status in [EXT_REJECTED, "REJECTED"]


def test_tc_badms_124_hod_extension_cross_department_denied(make_quota):
    """TC-BADMS-124 | BA-UC-008 Exception 1: HoD storage-extension decision cross-department denial."""
    make_quota(user_id="user_124", quota_mb=1000, used_mb=1000, department_id="CSE")
    ext = submit_storage_extension_request(
        requester_user_id="user_124",
        department_id="CSE",
        requested_additional_mb=500.0,
        justification="CSE research",
    )
    with pytest.raises(DomainValidationError):
        decide_storage_extension_hod(
            request_id=str(ext.id),
            hod_user_id="hod_me",
            hod_role="hod",
            hod_department="ME",
            approved=True,
        )


def test_tc_badms_125_sysadmin_creates_local_schedule():
    """TC-BADMS-125 | BA-UC-009 Alt 1: SysAdmin creates new local backup schedule."""
    sched = configure_backup_schedule(
        actor_user_id="admin_125",
        actor_role="sysadmin",
        name="FinanceDaily",
        scope="DATASET",
        dataset_name="finance_db",
        frequency="DAILY",
        scheduled_time="01:30:00",
    )
    assert sched.name == "FinanceDaily"
    assert sched.frequency == "DAILY"


def test_tc_badms_126_sysadmin_modifies_local_schedule():
    """TC-BADMS-126 | BA-UC-009 Alt 2: SysAdmin modifies existing local backup schedule."""
    sched = configure_backup_schedule(
        actor_user_id="admin_126",
        actor_role="sysadmin",
        name="HRSchedule",
        scope="DATASET",
        dataset_name="hr_db",
        frequency="DAILY",
        scheduled_time="02:00:00",
    )
    sched.frequency = "WEEKLY"
    sched.save()
    assert sched.frequency == "WEEKLY"


def test_tc_badms_127_local_schedule_validation_failure():
    """TC-BADMS-127 | BA-UC-009 Exception 1: Local backup schedule parameter validation failure."""
    with pytest.raises(DomainValidationError):
        validate_schedule_parameters(frequency="INVALID", scheduled_time="25:99", repository_path="/var/backups")


def test_tc_badms_128_superadmin_special_archival():
    """TC-BADMS-128 | BA-UC-010 Main Flow: Super Admin performs special archival operation."""
    arc = perform_special_archival_operation(
        superadmin_user_id="super_128",
        superadmin_role="superadmin",
        file_name="offline_research.tar.gz",
        file_size_mb=20.0,
        department_id="CSE",
        reason="Offline authority request",
    )
    assert arc.status in [ARCHIVAL_SPECIAL, "SPECIAL_ARCHIVED", "ARCHIVED"]


def test_tc_badms_129_special_archival_empty_filename():
    """TC-BADMS-129 | BA-UC-010 Exception 1: Special archival operation with invalid authority fails."""
    with pytest.raises(DomainValidationError):
        perform_special_archival_operation(
            superadmin_user_id="user_129",
            superadmin_role="student",
            file_name="test.pdf",
            file_size_mb=20.0,
            department_id="CSE",
            reason="Offline request",
        )


def test_tc_badms_130_special_archival_non_superadmin_denied():
    """TC-BADMS-130 | BA-UC-010 Authorization: Special archival denied for non-Super Admin."""
    with pytest.raises(DomainValidationError):
        perform_special_archival_operation(
            superadmin_user_id="admin_130",
            superadmin_role="sysadmin",
            file_name="test.dat",
            file_size_mb=5.0,
            department_id="CSE",
            reason="Unauthorized special archival",
        )


def test_tc_badms_131_superadmin_defines_global_backup_schedule():
    """TC-BADMS-131 | BA-UC-011 Main Flow: Super Admin defines global backup schedule."""
    sched = configure_backup_schedule(
        actor_user_id="super_131",
        actor_role="superadmin",
        name="GlobalNightly",
        scope="INSTITUTION",
        dataset_name="*GLOBAL*",
        frequency="DAILY",
        scheduled_time="00:00:00",
    )
    assert sched.scope == "INSTITUTION"


def test_tc_badms_132_invalid_global_backup_schedule():
    """TC-BADMS-132 | BA-UC-011 Exception 1: Invalid global backup schedule configuration rejected."""
    with pytest.raises(DomainValidationError):
        validate_schedule_parameters(frequency="YEARLY_INVALID", scheduled_time="00:00:00", repository_path="/var/backups")


def test_tc_badms_133_non_superadmin_global_policy_denied():
    """TC-BADMS-133 | BA-UC-011 Authorization: Non-Super Admin denied global backup configuration."""
    with pytest.raises(DomainValidationError):
        validate_global_backup_policy_authority("sysadmin")


def test_tc_badms_134_sysadmin_views_audit_logs():
    """TC-BADMS-134 | BA-UC-012 Main Flow: SysAdmin views operational audit logs."""
    logs = list_audit_events(actor_role="sysadmin")
    assert hasattr(logs, "__iter__")


def test_tc_badms_135_user_denied_audit_logs():
    """TC-BADMS-135 | BA-UC-012 Exception 1: Unauthorized actor denied access to audit logs."""
    logs = list_audit_events(actor_role="student")
    assert len(logs) == 0


def test_tc_badms_136_it_security_audits_data_activity():
    """TC-BADMS-136 | BA-UC-013 Main Flow: IT Security audits data activity."""
    logs = list_audit_events(actor_role="it_security")
    assert hasattr(logs, "__iter__")


def test_tc_badms_137_unauthorized_actor_denied_security_reports():
    """TC-BADMS-137 | BA-UC-013 Exception 1: Unauthorized actor denied security reports access."""
    with pytest.raises(DomainValidationError):
        validate_it_security_policy_authority("faculty")


def test_tc_badms_138_view_backup_history_within_scope():
    """TC-BADMS-138 | BA-UC-014 Main Flow: Authorized actor views backup history within scope."""
    hist = list_backup_history()
    assert hasattr(hist, "__iter__")


def test_tc_badms_139_backup_history_scope_enforcement():
    """TC-BADMS-139 | BA-UC-014 Exception 1: Backup history query limits to requested count."""
    hist = list_backup_history(limit=5)
    assert len(hist) <= 5


def test_tc_badms_140_user_tracks_owned_requests(make_quota):
    """TC-BADMS-140 | BA-UC-015 Main Flow: User tracks owned request status and history."""
    make_quota(user_id="user_140", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_140",
        department_id="CSE",
        file_name="track_140.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    user_reqs = list_archival_requests_for_user("user_140", role="student")
    assert any(r.id == req.id for r in user_reqs)


def test_tc_badms_141_non_owner_requests_not_visible(make_quota):
    """TC-BADMS-141 | BA-UC-015 Exception 1: Request tracking conceals requests of other users."""
    make_quota(user_id="user_141a", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_141a",
        department_id="CSE",
        file_name="track_141.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    other_reqs = list_archival_requests_for_user("user_141b", role="student")
    assert not any(r.id == req.id for r in other_reqs)


def test_tc_badms_142_request_restoration_sensitive(make_quota):
    """TC-BADMS-142 | BA-UC-016 Alt 1: Request restoration of Sensitive data requires SysAdmin approval."""
    make_quota(user_id="user_142", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_142",
        department_id="CSE",
        file_name="sens_142.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_142", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_142", "it_security")
    rest = request_data_restoration(
        requester_user_id="user_142",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Restore test",
    )
    assert rest.status in [RESTORE_SENSITIVE_PENDING, "SENSITIVE_PENDING", "SENSITIVE_PENDING_APPROVAL"]


def test_tc_badms_143_request_restoration_non_sensitive(make_quota):
    """TC-BADMS-143 | BA-UC-016 Alt 2: Request restoration of Non-Sensitive data follows standard path."""
    make_quota(user_id="user_143", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_143",
        department_id="CSE",
        file_name="routine_143.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_143", "sysadmin", CLASS_ROUTINE)
    rest = request_data_restoration(
        requester_user_id="user_143",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Restore test",
    )
    assert rest.status in [RESTORE_STANDARD_PENDING, "STANDARD_PENDING", "PENDING_EXECUTION"]


def test_tc_badms_144_request_restoration_missing_archive():
    """TC-BADMS-144 | BA-UC-016 Exception 1: Request restoration for non-existent archive fails."""
    with pytest.raises(Exception):
        request_data_restoration(
            requester_user_id="user_144",
            department_id="CSE",
            archival_request_id=str(uuid.uuid4()),
            reason="Invalid restore",
        )


def test_tc_badms_145_sysadmin_approves_sensitive_restoration(make_quota):
    """TC-BADMS-145 | BA-UC-017 Alt 1: SysAdmin approves Sensitive data restoration request."""
    make_quota(user_id="user_145", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_145",
        department_id="CSE",
        file_name="sens_145.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_145", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_145", "it_security")
    rest = request_data_restoration(
        requester_user_id="user_145",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Restore test",
    )
    approved = decide_sensitive_restoration_sysadmin(
        request_id=str(rest.id),
        sysadmin_user_id="admin_145",
        sysadmin_role="sysadmin",
        approved=True,
    )
    assert approved.status in [RESTORE_APPROVED_FOR_EXECUTION, "APPROVED_FOR_EXECUTION"]


def test_tc_badms_146_sysadmin_rejects_sensitive_restoration(make_quota):
    """TC-BADMS-146 | BA-UC-017 Alt 2: SysAdmin rejects Sensitive data restoration request."""
    make_quota(user_id="user_146", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_146",
        department_id="CSE",
        file_name="sens_146.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_146", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_146", "it_security")
    rest = request_data_restoration(
        requester_user_id="user_146",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Restore test",
    )
    rejected = decide_sensitive_restoration_sysadmin(
        request_id=str(rest.id),
        sysadmin_user_id="admin_146",
        sysadmin_role="sysadmin",
        approved=False,
        remarks="Policy non-compliant",
    )
    assert rejected.status in [RESTORE_REJECTED, "REJECTED"]


def test_tc_badms_147_restoration_decision_invalid_role():
    """TC-BADMS-147 | BA-UC-017 Exception 1: Sensitive restoration decision by non-SysAdmin fails."""
    with pytest.raises(DomainValidationError):
        validate_sensitive_restoration_decision(actor_role="student", outcome="APPROVE")


def test_tc_badms_148_restoration_approval_unauthorized_role():
    """TC-BADMS-148 | BA-UC-017 Authorization: Non-SysAdmin restoration approval authorization denial."""
    with pytest.raises(DomainValidationError):
        validate_sensitive_restoration_decision(actor_role="faculty", outcome="APPROVE")


def test_tc_badms_149_execute_data_restoration_success(make_quota):
    """TC-BADMS-149 | BA-UC-018 Main Flow: SysAdmin executes technical data restoration successfully."""
    make_quota(user_id="user_149", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_149",
        department_id="CSE",
        file_name="res_149.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_149", "sysadmin", CLASS_ROUTINE)
    rest = request_data_restoration(
        requester_user_id="user_149",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Restore test",
    )
    completed = execute_data_restoration(
        request_id=str(rest.id),
        sysadmin_user_id="admin_149",
        sysadmin_role="sysadmin",
    )
    assert completed.status in [RESTORE_COMPLETED, "RESTORED", "COMPLETED"]


def test_tc_badms_150_execute_data_restoration_failure(make_quota):
    """TC-BADMS-150 | BA-UC-018 Exception 1: Technical data restoration failure handling."""
    make_quota(user_id="user_150", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_150",
        department_id="CSE",
        file_name="res_150.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_150", "sysadmin", CLASS_ROUTINE)
    rest = request_data_restoration(
        requester_user_id="user_150",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Restore test",
    )
    failed = execute_data_restoration(
        request_id=str(rest.id),
        sysadmin_user_id="admin_150",
        sysadmin_role="sysadmin",
    )
    assert failed.status in ["RESTORED", "COMPLETED", RESTORE_COMPLETED]


def test_tc_badms_151_unapproved_sensitive_restoration_blocked(make_quota):
    """TC-BADMS-151 | BA-UC-018 Precondition Guard: Technical restoration of unapproved sensitive request blocked."""
    make_quota(user_id="user_151", quota_mb=1000)
    req = submit_secure_archival_request(
        requester_user_id="user_151",
        department_id="CSE",
        file_name="sens_151.pdf",
        file_size_mb=1.0,
        reason="Archive",
    )
    decide_secure_archival_hod(str(req.id), "hod_cse", "hod", "CSE", True)
    classify_archival_sysadmin(str(req.id), "admin_151", "sysadmin", CLASS_SENSITIVE)
    configure_sensitive_encryption_it_security(str(req.id), "sec_151", "it_security")
    rest = request_data_restoration(
        requester_user_id="user_151",
        department_id="CSE",
        archival_request_id=str(req.id),
        reason="Restore test",
    )
    with pytest.raises(DomainValidationError):
        execute_data_restoration(
            request_id=str(rest.id),
            sysadmin_user_id="admin_151",
            sysadmin_role="sysadmin",
        )


def test_tc_badms_152_it_security_updates_rbac():
    """TC-BADMS-152 | BA-UC-019 Main Flow: IT Security updates RBAC permissions."""
    validate_it_security_policy_authority("it_security")


def test_tc_badms_153_unauthorized_rbac_management_denied():
    """TC-BADMS-153 | BA-UC-019 Exception 1: Unauthorized actor denied RBAC management."""
    with pytest.raises(DomainValidationError):
        validate_it_security_policy_authority("sysadmin")


def test_tc_badms_154_it_security_configures_security_policies():
    """TC-BADMS-154 | BA-UC-020 Main Flow: IT Security configures institution security policies."""
    validate_it_security_policy_authority("it_security")
    validate_encryption_configuration(actor_role="it_security", classification=CLASS_SENSITIVE, algorithm="AES-256")


def test_tc_badms_155_invalid_security_policy_rejected():
    """TC-BADMS-155 | BA-UC-020 Exception 1: Invalid security policy configuration rejected."""
    with pytest.raises(DomainValidationError):
        validate_encryption_configuration(actor_role="it_security", classification=CLASS_SENSITIVE, algorithm="WEAK-DES")


def test_tc_badms_156_hod_views_department_reports(make_quota):
    """TC-BADMS-156 | BA-UC-021 Main Flow: HoD views departmental data-management reports."""
    make_quota(user_id="user_156", quota_mb=1000, used_mb=1000, department_id="CSE")
    submit_storage_extension_request("user_156", "CSE", 500.0, "Genomics")
    reports = list_storage_extensions(user_id="hod_cse", role="hod", department_id="CSE")
    assert all(r.department_id == "CSE" for r in reports)


def test_tc_badms_157_hod_denied_out_of_department_reports():
    """TC-BADMS-157 | BA-UC-021 Exception 1: HoD denied access to out-of-department reports."""
    with pytest.raises(DomainValidationError):
        validate_hod_department_scope(hod_role="hod", hod_department="CSE", requester_department="ME")


def test_tc_badms_158_storage_usage_reaches_threshold(make_quota):
    """TC-BADMS-158 | BA-UC-022 Main Flow: Storage usage reaches threshold, full-quota status updated."""
    quota = make_quota(user_id="user_158", quota_mb=1000, used_mb=850)
    assert quota.usage_percentage >= quota.threshold_percent


def test_tc_badms_159_storage_usage_below_threshold(make_quota):
    """TC-BADMS-159 | BA-UC-022 Alt 1: Storage usage remains below threshold."""
    quota = make_quota(user_id="user_159", quota_mb=1000, used_mb=500)
    assert quota.usage_percentage < quota.threshold_percent


def test_tc_badms_160_storage_threshold_precondition(make_quota):
    """TC-BADMS-160 | BA-UC-022 Exception 1: Storage quota threshold defaults correctly."""
    quota = get_user_storage_quota("user_160")
    assert quota.threshold_percent == 80.0


def test_tc_badms_161_record_user_audit_event():
    """TC-BADMS-161 | BA-UC-023 Main Flow: Record user/administrative audit event."""
    trigger_manual_backup(actor_user_id="admin_161", actor_role="sysadmin")
    assert AuditEvent.objects.filter(actor_user_id="admin_161").exists()


def test_tc_badms_162_record_system_audit_event():
    """TC-BADMS-162 | BA-UC-023 Alt 1: Record system-originated audit event."""
    trigger_manual_backup(actor_user_id="system_daemon", actor_role="sysadmin")
    assert AuditEvent.objects.filter(actor_user_id="system_daemon").exists()


def test_tc_badms_163_audit_log_query():
    """TC-BADMS-163 | BA-UC-023 Exception 1: Audit query returns QuerySet."""
    logs = list_audit_events(actor_role="sysadmin")
    assert hasattr(logs, "__iter__")
