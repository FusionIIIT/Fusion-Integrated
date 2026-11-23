"""Specification-based tests for Workflows (WF).

Source: WF_DESIGN.json (16 test cases)
Obligations: BW-DEPT-01..08, CW-DEPT-01..04
"""
import pytest

from modules.department.models import (
    DepartmentDetails,
    StockItem,
    StockMovement,
)

pytestmark = pytest.mark.django_db
BASE = "/api/v1/department"


def test_wf_001_01_stock_request_approved_and_issued(spec_client):
    """WF-001-01 | BW-DEPT-01 Stock Request Approved and Issued Path."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "WF Item 1", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 2}, format="json").json()
    assert req["status"] == "pending_hod"

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    app = hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json").json()
    assert app["status"] == "approved"

    iss = admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json").json()
    assert iss["status"] == "issued"
    assert StockItem.objects.get(id=item["id"]).quantity == 8


def test_wf_002_01_stock_request_rejected_by_hod(spec_client):
    """WF-002-01 | BW-DEPT-02 Stock Request Rejected by HOD Path."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "WF Item 2", "quantity": 5}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 2}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    rej = hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "reject"}, format="json").json()
    assert rej["status"] == "rejected"
    assert StockItem.objects.get(id=item["id"]).quantity == 5


def test_wf_003_01_stock_composite_approved_branch(spec_client):
    """WF-003-01 | CW-DEPT-01 Stock Request Composite Lifecycle Approved Branch."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "CW Item 1", "quantity": 20}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 5}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")

    iss = admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json").json()
    assert iss["status"] == "issued"
    assert StockMovement.objects.filter(stock_item_id=item["id"], kind="issue").exists()


def test_wf_003_02_stock_composite_rejected_branch(spec_client):
    """WF-003-02 | CW-DEPT-01 Stock Request Composite Lifecycle Rejected Branch."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "CW Item 2", "quantity": 20}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 5}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    rej = hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "reject"}, format="json").json()
    assert rej["status"] == "rejected"


def test_wf_004_01_feedback_disposed_by_admin(spec_client):
    """WF-004-01 | BW-DEPT-03 Feedback Disposed by Dept_Admin Path."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "BW-03 Simple issue"}, format="json").json()
    assert fb["status"] == "new"

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "categorize"}, format="json")
    cls = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "close", "resolution_notes": "Resolved by admin"}, format="json").json()
    assert cls["status"] == "closed"


def test_wf_005_01_feedback_disposed_with_hod_oversight(spec_client):
    """WF-005-01 | BW-DEPT-04 Feedback Disposed with HOD Oversight Path."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "BW-04 Major issue"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "categorize"}, format="json")

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "resolve", "resolution_notes": "Resolved by HOD"}, format="json").json()
    assert res["status"] == "resolved"


def test_wf_006_01_feedback_composite_admin_branch(spec_client):
    """WF-006-01 | CW-DEPT-02 Feedback Handling Composite Lifecycle Admin Branch."""
    faculty, _ = spec_client("faculty", user_id=11)
    fb = faculty.post(f"{BASE}/feedback", {"content": "CW-02 Admin Branch"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "categorize"}, format="json")
    cls = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "close", "resolution_notes": "Closed"}, format="json").json()
    assert cls["status"] == "closed"


def test_wf_006_02_feedback_composite_hod_branch(spec_client):
    """WF-006-02 | CW-DEPT-02 Feedback Handling Composite Lifecycle HOD Oversight Branch."""
    faculty, _ = spec_client("faculty", user_id=11)
    fb = faculty.post(f"{BASE}/feedback", {"content": "CW-02 HOD Branch"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "categorize"}, format="json")

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "resolve", "resolution_notes": "Resolved"}, format="json").json()
    assert res["status"] == "resolved"


def test_wf_007_01_official_change_approved(spec_client):
    """WF-007-01 | BW-DEPT-05 Official Department Change Approved Path."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {"field": "name", "value": "New Department Name"}, format="json").json()
    assert prop["status"] == "pending_hod"

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    app = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "approve"}, format="json").json()
    assert app["status"] == "approved"
    assert DepartmentDetails.objects.get(department="CSE").name == "New Department Name"


def test_wf_008_01_official_change_rejected(spec_client):
    """WF-008-01 | BW-DEPT-06 Official Department Change Rejected Path."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {"field": "name", "value": "Rejected Name"}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    rej = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "reject"}, format="json").json()
    assert rej["status"] == "rejected"
    assert DepartmentDetails.objects.get(department="CSE").name != "Rejected Name"


def test_wf_009_01_official_change_composite_approved(spec_client):
    """WF-009-01 | CW-DEPT-03 Official Department Change Composite Lifecycle Approved Branch."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {"field": "name", "value": "CW Approved Name"}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    app = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "approve"}, format="json").json()
    assert app["status"] == "approved"


def test_wf_009_02_official_change_composite_rejected(spec_client):
    """WF-009-02 | CW-DEPT-03 Official Department Change Composite Lifecycle Rejected Branch."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {"field": "name", "value": "CW Rejected Name"}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    rej = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "reject"}, format="json").json()
    assert rej["status"] == "rejected"


def test_wf_010_01_hod_reassignment_sync():
    """WF-010-01 | BW-DEPT-07 HOD Reassignment and Headship Synchronization Path."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_wf_011_01_deptadmin_reassignment_transition():
    """WF-011-01 | BW-DEPT-08 Dept_Admin Role Reassignment and Access Transition Path."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_wf_012_01_composite_role_reassignment_hod():
    """WF-012-01 | CW-DEPT-04 Department Role Reassignment Composite Lifecycle HOD Path."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_wf_012_02_composite_role_reassignment_admin():
    """WF-012-02 | CW-DEPT-04 Department Role Reassignment Composite Lifecycle Dept_Admin Path."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")
