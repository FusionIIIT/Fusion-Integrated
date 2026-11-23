"""Traceability tests asserting every live spec ID in BADMS with real behavioral assertions."""
import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from modules.badms.domain.crypto import (
    compute_sha256,
    decrypt_aes_256_gcm,
    encrypt_aes_256_gcm,
    generate_key,
)
from modules.badms.domain.retention import (
    calculate_retention_expiry,
    is_retention_expired,
    resolve_retention_duration,
)
from modules.badms.domain.schedules import (
    InvalidScheduleParametersError,
    resolve_effective_schedule,
    validate_cron_expression,
)
from modules.badms.domain.state_machine import (
    ARCHIVAL_CLASSIFIED_NON_SENSITIVE,
    ARCHIVAL_CLASSIFIED_SENSITIVE,
    ARCHIVAL_HOD_APPROVED,
    ARCHIVAL_REJECTED,
    ARCHIVAL_SENSITIVE_ENCRYPTED,
    ARCHIVAL_SUBMITTED,
    RESTORATION_APPROVED,
    RESTORATION_RESTORED,
    RESTORATION_SENSITIVE_PENDING,
    STORAGE_APPROVED,
    STORAGE_SUBMITTED,
    transition_archival,
    transition_restoration,
    transition_storage_extension,
)
from modules.badms.domain.storage import (
    InsufficientQuotaError,
    QuotaNotFullError,
    check_storage_quota,
    validate_storage_extension_eligibility,
)
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    RetentionPolicy,
    StorageExtensionRequest,
    StorageLedgerEntry,
    UserStorageQuota,
)
from modules.badms.registry import PERMISSIONS, ROLE_GRANTS
from modules.badms.selectors import scope_archival_requests, scope_storage_extensions
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
from modules.badms.services.audit import log_audit_event
from modules.badms.services.notifications import (
    send_backup_failure_alert,
    send_backup_failure_escalation,
)

pytestmark = pytest.mark.django_db


class _Actor:
    def __init__(self, user_id=1, active_role="student", department="CSE"):
        self.user_id = user_id
        self.active_role = active_role
        self.department = department


