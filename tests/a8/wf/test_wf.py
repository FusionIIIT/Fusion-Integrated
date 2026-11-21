"""WF Test Suite: Workflow Specifications (State Transitions & Decision Paths).
Generated from a8_design/WF_DESIGN.json.
"""
import pytest
from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.badms.models import (
    SecureArchivalRequest,
    DataRestorationRequest,
    StorageQuota,
    StorageExtensionRequest,
)
from modules.badms.domain import state_machine as sm
from modules.badms.services import operations as ops
from tests.a8.helpers import (
    sysadmin_actor,
    superadmin_actor,
    hod_actor,
    it_security_actor,
    regular_user_actor,
)

pytestmark = pytest.mark.django_db


# --- BW-BA-01: Secure Archival - HoD Rejection ---

def test_wf_001_bw_ba_01_transition_to_submitted():
    """TEST-WF-001 | BW-BA-01-T1: Not Submitted -> Submitted."""
    user = regular_user_actor(user_id=1, dept="CSE")
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="doc1.pdf", file_type="pdf", file_size_bytes=100, reason="Archival"
    )
    assert req.status == sm.ARCHIVAL_SUBMITTED


def test_wf_002_bw_ba_01_transition_to_rejected():
    """TEST-WF-002 | BW-BA-01-T2: Submitted -> Rejected by HoD."""
    user = regular_user_actor(user_id=1, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="doc1.pdf", file_type="pdf", file_size_bytes=100, reason="Archival"
    )
    res = ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="reject", remarks="Policy violation")
    assert res.status == sm.ARCHIVAL_HOD_REJECTED


# --- BW-BA-02: Secure Archival - Approved, Non-Sensitive Classification ---

def test_wf_003_bw_ba_02_transition_to_approved():
    """TEST-WF-003 | BW-BA-02-T2: Submitted -> HoD Approved."""
    user = regular_user_actor(user_id=3, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="doc2.pdf", file_type="pdf", file_size_bytes=200, reason="Archival"
    )
    res = ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    assert res.status == sm.ARCHIVAL_HOD_APPROVED


def test_wf_004_bw_ba_02_transition_to_completed_non_sensitive():
    """TEST-WF-004 | BW-BA-02-T3: HoD Approved -> Completed (Non-Sensitive)."""
    user = regular_user_actor(user_id=3, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    admin = sysadmin_actor(user_id=10)
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="doc2.pdf", file_type="pdf", file_size_bytes=200, reason="Archival"
    )
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    res = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="routine")
    assert res.status == sm.ARCHIVAL_COMPLETED
    assert res.retention_until is not None


# --- BW-BA-03: Secure Archival - Approved, Sensitive Encryption ---

def test_wf_005_bw_ba_03_transition_to_classified_sensitive():
    """TEST-WF-005 | BW-BA-03-T3: HoD Approved -> Classified (Sensitive)."""
    user = regular_user_actor(user_id=4, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    admin = sysadmin_actor(user_id=10)
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="doc3.pdf", file_type="pdf", file_size_bytes=300, reason="Sensitive data"
    )
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    res = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    assert res.status == sm.ARCHIVAL_CLASSIFIED


def test_wf_006_bw_ba_03_transition_to_encrypted_completed():
    """TEST-WF-006 | BW-BA-03-T4: Classified -> Sensitive Archive Encrypted (Completed)."""
    user = regular_user_actor(user_id=4, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    admin = sysadmin_actor(user_id=10)
    sec = it_security_actor(user_id=20)
    req = ops.submit_archival_request(
        actor=user, department="CSE", file_name="doc3.pdf", file_type="pdf", file_size_bytes=300, reason="Sensitive data"
    )
    ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    res = ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="AES-256")
    assert res.status == sm.ARCHIVAL_COMPLETED
    assert res.is_encrypted is True


# --- CW-BA-01: Secure Archival Request Processing ---

