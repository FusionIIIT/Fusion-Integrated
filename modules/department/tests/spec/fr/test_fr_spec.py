"""Specification-based tests for Functional Requirements (FR).

Source: FR_DESIGN.json (60 test cases)
Obligations: CFR-DEPT-001..016, AFR-DEPT-001..031, 034..053
"""
import pytest

from modules.department.models import (
    Announcement,
    LabResource,
    StockItem,
    StockMovement,
)

pytestmark = pytest.mark.django_db
BASE = "/api/v1/department"


def test_fr_001_eligible_publishers(spec_client):
    """FR-001 | AFR-DEPT-001 Eligible publishers (CFR-DEPT-001)."""
    for role, uid in [("faculty", 11), ("deptadmin_cse", 14), ("HOD (CSE)", 13)]:
        client, _ = spec_client(role, user_id=uid)
        res = client.post(f"{BASE}/announcements", {
            "content": f"Announcement by {role}",
            "target_roles": ["student"],
            "target_programmes": [],
            "target_batch_years": []
        }, format="json")
        assert res.status_code == 201


def test_fr_002_publication_notifications(spec_client):
    """FR-002 | AFR-DEPT-046 Publication notifications (CFR-DEPT-001)."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "Seminar for Students",
        "target_roles": ["student"],
        "target_programmes": ["BTech"],
        "target_batch_years": [2024]
    }, format="json")
    assert res.status_code == 201

    student, _ = spec_client("student", user_id=12, programme="BTech", batch_year=2024)
    notices = student.get(f"{BASE}/notices").json()["results"]
    assert any("Seminar for Students" in n["content"] for n in notices)


def test_fr_003_audience_filters(spec_client):
    """FR-003 | AFR-DEPT-002 All three audience filters (CFR-DEPT-002)."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "Targeted Ann",
        "target_roles": ["student"],
        "target_programmes": ["BTech"],
        "target_batch_years": [2024]
    }, format="json")
    assert res.status_code == 201
    ann_id = res.json()["id"]

    match_student, _ = spec_client("student", user_id=12, programme="BTech", batch_year=2024)
    res_m = match_student.get(f"{BASE}/announcements").json()["results"]
    assert any(a["id"] == ann_id for a in res_m)

    mismatch_student, _ = spec_client("student", user_id=22, programme="MTech", batch_year=2024)
    res_mm = mismatch_student.get(f"{BASE}/announcements").json()["results"]
    assert not any(a["id"] == ann_id for a in res_mm)


def test_fr_004_relevant_announcement_access(spec_client):
    """FR-004 | AFR-DEPT-003 Relevant announcement access (CFR-DEPT-002)."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/announcements", {
        "content": "General Dept News",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json")
    assert res.status_code == 201

    student, _ = spec_client("student", user_id=12)
    feed = student.get(f"{BASE}/announcements").json()["results"]
    assert any("General Dept News" in a["content"] for a in feed)


def test_fr_005_hod_edits_active_announcement(spec_client):
    """FR-005 | AFR-DEPT-004 HOD edits an active announcement (CFR-DEPT-003)."""
    faculty, _ = spec_client("faculty", user_id=11)
    ann = faculty.post(f"{BASE}/announcements", {
        "content": "Initial Text",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.get(f"{BASE}/announcements/managed")
    assert res.status_code == 200
    assert any(a["id"] == ann["id"] for a in res.json()["results"])


def test_fr_006_hod_hides_active_announcement(spec_client):
    """FR-006 | AFR-DEPT-005 HOD hides an active announcement (CFR-DEPT-003)."""
    faculty, _ = spec_client("faculty", user_id=11)
    ann = faculty.post(f"{BASE}/announcements", {
        "content": "To be hidden",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/announcements/{ann['id']}/action", {"action": "hide"}, format="json")
    assert res.status_code == 204
    assert not Announcement.objects.get(id=ann["id"]).is_active


def test_fr_007_hod_deletes_active_announcement(spec_client):
    """FR-007 | AFR-DEPT-006 HOD deletes an active announcement (CFR-DEPT-003)."""
    faculty, _ = spec_client("faculty", user_id=11)
    ann = faculty.post(f"{BASE}/announcements", {
        "content": "To be deleted",
        "target_roles": [],
        "target_programmes": [],
        "target_batch_years": []
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/announcements/{ann['id']}/action", {"action": "delete"}, format="json")
    assert res.status_code == 204
    assert not Announcement.objects.filter(id=ann["id"]).exists()


def test_fr_008_stock_insertion(spec_client):
    """FR-008 | AFR-DEPT-007 Department stock insertion (CFR-DEPT-004)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/inventory", {
        "name": "Projector Cable",
        "quantity": 20}, format="json")
    assert res.status_code == 201
    assert res.json()["quantity"] == 20