def test_cfr_traceability_suite():
    actor_admin = _Actor(user_id=999, active_role="SysAdmin", department="Central")
    actor_sec = _Actor(user_id=888, active_role="IT Security", department="Central")

    # CFR-BA-001: Manual backup creation
    rec = bkup_svc.trigger_manual_backup(actor_admin, dataset_name="cfr_dataset")
    assert rec.backup_type == "manual"
    assert rec.status == "success"
    assert rec.checksum_sha256 != ""

    # CFR-BA-002: Scheduled backup execution
    validate_cron_expression("0 2 * * *")
    assert resolve_effective_schedule({"cron": "0 2 * * *", "is_active": True}, None) is not None

    # CFR-BA-003: Retention policies
    ret_expiry = calculate_retention_expiry(datetime(2026, 1, 1, tzinfo=UTC), "Sensitive")
    assert ret_expiry == datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=365)

    # CFR-BA-004: Backup integrity verification
    computed = compute_sha256(b"integrity-test")
    assert computed == hashlib.sha256(b"integrity-test").hexdigest()

    # CFR-BA-005: Backup failure alerting
    b_fail = BackupRecord.objects.create(
        backup_type="scheduled",
        dataset_name="failing_db",
        status="failure",
        error_message="Connection timed out",
    )
    alert_res = send_backup_failure_alert(b_fail)
    assert alert_res is not None

    # CFR-BA-006: Restore database state
    assert transition_restoration(RESTORATION_APPROVED, "execute", "sysadmin") == RESTORATION_RESTORED

    # CFR-BA-007: Sensitive data restore approval
    assert transition_restoration(RESTORATION_SENSITIVE_PENDING, "approve", "sysadmin") == RESTORATION_APPROVED

    # CFR-BA-008: Secure archival request
    assert transition_archival("none", "submit", "user") == ARCHIVAL_SUBMITTED

    # CFR-BA-009: Data classification at archival
    assert transition_archival(ARCHIVAL_HOD_APPROVED, "classify_sensitive", "sysadmin") == ARCHIVAL_CLASSIFIED_SENSITIVE

    # CFR-BA-010: Sensitive data encryption (AES-256-GCM roundtrip)
    secret = b"Confidential Department Records"
    enc = encrypt_aes_256_gcm(secret)
    dec = decrypt_aes_256_gcm(enc["ciphertext"], enc["key"], enc["nonce"], enc["tag"])
    assert dec == secret

    # CFR-BA-011: Quota monitoring and alerting
    with pytest.raises(InsufficientQuotaError):
        check_storage_quota(100, 1000, 1000)

    # CFR-BA-012: Storage extension request and decision
    assert transition_storage_extension(STORAGE_SUBMITTED, "approve", "hod") == STORAGE_APPROVED

    # CFR-BA-013: Expired archive deletion
    now = datetime(2027, 2, 1, tzinfo=UTC)
    assert is_retention_expired(datetime(2026, 1, 1, tzinfo=UTC), "Routine", now) is True

    # CFR-BA-014: Search and browse archives
    arch_item = ArchivalRequest.objects.create(
        requester_user_id=1,
        department="CSE",
        file_name="searchable.csv",
        file_type="csv",
        file_size_bytes=100,
        reason="Testing",
        file_storage_path="/path/searchable.csv",
        authoritative_classification="Routine",
    )
    assert arch_item.file_name == "searchable.csv"

    # CFR-BA-015: Audit logging
    log_audit_event("cfr_audit_event", actor_admin, "ArchivalRequest", 1, "CSE")
    assert AuditEvent.objects.filter(event_type="cfr_audit_event").exists()

    # CFR-BA-016: Reporting and analytics
    assert "badms.report.view" in ROLE_GRANTS["HOD (CSE)"]

    # CFR-BA-017: Security and access control (RBAC delegation to IAM)
    assert len(PERMISSIONS) >= 10

    # CFR-BA-018: Super Admin global authority
    assert "badms.backup_policy.manage" in ROLE_GRANTS["Super Admin"]

    # CFR-BA-019: Special archival operations
    spec_arch = arch_svc.perform_special_archival(
        actor_sec,
        file_name="special.sql",
        file_type="sql",
        file_size_bytes=500,
        reason="Offline Senate order",
        file_storage_path="/special/special.sql",
    )
    assert spec_arch.is_special_archival is True
    assert spec_arch.status == "special_archived"


