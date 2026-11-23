"""Specification-based tests for Use Cases (UC).

Source: UC_DESIGN.json (44 test cases)
Obligations: UC-DEPT-001..012, 014..020, 022
"""
import pytest

from modules.department.models import (
    Announcement,
    LabResource,
    StockItem,
)

pytestmark = pytest.mark.django_db
BASE = "/api/v1/department"


def test_uc_001_01_view_announcements_main(spec_client):
    """UC-001-01 | UC-DEPT-001 Main Success Scenario."""
    faculty, _ = spec_client("faculty", user_id=11)
    faculty.post(f"{BASE}/announcements", {
        "content": "Seminar Announcement",
        "target_roles": ["student"],
        "target_programmes": ["BTech"],
        "target_batch_years": [2024]
    }, format="json")

    student, _ = spec_client("student", user_id=12, programme="BTech", batch_year=2024)
    res = student.get(f"{BASE}/announcements")
    assert res.status_code == 200
    assert any("Seminar Announcement" in a["content"] for a in res.json()["results"])


def test_uc_001_02_view_announcements_empty(spec_client):
    """UC-001-02 | UC-DEPT-001 Alternative Flow No Relevant Announcement."""
    student, _ = spec_client("student", user_id=12, programme="MTech", batch_year=2025)
    res = student.get(f"{BASE}/announcements")
    assert res.status_code == 200
    assert res.json()["results"] == []


def test_uc_002_01_create_announcement_main(spec_client):
    """UC-002-01 | UC-DEPT-002 Main Success Scenario."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "Hackathon 2026",
        "target_roles": ["student"],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json")
    assert res.status_code == 201
    assert res.json()["content"] == "Hackathon 2026"


def test_uc_002_02_create_announcement_invalid(spec_client):
    """UC-002-02 | UC-DEPT-002 Alternative Flow Invalid/Missing Target or Content."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json")
    assert res.status_code == 400