def test_wf_007_cw_ba_01_composite_non_sensitive():
    """TEST-WF-007 | CW-BA-01-COMPOSITE-NON-SENSITIVE: Composite archival lifecycle non-sensitive."""
    user = regular_user_actor(user_id=5, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    admin = sysadmin_actor(user_id=10)

    # 1. Submit
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="c1.pdf", file_type="pdf", file_size_bytes=100, reason="C1")
    assert req.status == sm.ARCHIVAL_SUBMITTED

    # 2. HoD Approve
    app = ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    assert app.status == sm.ARCHIVAL_HOD_APPROVED

    # 3. Classify Routine -> Completed
    comp = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="routine")
    assert comp.status == sm.ARCHIVAL_COMPLETED


def test_wf_008_cw_ba_01_composite_sensitive():
    """TEST-WF-008 | CW-BA-01-COMPOSITE-SENSITIVE: Composite archival lifecycle sensitive with encryption."""
    user = regular_user_actor(user_id=6, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    admin = sysadmin_actor(user_id=10)
    sec = it_security_actor(user_id=20)

    # 1. Submit
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="c2.pdf", file_type="pdf", file_size_bytes=200, reason="C2")
    assert req.status == sm.ARCHIVAL_SUBMITTED

    # 2. HoD Approve
    app = ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="approve")
    assert app.status == sm.ARCHIVAL_HOD_APPROVED

    # 3. Classify Sensitive -> Classified
    cls = ops.sysadmin_classify_archival(actor=admin, request_id=req.pk, authoritative_classification="sensitive")
    assert cls.status == sm.ARCHIVAL_CLASSIFIED

    # 4. IT Security Encrypt -> Completed
    enc = ops.it_security_configure_encryption(actor=sec, request_id=req.pk, algorithm="AES-256")
    assert enc.status == sm.ARCHIVAL_COMPLETED