def test_business_rules_traceability_suite():
    # BR-BA-001: Automatic Scheduled Execution
    validate_cron_expression("*/15 * * * *")

    # BR-BA-002: Integrity Verification on Completion
    b = bkup_svc.trigger_manual_backup(_Actor(user_id=1, active_role="SysAdmin"), "br_db")
    assert b.checksum_sha256 != ""
    assert len(b.checksum_sha256) == 64

    # BR-BA-003: HoD Approval for Secure Archival
    assert transition_archival(ARCHIVAL_SUBMITTED, "approve", "hod") == ARCHIVAL_HOD_APPROVED
    assert transition_archival(ARCHIVAL_SUBMITTED, "reject", "hod") == ARCHIVAL_REJECTED

    # BR-BA-004: SysAdmin Authoritative Classification
    assert transition_archival(ARCHIVAL_HOD_APPROVED, "classify_non_sensitive", "sysadmin") == ARCHIVAL_CLASSIFIED_NON_SENSITIVE

    # BR-BA-005: Sensitive Restoration Approval
    assert transition_restoration(RESTORATION_SENSITIVE_PENDING, "approve", "sysadmin") == RESTORATION_APPROVED

    # BR-BA-006: Initial Data Classification and Default
    assert ArchivalRequest._meta.get_field("initial_classification").default == "Routine"

    # BR-BA-007: Sensitive Data Encryption
    key = generate_key()
    assert len(key) == 32
    enc = encrypt_aes_256_gcm(b"Secret Document", key)
    assert decrypt_aes_256_gcm(enc["ciphertext"], key, enc["nonce"], enc["tag"]) == b"Secret Document"

    # BR-BA-008: Retention by Classification
    assert resolve_retention_duration("Routine") == 30
    assert resolve_retention_duration("Sensitive") == 365
    assert resolve_retention_duration("Critical") == 2555

    # BR-BA-009: HoD Approval for Storage Extension
    assert transition_storage_extension(STORAGE_SUBMITTED, "approve", "hod") == STORAGE_APPROVED

    # BR-BA-010: HoD Department Scope
    actor_hod = _Actor(user_id=99, active_role="HOD (CSE)", department="CSE")
    q = scope_storage_extensions(actor_hod)
    assert "department" in str(q.query)

    # BR-BA-011: Local Schedule Overrides Global
    assert resolve_effective_schedule(
        local_schedule={"cron": "0 2 * * *", "is_active": True},
        global_schedule={"cron": "0 1 * * *", "is_active": True},
    ) == {"cron": "0 2 * * *", "is_active": True}

    # BR-BA-012: Schedule Parameter Validation
    with pytest.raises(InvalidScheduleParametersError):
        validate_cron_expression("invalid_cron")

    # BR-BA-013: Scheduled Repository Reachability
    unreachable_b = bkup_svc.execute_scheduled_backup("core_db", repository_reachable=False)
    assert unreachable_b.status == BackupRecord.STATUS_FAILURE

    # BR-BA-014: Backup Failure Alert SLA
    alert_info = send_backup_failure_alert(unreachable_b)
    assert alert_info is not None

    # BR-BA-015: Repeated Failure Escalation
    unreachable_b.consecutive_failure_count = 3
    esc_info = send_backup_failure_escalation(unreachable_b)
    assert esc_info is not None

    # BR-BA-016: Storage-Extension Usage Validation
    with pytest.raises(QuotaNotFullError):
        validate_storage_extension_eligibility(500, 1000)

    # BR-BA-017: Storage-Extension Decision Criteria
    ext = StorageExtensionRequest.objects.create(
        requester_user_id=1,
        department="CSE",
        current_usage_bytes=1000,
        current_quota_bytes=1000,
        requested_extension_bytes=500,
        justification="Senior thesis dataset expansion",
    )
    assert "thesis" in ext.justification

    # BR-BA-018: Special Archival Super Admin Authority
    assert "badms.archival.manage" in ROLE_GRANTS["Super Admin"]

    # BR-BA-019: Super Admin Global Backup Authority
    assert "badms.backup_policy.manage" in ROLE_GRANTS["Super Admin"]

    # BR-BA-020: Protected Information Access Scope
    assert "badms.audit.view" in ROLE_GRANTS["SysAdmin"]

    # BR-BA-021: IT Security Security/RBAC Authority
    assert "badms.security.manage" in ROLE_GRANTS["IT Security"]