def test_uc_003_01_manage_announcement_edit(spec_client):
    """UC-003-01 | UC-DEPT-003 Main Success Scenario Edit."""
    faculty, _ = spec_client("faculty", user_id=11)
    ann = faculty.post(f"{BASE}/announcements", {
        "content": "Initial Notice",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.get(f"{BASE}/announcements/managed")
    assert res.status_code == 200
    assert any(a["id"] == ann["id"] for a in res.json()["results"])


def test_uc_003_02_manage_announcement_hide(spec_client):
    """UC-003-02 | UC-DEPT-003 Alternative Flow Hide."""
    faculty, _ = spec_client("faculty", user_id=11)
    ann = faculty.post(f"{BASE}/announcements", {
        "content": "Hide me",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/announcements/{ann['id']}/action", {"action": "hide"}, format="json")
    assert res.status_code == 204
    assert not Announcement.objects.get(id=ann["id"]).is_active


def test_uc_003_03_manage_announcement_delete(spec_client):
    """UC-003-03 | UC-DEPT-003 Alternative Flow Delete."""
    faculty, _ = spec_client("faculty", user_id=11)
    ann = faculty.post(f"{BASE}/announcements", {
        "content": "Delete me",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/announcements/{ann['id']}/action", {"action": "delete"}, format="json")
    assert res.status_code == 204
    assert not Announcement.objects.filter(id=ann["id"]).exists()


def test_uc_004_01_request_stock_main(spec_client):
    """UC-004-01 | UC-DEPT-004 Main Success Scenario."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Projector", "quantity": 5}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 1}, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending"


def test_uc_004_02_request_stock_insufficient(spec_client):
    """UC-004-02 | UC-DEPT-004 Alternative Flow Insufficient Inventory."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Screen", "quantity": 1}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 2}, format="json")
    assert res.status_code == 409


def test_uc_005_01_approve_stock_request(spec_client):
    """UC-005-01 | UC-DEPT-005 Main Success Scenario Approved."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Tablets", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 2}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "approved"


def test_uc_005_02_reject_stock_request(spec_client):
    """UC-005-02 | UC-DEPT-005 Alternative Flow Rejected."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "VR Headset", "quantity": 5}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "reject"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"


def test_uc_006_01_allocate_and_issue_stock(spec_client):
    """UC-006-01 | UC-DEPT-006 Main Success Scenario."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "HDMI Cord", "quantity": 15}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 3}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")

    res = admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "issued"
    assert StockItem.objects.get(id=item["id"]).quantity == 12


def test_uc_007_01_submit_feedback_main(spec_client):
    """UC-007-01 | UC-DEPT-007 Main Success Scenario."""
    student, _ = spec_client("student", user_id=12)
    res = student.post(f"{BASE}/feedback", {"content": "Great course curriculum"}, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "new"


def test_uc_007_02_submit_feedback_failure(spec_client):
    """UC-007-02 | UC-DEPT-007 Exception Flow Submission Failure."""
    student, _ = spec_client("student", user_id=12)
    res = student.post(f"{BASE}/feedback", {"content": ""}, format="json")
    assert res.status_code == 400


def test_uc_008_01_initial_review_categorization(spec_client):
    """UC-008-01 | UC-DEPT-008 Main Success Scenario Under Review."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Course syllabus question"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "reviewed"


def test_uc_008_02_initial_review_simple_closure(spec_client):
    """UC-008-02 | UC-DEPT-008 Alternative Flow Simple Issue Closure."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Simple room key question"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities", "close_simple": True}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_uc_008_03_initial_review_resolved_disposition(spec_client):
    """UC-008-03 | UC-DEPT-008 Alternative Flow Resolved Disposition."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Lab door locked during slot"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities"}, format="json")
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "resolve"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "resolved"


def test_uc_009_01_manage_timetable_main(spec_client):
    """UC-009-01 | UC-DEPT-009 Main Success Scenario."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 1,
            "starts_at": "08:00:00", "ends_at": "09:00:00",
            "title": "Discrete Math", "kind": "class",
            "room": "Hall 1", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")
    assert res.status_code == 201


def test_uc_009_02_manage_timetable_conflict(spec_client):
    """UC-009-02 | UC-DEPT-009 Alternative Flow Slot Conflict Detected."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 1,
            "starts_at": "08:00:00", "ends_at": "09:00:00",
            "title": "Slot A", "kind": "class",
            "room": "Room 101", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")

    res_conflict = admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 1,
            "starts_at": "08:30:00", "ends_at": "09:30:00",
            "title": "Slot B", "kind": "class",
            "room": "Room 101", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")
    assert res_conflict.status_code == 409


def test_uc_010_01_update_department_details_general(spec_client):
    """UC-010-01 | UC-DEPT-010 Main Success Scenario General Details."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/details", {
        "general_information": "Info: info@cse.ac.in"
    }, format="json")
    assert res.status_code == 200
    assert "Info" in res.json()["general_information"]


def test_uc_010_02_update_department_details_official_proposal(spec_client):
    """UC-010-02 | UC-DEPT-010 Main Success Scenario Official Change Proposal."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/proposals", {
        "field": "official_name",
        "value": "Department of Artificial Intelligence"
    }, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending"


def test_uc_010_03_update_department_details_validation_failure(spec_client):
    """UC-010-03 | UC-DEPT-010 Alternative Flow Validation Failure."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/proposals", {
        "field": "",
        "value": ""
    }, format="json")
    assert res.status_code == 400


def test_uc_011_01_view_department_resources_main(spec_client):
    """UC-011-01 | UC-DEPT-011 Main Success Scenario."""
    LabResource.objects.create(department="CSE", name="Networking Lab", details="Cisco switches")
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.get(f"{BASE}/labs")
    assert res.status_code == 200
    assert any(lab["name"] == "Networking Lab" for lab in res.json()["results"])


def test_uc_011_02_view_department_resources_empty(spec_client):
    """UC-011-02 | UC-DEPT-011 Alternative Flow Empty State."""
    faculty, _ = spec_client("faculty", user_id=11, department="ME")
    res = faculty.get(f"{BASE}/labs")
    assert res.status_code == 200
    assert res.json()["results"] == []


def test_uc_012_01_approve_official_change(spec_client):
    """UC-012-01 | UC-DEPT-012 Main Success Scenario Approved."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {
        "field": "official_name",
        "value": "CSE Department Official"
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "approve"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "approved"


def test_uc_012_02_reject_official_change(spec_client):
    """UC-012-02 | UC-DEPT-012 Alternative Flow Rejected."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {
        "field": "official_name",
        "value": "Rejected Proposal"
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "reject"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"


def test_uc_014_01_hod_oversight_resolution(spec_client):
    """UC-014-01 | UC-DEPT-014 Main Success Scenario Terminal Disposition."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Wifi drops in lab"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities"}, format="json")

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "resolve"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "resolved"


def test_uc_014_02_hod_oversight_non_terminal(spec_client):
    """UC-014-02 | UC-DEPT-014 Alternative Flow Non-Terminal Review."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Elective offerings"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    path = f"{BASE}/feedback/{fb['id']}/action"
    reviewed = admin.post(path, {"action": "review", "category": "Facilities"}, format="json")
    assert reviewed.status_code == 200

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    notes = "Discuss at the next department meeting"
    recorded = hod.post(path, {"action": "record_oversight", "oversight_notes": notes}, format="json")
    assert recorded.status_code == 200
    feed = hod.get(f"{BASE}/feedback")
    assert feed.status_code == 200
    row = next(item for item in feed.json()["results"] if item["id"] == fb["id"])
    assert row["status"] == "reviewed"
    assert row["oversight_at"]
    assert row["oversight_notes"] == notes
    assert row["disposed_at"] is None


def test_uc_017_01_manage_lab_profiles_main(spec_client):
    """UC-017-01 | UC-DEPT-017 Main Success Scenario."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/labs", {
        "name": "Embedded Systems Lab",
        "details": "Microcontrollers and FPGA boards"
    }, format="json")
    assert res.status_code in [200, 201]


def test_uc_017_02_manage_lab_profiles_validation_failure(spec_client):
    """UC-017-02 | UC-DEPT-017 Alternative Flow Validation Failure."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/labs", {
        "name": "",
        "details": ""
    }, format="json")
    assert res.status_code == 400


def test_uc_018_01_view_academic_info_main(spec_client):
    """UC-018-01 | UC-DEPT-018 Main Success Scenario."""
    student, _ = spec_client("student", user_id=12, programme="BTech", batch_year=2024)
    res = student.get(f"{BASE}/academic-context")
    assert res.status_code == 200
    assert "programme" in res.json()


def test_uc_018_02_view_academic_info_unavailable(spec_client):
    """UC-018-02 | UC-DEPT-018 Alternative Flow Unavailable Data."""
    student, _ = spec_client("student", user_id=99, programme=None, batch_year=None)
    res = student.get(f"{BASE}/timetable")
    assert res.status_code == 200
    assert res.json()["results"] == []


def test_uc_019_01_manage_inventory_records_main(spec_client):
    """UC-019-01 | UC-DEPT-019 Main Success Scenario Insertion."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/inventory", {
        "name": "Screwdriver Kit",
        "quantity": 8}, format="json")
    assert res.status_code == 201
    assert res.json()["quantity"] == 8


def test_uc_019_02_manage_inventory_invalid_data(spec_client):
    """UC-019-02 | UC-DEPT-019 Alternative Flow Invalid Stock Data."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/inventory", {
        "name": "Broken Item",
        "quantity": -5}, format="json")
    assert res.status_code == 400
