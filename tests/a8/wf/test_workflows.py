"""End-to-end backend checks for the seven explicit basis workflow paths."""
import pytest

from modules.badms.domain import state_machine as sm


@pytest.mark.django_db
def test_wf_001_archival_hod_rejection_stops_the_request(principal_factory):
    """WF-001 / BW-BA-01 rejection path."""
    from modules.badms.services.operations import hod_review_archival, submit_archival_request

    request = submit_archival_request(
        actor=principal_factory(user_id=401), department="CSE", file_name="reject.txt",
        file_type="text/plain", file_size_bytes=4, reason="Rejection path",
    )
    result = hod_review_archival(
        actor=principal_factory(user_id=402, permissions={"badms.department.review"}),
        request_id=request.pk, action="reject", remarks="Not approved",
    )
    assert result.status == sm.ARCHIVAL_HOD_REJECTED
    assert not result.archive_location


@pytest.mark.django_db
def test_wf_002_approved_non_sensitive_archival_completes(principal_factory):
    """WF-002 / BW-BA-02 approved non-sensitive path."""
    from modules.badms.services.operations import hod_review_archival, submit_archival_request, sysadmin_classify_archival

    request = submit_archival_request(
        actor=principal_factory(user_id=403), department="CSE", file_name="routine.txt",
        file_type="text/plain", file_size_bytes=5, reason="Routine archive",
    )
    approved = hod_review_archival(
        actor=principal_factory(user_id=404, permissions={"badms.department.review"}),
        request_id=request.pk, action="approve",
    )
    completed = sysadmin_classify_archival(
        actor=principal_factory(user_id=405, permissions={"badms.archival.classify_authoritative"}),
        request_id=approved.pk, authoritative_classification=sm.TIER_ROUTINE,
    )
    assert completed.status == sm.ARCHIVAL_COMPLETED
    assert completed.archive_location
    assert completed.retention_until is not None


@pytest.mark.django_db
def test_wf_003_approved_sensitive_archival_requires_encryption(principal_factory):
    """WF-003 / BW-BA-03 approved sensitive encryption path."""
    from modules.badms.services.operations import (
        hod_review_archival, it_security_configure_encryption, submit_archival_request,
        sysadmin_classify_archival,
    )

    request = submit_archival_request(
        actor=principal_factory(user_id=406), department="CSE", file_name="sensitive.bin",
        file_type="application/octet-stream", file_size_bytes=8, reason="Sensitive archive",
        initial_classification=sm.TIER_SENSITIVE,
    )
    approved = hod_review_archival(
        actor=principal_factory(user_id=407, permissions={"badms.department.review"}),
        request_id=request.pk, action="approve",
    )
    classified = sysadmin_classify_archival(
        actor=principal_factory(user_id=408, permissions={"badms.archival.classify_authoritative"}),
        request_id=approved.pk, authoritative_classification=sm.TIER_SENSITIVE,
    )
    assert classified.status == sm.ARCHIVAL_CLASSIFIED
    assert not classified.archive_location
    encrypted = it_security_configure_encryption(
        actor=principal_factory(user_id=409, permissions={"badms.security.manage"}),
        request_id=classified.pk,
    )
    assert encrypted.status == sm.ARCHIVAL_COMPLETED
    assert encrypted.is_encrypted


@pytest.mark.django_db
def test_wf_004_storage_extension_rejection_path(principal_factory):
    """WF-004 / BW-BA-04 rejection path."""
    from modules.badms.models import StorageExtensionRequest
    from modules.badms.services.operations import hod_review_storage_extension

    request = StorageExtensionRequest.objects.create(
        user_id=410, department="CSE", requested_additional_mb=512, reason="Storage need"
    )
    rejected = hod_review_storage_extension(
        actor=principal_factory(user_id=411, permissions={"badms.department.review"}),
        request_id=request.pk, action="reject", remarks="Not approved",
    )
    assert rejected.status == sm.STORAGE_REJECTED


@pytest.mark.django_db
def test_wf_005_storage_extension_approval_updates_quota(principal_factory):
    """WF-005 / BW-BA-05 approval path."""
    from modules.badms.models import StorageExtensionRequest, StorageQuota
    from modules.badms.services.operations import hod_review_storage_extension

    StorageQuota.objects.create(user_id=412, allocated_mb=1024, used_mb=1024)
    request = StorageExtensionRequest.objects.create(
        user_id=412, department="CSE", requested_additional_mb=512, reason="Storage need"
    )
    approved = hod_review_storage_extension(
        actor=principal_factory(user_id=413, permissions={"badms.department.review"}),
        request_id=request.pk, action="approve",
    )
    quota = StorageQuota.objects.get(user_id=412)
    assert approved.status == sm.STORAGE_APPROVED
    assert quota.allocated_mb == 1536


@pytest.mark.django_db
def test_wf_006_non_sensitive_restoration_takes_standard_path(principal_factory):
    """WF-006 / BW-BA-06 non-sensitive standard path."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import submit_restoration_request

    owner = principal_factory(user_id=414)
    archive = SecureArchivalRequest.objects.create(
        user_id=owner.user_id, department="CSE", file_name="routine.zip", file_type="application/zip",
        file_size_bytes=16, reason="Routine archive", authoritative_classification=sm.TIER_ROUTINE,
        status=sm.ARCHIVAL_COMPLETED,
    )
    restoration = submit_restoration_request(
        actor=owner, archival_request_id=archive.pk, reason="Recover routine data"
    )
    assert restoration.status == sm.RESTORATION_COMPLETED
    assert restoration.restored_at is not None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "action,expected",
    [("approve", sm.RESTORATION_COMPLETED), ("reject", sm.RESTORATION_SYSADMIN_REJECTED)],
)
def test_wf_007_sensitive_restoration_decision_paths(principal_factory, action, expected):
    """WF-007 / BW-BA-07 sensitive approval and rejection paths."""
    from modules.badms.models import SecureArchivalRequest
    from modules.badms.services.operations import submit_restoration_request, sysadmin_review_restoration

    owner = principal_factory(user_id=415)
    archive = SecureArchivalRequest.objects.create(
        user_id=owner.user_id, department="CSE", file_name="sensitive.zip", file_type="application/zip",
        file_size_bytes=16, reason="Sensitive archive", authoritative_classification=sm.TIER_SENSITIVE,
        status=sm.ARCHIVAL_COMPLETED,
    )
    restoration = submit_restoration_request(
        actor=owner, archival_request_id=archive.pk, reason="Recover sensitive data"
    )
    assert restoration.status == sm.RESTORATION_SUBMITTED
    result = sysadmin_review_restoration(
        actor=principal_factory(user_id=416, permissions={"badms.restoration.approve_sensitive"}),
        restoration_id=restoration.pk, action=action,
    )
    assert result.status == expected