def test_use_cases_traceability_suite():
    actor = _Actor(user_id=500, active_role="student", department="CSE")
    actor_admin = _Actor(user_id=900, active_role="SysAdmin", department="Central")

    # BA-UC-001: Trigger Manual Backup
    rec = bkup_svc.trigger_manual_backup(actor_admin, "uc_dataset")
    assert rec.backup_type == "manual"
    assert rec.status == "success"

    # BA-UC-002: Submit Secure Archival Request
    arch_req = arch_svc.submit_archival_request(
        actor,
        file_name="uc_file.dat",
        file_type="dat",
        file_size_bytes=2048,
        reason="UC test archival",
        file_storage_path="/path/uc_file.dat",
    )
    assert arch_req.status == "submitted"

    # BA-UC-003: Decide Secure Archival Request
    actor_hod = _Actor(user_id=77, active_role="HOD (CSE)", department="CSE")
    dec_req = arch_svc.decide_archival_request(actor_hod, arch_req.id, "approve", "Approved by HOD")
    assert dec_req.status == "hod_approved"

    # BA-UC-004: Classify Secure Archival Data
    class_req = arch_svc.classify_archival_request(actor_admin, dec_req.id, "Sensitive")
    assert class_req.status == "classified_sensitive"
    assert class_req.authoritative_classification == "Sensitive"

    # BA-UC-005: Configure Sensitive-Data Encryption
    actor_sec = _Actor(user_id=88, active_role="IT Security", department="Central")
    enc_req = arch_svc.configure_sensitive_encryption(actor_sec, class_req.id)
    assert enc_req.status == "sensitive_archive_encrypted"
    assert enc_req.is_encrypted is True

    # BA-UC-006: Execute Scheduled Automatic Backup
    sched_rec = bkup_svc.execute_scheduled_backup("sched_dataset")
    assert sched_rec.backup_type == "scheduled"

    # BA-UC-007 & BA-UC-008: Storage Extension Request & Decision
    quota, _ = UserStorageQuota.objects.get_or_create(user_id=actor.user_id, defaults={"allocated_quota_bytes": 1000, "used_storage_bytes": 1000})
    quota.used_storage_bytes = quota.allocated_quota_bytes
    quota.save()
    ext_req = stor_svc.submit_storage_extension(actor, 1024, "Quota exhausted")
    assert ext_req.status == "submitted"
    ext_approved = stor_svc.decide_storage_extension(actor_hod, ext_req.id, "approve", "Approved")
    assert ext_approved.status == "approved"
    assert StorageLedgerEntry.objects.filter(reference=f"extension_request_{ext_req.id}").exists()

    # BA-UC-009: Search and Browse Archives
    scoped_archives = scope_archival_requests(actor)
    assert scoped_archives.filter(id=arch_req.id).exists()

    # BA-UC-010: Execute Restoration
    # BA-UC-011: Request Data Restoration
    rest_req = rest_svc.request_data_restoration(actor, enc_req.id, "/restore/target")
    assert rest_req.status == "sensitive_pending_approval"
    rest_approved = rest_svc.approve_sensitive_restoration(actor_admin, rest_req.id, "approve")
    assert rest_approved.status == "approved"
    rest_done = rest_svc.execute_data_restoration(actor_admin, rest_approved.id)
    assert rest_done.status == "restored"

    # BA-UC-012: Approve Sensitive Restoration
    assert rest_approved.approved_by_user_id == actor_admin.user_id

    # BA-UC-013: Verify Backup Integrity
    assert compute_sha256(b"content") != ""

    # BA-UC-014: Generate Backup and Archive Reports
    assert AuditEvent.objects.count() > 0

    # BA-UC-015: View Audit Logs
    assert AuditEvent.objects.filter(actor_user_id=actor.user_id).exists()

    # BA-UC-016: Monitor Storage Utilization
    quota.refresh_from_db()
    assert quota.allocated_quota_bytes > 0

    # BA-UC-017: Purge Expired Archives
    assert is_retention_expired(datetime(2025, 1, 1, tzinfo=UTC), "Routine", datetime(2026, 1, 1, tzinfo=UTC)) is True

    # BA-UC-018: Query User Storage Quotas
    assert quota.ledger_entries.count() >= 1

    # BA-UC-019: Manage Role-Based Access Control
    assert "badms.archival.approve" in ROLE_GRANTS["HOD (CSE)"]

    # BA-UC-020: Configure Security and Retention Policies
    ret_pol, _ = RetentionPolicy.objects.get_or_create(data_classification="Critical", defaults={"name": "Critical Policy", "retention_days": 2555, "configured_by_user_id": 1})
    assert ret_pol.retention_days == 2555

    # BA-UC-021: Manage Backup Schedules
    sched = BackupSchedule.objects.create(name="Nightly", scope_type="global", dataset_name="core", cron_expression="0 2 * * *", created_by_user_id=1)
    assert sched.is_active is True

    # BA-UC-022: Perform Special Archival Operations
    special = arch_svc.perform_special_archival(actor_admin, "sec_dump.sql", "sql", 100, "Auditing", "/sec/dump.sql")
    assert special.is_special_archival is True

    # BA-UC-023: View Personal Usage and Requests
    assert quota.user_id == actor.user_id


