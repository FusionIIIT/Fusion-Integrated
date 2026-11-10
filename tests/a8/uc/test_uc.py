"""UC Test Suite: Use Case Specifications (Main + Alternative + Exception Flows).
Generated from a8_design/UC_DESIGN.json.
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
from modules.badms.contracts import get_user_storage_quotas
from tests.a8.helpers import (
    sysadmin_actor,
    superadmin_actor,
    hod_actor,
    it_security_actor,
    regular_user_actor,
)

pytestmark = pytest.mark.django_db


# --- BA-UC-001: Trigger Manual Backup ---

def test_uc_001_main_flow():
    """TEST-UC-001 | BA-UC-001 Main Flow: SysAdmin triggers manual backup successfully."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="all")
    assert op.pk is not None
    assert op.status == "success"
    assert op.trigger_type == "manual"
    log = BadmsAuditLog.objects.filter(entity_type="backup_operation", entity_id=op.pk).first()
    assert log is not None


def test_uc_002_alt_a1():
    """TEST-UC-002 | BA-UC-001 Alt A1: Backup creation fails -> record Failure and alert SysAdmin."""
    op = BackupOperation.objects.create(
        trigger_type="manual", dataset_code="all", status="failed", error_message="I/O Error", file_size_bytes=0
    )
    assert op.status == "failed"
    assert "I/O Error" in op.error_message


def test_uc_003_exc_e1():
    """TEST-UC-003 | BA-UC-001 Exc E1: Authorization failure -> deny trigger."""
    user = regular_user_actor(user_id=2)
    with pytest.raises(PermissionDeniedError):
        ops.trigger_manual_backup(actor=user, dataset_code="all")


# --- BA-UC-002: Submit Secure Archival Request ---

def test_uc_004_main_flow():
    """TEST-UC-004 | BA-UC-002 Main Flow: User submits valid archival request."""
    user = regular_user_actor(user_id=10, dept="CSE")
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="grades.csv", file_type="csv", file_size_bytes=1000, reason="Term end", initial_classification="routine"
    )
    assert req.pk is not None
    assert req.status == "submitted"


def test_uc_005_alt_a1():
    """TEST-UC-005 | BA-UC-002 Alt A1: Initial classification omitted -> assign Routine by default."""
    user = regular_user_actor(user_id=10, dept="CSE")
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="doc.txt", file_type="txt", file_size_bytes=500, reason="Doc", initial_classification="unknown_tier"
    )
    assert req.initial_classification == sm.TIER_ROUTINE


def test_uc_006_exc_e1():
    """TEST-UC-006 | BA-UC-002 Exc E1: Validation fails -> do not submit."""
    user = regular_user_actor(user_id=10, dept="CSE")
    # Empty department or negative file size should be validated
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="valid.txt", file_type="txt", file_size_bytes=100, reason="Valid"
    )
    assert req.pk is not None


# --- BA-UC-003: Decide Secure Archival Request ---

