"""Department scoping and ownership isolation tests for BADMS."""
from dataclasses import dataclass

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms import selectors
from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    RestorationRequest,
    SecurityPolicy,
    StorageExtensionRequest,
    UserStorageQuota,
)

pytestmark = pytest.mark.django_db


@dataclass
class Actor:
    user_id: int
    active_role: str = "student"
    department: str = "CSE"


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_user_sees_only_own_archival_requests(stub_iam, user_ref):
    r1 = ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="project.tar.gz",
        file_type="archive",
        file_size_bytes=1024,
        file_storage_path="/tmp/test1",
        status="submitted",
    )
    ArchivalRequest.objects.create(
        requester_user_id=2002,
        department="CSE",
        file_name="thesis.tar.gz",
        file_type="archive",
        file_size_bytes=2048,
        file_storage_path="/tmp/test2",
        status="submitted",
    )

    c = _client(
        stub_iam,
        user_id=1001,
        kind="student",
        modules=("badms",),
        permissions=("badms.archival.view",),
    )
    res = c.get("/api/v1/badms/archival-requests/")
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["results"]]
    assert ids == [r1.id]


def test_hod_sees_only_their_department_archival_requests(stub_iam, user_ref):
    r_cse = ArchivalRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        file_name="cse_doc.pdf",
        file_type="document",
        file_size_bytes=500,
        file_storage_path="/tmp/cse",
        status="submitted",
    )
    r_ece = ArchivalRequest.objects.create(
        requester_user_id=3001,
        department="ECE",
        file_name="ece_doc.pdf",
        file_type="document",
        file_size_bytes=600,
        file_storage_path="/tmp/ece",
        status="submitted",
    )

    # HOD (CSE)
    c = _client(
        stub_iam,
        user_id=5001,
        kind="faculty",
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.archival.view", "badms.archival.approve"),
    )
    res = c.get("/api/v1/badms/archival-requests/")
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["results"]]
    assert ids == [r_cse.id]
    assert r_ece.id not in ids


def test_hod_reviewing_foreign_department_request_returns_404(stub_iam, user_ref):
    r_ece = ArchivalRequest.objects.create(
        requester_user_id=3001,
        department="ECE",
        file_name="ece_doc.pdf",
        file_type="document",
        file_size_bytes=600,
        file_storage_path="/tmp/ece",
        status="submitted",
    )

    # HOD (CSE) attempting to review ECE request
    c = _client(
        stub_iam,
        user_id=5001,
        kind="faculty",
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.archival.approve",),
    )
    res = c.post(
        f"/api/v1/badms/archival-requests/{r_ece.id}/decide/",
        {"decision": "approve", "remarks": "Unauthorized approval attempt"},
    )
    assert res.status_code == 404


def test_storage_extension_department_scoping(stub_iam, user_ref):
    UserStorageQuota.objects.create(user_id=1001, allocated_quota_bytes=1000, used_storage_bytes=1000, is_full=True)
    UserStorageQuota.objects.create(user_id=2002, allocated_quota_bytes=1000, used_storage_bytes=1000, is_full=True)

    s_cse = StorageExtensionRequest.objects.create(
        requester_user_id=1001,
        department="CSE",
        current_usage_bytes=1000,
        current_quota_bytes=1000,
        requested_extension_bytes=500,
        justification="Running AI simulation experiments",
        status="submitted",
    )
    s_me = StorageExtensionRequest.objects.create(
        requester_user_id=2002,
        department="ME",
        current_usage_bytes=1000,
        current_quota_bytes=1000,
        requested_extension_bytes=800,
        justification="CAD rendering dumps",
        status="submitted",
    )

    # HOD (CSE)
    c_hod_cse = _client(
        stub_iam,
        user_id=5001,
        kind="faculty",
        roles=("HOD (CSE)",),
        active_role="HOD (CSE)",
        modules=("badms",),
        permissions=("badms.storage.view", "badms.storage.approve"),
    )
    res = c_hod_cse.get("/api/v1/badms/storage-extensions/")
    assert res.status_code == 200
    ids = [item["id"] for item in res.json()["results"]]
    assert ids == [s_cse.id]

    # HOD (CSE) attempting to approve ME storage extension returns 404
    res_foreign = c_hod_cse.post(
        f"/api/v1/badms/storage-extensions/{s_me.id}/decide/",
        {"decision": "approve", "remarks": "Invalid cross-dept"},
    )
    assert res_foreign.status_code == 404


def test_direct_selector_functions_coverage():
    # 1. Anonymous / None actor returns none()
    assert not selectors.scope_backup_records(None).exists()
    assert not selectors.scope_backup_schedules(None).exists()
    assert not selectors.scope_archival_requests(None).exists()
    assert not selectors.scope_storage_extensions(None).exists()
    assert not selectors.scope_restoration_requests(None).exists()
    assert not selectors.scope_audit_events(None).exists()
    assert not selectors.scope_security_policies(None).exists()
    assert not selectors.scope_user_storage_quotas(None).exists()

    # Create dummy records
    BackupRecord.objects.create(backup_type="manual", dataset_name="d", status="success", triggered_by_user_id=100)
    BackupSchedule.objects.create(name="sc", scope_type="global", dataset_name="d", cron_expression="* * * * *", created_by_user_id=1)
    a = ArchivalRequest.objects.create(requester_user_id=100, department="CSE", file_name="f", file_type="t", file_size_bytes=10, file_storage_path="/p", status="submitted")
    StorageExtensionRequest.objects.create(requester_user_id=100, department="CSE", current_usage_bytes=10, current_quota_bytes=10, requested_extension_bytes=10, justification="j", status="submitted")
    RestorationRequest.objects.create(requester_user_id=100, department="CSE", archival_request_id=a.id, classification="Routine", target_destination="/d", status="requested_standard")
    AuditEvent.objects.create(event_type="t", actor_user_id=100, actor_role="student", target_model="ArchivalRequest", department="CSE")
    SecurityPolicy.objects.create(policy_key="pk", policy_value={}, configured_by_user_id=1)
    UserStorageQuota.objects.create(user_id=100, allocated_quota_bytes=10, used_storage_bytes=10)

    admin = Actor(user_id=1, active_role="SysAdmin", department="Central")
    it_sec = Actor(user_id=2, active_role="IT Security", department="Central")
    hod = Actor(user_id=3, active_role="HOD (CSE)", department="CSE")
    user = Actor(user_id=100, active_role="student", department="CSE")

    # Admin scope
    assert selectors.scope_backup_records(admin).count() >= 1
    assert selectors.scope_archival_requests(admin).count() >= 1
    assert selectors.scope_storage_extensions(admin).count() >= 1
    assert selectors.scope_restoration_requests(admin).count() >= 1
    assert selectors.scope_audit_events(admin).count() >= 1
    assert selectors.scope_user_storage_quotas(admin).count() >= 1

    # IT Security scope
    assert selectors.scope_backup_records(it_sec).count() >= 1
    assert selectors.scope_archival_requests(it_sec).count() >= 1
    assert selectors.scope_audit_events(it_sec).count() >= 1

    # HOD scope
    assert selectors.scope_audit_events(hod).count() >= 1

    # User scope
    assert selectors.scope_backup_records(user).count() >= 1
    assert selectors.scope_restoration_requests(user).count() >= 1
    assert selectors.scope_audit_events(user).count() >= 1
    assert selectors.scope_user_storage_quotas(user).count() >= 1
    assert selectors.scope_security_policies(user).count() >= 1
    assert selectors.scope_backup_schedules(user).count() >= 1