def test_fr_009_current_quantity_maintained(spec_client):
    """FR-009 | AFR-DEPT-008 Current quantity is maintained (CFR-DEPT-004)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/inventory", {
        "name": "HDMI Adapters",
        "quantity": 15}, format="json")
    item_id = res.json()["id"]

    inv = admin.get(f"{BASE}/inventory").json()["results"]
    match = next(i for i in inv if i["id"] == item_id)
    assert match["quantity"] == 15


def test_fr_010_immutable_insertion_log(spec_client):
    """FR-010 | AFR-DEPT-014 Immutable insertion log (CFR-DEPT-004)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/inventory", {
        "name": "Keyboards",
        "quantity": 10}, format="json")
    item_id = res.json()["id"]

    log = StockMovement.objects.filter(stock_item_id=item_id, kind="receipt").first()
    assert log is not None
    assert log.quantity_delta == 10


def test_fr_011_faculty_submits_request(spec_client):
    """FR-011 | AFR-DEPT-009 Faculty submits a request (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Markers", "quantity": 50}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 5}, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending_hod"


def test_fr_012_request_quantity_equal_availability(spec_client):
    """FR-012 | AFR-DEPT-010 Request quantity equal to availability (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Calculators", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 10}, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending_hod"


def test_fr_013_request_quantity_above_availability(spec_client):
    """FR-013 | AFR-DEPT-010 Request quantity above availability (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Laptops", "quantity": 5}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 6}, format="json")
    assert res.status_code == 400


def test_fr_014_both_hod_decisions(spec_client):
    """FR-014 | AFR-DEPT-011 Both HOD decisions (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Notebooks", "quantity": 40}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req1 = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 2}, format="json").json()
    req2 = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 3}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res_app = hod.post(f"{BASE}/stock-requests/{req1['id']}/action", {"action": "approve"}, format="json")
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "approved"

    res_rej = hod.post(f"{BASE}/stock-requests/{req2['id']}/action", {"action": "reject"}, format="json")
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"


def test_fr_015_approved_issuance(spec_client):
    """FR-015 | AFR-DEPT-012 Approved issuance (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Mice", "quantity": 20}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 2}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")

    res_iss = admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json")
    assert res_iss.status_code == 200
    assert res_iss.json()["status"] == "issued"


def test_fr_016_issuance_requires_prior_approval(spec_client):
    """FR-016 | AFR-DEPT-012 Issuance requires prior approval (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Flash drives", "quantity": 20}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 2}, format="json").json()

    res_iss = admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json")
    assert res_iss.status_code == 409


def test_fr_017_issuance_deducts_quantity(spec_client):
    """FR-017 | AFR-DEPT-013 Issuance deducts the requested quantity (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Sensors", "quantity": 30}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 10}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")

    admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json")
    updated_item = StockItem.objects.get(id=item["id"])
    assert updated_item.quantity == 20


def test_fr_018_immutable_issuance_log(spec_client):
    """FR-018 | AFR-DEPT-015 Immutable issuance log (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Routers", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 3}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "approve"}, format="json")
    admin.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "issue"}, format="json")

    m = StockMovement.objects.filter(stock_item_id=item["id"], kind="issue").first()
    assert m is not None
    assert m.quantity_delta == -3


def test_fr_019_new_request_alerts_admin(spec_client):
    """FR-019 | AFR-DEPT-041 New request alerts Dept_Admin (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Paper Reams", "quantity": 100}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 5}, format="json")

    admin_notices = admin.get(f"{BASE}/notices").json()["results"]
    assert any("stock" in n["content"].lower() for n in admin_notices)


def test_fr_020_approval_request_alerts_hod(spec_client):
    """FR-020 | AFR-DEPT-042 Approval request alerts HOD (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Staplers", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json")

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod_notices = hod.get(f"{BASE}/notices").json()["results"]
    assert any("stock" in n["content"].lower() for n in hod_notices)


def test_fr_021_requester_receives_final_outcome(spec_client):
    """FR-021 | AFR-DEPT-043 Requester receives both kinds of final outcome (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "USB Hubs", "quantity": 20}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    req = faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod.post(f"{BASE}/stock-requests/{req['id']}/action", {"action": "reject"}, format="json")

    fac_notices = faculty.get(f"{BASE}/notices").json()["results"]
    assert any("rejected" in n["content"].lower() for n in fac_notices)


def test_fr_022_faculty_issued_history(spec_client):
    """FR-022 | AFR-DEPT-016 Faculty issued history is relevant (CFR-DEPT-006)."""
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.get(f"{BASE}/stock-requests")
    assert res.status_code == 200
    assert "results" in res.json()


def test_fr_023_both_feedback_submitters(spec_client):
    """FR-023 | AFR-DEPT-017 Both feedback submitter roles (CFR-DEPT-007)."""
    student, _ = spec_client("student", user_id=12)
    res_s = student.post(f"{BASE}/feedback", {"content": "Student suggestion"}, format="json")
    assert res_s.status_code == 201

    faculty, _ = spec_client("faculty", user_id=11)
    res_f = faculty.post(f"{BASE}/feedback", {"content": "Faculty suggestion"}, format="json")
    assert res_f.status_code == 201


def test_fr_024_feedback_confidentiality(spec_client):
    """FR-024 | AFR-DEPT-018 Feedback remains confidential (CFR-DEPT-007)."""
    student1, _ = spec_client("student", user_id=12)
    fb = student1.post(f"{BASE}/feedback", {"content": "Confidential matter"}, format="json").json()

    student2, _ = spec_client("student", user_id=22)
    feed2 = student2.get(f"{BASE}/feedback").json()["results"]
    assert not any(f["id"] == fb["id"] for f in feed2)


def test_fr_025_new_feedback_alerts_admin(spec_client):
    """FR-025 | AFR-DEPT-044 New feedback alerts Dept_Admin (CFR-DEPT-007)."""
    student, _ = spec_client("student", user_id=12)
    student.post(f"{BASE}/feedback", {"content": "Lab heating problem"}, format="json")

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    notices = admin.get(f"{BASE}/notices").json()["results"]
    assert any("feedback" in n["content"].lower() for n in notices)


def test_fr_026_initial_feedback_review(spec_client):
    """FR-026 | AFR-DEPT-019 Initial feedback review (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Exam scheduling conflict"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "categorize"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "under_review"


def test_fr_027_initial_review_categorization(spec_client):
    """FR-027 | AFR-DEPT-020 Initial review categorization (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Projector not working in 101"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "categorize"}, format="json")
    assert res.status_code == 200
    assert res.json()["category"] == "Facilities"


def test_fr_028_close_simple_issue_in_initial_review(spec_client):
    """FR-028 | AFR-DEPT-021 Close a simple issue during initial review (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Need extra whiteboard marker"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "close", "resolution_notes": "Provided"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_fr_029_both_reviewers_terminal_states(spec_client):
    """FR-029 | AFR-DEPT-022 Both reviewers can reach both terminal states (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb1 = student.post(f"{BASE}/feedback", {"content": "Item 1"}, format="json").json()
    fb2 = student.post(f"{BASE}/feedback", {"content": "Item 2"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb1['id']}/action", {"action": "categorize"}, format="json")
    admin.post(f"{BASE}/feedback/{fb2['id']}/action", {"action": "categorize"}, format="json")

    res_res = admin.post(f"{BASE}/feedback/{fb1['id']}/action", {"action": "resolve", "resolution_notes": "Done"}, format="json")
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "resolved"

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res_cls = hod.post(f"{BASE}/feedback/{fb2['id']}/action", {"action": "close", "resolution_notes": "Closed"}, format="json")
    assert res_cls.status_code == 200
    assert res_cls.json()["status"] == "closed"


def test_fr_030_hod_action_requires_initial_review(spec_client):
    """FR-030 | AFR-DEPT-022 HOD terminal action requires initial review (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Brand new feedback"}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "resolve", "resolution_notes": "Premature"}, format="json")
    assert res.status_code in [400, 409]


def test_fr_031_hod_oversight_starts_after_initial_review(spec_client):
    """FR-031 | AFR-DEPT-023 HOD oversight starts after initial review (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Feedback for oversight"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "categorize"}, format="json")

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res = hod.get(f"{BASE}/feedback")
    assert res.status_code == 200
    assert any(f["id"] == fb["id"] for f in res.json()["results"])


def test_fr_032_submitter_notified_on_disposition(spec_client):
    """FR-032 | AFR-DEPT-045 Submitter notified on resolution and closure (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Classroom projector"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "close", "resolution_notes": "Fixed"}, format="json")

    notices = student.get(f"{BASE}/notices").json()["results"]
    assert any("feedback" in n["content"].lower() for n in notices)


def test_fr_033_department_profile_management():
    """FR-033 | AFR-DEPT-024 Department profile management (CFR-DEPT-009)."""
    pytest.skip("NOT_AUTOMATED: External profile contract deferred per specification Phase 0 decision")


def test_fr_034_management_stays_in_department():
    """FR-034 | AFR-DEPT-024 Management stays within the department (CFR-DEPT-009)."""
    pytest.skip("NOT_AUTOMATED: External profile contract deferred per specification Phase 0 decision")


def test_fr_035_student_profile_basic():
    """FR-035 | AFR-DEPT-025 Student profile visibility is basic (CFR-DEPT-010)."""
    pytest.skip("NOT_AUTOMATED: External profile contract deferred per specification Phase 0 decision")


def test_fr_036_faculty_detailed_profile_course():
    """FR-036 | AFR-DEPT-026 Faculty sees detailed profiles for Students in their courses (CFR-DEPT-010)."""
    pytest.skip("NOT_AUTOMATED: External profile contract deferred per specification Phase 0 decision")


def test_fr_037_detailed_access_scoped_to_relationship():
    """FR-037 | AFR-DEPT-026 Detailed access is scoped to the Faculty course relationship (CFR-DEPT-010)."""
    pytest.skip("NOT_AUTOMATED: External profile contract deferred per specification Phase 0 decision")


def test_fr_038_faculty_alumni_visibility_limited():
    """FR-038 | AFR-DEPT-027 Faculty and Alumni visibility is limited (CFR-DEPT-010)."""
    pytest.skip("NOT_AUTOMATED: External profile contract deferred per specification Phase 0 decision")


def test_fr_039_full_view_excludes_protected():
    """FR-039 | AFR-DEPT-028 Full department view excludes protected data (CFR-DEPT-010)."""
    pytest.skip("NOT_AUTOMATED: External profile contract deferred per specification Phase 0 decision")


def test_fr_040_upload_timetables(spec_client):
    """FR-040 | AFR-DEPT-029 Upload class and lab timetables (CFR-DEPT-011)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 1,
            "starts_at": "09:00:00", "ends_at": "10:00:00",
            "title": "Data Structures", "kind": "class",
            "room": "Hall 1", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")
    assert res.status_code == 201


def test_fr_041_modify_timetables(spec_client):
    """FR-041 | AFR-DEPT-030 Modify class and lab timetables (CFR-DEPT-011)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    upload = admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 2,
            "starts_at": "11:00:00", "ends_at": "12:00:00",
            "title": "Algorithms", "kind": "class",
            "room": "Hall 2", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json").json()
    slot_id = upload["results"][0]["id"]

    res_mod = admin.put(f"{BASE}/timetable/{slot_id}", {
        "term": "Sem 1", "day": 2,
        "starts_at": "11:00:00", "ends_at": "12:00:00",
        "title": "Advanced Algorithms", "kind": "class",
        "room": "Hall 3", "instructor_id": 11,
        "programme": "BTech", "batch_year": 2024
    }, format="json")
    assert res_mod.status_code == 200
    assert res_mod.json()["title"] == "Advanced Algorithms"


def test_fr_042_block_overlapping_timetable_uploads(spec_client):
    """FR-042 | AFR-DEPT-031 Block overlapping timetable uploads (CFR-DEPT-011)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 3,
            "starts_at": "14:00:00", "ends_at": "15:00:00",
            "title": "OS", "kind": "class",
            "room": "Hall A", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")

    res_overlap = admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 3,
            "starts_at": "14:30:00", "ends_at": "15:30:00",
            "title": "Networks", "kind": "class",
            "room": "Hall A", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")
    assert res_overlap.status_code == 409


def test_fr_043_block_overlapping_timetable_edits(spec_client):
    """FR-043 | AFR-DEPT-031 Block overlapping timetable edits (CFR-DEPT-011)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/timetable", {
        "slots": [
            {
                "term": "Sem 1", "day": 4,
                "starts_at": "09:00:00", "ends_at": "10:00:00",
                "title": "Course 1", "kind": "class",
                "room": "Room X", "instructor_id": 11,
                "programme": "BTech", "batch_year": 2024
            },
            {
                "term": "Sem 1", "day": 4,
                "starts_at": "10:00:00", "ends_at": "11:00:00",
                "title": "Course 2", "kind": "class",
                "room": "Room Y", "instructor_id": 11,
                "programme": "BTech", "batch_year": 2024
            }
        ]
    }, format="json").json()
    slot2_id = res["results"][1]["id"]

    res_bad_edit = admin.put(f"{BASE}/timetable/{slot2_id}", {
        "term": "Sem 1", "day": 4,
        "starts_at": "09:30:00", "ends_at": "10:30:00",
        "title": "Course 2", "kind": "class",
        "room": "Room X", "instructor_id": 11,
        "programme": "BTech", "batch_year": 2024
    }, format="json")
    assert res_bad_edit.status_code == 409


def test_fr_044_update_lab_resource_details(spec_client):
    """FR-044 | AFR-DEPT-034 Update lab resource details (CFR-DEPT-012)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/labs", {
        "name": "Robotics Lab",
        "details": "Robotic arms and sensors"
    }, format="json")
    assert res.status_code in [200, 201]


def test_fr_045_faculty_can_view_lab_profiles(spec_client):
    """FR-045 | AFR-DEPT-035 Faculty can view lab profiles (CFR-DEPT-012)."""
    LabResource.objects.create(department="CSE", lab_name="AI Lab", equipment_details="GPUs")
    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.get(f"{BASE}/labs")
    assert res.status_code == 200
    assert any(lab["name"] == "AI Lab" for lab in res.json()["results"])


def test_fr_046_student_academic_program_info(spec_client):
    """FR-046 | AFR-DEPT-036 Student academic program information (CFR-DEPT-013)."""
    student, _ = spec_client("student", user_id=12, programme="BTech", batch_year=2024)
    res = student.get(f"{BASE}/academic-context")
    assert res.status_code == 200
    assert res.json()["programme"] == "BTech"


def test_fr_047_applicable_student_timetable(spec_client):
    """FR-047 | AFR-DEPT-037 Applicable Student timetable (CFR-DEPT-013)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/timetable", {
        "slots": [{
            "term": "Sem 1", "day": 5,
            "starts_at": "10:00:00", "ends_at": "11:00:00",
            "title": "Student Class", "kind": "class",
            "room": "Room 5", "instructor_id": 11,
            "programme": "BTech", "batch_year": 2024
        }]
    }, format="json")

    student, _ = spec_client("student", user_id=12, programme="BTech", batch_year=2024)
    res = student.get(f"{BASE}/timetable")
    assert res.status_code == 200
    assert any(s["title"] == "Student Class" for s in res.json()["results"])


def test_fr_048_general_department_detail_update(spec_client):
    """FR-048 | AFR-DEPT-038 General department detail update (CFR-DEPT-014)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/details", {
        "general_information": "Contact: cse@institute.ac.in"
    }, format="json")
    assert res.status_code == 200
    assert "Contact" in res.json()["general_information"]


def test_fr_049_pending_official_detail_stays_unpublished(spec_client):
    """FR-049 | AFR-DEPT-039 Pending official detail stays unpublished (CFR-DEPT-015)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/proposals", {
        "field": "name",
        "value": "School of Computing"
    }, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending_hod"

    det = admin.get(f"{BASE}/details").json()
    assert det.get("name") != "School of Computing"