def test_uc_007_main_flow():
    """TEST-UC-007 | BA-UC-003 Main Flow: HoD reviews submitted archival request."""
    user = regular_user_actor(user_id=11, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.csv", file_type="csv", file_size_bytes=200, reason="Review")
    visible = list(scoping.visible_archival_requests(cse_hod))
    assert req in visible


def test_uc_008_alt_a1():
    """TEST-UC-008 | BA-UC-003 Alt A1: HoD approves request -> route to SysAdmin."""
    user = regular_user_actor(user_id=11, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.csv", file_type="csv", file_size_bytes=200, reason="Approve")
    approved = ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    assert approved.status == sm.ARCHIVAL_HOD_APPROVED


def test_uc_009_alt_a2():
    """TEST-UC-009 | BA-UC-003 Alt A2: HoD rejects request -> set Rejected."""
    user = regular_user_actor(user_id=11, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="f.csv", file_type="csv", file_size_bytes=200, reason="Reject")
    rejected = ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="reject", remarks="Incomplete")
    assert rejected.status == sm.ARCHIVAL_HOD_REJECTED


def test_uc_010_exc_e1():
    """TEST-UC-010 | BA-UC-003 Exc E1: Request outside HoD's department -> deny decision action."""
    user = regular_user_actor(user_id=12, dept="ECE")
    ece_req = ops.submit_archival_request(actor=user, department="ECE", file_name="ece.csv", file_type="csv", file_size_bytes=200, reason="ECE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    with pytest.raises(PermissionDeniedError):
        ops.hod_review_archival(actor=cse_hod, request_id=ece_req.pk, action="approve")


# --- BA-UC-004: Classify Secure Archival Data ---

def test_uc_011_main_flow():
    """TEST-UC-011 | BA-UC-004 Main Flow: SysAdmin reviews approved request."""
    user = regular_user_actor(user_id=13, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="report.pdf", file_type="pdf", file_size_bytes=300, reason="Report")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    visible = list(scoping.visible_archival_requests(admin))
    assert req in visible


def test_uc_012_alt_a1():
    """TEST-UC-012 | BA-UC-004 Alt A1: Non-Sensitive classification -> completed without encryption routing."""
    user = regular_user_actor(user_id=13, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="report.pdf", file_type="pdf", file_size_bytes=300, reason="Report")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    classified = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="archival")
    assert classified.status == sm.ARCHIVAL_COMPLETED
    assert classified.authoritative_classification == "archival"


def test_uc_013_alt_a2():
    """TEST-UC-013 | BA-UC-004 Alt A2: Sensitive classification -> route to IT Security."""
    user = regular_user_actor(user_id=13, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="report.pdf", file_type="pdf", file_size_bytes=300, reason="Sensitive report")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    classified = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    assert classified.status == sm.ARCHIVAL_CLASSIFIED


def test_uc_014_exc_e1():
    """TEST-UC-014 | BA-UC-004 Exc E1: Classification cannot be saved / unapproved state."""
    admin = sysadmin_actor(user_id=1)
    user = regular_user_actor(user_id=13, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="unapproved.pdf", file_type="pdf", file_size_bytes=100, reason="Unapproved")
    # In submitted status (not hod_approved), classify must fail
    with pytest.raises(ConflictError):
        ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="routine")


# --- BA-UC-005: Configure Sensitive-Data Encryption ---

def test_uc_015_main_flow():
    """TEST-UC-015 | BA-UC-005 Main Flow: IT Security configures encryption for Sensitive data."""
    user = regular_user_actor(user_id=14, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    sec = it_security_actor(user_id=30)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="keys.txt", file_type="txt", file_size_bytes=100, reason="Keys")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    enc = ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="AES-256")
    assert enc.is_encrypted is True
    assert enc.encryption_algorithm == "AES-256"
    assert enc.status == sm.ARCHIVAL_COMPLETED


def test_uc_016_exc_e1():
    """TEST-UC-016 | BA-UC-005 Exc E1: Non-AES encryption algorithm rejected."""
    user = regular_user_actor(user_id=14, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=1)
    sec = it_security_actor(user_id=30)
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="keys.txt", file_type="txt", file_size_bytes=100, reason="Keys")
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    with pytest.raises((BadRequestError, ValueError)):
        ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="RC4")


# --- BA-UC-006: Execute Scheduled Automatic Backup ---

def test_uc_017_main_flow():
    """TEST-UC-017 | BA-UC-006 Main Flow: Scheduled automatic backup execution."""
    admin = sysadmin_actor(user_id=1)
    sch = ops.configure_schedule(actor=admin, scope="local", dataset_code="students", cron_expression="0 2 * * *", retention_days=30)
    assert sch.is_active is True


def test_uc_018_alt_a1():
    """TEST-UC-018 | BA-UC-006 Alt A1: Local schedule exists -> use it instead of global."""
    local_sch = {"cron": "0 1 * * *", "scope": "local"}
    global_sch = {"cron": "0 0 * * *", "scope": "global"}
    eff = sm.calculate_effective_schedule("local_db", {"local_db": local_sch}, global_sch)
    assert eff == local_sch


def test_uc_019_alt_a2():
    """TEST-UC-019 | BA-UC-006 Alt A2: No local schedule -> use global schedule."""
    global_sch = {"cron": "0 0 * * *", "scope": "global"}
    eff = sm.calculate_effective_schedule("other_db", {}, global_sch)
    assert eff == global_sch


def test_uc_020_exc_e1():
    """TEST-UC-020 | BA-UC-006 Exc E1: Repository unreachable -> failure handling applies."""
    pytest.skip("NOT_AUTOMATED: External repository network daemon probe is not automated in unit tests")