def test_wf_009_cw_ba_01_composite_rejection():
    """TEST-WF-009 | CW-BA-01-COMPOSITE-REJECTION: Composite archival lifecycle ending in rejection."""
    user = regular_user_actor(user_id=7, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    req = ops.submit_archival_request(actor=user, department="CSE", file_name="c3.pdf", file_type="pdf", file_size_bytes=300, reason="C3")
    rej = ops.hod_review_archival(actor=cse_hod, request_id=req.pk, action="reject", remarks="Rejected by HoD")
    assert rej.status == sm.ARCHIVAL_HOD_REJECTED


# --- BW-BA-04: Storage Extension - Rejected ---

def test_wf_010_bw_ba_04_transition_to_submitted():
    """TEST-WF-010 | BW-BA-04-T1: Not Submitted -> Submitted for Storage Extension."""
    user = regular_user_actor(user_id=15, dept="CSE")
    StorageQuota.objects.create(user_id=15, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Full")
    assert ext.status == sm.STORAGE_SUBMITTED


def test_wf_011_bw_ba_04_transition_to_rejected():
    """TEST-WF-011 | BW-BA-04-T2: Submitted -> Rejected for Storage Extension."""
    user = regular_user_actor(user_id=15, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    StorageQuota.objects.create(user_id=15, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Full")
    res = ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="reject")
    assert res.status == sm.STORAGE_REJECTED


# --- BW-BA-05: Storage Extension - Approved ---

def test_wf_012_bw_ba_05_transition_to_approved():
    """TEST-WF-012 | BW-BA-05-T2: Submitted -> Approved for Storage Extension."""
    user = regular_user_actor(user_id=16, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    StorageQuota.objects.create(user_id=16, allocated_mb=5120, used_mb=5120)
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=2048, reason="Full")
    res = ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="approve")
    assert res.status == sm.STORAGE_APPROVED
    assert StorageQuota.objects.get(user_id=16).allocated_mb == 5120 + 2048


# --- CW-BA-02: Storage-Extension Request Processing ---

def test_wf_013_cw_ba_02_composite_extension():
    """TEST-WF-013 | CW-BA-02-COMPOSITE-EXTENSION: Composite storage extension lifecycle."""
    user = regular_user_actor(user_id=17, dept="CSE")
    cse_hod = hod_actor(user_id=2, dept="CSE")
    StorageQuota.objects.create(user_id=17, allocated_mb=5120, used_mb=5120)

    # 1. Submit
    ext = ops.submit_storage_extension(actor=user, department="CSE", requested_additional_mb=1024, reason="Growth")
    assert ext.status == sm.STORAGE_SUBMITTED

    # 2. HoD Approve
    app = ops.hod_review_storage_extension(actor=cse_hod, request_id=ext.pk, action="approve")
    assert app.status == sm.STORAGE_APPROVED
    assert StorageQuota.objects.get(user_id=17).allocated_mb == 5120 + 1024


# --- BW-BA-06: Restoration - Non-Sensitive Standard Path ---

def test_wf_014_bw_ba_06_non_sensitive_auto_restored():
    """TEST-WF-014 | BW-BA-06-T1: Restoration Non-Sensitive Standard Path auto completes."""
    user = regular_user_actor(user_id=18, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=18, department="CSE", file_name="f.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="routine"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Restore")
    assert rest_req.status == sm.RESTORATION_COMPLETED
    assert rest_req.restored_at is not None


# --- BW-BA-07: Restoration - Sensitive SysAdmin Approval ---

def test_wf_015_bw_ba_07_sensitive_pending_approval():
    """TEST-WF-015 | BW-BA-07-T1: Sensitive Restoration transitions to Submitted/Pending."""
    user = regular_user_actor(user_id=19, dept="CSE")
    arch = SecureArchivalRequest.objects.create(
        user_id=19, department="CSE", file_name="f_sec.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Restore sensitive")
    assert rest_req.status == sm.RESTORATION_SUBMITTED


def test_wf_016_bw_ba_07_sysadmin_rejection():
    """TEST-WF-016 | BW-BA-07-T2-REJECT: Sensitive Restoration rejected by SysAdmin."""
    user = regular_user_actor(user_id=19, dept="CSE")
    admin = sysadmin_actor(user_id=10)
    arch = SecureArchivalRequest.objects.create(
        user_id=19, department="CSE", file_name="f_sec.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Restore sensitive")
    res = ops.sysadmin_review_restoration(actor=admin, restoration_id=rest_req.pk, action="reject")
    assert res.status == sm.RESTORATION_SYSADMIN_REJECTED


def test_wf_017_bw_ba_07_sysadmin_approval():
    """TEST-WF-017 | BW-BA-07-T2-APPROVE: Sensitive Restoration approved by SysAdmin."""
    user = regular_user_actor(user_id=19, dept="CSE")
    admin = sysadmin_actor(user_id=10)
    arch = SecureArchivalRequest.objects.create(
        user_id=19, department="CSE", file_name="f_sec.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Restore sensitive")
    res = ops.sysadmin_review_restoration(actor=admin, restoration_id=rest_req.pk, action="approve")
    assert res.status == sm.RESTORATION_COMPLETED
    assert res.restored_at is not None


# --- CW-BA-03: Data Restoration Processing ---

def test_wf_018_cw_ba_03_composite_restoration():
    """TEST-WF-018 | CW-BA-03-COMPOSITE-RESTORATION-SENSITIVE: Composite restoration lifecycle for sensitive archive."""
    user = regular_user_actor(user_id=20, dept="CSE")
    admin = sysadmin_actor(user_id=10)
    arch = SecureArchivalRequest.objects.create(
        user_id=20, department="CSE", file_name="f_audit.dat", file_type="dat", file_size_bytes=100, status=sm.ARCHIVAL_COMPLETED, authoritative_classification="sensitive"
    )
    # 1. Submit
    rest_req = ops.submit_restoration_request(actor=user, archival_request_id=arch.pk, reason="Audit request")
    assert rest_req.status == sm.RESTORATION_SUBMITTED

    # 2. SysAdmin Approve
    res = ops.sysadmin_review_restoration(actor=admin, restoration_id=rest_req.pk, action="approve")
    assert res.status == sm.RESTORATION_COMPLETED
