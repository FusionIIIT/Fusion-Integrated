"""Executable coverage for the frozen BADMS workflow design."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import (
    ArchivalRequest,
    RestorationRequest,
    StorageExtensionRequest,
    UserStorageQuota,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kwargs):
    stub_iam(make_session(**kwargs))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token wf-design")
    return client


def _archival_request(*, status="submitted", classification="Routine", **kwargs):
    return ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="workflow.tar",
        file_type="tar",
        file_size_bytes=100,
        reason="WF design fixture",
        file_storage_path="/archive/workflow.tar",
        initial_classification=classification,
        authoritative_classification=(classification if status != "submitted" else ""),
        status=status,
        **kwargs,
    )


def _storage_request():
    UserStorageQuota.objects.create(
        user_id=1001,
        allocated_quota_bytes=1000,
        used_storage_bytes=1000,
        is_full=True,
    )
    return StorageExtensionRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        current_usage_bytes=1000,
        current_quota_bytes=1000,
        requested_extension_bytes=500,
        justification="Workflow fixture",
        status="submitted",
    )


def _hod_client(stub_iam):
    return _client(
        stub_iam,
        user_id=5001,
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.archival.approve", "badms.storage.approve"),
    )


def _sysadmin_client(stub_iam):
    return _client(
        stub_iam,
        user_id=6001,
        roles=("SysAdmin",),
        active_role="SysAdmin",
        modules=("badms",),
        permissions=(
            "badms.archival.review",
            "badms.restoration.approve",
            "badms.restoration.restore",
        ),
    )


def test_wf_design_001_bw_ba_01_secure_archival_hod_rejection(stub_iam):
    """test_id: WF-DESIGN-001; source_id: BW-BA-01."""
    request = _archival_request()
    hod = _hod_client(stub_iam)

    rejected = hod.post(
        f"/api/v1/badms/archival-requests/{request.id}/decide/",
        {"decision": "reject", "remarks": "Not approved"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    # Classification is a SysAdmin operation; use a client whose IAM session
    # is active for this request (the fake IAM is process-global).
    refused = _sysadmin_client(stub_iam).post(
        f"/api/v1/badms/archival-requests/{request.id}/classify/",
        {"classification": "Routine"},
    )
    assert refused.status_code == 409
    request.refresh_from_db()
    assert request.status == "rejected"
    assert request.authoritative_classification == ""


def test_wf_design_002_bw_ba_02_secure_archival_non_sensitive(stub_iam):
    """test_id: WF-DESIGN-002; source_id: BW-BA-02."""
    request = _archival_request()
    hod = _hod_client(stub_iam)
    approved = hod.post(
        f"/api/v1/badms/archival-requests/{request.id}/decide/",
        {"decision": "approve"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "hod_approved"
    sysadmin = _sysadmin_client(stub_iam)
    classified = sysadmin.post(
        f"/api/v1/badms/archival-requests/{request.id}/classify/",
        {"classification": "Routine"},
    )
    assert classified.status_code == 200
    assert classified.json()["status"] == "classified_non_sensitive"
    request.refresh_from_db()
    assert request.status == "classified_non_sensitive"
    assert request.authoritative_classification == "Routine"


def test_wf_design_003_bw_ba_03_secure_archival_sensitive_encryption(stub_iam):
    """test_id: WF-DESIGN-003; source_id: BW-BA-03."""
    request = _archival_request()
    hod = _hod_client(stub_iam)
    approved = hod.post(
        f"/api/v1/badms/archival-requests/{request.id}/decide/",
        {"decision": "approve"},
    )
    assert approved.status_code == 200
    sysadmin = _sysadmin_client(stub_iam)
    classified = sysadmin.post(
        f"/api/v1/badms/archival-requests/{request.id}/classify/",
        {"classification": "Sensitive"},
    )
    security = _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.security.manage",),
    )
    encrypted = security.post(
        f"/api/v1/badms/archival-requests/{request.id}/configure-encryption/",
        {"encryption_algorithm": "AES-256-GCM"},
    )
    assert classified.status_code == 200
    assert classified.json()["status"] == "classified_sensitive"
    assert encrypted.status_code == 200
    assert encrypted.json()["status"] == "sensitive_archive_encrypted"
    assert encrypted.json()["is_encrypted"] is True
    request.refresh_from_db()
    assert request.status == "sensitive_archive_encrypted"


def test_wf_design_004_bw_ba_04_storage_extension_rejected(stub_iam):
    """test_id: WF-DESIGN-004; source_id: BW-BA-04."""
    request = _storage_request()
    hod = _hod_client(stub_iam)

    response = hod.post(
        f"/api/v1/badms/storage-extensions/{request.id}/decide/",
        {"decision": "reject", "remarks": "Not approved"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    request.refresh_from_db()
    assert request.status == "rejected"
    assert request.hod_reviewed_by_user_id == 5001


def test_wf_design_005_bw_ba_05_storage_extension_approved(stub_iam):
    """test_id: WF-DESIGN-005; source_id: BW-BA-05."""
    request = _storage_request()
    hod = _hod_client(stub_iam)

    response = hod.post(
        f"/api/v1/badms/storage-extensions/{request.id}/decide/",
        {"decision": "approve"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    request.refresh_from_db()
    assert request.status == "approved"
    assert UserStorageQuota.objects.get(user_id=1001).allocated_quota_bytes == 1500


def test_wf_design_006_bw_ba_06_standard_restoration(stub_iam):
    """test_id: WF-DESIGN-006; source_id: BW-BA-06."""
    archive = _archival_request(
        status="classified_non_sensitive", classification="Routine"
    )
    user = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.restoration.create",),
    )
    requested = user.post(
        "/api/v1/badms/restorations/",
        {"archival_request_id": archive.id, "target_destination": "/restore/workflow"},
    )
    sysadmin = _sysadmin_client(stub_iam)
    restoration_id = requested.json()["id"]
    executed = sysadmin.post(f"/api/v1/badms/restorations/{restoration_id}/execute/")
    assert requested.status_code == 201
    assert requested.json()["status"] == "requested_standard"
    assert executed.status_code == 200
    assert executed.json()["status"] == "restored"
    assert RestorationRequest.objects.get(id=restoration_id).status == "restored"


def test_wf_design_007_bw_ba_07_sensitive_restoration_approval(stub_iam):
    """test_id: WF-DESIGN-007; source_id: BW-BA-07."""
    archive = _archival_request(
        status="sensitive_archive_encrypted", classification="Sensitive"
    )
    user = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.restoration.create",),
    )
    requested = user.post(
        "/api/v1/badms/restorations/",
        {"archival_request_id": archive.id, "target_destination": "/restore/workflow"},
    )
    sysadmin = _sysadmin_client(stub_iam)
    restoration_id = requested.json()["id"]

    refused = sysadmin.post(f"/api/v1/badms/restorations/{restoration_id}/execute/")
    assert refused.status_code == 409
    pending = RestorationRequest.objects.get(id=restoration_id)
    assert pending.status == "sensitive_pending_approval"
    assert pending.restored_at is None

    approved = sysadmin.post(
        f"/api/v1/badms/restorations/{restoration_id}/approve/",
        {"decision": "approve"},
    )
    executed = sysadmin.post(f"/api/v1/badms/restorations/{restoration_id}/execute/")
    assert requested.status_code == 201
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert executed.status_code == 200
    assert executed.json()["status"] == "restored"


def test_wf_design_008_cw_ba_01_secure_archival_branches(stub_iam):
    """test_id: WF-DESIGN-008; source_id: CW-BA-01."""
    hod = _hod_client(stub_iam)
    assert _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.security.manage",),
    )

    rejected = _archival_request()
    hod = _hod_client(stub_iam)
    assert hod.post(
        f"/api/v1/badms/archival-requests/{rejected.id}/decide/",
        {"decision": "reject"},
    ).status_code == 200

    routine = _archival_request()
    hod = _hod_client(stub_iam)
    assert hod.post(
        f"/api/v1/badms/archival-requests/{routine.id}/decide/",
        {"decision": "approve"},
    ).status_code == 200
    sysadmin = _sysadmin_client(stub_iam)
    assert sysadmin.post(
        f"/api/v1/badms/archival-requests/{routine.id}/classify/",
        {"classification": "Routine"},
    ).status_code == 200

    sensitive = _archival_request()
    hod = _hod_client(stub_iam)
    assert hod.post(
        f"/api/v1/badms/archival-requests/{sensitive.id}/decide/",
        {"decision": "approve"},
    ).status_code == 200
    sysadmin = _sysadmin_client(stub_iam)
    assert sysadmin.post(
        f"/api/v1/badms/archival-requests/{sensitive.id}/classify/",
        {"classification": "Sensitive"},
    ).status_code == 200
    assert _client(
        stub_iam,
        user_id=7001,
        roles=("IT Security",),
        active_role="IT Security",
        modules=("badms",),
        permissions=("badms.security.manage",),
    ).post(
        f"/api/v1/badms/archival-requests/{sensitive.id}/configure-encryption/",
        {},
    ).status_code == 200

    rejected.refresh_from_db()
    routine.refresh_from_db()
    sensitive.refresh_from_db()
    assert {
        rejected.status,
        routine.status,
        sensitive.status,
    } == {"rejected", "classified_non_sensitive", "sensitive_archive_encrypted"}


def test_wf_design_009_cw_ba_02_storage_extension_branches(stub_iam):
    """test_id: WF-DESIGN-009; source_id: CW-BA-02."""
    hod = _hod_client(stub_iam)
    rejected = _storage_request()
    approved = StorageExtensionRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        current_usage_bytes=1000,
        current_quota_bytes=1000,
        requested_extension_bytes=250,
        justification="Workflow fixture",
        status="submitted",
    )

    assert hod.post(
        f"/api/v1/badms/storage-extensions/{rejected.id}/decide/",
        {"decision": "reject"},
    ).status_code == 200
    assert hod.post(
        f"/api/v1/badms/storage-extensions/{approved.id}/decide/",
        {"decision": "approve"},
    ).status_code == 200

    rejected.refresh_from_db()
    approved.refresh_from_db()
    assert rejected.status == "rejected"
    assert approved.status == "approved"


def test_wf_design_010_cw_ba_03_restoration_branches(stub_iam):
    """test_id: WF-DESIGN-010; source_id: CW-BA-03."""
    user = _client(
        stub_iam,
        user_id=1001,
        modules=("badms",),
        permissions=("badms.restoration.create",),
    )
    routine_archive = _archival_request(
        status="classified_non_sensitive", classification="Routine"
    )
    sensitive_archive = _archival_request(
        status="sensitive_archive_encrypted", classification="Sensitive"
    )

    routine = user.post(
        "/api/v1/badms/restorations/",
        {"archival_request_id": routine_archive.id, "target_destination": "/restore/routine"},
    )
    sensitive = user.post(
        "/api/v1/badms/restorations/",
        {
            "archival_request_id": sensitive_archive.id,
            "target_destination": "/restore/sensitive",
        },
    )
    sysadmin = _sysadmin_client(stub_iam)
    routine_exec = sysadmin.post(
        f"/api/v1/badms/restorations/{routine.json()['id']}/execute/"
    )
    sensitive_refusal = sysadmin.post(
        f"/api/v1/badms/restorations/{sensitive.json()['id']}/execute/"
    )
    sensitive_approval = sysadmin.post(
        f"/api/v1/badms/restorations/{sensitive.json()['id']}/approve/",
        {"decision": "approve"},
    )
    sensitive_exec = sysadmin.post(
        f"/api/v1/badms/restorations/{sensitive.json()['id']}/execute/"
    )

    assert routine.status_code == 201
    assert sensitive.status_code == 201
    assert routine_exec.status_code == 200
    assert routine_exec.json()["status"] == "restored"
    assert sensitive_refusal.status_code == 409
    assert sensitive_approval.status_code == 200
    assert sensitive_exec.status_code == 200
    assert sensitive_exec.json()["status"] == "restored"
    assert RestorationRequest.objects.get(id=routine.json()["id"]).status == "restored"
    assert RestorationRequest.objects.get(id=sensitive.json()["id"]).status == "restored"