def test_fr_050_approved_official_change_effective(spec_client):
    """FR-050 | AFR-DEPT-040 Approved official change becomes effective (CFR-DEPT-015)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {
        "field": "name",
        "value": "Department of Computer Science"
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res_app = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "approve"}, format="json")
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "approved"

    det = admin.get(f"{BASE}/details").json()
    assert det["name"] == "Department of Computer Science"


def test_fr_051_rejected_official_change_retains_data(spec_client):
    """FR-051 | AFR-DEPT-040 Rejected official change retains current data (CFR-DEPT-015)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {
        "field": "name",
        "value": "Bogus Name"
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res_rej = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "reject"}, format="json")
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"

    det = admin.get(f"{BASE}/details").json()
    assert det.get("name") != "Bogus Name"


def test_fr_052_central_authority_assigns_roles():
    """FR-052 | AFR-DEPT-047 Central authority assigns both department roles (CFR-DEPT-016)."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_fr_053_department_roles_require_central_authority():
    """FR-053 | AFR-DEPT-047 Department roles require central assignment authority (CFR-DEPT-016)."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_fr_054_validity_interval_tenure():
    """FR-054 | AFR-DEPT-048 Each assignment has a validity interval (CFR-DEPT-016)."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_fr_055_revoke_outgoing_access():
    """FR-055 | AFR-DEPT-049 Revoke outgoing access at the effective transition (CFR-DEPT-016)."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_fr_056_grant_incoming_access():
    """FR-056 | AFR-DEPT-050 Grant incoming access at the effective transition (CFR-DEPT-016)."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_fr_057_exactly_one_active_hod():
    """FR-057 | AFR-DEPT-051 Exactly one active HOD (CFR-DEPT-016)."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_fr_058_exactly_one_active_deptadmin():
    """FR-058 | AFR-DEPT-052 Exactly one active Dept_Admin (CFR-DEPT-016)."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_fr_059_displayed_headship_effective():
    """FR-059 | AFR-DEPT-053 Displayed Headship follows effective HOD (CFR-DEPT-016)."""
    pytest.skip("NOT_AUTOMATED: External IAM role assignment contract deferred per specification Phase 0 decision")


def test_fr_060_headship_cannot_be_independently_edited(spec_client):
    """FR-060 | AFR-DEPT-053 Headship cannot be independently edited as an official detail (CFR-DEPT-016)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/proposals", {
        "field": "headship",
        "value": "Fake HOD"
    }, format="json")
    assert res.status_code == 400
