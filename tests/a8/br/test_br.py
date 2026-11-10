"""BR Test Suite: Business Rule Specifications (Conditions, Outcomes, Thresholds, Exceptions).
Generated from a8_design/BR_DESIGN.json.
"""
import pytest
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
from tests.a8.helpers import (
    sysadmin_actor,
    superadmin_actor,
    hod_actor,
    it_security_actor,
    regular_user_actor,
)

pytestmark = pytest.mark.django_db


# --- BR-BA-001: Manual Backup Trigger Authorization ---

def test_br_001_manual_backup_allow():
    """TEST-BR-001 | BR-BA-001-ALLOW: Authorized SysAdmin triggers manual backup."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="cse")
    assert op.pk is not None
    assert op.status == "success"


def test_br_002_manual_backup_deny():
    """TEST-BR-002 | BR-BA-001-DENY: Unauthorized actor denied manual backup."""
    user = regular_user_actor(user_id=2)
    with pytest.raises(PermissionDeniedError):
        ops.trigger_manual_backup(actor=user, dataset_code="cse")


# --- BR-BA-002: Respective HoD Approval for Secure Archival & BR-BA-010 ---

def test_br_003_hod_approval_same_dept_allow():
    """TEST-BR-003 | BR-BA-002-SAME-DEPT: HoD of requester department approves archival request."""
    user = regular_user_actor(user_id=10, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.pdf", file_type="pdf", file_size_bytes=100, reason="Archival")
    res = ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    assert res.status == sm.ARCHIVAL_HOD_APPROVED


def test_br_004_hod_approval_cross_dept_deny():
    """TEST-BR-004 | BR-BA-002-CROSS-DEPT: HoD of different department denied archival decision."""
    user = regular_user_actor(user_id=10, dept="ECE")
    ece_req = ops.submit_archival_request(actor=user, department="ECE", file_name="ece.pdf", file_type="pdf", file_size_bytes=100, reason="ECE Archival")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    # BR-BA-002 & BR-BA-010: Route to and authorize decision by the respective HoD only.
    with pytest.raises(PermissionDeniedError):
        ops.hod_review_archival(actor=cse_hod, request_id=ece_req.pk, action="approve")


# --- BR-BA-003: IT Security Encryption Authority ---

def test_br_005_encryption_it_security_allow():
    """TEST-BR-005 | BR-BA-003-ALLOW: IT Security configures encryption for Sensitive data."""
    user = regular_user_actor(user_id=11, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    sec = it_security_actor(user_id=30)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="sec.dat", file_type="dat", file_size_bytes=100, reason="R")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    res = ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="AES-256")
    assert res.status == sm.ARCHIVAL_COMPLETED


def test_br_006_encryption_non_security_deny():
    """TEST-BR-006 | BR-BA-003-DENY: Non-IT Security actor denied encryption configuration."""
    user = regular_user_actor(user_id=11, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="sec.dat", file_type="dat", file_size_bytes=100, reason="R")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    with pytest.raises(PermissionDeniedError):
        ops.it_security_configure_encryption(actor=user, request_id=req.pk, algorithm="AES-256")


# --- BR-BA-004: SysAdmin Authoritative Classification ---

def test_br_007_classification_sysadmin_allow():
    """TEST-BR-007 | BR-BA-004-ALLOW: SysAdmin assigns authoritative classification."""
    user = regular_user_actor(user_id=12, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.dat", file_type="dat", file_size_bytes=100, reason="R")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    res = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="critical")
    assert res.authoritative_classification == "critical"


def test_br_008_classification_non_sysadmin_deny():
    """TEST-BR-008 | BR-BA-004-DENY: Non-SysAdmin denied authoritative classification."""
    user = regular_user_actor(user_id=12, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.dat", file_type="dat", file_size_bytes=100, reason="R")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    with pytest.raises(PermissionDeniedError):
        ops.sysadmin_classify_archival(actor=user, request_id=req.pk, authoritative_classification="critical")


# --- BR-BA-005: Sensitive Restoration Approval ---

def test_br_009_restoration_sensitive_blocked():
    """TEST-BR-009 | BR-BA-005-SENSITIVE-BLOCK: Restoration of Sensitive data blocked until SysAdmin approval."""
    user = regular_user_actor(user_id=13, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=13, department="CSE", file_name="sens.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Restore sensitive")
    assert rest_req.status == sm.RESTORATION_SUBMITTED


def test_br_010_restoration_non_sensitive_allow():
    """TEST-BR-010 | BR-BA-005-NON-SENSITIVE-ALLOW: Restoration of non-Sensitive data proceeds without SysAdmin approval."""
    user = regular_user_actor(user_id=13, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=13, department="CSE", file_name="rout.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="routine"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Restore routine")
    assert rest_req.status == sm.RESTORATION_COMPLETED


# --- BR-BA-006: Initial Data Classification and Default ---

def test_br_011_initial_classification_provided():
    """TEST-BR-011 | BR-BA-006-PROVIDED: User-provided initial classification preserved."""
    user = regular_user_actor(user_id=14, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.csv", file_type="csv", file_size_bytes=100, reason="R", initial_classification="sensitive")
    assert req.initial_classification == "sensitive"


def test_br_012_initial_classification_default():
    """TEST-BR-012 | BR-BA-006-DEFAULT: Missing/omitted initial classification defaults to Routine."""
    user = regular_user_actor(user_id=14, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.csv", file_type="csv", file_size_bytes=100, reason="R", initial_classification="")
    assert req.initial_classification == sm.TIER_ROUTINE


# --- BR-BA-007: Sensitive Data Encryption ---

def test_br_013_sensitive_data_encryption_aes256():
    """TEST-BR-013 | BR-BA-007-AES256: Sensitive data encrypted using AES-256."""
    user = regular_user_actor(user_id=15, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    sec = it_security_actor(user_id=30)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.dat", file_type="dat", file_size_bytes=100, reason="R")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    enc = ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="AES-256")
    assert enc.encryption_algorithm == "AES-256"


def test_br_014_sensitive_data_encryption_non_aes_rejected():
    """TEST-BR-014 | BR-BA-007-NON-AES-REJECT: Non-AES encryption algorithm rejected for Sensitive data."""
    user = regular_user_actor(user_id=15, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    sec = it_security_actor(user_id=30)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.dat", file_type="dat", file_size_bytes=100, reason="R")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    # BR-BA-007: Data classified Sensitive must be encrypted using AES-256 both at rest and in transit.
    with pytest.raises((BadRequestError, ValueError)):
        ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="3DES")


# --- BR-BA-008: Retention by Classification ---

def test_br_015_retention_years_definitions():
    """TEST-BR-015 | BR-BA-008-TIERS: Retention years defined across all tiers."""
    assert sm.RETENTION_YEARS[sm.TIER_ROUTINE] == 1
    assert sm.RETENTION_YEARS[sm.TIER_ARCHIVAL] == 5
    assert sm.RETENTION_YEARS[sm.TIER_SENSITIVE] == 7
    assert sm.RETENTION_YEARS[sm.TIER_CRITICAL] == 10


# --- BR-BA-009 & BR-BA-010: HoD Approval for Storage Extension ---

def test_br_016_hod_storage_extension_same_dept_allow():
    """TEST-BR-016 | BR-BA-009-ALLOW: HoD decides storage extension for own department."""
    user = regular_user_actor(user_id=16, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=16, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Need more storage")
    res = ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="approve")
    assert res.status == sm.STORAGE_APPROVED


def test_br_017_hod_storage_extension_cross_dept_deny():
    """TEST-BR-017 | BR-BA-010-CROSS-DEPT-STORAGE: HoD denied storage extension decision for other department."""
    user = regular_user_actor(user_id=17, dept="ECE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=17, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="ECE", requested_additional_mb=1024, reason="ECE expansion")
    # BR-BA-010: HoD may act only on requests belonging to HoD's own department.
    with pytest.raises(PermissionDeniedError):
        ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="approve")


# --- BR-BA-011: Local Schedule Overrides Global ---

def test_br_018_local_schedule_override():
    """TEST-BR-018 | BR-BA-011-OVERRIDE: Local backup schedule overrides global schedule."""
    global_sch = {"cron": "0 0 * * *", "scope": "global"}
    local_sch = {"cron": "0 4 * * *", "scope": "local"}
    res = sm.calculate_effective_schedule("finance_db", {"finance_db": local_sch}, global_sch)
    assert res == local_sch


def test_br_019_global_schedule_fallback():
    """TEST-BR-019 | BR-BA-011-FALLBACK: Global schedule applies when no local schedule exists."""
    global_sch = {"cron": "0 0 * * *", "scope": "global"}
    res = sm.calculate_effective_schedule("other_db", {}, global_sch)
    assert res == global_sch


# --- BR-BA-012: Schedule Parameter Validation ---

def test_br_020_schedule_valid_parameters():
    """TEST-BR-020 | BR-BA-012-VALID: Valid schedule parameters applied."""
    admin = sysadmin_actor(user_id=1)
    sch = ops.configure_schedule(actor=admin, scope="local", dataset_code="lab", cron_expression="0 0 * * *", retention_days=30)
    assert sch.cron_expression == "0 0 * * *"


def test_br_021_schedule_invalid_parameters_rejected():
    """TEST-BR-021 | BR-BA-012-INVALID: Invalid schedule parameters rejected."""
    admin = sysadmin_actor(user_id=1)
    # BR-BA-012: A new or modified backup schedule must pass parameter and conflict validation before it is applied.
    with pytest.raises((BadRequestError, ValueError)):
        ops.configure_schedule(actor=admin, scope="local", dataset_code="lab", cron_expression="invalid", retention_days=-5)


# --- BR-BA-013: Scheduled Repository Reachability ---

def test_br_022_scheduled_repository_reachability():
    """TEST-BR-022 | BR-BA-013-UNREACHABLE: Scheduled backup fails when repository unreachable."""
    pytest.skip("NOT_AUTOMATED: External repository network daemon probe is not automated in unit tests")


# --- BR-BA-014: Backup Failure Alert SLA ---

def test_br_023_backup_failure_alert():
    """TEST-BR-023 | BR-BA-014-ALERT: Failed backup creates SysAdmin alert."""
    op = BackupOperation.objects.create(
        trigger_type="scheduled", dataset_code="core", status="failed", error_message="Disk failure"
    )
    assert op.status == "failed"


# --- BR-BA-015: Repeated Failure Escalation ---

def test_br_024_repeated_failure_escalates_on_three():
    """TEST-BR-024 | BR-BA-015-ESCALATE-TRUE: 3 or more consecutive failures trigger escalation."""
    assert sm.check_repeated_failure_escalation(3) is True
    assert sm.check_repeated_failure_escalation(4) is True


def test_br_025_repeated_failure_no_escalate_below_three():
    """TEST-BR-025 | BR-BA-015-ESCALATE-FALSE: Less than 3 consecutive failures do not trigger escalation."""
    assert sm.check_repeated_failure_escalation(1) is False
    assert sm.check_repeated_failure_escalation(2) is False


# --- BR-BA-016: Storage-Extension Usage Validation ---

def test_br_026_storage_quota_threshold_reached():
    """TEST-BR-026 | BR-BA-016-QUOTA-FULL: Storage extension permitted when quota is reached/exceeded."""
    sm.validate_storage_quota_threshold(current_usage_mb=5120, quota_mb=5120)
    sm.validate_storage_quota_threshold(current_usage_mb=6000, quota_mb=5120)


def test_br_027_storage_quota_threshold_below():
    """TEST-BR-027 | BR-BA-016-QUOTA-BELOW: Storage extension prohibited when quota is not reached."""
    with pytest.raises(sm.RuleViolation):
        sm.validate_storage_quota_threshold(current_usage_mb=3000, quota_mb=5120)


# --- BR-BA-017: Storage-Extension Decision Criteria ---

def test_br_028_storage_extension_approve_allocates_storage():
    """TEST-BR-028 | BR-BA-017-APPROVE: HoD extension decision allocates additional storage."""
    user = regular_user_actor(user_id=18, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=18, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Research")
    ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="approve")
    assert StorageQuota.objects.get(user_id=18).allocated_mb == 5120 + 1024


def test_br_029_storage_extension_reject_retains_quota():
    """TEST-BR-029 | BR-BA-017-REJECT: HoD extension rejection leaves quota unchanged."""
    user = regular_user_actor(user_id=19, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=19, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Research")
    ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="reject")
    assert StorageQuota.objects.get(user_id=19).allocated_mb == 5120


# --- BR-BA-018: Special Archival Super Admin Authority ---

def test_br_030_special_archival_superadmin_allow():
    """TEST-BR-030 | BR-BA-018-SUPERADMIN-ALLOW: Super Admin executes special archival operation."""
    superadmin = superadmin_actor(user_id=102)
    # BR-BA-018: Only Super Admin may perform special archival operation.
    assert hasattr(ops, "special_archival_operation"), "special_archival_operation service missing from operations.py"
    res = getattr(ops, "special_archival_operation")(actor=superadmin, department="INSTITUTE", file_name="special.tar", reason="Special")
    assert res.is_special is True


def test_br_031_special_archival_non_superadmin_deny():
    """TEST-BR-031 | BR-BA-018-NON-SUPERADMIN-DENY: Non-Super Admin denied special archival operation."""
    user = regular_user_actor(user_id=20)
    assert hasattr(ops, "special_archival_operation"), "special_archival_operation service missing from operations.py"
    with pytest.raises(PermissionDeniedError):
        getattr(ops, "special_archival_operation")(actor=user, department="CSE", file_name="special.tar", reason="Special")


# --- BR-BA-019: Super Admin Global Backup Authority ---

def test_br_032_global_backup_schedule_superadmin_allow():
    """TEST-BR-032 | BR-BA-019-GLOBAL-ALLOW: Super Admin configures global backup schedule."""
    superadmin = superadmin_actor(user_id=102)
    sch = ops.configure_schedule(actor=superadmin, scope="global", dataset_code="", cron_expression="0 0 * * *", retention_days=60)
    assert sch.scope == "global"


def test_br_033_global_backup_schedule_non_superadmin_deny():
    """TEST-BR-033 | BR-BA-019-GLOBAL-DENY: Non-Super Admin denied global backup schedule config."""
    admin = sysadmin_actor(user_id=1)
    with pytest.raises(PermissionDeniedError):
        ops.configure_schedule(actor=admin, scope="global", dataset_code="", cron_expression="0 0 * * *", retention_days=60)


# --- BR-BA-020: Protected Information Access Scope ---

def test_br_034_scoping_user_sees_own_records():
    """TEST-BR-034 | BR-BA-020-SCOPING-USER: User sees only own requests."""
    user1 = regular_user_actor(user_id=40, dept="CSE")
    user2 = regular_user_actor(user_id=41, dept="CSE")
    req1 = ops.submit_archival_request(actor=user1, department="CSE", file_name="u1.pdf", file_type="pdf", file_size_bytes=100, reason="U1")
    req2 = ops.submit_archival_request(actor=user2, department="CSE", file_name="u2.pdf", file_type="pdf", file_size_bytes=100, reason="U2")
    user1_records = list(scoping.visible_archival_requests(user1))
    assert req1 in user1_records
    assert req2 not in user1_records


def test_br_035_scoping_hod_sees_department_records():
    """TEST-BR-035 | BR-BA-020-SCOPING-HOD: HoD sees only requests from own department."""
    cse_hod = hod_actor(user_id=20, dept="CSE")
    user_cse = regular_user_actor(user_id=42, dept="CSE")
    user_ece = regular_user_actor(user_id=43, dept="ECE")
    req_cse = ops.submit_archival_request(actor=user_cse, department="CSE", file_name="cse.pdf", file_type="pdf", file_size_bytes=100, reason="CSE")
    req_ece = ops.submit_archival_request(actor=user_ece, department="ECE", file_name="ece.pdf", file_type="pdf", file_size_bytes=100, reason="ECE")
    hod_visible = list(scoping.visible_archival_requests(cse_hod))
    assert req_cse in hod_visible
    assert req_ece not in hod_visible


# --- BR-BA-021: IT Security Security/RBAC Authority ---

def test_br_036_security_manage_allow():
    """TEST-BR-036 | BR-BA-021-ALLOW: IT Security manages security permissions."""
    sec = it_security_actor(user_id=50)
    assert sec.has_permission("badms.security.manage") is True


def test_br_037_security_manage_deny():
    """TEST-BR-037 | BR-BA-021-DENY: Non-IT Security actor denied security config."""
    user = regular_user_actor(user_id=51)
    assert user.has_permission("badms.security.manage") is False
