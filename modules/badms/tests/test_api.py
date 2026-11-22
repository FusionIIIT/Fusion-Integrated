"""API endpoint integration tests for BADMS."""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.badms.models import (
    ArchivalRequest,
    UserStorageQuota,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    modules = kw.pop("modules", ("badms",))
    kw.pop("username", None)
    stub_iam(make_session(modules=modules, **kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_user_submits_archival_and_tracks(stub_iam):
    c = _client(
        stub_iam,
        user_id=101,
        username="student1",
        permissions=("badms.archival.submit", "badms.archival.view"),
    )

    # 1. Submit archival
    payload = {
        "file_name": "ai_report.pdf",
        "file_type": "application/pdf",
        "file_size_bytes": 1024,
        "owners": "student1",
        "reason": "Final submission",
        "attachment_path": "/uploads/ai.pdf",
        "initial_classification": "routine",
        "department_id": 1,
    }
    res = c.post("/api/v1/badms/archival-requests", data=payload, format="json")
    assert res.status_code == 201
    arch_id = res.json()["id"]

    # 2. View user list
    res_list = c.get("/api/v1/badms/archival-requests")
    assert res_list.status_code == 200
    ids = [r["id"] for r in res_list.json()["results"]]
    assert arch_id in ids


def test_hod_approval_and_scoping(stub_iam):
    req = ArchivalRequest.objects.create(
        user_id=102,
        department_id=1,
        file_name="dept_file.csv",
        file_type="text/csv",
        file_size_bytes=2048,
        owners="user102",
        reason="Dept data",
        attachment_path="/tmp/f.csv",
        status="submitted",
    )

    # HoD for CSE (dept 1) approves
    c_hod1 = _client(
        stub_iam,
        user_id=501,
        username="hod_cse",
        active_role="hod",
        permissions=("badms.archival.hod_decide",),
    )
    res = c_hod1.post(
        f"/api/v1/badms/archival-requests/{req.id}/hod-decision",
        data={"approve": True, "department_id": 1},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["status"] == "hod_approved"


def test_sysadmin_trigger_manual_backup(stub_iam):
    c = _client(
        stub_iam,
        user_id=1,
        username="sysadmin",
        active_role="sysadmin",
        permissions=("badms.backup.trigger", "badms.backup.view"),
    )

    res = c.post("/api/v1/badms/backups/manual", data={"dataset": "academics"}, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "success"
    assert res.json()["dataset"] == "academics"

    # List backups
    res_list = c.get("/api/v1/badms/backups")
    assert res_list.status_code == 200
    assert len(res_list.json()["results"]) >= 1


def test_storage_extension_api_flow(stub_iam):
    # Set quota to full
    UserStorageQuota.objects.create(
        user_id=205,
        department_id=1,
        used_bytes=1000,
        quota_bytes=1000,
        is_full=True,
    )

    c_user = _client(
        stub_iam,
        user_id=205,
        username="user205",
        permissions=("badms.storage.request_extension", "badms.storage.view"),
    )
    res = c_user.post(
        "/api/v1/badms/storage/extensions",
        data={"requested_bytes": 5000, "justification": "Full disk", "department_id": 1},
        format="json",
    )
    assert res.status_code == 201
    ext_id = res.json()["id"]

    # HoD approves
    c_hod = _client(
        stub_iam,
        user_id=901,
        active_role="hod",
        permissions=("badms.storage.hod_decide",),
    )
    res_appr = c_hod.post(
        f"/api/v1/badms/storage/extensions/{ext_id}/hod-decision",
        data={"approve": True, "department_id": 1},
        format="json",
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "approved"


def test_reports_endpoints(stub_iam):
    c_hod = _client(
        stub_iam,
        user_id=901,
        active_role="hod",
        permissions=("badms.report.departmental",),
    )
    res_dept = c_hod.get("/api/v1/badms/reports/departmental?department_id=1")
    assert res_dept.status_code == 200
    assert "archival_summary" in res_dept.json()

    c_sec = _client(
        stub_iam,
        user_id=701,
        active_role="it_security_lead",
        permissions=("badms.report.security",),
    )
    res_sec = c_sec.get("/api/v1/badms/reports/security")
    assert res_sec.status_code == 200
    assert "total_security_events" in res_sec.json()

    c_admin = _client(
        stub_iam,
        user_id=801,
        active_role="sysadmin",
        permissions=("badms.report.compliance",),
    )
    res_comp = c_admin.get("/api/v1/badms/reports/compliance")
    assert res_comp.status_code == 200
    assert "total_backups" in res_comp.json()
