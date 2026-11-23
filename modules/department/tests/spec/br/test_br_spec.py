
"""Specification-based tests for Business Rules (BR).

Source: BR_DESIGN.json (46 test cases)
Obligations: BR-DEPT-001..013, 015..019, 021..024
"""
import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from modules.department.models import (
    LabResource,
    StockMovement,
)

pytestmark = pytest.mark.django_db
BASE = "/api/v1/department"


def test_br_001_01_permitted_announcement_creators(spec_client):
    """BR-001-01 | BR-DEPT-001 Permitted Announcement Creators."""
    for role, uid in [("faculty", 11), ("deptadmin_cse", 14), ("HOD (CSE)", 13)]:
        client, _ = spec_client(role, user_id=uid)
        res = client.post(f"{BASE}/announcements", {
            "content": f"Notice by {role}",
            "target_roles": [],
            "target_programmes": [],
            "target_batch_years": []
        }, format="json")
        assert res.status_code == 201


def test_br_001_02_prohibited_announcement_creators(spec_client):
    """BR-001-02 | BR-DEPT-001 Prohibited Announcement Creators."""
    student, _ = spec_client("student", user_id=12)
    res = student.post(f"{BASE}/announcements", {
        "content": "Student notice",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json")
    assert res.status_code == 403


def test_br_002_01_matching_viewer_filter(spec_client):
    """BR-002-01 | BR-DEPT-002 Matching Viewer Filter."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "BTech 2024 Notice",
        "target_roles": ["student"],
        "target_programmes": ["BTech"],
        "target_batch_years": [2024]
    }, format="json")
    ann_id = res.json()["id"]

    student, _ = spec_client("student", user_id=12, programme="BTech", batch_year=2024)
    feed = student.get(f"{BASE}/announcements").json()["results"]
    assert any(a["id"] == ann_id for a in feed)


def test_br_002_02_mismatch_viewer_filter(spec_client):
    """BR-002-02 | BR-DEPT-002 Non-Matching Role/Program/Year Mismatch."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "Targeted Exclusive",
        "target_roles": ["student"],
        "target_programmes": ["BTech"],
        "target_batch_years": [2024]
    }, format="json")
    ann_id = res.json()["id"]

    student_diff_year, _ = spec_client("student", user_id=22, programme="BTech", batch_year=2026)
    feed = student_diff_year.get(f"{BASE}/announcements").json()["results"]
    assert not any(a["id"] == ann_id for a in feed)


def test_br_003_01_complete_publication_payload(spec_client):
    """BR-003-01 | BR-DEPT-003 Complete Publication Payload."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "Complete Content",
        "target_roles": ["faculty", "student"],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json")
    assert res.status_code == 201


def test_br_003_02_incomplete_publication_payload_refusal(spec_client):
    """BR-003-02 | BR-DEPT-003 Incomplete Publication Payload Refusal."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "",
        "target_roles": []
    }, format="json")
    assert res.status_code == 400


def test_br_004_01_hod_modification_authority(spec_client):
    """BR-004-01 | BR-DEPT-004 HOD Modification Authority."""
    faculty, _ = spec_client("faculty", user_id=11)
    ann = faculty.post(f"{BASE}/announcements", {
        "content": "Active Post",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res_hide = hod.post(f"{BASE}/announcements/{ann['id']}/action", {"action": "hide"}, format="json")
    assert res_hide.status_code == 204


def test_br_004_02_non_hod_modification_refusal(spec_client):
    """BR-004-02 | BR-DEPT-004 Non-HOD Modification Refusal."""
    faculty, _ = spec_client("faculty", user_id=11)
    ann = faculty.post(f"{BASE}/announcements", {
        "content": "Active Post",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/announcements/{ann['id']}/action", {"action": "hide"}, format="json")
    assert res.status_code == 403


def test_br_005_01_faculty_stock_request_permitted(spec_client):
    """BR-005-01 | BR-DEPT-005 Faculty Stock Request Permitted."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Paper", "quantity": 100}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 5}, format="json")
    assert res.status_code == 201


def test_br_005_02_non_faculty_stock_request_prohibited(spec_client):
    """BR-005-02 | BR-DEPT-005 Non-Faculty Stock Request Prohibited."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Paper", "quantity": 100}, format="json").json()

    student, _ = spec_client("student", user_id=12)
    res = student.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 1}, format="json")
    assert res.status_code == 403