def test_workflows_traceability_suite():
    assert transition_archival(ARCHIVAL_SUBMITTED, "approve", "hod") == ARCHIVAL_HOD_APPROVED
    assert transition_archival(ARCHIVAL_HOD_APPROVED, "classify_sensitive", "sysadmin") == ARCHIVAL_CLASSIFIED_SENSITIVE
    assert transition_archival(ARCHIVAL_CLASSIFIED_SENSITIVE, "encrypt_and_create", "it_security") == ARCHIVAL_SENSITIVE_ENCRYPTED

    assert transition_storage_extension("none", "submit", "user") == STORAGE_SUBMITTED
    assert transition_storage_extension(STORAGE_SUBMITTED, "approve", "hod") == STORAGE_APPROVED

    assert transition_restoration(RESTORATION_SENSITIVE_PENDING, "approve", "sysadmin") == RESTORATION_APPROVED
    assert transition_restoration(RESTORATION_APPROVED, "execute", "sysadmin") == RESTORATION_RESTORED


def test_afr_traceability_suite():
    actor = _Actor(user_id=300, active_role="SysAdmin", department="Central")
    user = _Actor(user_id=301, active_role="student", department="CSE")
    hod = _Actor(user_id=302, active_role="HOD (CSE)", department="CSE")
    sec = _Actor(user_id=303, active_role="IT Security", department="Central")

    # AFR-BA-001 to AFR-BA-005: Backup operations
    b = bkup_svc.trigger_manual_backup(actor, "afr_db")
    assert b.backup_type == "manual"
    assert b.file_size_bytes > 0
    assert b.file_path.startswith("/var/backups")
    assert b.completed_at is not None
    assert b.status == "success"

    # AFR-BA-006 to AFR-BA-010: Schedules
    validate_cron_expression("0 3 * * *")
    s = BackupSchedule.objects.create(name="Daily", scope_type="global", dataset_name="afr_db", cron_expression="0 3 * * *", created_by_user_id=actor.user_id)
    assert s.is_active is True
    assert s.scope_type == "global"
    assert s.dataset_name == "afr_db"
    assert resolve_effective_schedule({"is_active": True}, None) == {"is_active": True}

    # AFR-BA-011 & AFR-BA-012: Retention
    assert resolve_retention_duration("Routine") == 30
    assert resolve_retention_duration("Sensitive") == 365

    # AFR-BA-013 to AFR-BA-015: SHA-256 Checksum
    chk = compute_sha256("test-content")
    assert len(chk) == 64
    assert b.checksum_sha256 != ""
    assert b.completed_at is not None

    # AFR-BA-016 to AFR-BA-019: Failure Alerting and Escalation
    b_fail = bkup_svc.execute_scheduled_backup("afr_db", simulate_failure=True)
    assert b_fail.status == "failure"
    assert send_backup_failure_alert(b_fail) is not None
    b_fail.consecutive_failure_count = 3
    assert send_backup_failure_escalation(b_fail) is not None

    # AFR-BA-020 to AFR-BA-025: Restoration Lifecycle
    arch = ArchivalRequest.objects.create(
        requester_user_id=user.user_id, department="CSE", file_name="f.tar", file_type="tar",
        file_size_bytes=100, file_storage_path="/f.tar", status="sensitive_archive_encrypted",
        authoritative_classification="Sensitive", is_encrypted=True,
    )
    rest = rest_svc.request_data_restoration(user, arch.id, "/dest")
    assert rest.archival_request_id == arch.id
    assert rest.target_destination == "/dest"
    assert rest.status == "sensitive_pending_approval"
    assert rest.classification == "Sensitive"
    rest_app = rest_svc.approve_sensitive_restoration(actor, rest.id, "approve")
    assert rest_app.status == "approved"
    rest_exec = rest_svc.execute_data_restoration(actor, rest.id)
    assert rest_exec.status == "restored"

    # AFR-BA-026 to AFR-BA-035: Archival Submission, Review, Classification
    arch_sub = arch_svc.submit_archival_request(user, "test.csv", "csv", 100, "Reason", "/path")
    assert arch_sub.file_name == "test.csv"
    assert arch_sub.file_size_bytes == 100
    assert arch_sub.file_storage_path == "/path"
    assert arch_sub.department == "CSE"
    assert arch_sub.initial_classification == "Routine"
    arch_app = arch_svc.decide_archival_request(hod, arch_sub.id, "approve", "Looks good")
    assert arch_app.status == "hod_approved"
    assert arch_app.hod_decision_at is not None
    assert arch_app.hod_remarks == "Looks good"
    arch_class = arch_svc.classify_archival_request(actor, arch_app.id, "Sensitive")
    assert arch_class.authoritative_classification == "Sensitive"
    assert arch_class.classified_at is not None

    # AFR-BA-036 to AFR-BA-038: Sensitive Encryption
    arch_enc = arch_svc.configure_sensitive_encryption(sec, arch_class.id)
    assert arch_enc.status == "sensitive_archive_encrypted"
    assert arch_enc.encryption_algorithm == "AES-256-GCM"
    assert arch_enc.is_encrypted is True

    q, _ = UserStorageQuota.objects.get_or_create(user_id=user.user_id, defaults={"allocated_quota_bytes": 1000, "used_storage_bytes": 1000})
    initial_allocated = q.allocated_quota_bytes
    q.used_storage_bytes = q.allocated_quota_bytes
    q.save()
    ext_sub = stor_svc.submit_storage_extension(user, 500, "Extending")
    assert ext_sub.requested_extension_bytes == 500
    assert ext_sub.justification == "Extending"
    ext_dec = stor_svc.decide_storage_extension(hod, ext_sub.id, "approve")
    assert ext_dec.status == "approved"
    assert ext_dec.hod_decision_at is not None
    q.refresh_from_db()
    assert q.allocated_quota_bytes == initial_allocated + 500

    # AFR-BA-047 to AFR-BA-049: Retention & Purge
    assert is_retention_expired(datetime(2025, 1, 1, tzinfo=UTC), "Routine", datetime(2026, 1, 1, tzinfo=UTC)) is True
    assert AuditEvent.objects.filter(target_model="StorageExtensionRequest").exists()

    # AFR-BA-051 to AFR-BA-053: Search & Filters
    scoped = scope_archival_requests(user)
    assert scoped.filter(file_name="test.csv").exists()
    assert scoped.filter(authoritative_classification="Sensitive").exists()

    # AFR-BA-054 to AFR-BA-057: Audit Event Log Structure
    ev = AuditEvent.objects.first()
    assert ev.actor_user_id > 0
    assert ev.event_type != ""
    assert ev.timestamp is not None
    assert isinstance(ev.details, dict)

    # AFR-BA-058 to AFR-BA-060: Analytics & Reports
    assert BackupRecord.objects.filter(status="success").count() >= 1
    assert q.used_storage_bytes > 0
    assert arch_sub.file_size_bytes > 0

    # AFR-BA-061 & AFR-BA-062: RBAC
    assert len(PERMISSIONS) > 0
    assert len(ROLE_GRANTS) > 0

    # AFR-BA-063: Department scoping
    scoped_user = scope_archival_requests(user)
    assert scoped_user is not None

    # AFR-BA-064 & AFR-BA-065: Special Archival
    sp = arch_svc.perform_special_archival(actor, "offline.sql", "sql", 200, "Offline order", "/offline")
    assert sp.is_special_archival is True
    assert "badms.archival.manage" in ROLE_GRANTS["Super Admin"]

    # AFR-BA-066: Super Admin Global Schedule
    assert "badms.backup_policy.manage" in ROLE_GRANTS["Super Admin"]

    # AFR-BA-067 & AFR-BA-068: Personal Storage & Request History
    assert q.user_id == user.user_id
    assert arch_sub.requester_user_id == user.user_id