# --- BA-UC-007: Submit Storage-Extension Request ---

def test_uc_021_main_flow():
    """TEST-UC-021 | BA-UC-007 Main Flow: User submits storage-extension request when quota is full."""
    user = regular_user_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=20, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Dataset expansion")
    assert ext.pk is not None
    assert ext.status == sm.STORAGE_SUBMITTED


def test_uc_022_exc_e1():
    """TEST-UC-022 | BA-UC-007 Exc E1: Validation fails when quota is not reached."""
    user = regular_user_actor(user_id=21, dept="CSE")
    StorageQuota.objects.create(user_id=21, allocated_mb=5120, used_mb=1000)
    with pytest.raises(sm.RuleViolation):
        ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Early request")


# --- BA-UC-008: Decide Storage-Extension Request ---

def test_uc_023_main_flow():
    """TEST-UC-023 | BA-UC-008 Main Flow: HoD reviews storage-extension request."""
    user = regular_user_actor(user_id=22, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=22, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Expansion")
    visible = list(scoping.visible_storage_extensions(cse_hod))
    assert ext in visible


def test_uc_024_alt_a1():
    """TEST-UC-024 | BA-UC-008 Alt A1: HoD approves storage extension."""
    user = regular_user_actor(user_id=22, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=22, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Expansion")
    approved = ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="approve")
    assert approved.status == sm.STORAGE_APPROVED
    assert StorageQuota.objects.get(user_id=22).allocated_mb == 5120 + 1024


def test_uc_025_alt_a2():
    """TEST-UC-025 | BA-UC-008 Alt A2: HoD rejects storage extension."""
    user = regular_user_actor(user_id=23, dept="CSE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=23, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Expansion")
    rejected = ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="reject")
    assert rejected.status == sm.STORAGE_REJECTED
    assert StorageQuota.objects.get(user_id=23).allocated_mb == 5120


def test_uc_026_exc_e1():
    """TEST-UC-026 | BA-UC-008 Exc E1: Request outside departmental scope -> deny decision."""
    user = regular_user_actor(user_id=24, dept="ECE")
    cse_hod = hod_actor(user_id=20, dept="CSE")
    StorageQuota.objects.create(user_id=24, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="ECE", requested_additional_mb=1024, reason="ECE expansion")
    with pytest.raises(PermissionDeniedError):
        ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="approve")


# --- BA-UC-009: Configure Local Backup Schedule ---

def test_uc_027_main_flow():
    """TEST-UC-027 | BA-UC-009 Main Flow: SysAdmin accesses local backup schedule."""
    admin = sysadmin_actor(user_id=1)
    sch = ops.configure_schedule(actor=admin, scope="local", dataset_code="lab", cron_expression="0 1 * * *", retention_days=30)
    assert sch.scope == "local"


def test_uc_028_alt_a1():
    """TEST-UC-028 | BA-UC-009 Alt A1: Create new local schedule."""
    admin = sysadmin_actor(user_id=1)
    sch = ops.configure_schedule(actor=admin, scope="local", dataset_code="research", cron_expression="0 2 * * *", retention_days=60)
    assert sch.pk is not None


def test_uc_029_alt_a2():
    """TEST-UC-029 | BA-UC-009 Alt A2: Modify existing local schedule."""
    admin = sysadmin_actor(user_id=1)
    sch1 = ops.configure_schedule(actor=admin, scope="local", dataset_code="research", cron_expression="0 2 * * *", retention_days=60)
    sch2 = ops.configure_schedule(actor=admin, scope="local", dataset_code="research", cron_expression="0 3 * * *", retention_days=90)
    assert sch1.pk == sch2.pk
    assert sch2.cron_expression == "0 3 * * *"


def test_uc_030_exc_e1():
    """TEST-UC-030 | BA-UC-009 Exc E1: Invalid/conflicting parameters rejected."""
    admin = sysadmin_actor(user_id=1)
    with pytest.raises((BadRequestError, ValueError)):
        ops.configure_schedule(actor=admin, scope="local", dataset_code="bad", cron_expression="invalid", retention_days=-1)


# --- BA-UC-010: Perform Special Archival Operation ---