def test_br_006_01_hod_stock_approval_permitted(spec_client):
    """BR-006-01 | BR-DEPT-006 HOD Stock Approval Authority."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Toner", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "approved"


def test_br_006_02_non_hod_stock_approval_prohibited(spec_client):
    """BR-006-02 | BR-DEPT-006 Non-HOD Stock Approval Prohibited."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Toner", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json").json()

    res = admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")
    assert res.status_code == 403


def test_br_007_01_approved_issuance_permitted(spec_client):
    """BR-007-01 | BR-DEPT-007 Approved Request Issuance Permitted."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "VGA Cable", "quantity": 5}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")

    res = admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "issued"


def test_br_007_02_unapproved_issuance_prohibited(spec_client):
    """BR-007-02 | BR-DEPT-007 Unapproved Request Issuance Prohibited."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "DVI Cable", "quantity": 5}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json").json()

    res = admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json")
    assert res.status_code == 409


def test_br_007_03_non_admin_issuance_prohibited(spec_client):
    """BR-007-03 | BR-DEPT-007 Non-Dept_Admin Issuance Prohibited."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Power Cord", "quantity": 5}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")

    res = faculty.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json")
    assert res.status_code == 403


def test_br_008_01_eligible_feedback_submitters(spec_client):
    """BR-008-01 | BR-DEPT-008 Eligible Feedback Submitters."""
    student, _ = spec_client("student", user_id=12)
    res_s = student.post(f"{BASE}/feedback", {"content": "Student Voice"}, format="json")
    assert res_s.status_code == 201

    faculty, _ = spec_client("faculty", user_id=11)
    res_f = faculty.post(f"{BASE}/feedback", {"content": "Faculty Voice"}, format="json")
    assert res_f.status_code == 201


def test_br_008_02_unauthenticated_feedback_refusal():
    """BR-008-02 | BR-DEPT-008 Unauthenticated Feedback Refusal."""
    client = APIClient()
    res = client.post(f"{BASE}/feedback", {"content": "Anon message"}, format="json")
    assert res.status_code in [401, 403]


def test_br_009_01_authorized_terminal_feedback_disposition(spec_client):
    """BR-009-01 | BR-DEPT-009 Authorized Terminal Feedback Disposition."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Lab setup issue"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities"}, format="json")

    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "resolve"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "resolved"


def test_br_009_02_simple_issue_closure_by_admin(spec_client):
    """BR-009-02 | BR-DEPT-009 Simple Issue Direct Closure by Dept_Admin."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Query about lab timings"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities", "close_simple": True}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_br_009_03_unauthorized_feedback_disposition_prohibited(spec_client):
    """BR-009-03 | BR-DEPT-009 Unauthorized Feedback Disposition Prohibited."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "General issue"}, format="json").json()

    res = student.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "close"}, format="json")
    assert res.status_code == 403


def test_br_010_01_conflict_free_timetable_save(spec_client):
    """BR-010-01 | BR-DEPT-010 Conflict-Free Timetable Save."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 1,
            "starts_at": "12:00:00", "ends_at": "13:00:00",
            "title": "Maths", "kind": "class",
            "room": "Room A", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")
    assert res.status_code == 201


def test_br_010_02_overlapping_timetable_refusal(spec_client):
    """BR-010-02 | BR-DEPT-010 Overlapping Room/Instructor/Cohort Refusal."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 1,
            "starts_at": "13:00:00", "ends_at": "14:00:00",
            "title": "Physics", "kind": "class",
            "room": "Lab 1", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")

    res = admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 1,
            "starts_at": "13:30:00", "ends_at": "14:30:00",
            "title": "Chemistry", "kind": "class",
            "room": "Lab 1", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")
    assert res.status_code == 409


def test_br_011_01_official_change_remains_pending(spec_client):
    """BR-011-01 | BR-DEPT-011 Official Change Remains Pending Until Approval."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/proposals", {
        "field": "official_name",
        "value": "Department of Computer Science & Engineering"
    }, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending"


def test_br_011_02_general_change_effective_without_approval(spec_client):
    """BR-011-02 | BR-DEPT-011 General Change Effective Without Approval."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/details", {
        "general_information": "Admin: admin@cse.ac.in"
    }, format="json")
    assert res.status_code == 200
    assert "Admin" in res.json()["general_information"]


def test_br_012_01_department_resource_scope_permitted(spec_client):
    """BR-012-01 | BR-DEPT-012 Department Resource Scope Permitted."""
    LabResource.objects.create(department="CSE", name="Software Lab", details="Desktops")
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.get(f"{BASE}/labs")
    assert res.status_code == 200
    assert any(lab["name"] == "Software Lab" for lab in res.json()["results"])


def test_br_012_02_cross_department_resource_refused(spec_client):
    """BR-012-02 | BR-DEPT-012 Cross-Department Resource Access Refused."""
    LabResource.objects.create(department="ME", name="Workshop", details="Lathes")
    faculty, _ = spec_client("faculty", user_id=11, department="CSE")
    res = faculty.get(f"{BASE}/labs")
    assert res.status_code == 200
    assert not any(lab["name"] == "Workshop" for lab in res.json()["results"])


def test_br_013_01_hod_official_decision_permitted(spec_client):
    """BR-013-01 | BR-DEPT-013 HOD Official Update Decision Authority."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {"field": "official_name", "value": "CSE Dept"}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "approve"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "approved"


def test_br_013_02_non_hod_official_decision_prohibited(spec_client):
    """BR-013-02 | BR-DEPT-013 Non-HOD Official Decision Prohibited."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {"field": "official_name", "value": "CSE Dept"}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "approve"}, format="json")
    assert res.status_code == 403


def test_br_015_01_available_quantity_acceptance(spec_client):
    """BR-015-01 | BR-DEPT-015 Available Quantity Acceptance."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Keyboard", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 5}, format="json")
    assert res.status_code == 201


def test_br_015_02_exceeding_quantity_refusal(spec_client):
    """BR-015-02 | BR-DEPT-015 Exceeding Quantity Refusal."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Keyboard", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 11}, format="json")
    assert res.status_code == 409


def test_br_016_01_audit_log_created(spec_client):
    """BR-016-01 | BR-DEPT-016 Stock Movement Audit Immutability."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Monitors", "quantity": 12}, format="json").json()

    movement = StockMovement.objects.filter(item_id=item["id"]).first()
    assert movement is not None
    assert movement.delta == 12
    assert movement.actor_id == 14
    assert movement.created_at is not None


def test_br_016_02_movement_log_immutability(spec_client):
    """BR-016-02 | BR-DEPT-016 Movement Log Immutability Enforcement."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Cables", "quantity": 5}, format="json").json()
    movements = StockMovement.objects.filter(item_id=item["id"])
    assert movements.get().delta == 5
    with pytest.raises(IntegrityError), transaction.atomic():
        movements.update(delta=99)
    with pytest.raises(IntegrityError), transaction.atomic():
        movements.delete()
    assert movements.get().delta == 5


def test_br_017_01_authorized_feedback_access(spec_client):
    """BR-017-01 | BR-DEPT-017 Feedback Confidentiality and Access."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Confidential matter"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    feed_admin = admin.get(f"{BASE}/feedback").json()["results"]
    assert any(f["id"] == fb["id"] for f in feed_admin)


def test_br_017_02_third_party_feedback_refused(spec_client):
    """BR-017-02 | BR-DEPT-017 Third-Party Feedback Access Refusal."""
    student1, _ = spec_client("student", user_id=12)
    fb = student1.post(f"{BASE}/feedback", {"content": "Secret note"}, format="json").json()

    student2, _ = spec_client("student", user_id=22)
    response = student2.get(f"{BASE}/feedback")
    assert response.status_code == 403
    assert fb["id"] not in [row["id"] for row in response.json().get("results", [])]


def test_br_018_01_mandatory_admin_initial_review(spec_client):
    """BR-018-01 | BR-DEPT-018 Feedback Initial Review Responsibility."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Needs triage"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "reviewed"


def test_br_018_02_hod_action_pre_review_restraint(spec_client):
    """BR-018-02 | BR-DEPT-018 HOD Action Pre-Review Restraint."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Direct HOD attempt"}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "resolve"}, format="json")
    assert res.status_code == 404