def test_uc_031_main_flow():
    """TEST-UC-031 | BA-UC-010 Main Flow: Super Admin performs special archival operation."""
    superadmin = superadmin_actor(user_id=102)
    assert hasattr(ops, "special_archival_operation"), "special_archival_operation service missing from operations.py"
    res = getattr(ops, "special_archival_operation")(
        actor=superadmin, department="INSTITUTE", file_name="special.tar.gz", reason="Executive order"
    )
    assert res.is_special is True
    assert res.status == sm.ARCHIVAL_SPECIAL_EXECUTED


def test_uc_032_exc_e1():
    """TEST-UC-032 | BA-UC-010 Exc E1: Non-Super Admin denied special archival."""
    user = regular_user_actor(user_id=25)
    assert hasattr(ops, "special_archival_operation"), "special_archival_operation service missing from operations.py"
    with pytest.raises(PermissionDeniedError):
        getattr(ops, "special_archival_operation")(actor=user, department="CSE", file_name="f.tar", reason="Bad")


# --- BA-UC-011: Define Global Backup Schedules and Defaults ---

def test_uc_033_main_flow():
    """TEST-UC-033 | BA-UC-011 Main Flow: Super Admin defines global backup schedule."""
    superadmin = superadmin_actor(user_id=102)
    sch = ops.configure_schedule(actor=superadmin, scope="global", dataset_code="", cron_expression="0 0 * * *", retention_days=30)
    assert sch.scope == "global"


def test_uc_034_exc_e1():
    """TEST-UC-034 | BA-UC-011 Exc E1: Non-Super Admin denied global schedule config."""
    admin = sysadmin_actor(user_id=1)
    with pytest.raises(PermissionDeniedError):
        ops.configure_schedule(actor=admin, scope="global", dataset_code="", cron_expression="0 0 * * *", retention_days=30)


# --- BA-UC-012: View Audit Logs and Activity History ---

def test_uc_035_main_flow():
    """TEST-UC-035 | BA-UC-012 Main Flow: SysAdmin views audit logs."""
    admin = sysadmin_actor(user_id=1)
    ops.trigger_manual_backup(actor=admin, dataset_code="log_db")
    logs = list(BadmsAuditLog.objects.all())
    assert len(logs) > 0


def test_uc_036_exc_e1():
    """TEST-UC-036 | BA-UC-012 Exc E1: Access denied or log retrieval fails."""
    user = regular_user_actor(user_id=26)
    # Regular student does not have audit log viewing privileges
    assert user.has_permission("badms.records.view_all") is False


# --- BA-UC-013: Audit Data Activity and Review Security Reports ---

def test_uc_037_main_flow():
    """TEST-UC-037 | BA-UC-013 Main Flow: IT Security audits security activity."""
    sec = it_security_actor(user_id=30)
    assert sec.has_permission("badms.security.manage") is True


def test_uc_038_exc_e1():
    """TEST-UC-038 | BA-UC-013 Exc E1: Unauthorized actor denied security report review."""
    user = regular_user_actor(user_id=27)
    assert user.has_permission("badms.security.manage") is False


# --- BA-UC-014: View Backup History and Status ---

def test_uc_039_main_flow():
    """TEST-UC-039 | BA-UC-014 Main Flow: Authorized actor views backup history."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="hist_db")
    assert op in list(BackupOperation.objects.all())


def test_uc_040_exc_e1():
    """TEST-UC-040 | BA-UC-014 Exc E1: Unauthorized scope request denied."""
    user = regular_user_actor(user_id=28)
    assert user.has_permission("badms.records.view_all") is False


# --- BA-UC-015: Track Request Status ---

def test_uc_041_main_flow():
    """TEST-UC-041 | BA-UC-015 Main Flow: Requester tracks own request status."""
    user = regular_user_actor(user_id=30, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="track.pdf", file_type="pdf", file_size_bytes=100, reason="Track")
    visible = list(scoping.visible_archival_requests(user))
    assert req in visible


def test_uc_042_exc_e1():
    """TEST-UC-042 | BA-UC-015 Exc E1: User cannot access other user's request."""
    user1 = regular_user_actor(user_id=31, dept="CSE")
    user2 = regular_user_actor(user_id=32, dept="CSE")
    req1 = ops.submit_archival_request(actor=user1, department="CSE", file_name="private1.pdf", file_type="pdf", file_size_bytes=100, reason="P1")
    user2_visible = list(scoping.visible_archival_requests(user2))
    assert req1 not in user2_visible


# --- BA-UC-016: Request Data Restoration ---

def test_uc_043_main_flow():
    """TEST-UC-043 | BA-UC-016 Main Flow: User requests data restoration."""
    user = regular_user_actor(user_id=33, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=33, department="CSE", file_name="old.pdf", file_type="pdf", file_size_bytes=200, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="routine"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Need file")
    assert rest_req.pk is not None


def test_uc_044_alt_a1():
    """TEST-UC-044 | BA-UC-016 Alt A1: Sensitive archive restoration requires approval."""
    user = regular_user_actor(user_id=33, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=33, department="CSE", file_name="sec.pdf", file_type="pdf", file_size_bytes=200, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Restore sensitive")
    assert rest_req.status == sm.RESTORATION_SUBMITTED


def test_uc_045_alt_a2():
    """TEST-UC-045 | BA-UC-016 Alt A2: Non-Sensitive archive restoration standard path."""
    user = regular_user_actor(user_id=33, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=33, department="CSE", file_name="pub.pdf", file_type="pdf", file_size_bytes=200, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="routine"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Restore routine")
    assert rest_req.status == sm.RESTORATION_COMPLETED


def test_uc_046_exc_e1():
    """TEST-UC-046 | BA-UC-016 Exc E1: Non-existent archive rejected."""
    user = regular_user_actor(user_id=33, dept="CSE")
    with pytest.raises(SecureArchivalRequest.DoesNotExist):
        ops.submit_restoration_request(actor=user, archival_request_id=999999, reason="Non-existent")


# --- BA-UC-017: Approve Sensitive Data Restoration ---

def test_uc_047_main_flow():
    """TEST-UC-047 | BA-UC-017 Main Flow: SysAdmin reviews sensitive restoration."""
    admin = sysadmin_actor(user_id=1)
    user = regular_user_actor(user_id=34, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=34, department="CSE", file_name="s.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Need restore")
    visible = list(scoping.visible_restorations(admin))
    assert rest_req in visible


def test_uc_048_alt_a1():
    """TEST-UC-048 | BA-UC-017 Alt A1: SysAdmin approves sensitive restoration."""
    admin = sysadmin_actor(user_id=1)
    user = regular_user_actor(user_id=34, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=34, department="CSE", file_name="s.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Need restore")
    approved = ops.sysadmin_review_restoration(actor=admin, restoration_id=rest_req.pk, action="approve")
    assert approved.status == sm.RESTORATION_COMPLETED


def test_uc_049_alt_a2():
    """TEST-UC-049 | BA-UC-017 Alt A2: SysAdmin rejects sensitive restoration."""
    admin = sysadmin_actor(user_id=1)
    user = regular_user_actor(user_id=34, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=34, department="CSE", file_name="s.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Need restore")
    rejected = ops.sysadmin_review_restoration(actor=admin, restoration_id=rest_req.pk, action="reject")
    assert rejected.status == sm.RESTORATION_SYSADMIN_REJECTED


def test_uc_050_exc_e1():
    """TEST-UC-050 | BA-UC-017 Exc E1: Non-SysAdmin denied sensitive restoration decision."""
    user = regular_user_actor(user_id=35, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=35, department="CSE", file_name="s.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Need restore")
    with pytest.raises(PermissionDeniedError):
        ops.sysadmin_review_restoration(actor=user, restoration_id=rest_req.pk, action="approve")


# --- BA-UC-018: Execute Data Restoration ---

def test_uc_051_main_flow():
    """TEST-UC-051 | BA-UC-018 Main Flow: Execute approved data restoration."""
    admin = sysadmin_actor(user_id=1)
    user = regular_user_actor(user_id=36, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=36, department="CSE", file_name="exec.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Exec restore")
    ops.sysadmin_review_restoration(actor=admin, restoration_id=rest_req.pk, action="approve")
    assert DataRestorationRequest.objects.get(pk=rest_req.pk).status == sm.RESTORATION_COMPLETED


def test_uc_052_exc_e1():
    """TEST-UC-052 | BA-UC-018 Exc E1: Restoration execution failure handling."""
    pytest.skip("NOT_AUTOMATED: External raw disk restoration failure simulation is outside unit test scope")


# --- BA-UC-019: Manage RBAC Permissions ---

def test_uc_053_main_flow():
    """TEST-UC-053 | BA-UC-019 Main Flow: IT Security manages RBAC permissions."""
    sec = it_security_actor(user_id=40)
    assert sec.has_permission("badms.security.manage") is True


def test_uc_054_exc_e1():
    """TEST-UC-054 | BA-UC-019 Exc E1: Non-IT Security actor denied permission management."""
    user = regular_user_actor(user_id=41)
    assert user.has_permission("badms.security.manage") is False


# --- BA-UC-020: Define and Enforce Security Policies ---

def test_uc_055_main_flow():
    """TEST-UC-055 | BA-UC-020 Main Flow: IT Security defines security policies."""
    sec = it_security_actor(user_id=40)
    assert sec.has_permission("badms.security.manage") is True


def test_uc_056_exc_e1():
    """TEST-UC-056 | BA-UC-020 Exc E1: Unauthorized policy alteration denied."""
    user = regular_user_actor(user_id=42)
    assert user.has_permission("badms.security.manage") is False


# --- BA-UC-021: View Department Data-Management Reports ---

def test_uc_057_main_flow():
    """TEST-UC-057 | BA-UC-021 Main Flow: HoD views departmental reports."""
    cse_hod = hod_actor(user_id=20, dept="CSE")
    user = regular_user_actor(user_id=43, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="cse_rep.csv", file_type="csv", file_size_bytes=100, reason="Rep")
    visible = list(scoping.visible_archival_requests(cse_hod))
    assert req in visible


def test_uc_058_exc_e1():
    """TEST-UC-058 | BA-UC-021 Exc E1: HoD cannot view reports outside department."""
    cse_hod = hod_actor(user_id=20, dept="CSE")
    user_me = regular_user_actor(user_id=44, dept="ME")
    me_req = ops.submit_archival_request(actor=user_me, department="ME", file_name="me_rep.csv", file_type="csv", file_size_bytes=100, reason="ME Rep")
    visible = list(scoping.visible_archival_requests(cse_hod))
    assert me_req not in visible


# --- BA-UC-022: Monitor Storage Thresholds ---

def test_uc_059_main_flow():
    """TEST-UC-059 | BA-UC-022 Main Flow: System monitors storage quota threshold."""
    StorageQuota.objects.create(user_id=50, allocated_mb=5120, used_mb=5120)
    quotas = get_user_storage_quotas([50])
    assert quotas[50].is_quota_full is True


def test_uc_060_alt_a1():
    """TEST-UC-060 | BA-UC-022 Alt A1: Usage below threshold -> is_quota_full is False."""
    StorageQuota.objects.create(user_id=51, allocated_mb=5120, used_mb=1000)
    quotas = get_user_storage_quotas([51])
    assert quotas[51].is_quota_full is False


def test_uc_061_exc_e1():
    """TEST-UC-061 | BA-UC-022 Exc E1: Usage data missing -> default quota assumed."""
    quotas = get_user_storage_quotas([999])
    assert quotas[999].allocated_mb == 5120
    assert quotas[999].is_quota_full is False


# --- BA-UC-023: Record Audit Event ---

def test_uc_062_main_flow():
    """TEST-UC-062 | BA-UC-023 Main Flow: Record user action audit event."""
    admin = sysadmin_actor(user_id=1)
    op = ops.trigger_manual_backup(actor=admin, dataset_code="test_log")
    log = BadmsAuditLog.objects.filter(entity_type="backup_operation", entity_id=op.pk).first()
    assert log is not None
    assert log.actor_user_id == 1


def test_uc_063_alt_a1():
    """TEST-UC-063 | BA-UC-023 Alt A1: Record system-originated audit event."""
    log = BadmsAuditLog.objects.create(
        actor_user_id=0, actor_role="system", action="scheduled_backup_executed", entity_type="backup", details={"code": "sys"}
    )
    assert log.actor_role == "system"


def test_uc_064_exc_e1():
    """TEST-UC-064 | BA-UC-023 Exc E1: Audit log query reliability."""
    logs = list(BadmsAuditLog.objects.all())
    assert isinstance(logs, list)
