"""Specification-based tests for Functional Requirements (FR).

Source: FR_DESIGN.json (60 test cases)
Obligations: CFR-DEPT-001..016, AFR-DEPT-001..031, 034..053
"""
import pytest
from django.db import IntegrityError, transaction

from modules.department.models import (
    Announcement,
    DepartmentDetails,
    Feedback,
    LabResource,
    StockItem,
    StockMovement,
    StockRequest,
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
        "target_roles": ["student", "faculty"],
        "target_programmes": ["BTech"],
        "target_batch_years": [2024]
    }, format="json")
    assert res.status_code == 201

    for role, user_id in (("student", 12), ("faculty", 11)):
        matching, _ = spec_client(role, user_id=user_id, programme="BTech", batch_year=2024)
        outside, _ = spec_client(role, user_id=user_id + 20, programme="BTech", batch_year=2023)
        notices = matching.get(f"{BASE}/notices")
        assert notices.status_code == 200
        assert len(notices.json()["results"]) == 1
        excluded = outside.get(f"{BASE}/notices")
        assert excluded.status_code == 200
        assert excluded.json()["results"] == []


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
    original = {"content": "Initial Text", "target_roles": [], "target_programmes": [], "target_batch_years": []}
    created = faculty.post(f"{BASE}/announcements", original, format="json")
    assert created.status_code == 201
    announcement_id = created.json()["id"]

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    response = hod.post(f"{BASE}/announcements/{announcement_id}/action", {
        "action": "edit",
        "announcement": {**original, "content": "Updated Text"},
    }, format="json")
    assert response.status_code == 204
    assert Announcement.objects.get(pk=announcement_id).content == "Updated Text"


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

    log = StockMovement.objects.filter(item_id=item_id, request__isnull=True).first()
    assert log is not None
    assert log.delta == 10
    original_delta = log.delta
    movements = StockMovement.objects.filter(pk=log.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        movements.update(delta=original_delta * 2)
    with pytest.raises(IntegrityError), transaction.atomic():
        movements.delete()
    assert movements.get().delta == original_delta


def test_fr_011_faculty_submits_request(spec_client):
    """FR-011 | AFR-DEPT-009 Faculty submits a request (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Markers", "quantity": 50}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 5}, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending"


def test_fr_012_request_quantity_equal_availability(spec_client):
    """FR-012 | AFR-DEPT-010 Request quantity equal to availability (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Calculators", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 10}, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending"


def test_fr_013_request_quantity_above_availability(spec_client):
    """FR-013 | AFR-DEPT-010 Request quantity above availability (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Laptops", "quantity": 5}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    res = faculty.post(f"{BASE}/stock-requests", {
        "item_id": item["id"],
        "quantity": 6}, format="json")
    assert res.status_code == 409
    assert not StockRequest.objects.filter(item_id=item["id"]).exists()
    assert StockItem.objects.get(pk=item["id"]).quantity == 5


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
    inventory = admin.post(f"{BASE}/inventory", {"name": "Flash drives", "quantity": 20}, format="json")
    assert inventory.status_code == 201
    item_id = inventory.json()["id"]
    faculty, _ = spec_client("faculty", user_id=11)
    hod, _ = spec_client("HOD (CSE)", user_id=13)

    for expected_state in ("pending", "rejected"):
        response = faculty.post(f"{BASE}/stock-requests", {"item_id": item_id, "quantity": 2}, format="json")
        assert response.status_code == 201
        request_id = response.json()["id"]
        if expected_state == "rejected":
            decision = hod.post(f"{BASE}/stock-requests/{request_id}/action", {"action": "reject"}, format="json")
            assert decision.status_code == 200
        issuance = admin.post(f"{BASE}/stock-requests/{request_id}/action", {"action": "issue"}, format="json")
        assert issuance.status_code == 409
        assert StockRequest.objects.get(pk=request_id).status == expected_state
        assert StockItem.objects.get(pk=item_id).quantity == 20


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

    m = StockMovement.objects.filter(item_id=item["id"], request_id=req["id"]).first()
    assert m is not None
    assert m.delta == -3
    original_delta = m.delta
    movements = StockMovement.objects.filter(pk=m.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        movements.update(delta=original_delta * 2)
    with pytest.raises(IntegrityError), transaction.atomic():
        movements.delete()
    assert movements.get().delta == original_delta


def test_fr_019_new_request_alerts_admin(spec_client):
    """FR-019 | AFR-DEPT-041 New request alerts Dept_Admin (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Paper Reams", "quantity": 100}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 5}, format="json")

    admin_notices = admin.get(f"{BASE}/notices").json()["results"]
    assert any("stock" in n["message"].lower() for n in admin_notices)


def test_fr_020_approval_request_alerts_hod(spec_client):
    """FR-020 | AFR-DEPT-042 Approval request alerts HOD (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    item = admin.post(f"{BASE}/inventory", {"name": "Staplers", "quantity": 10}, format="json").json()

    faculty, _ = spec_client("faculty", user_id=11)
    faculty.post(f"{BASE}/stock-requests", {"item_id": item["id"], "quantity": 1}, format="json")

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    hod_notices = hod.get(f"{BASE}/notices").json()["results"]
    assert any("stock" in n["message"].lower() for n in hod_notices)


def test_fr_021_requester_receives_final_outcome(spec_client):
    """FR-021 | AFR-DEPT-043 Requester receives both kinds of final outcome (CFR-DEPT-005)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    inventory = admin.post(f"{BASE}/inventory", {"name": "USB Hubs", "quantity": 20}, format="json")
    assert inventory.status_code == 201
    hod, _ = spec_client("HOD (CSE)", user_id=13)

    requesters = []
    for user_id, outcome in ((11, "issued"), (21, "rejected")):
        faculty, _ = spec_client("faculty", user_id=user_id)
        submitted = faculty.post(f"{BASE}/stock-requests", {
            "item_id": inventory.json()["id"], "quantity": 1,
        }, format="json")
        assert submitted.status_code == 201
        request_id = submitted.json()["id"]
        path = f"{BASE}/stock-requests/{request_id}/action"
        decision = hod.post(path, {"action": "approve" if outcome == "issued" else "reject"}, format="json")
        assert decision.status_code == 200
        if outcome == "issued":
            assert admin.post(path, {"action": "issue"}, format="json").status_code == 200
        requesters.append((faculty, request_id, outcome))

    for faculty, request_id, outcome in requesters:
        notices = faculty.get(f"{BASE}/notices")
        assert notices.status_code == 200
        assert [row["message"] for row in notices.json()["results"]] == [
            f"Stock request #{request_id} was {outcome}.",
        ]


def test_fr_022_faculty_issued_history(spec_client):
    """FR-022 | AFR-DEPT-016 Faculty issued history is relevant (CFR-DEPT-006)."""
    own = StockItem.objects.create(department="CSE", name="Adapter", quantity=10)
    other = StockItem.objects.create(department="CSE", name="Cable", quantity=10)
    issued = StockRequest.objects.create(item=own, user_id=11, quantity=1, status="issued")
    StockRequest.objects.create(item=other, user_id=21, quantity=1, status="issued")
    StockRequest.objects.create(item=own, user_id=11, quantity=1, status="pending")

    faculty, _ = spec_client("faculty", user_id=11)
    response = faculty.get(f"{BASE}/stock-requests")
    assert response.status_code == 200
    assert [row["id"] for row in response.json()["results"]] == [issued.pk]


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

    handler, _ = spec_client("deptadmin_cse", user_id=14)
    inbox = handler.get(f"{BASE}/feedback")
    assert inbox.status_code == 200
    assert [(row["id"], row["content"]) for row in inbox.json()["results"]] == [
        (fb["id"], "Confidential matter"),
    ]

    student2, _ = spec_client("student", user_id=22)
    response = student2.get(f"{BASE}/feedback")
    assert response.status_code == 403
    assert fb["id"] not in [row["id"] for row in response.json().get("results", [])]


def test_fr_025_new_feedback_alerts_admin(spec_client):
    """FR-025 | AFR-DEPT-044 New feedback alerts Dept_Admin (CFR-DEPT-007)."""
    student, _ = spec_client("student", user_id=12)
    student.post(f"{BASE}/feedback", {"content": "Lab heating problem"}, format="json")

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    notices = admin.get(f"{BASE}/notices").json()["results"]
    assert any("feedback" in n["message"].lower() for n in notices)


def test_fr_026_initial_feedback_review(spec_client):
    """FR-026 | AFR-DEPT-019 Initial feedback review (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Exam scheduling conflict"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities"}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "reviewed"
    assert res.json()["reviewed_at"] is not None


def test_fr_027_initial_review_categorization(spec_client):
    """FR-027 | AFR-DEPT-020 Initial review categorization (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Projector not working in 101"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities"}, format="json")
    assert res.status_code == 200
    assert res.json()["category"] == "Facilities"


def test_fr_028_close_simple_issue_in_initial_review(spec_client):
    """FR-028 | AFR-DEPT-021 Close a simple issue during initial review (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Need extra whiteboard marker"}, format="json").json()

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities", "close_simple": True}, format="json")
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_fr_029_both_reviewers_terminal_states(spec_client):
    """FR-029 | AFR-DEPT-022 Both reviewers can reach both terminal states (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    hod, _ = spec_client("HOD (CSE)", user_id=13)

    for reviewer in (admin, hod):
        for action, outcome in (("close", "closed"), ("resolve", "resolved")):
            submission = student.post(f"{BASE}/feedback", {"content": "Feedback item"}, format="json")
            assert submission.status_code == 201
            path = f"{BASE}/feedback/{submission.json()['id']}/action"
            reviewed = admin.post(path, {"action": "review", "category": "Facilities"}, format="json")
            assert reviewed.status_code == 200
            disposition = reviewer.post(path, {"action": action}, format="json")
            assert disposition.status_code == 200
            assert disposition.json()["status"] == outcome


def test_fr_030_hod_action_requires_initial_review(spec_client):
    """FR-030 | AFR-DEPT-022 HOD terminal action requires initial review (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Brand new feedback"}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    for action in ("resolve", "close"):
        res = hod.post(f"{BASE}/feedback/{fb['id']}/action", {"action": action}, format="json")
        assert res.status_code == 404
    assert Feedback.objects.get(pk=fb["id"]).status == "new"


def test_fr_031_hod_oversight_starts_after_initial_review(spec_client):
    """FR-031 | AFR-DEPT-023 HOD oversight starts after initial review (CFR-DEPT-008)."""
    student, _ = spec_client("student", user_id=12)
    fb = student.post(f"{BASE}/feedback", {"content": "Feedback for oversight"}, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    before = hod.get(f"{BASE}/feedback")
    assert before.status_code == 200
    assert before.json()["results"] == []

    admin, _ = spec_client("deptadmin_cse", user_id=14)
    admin.post(f"{BASE}/feedback/{fb['id']}/action", {"action": "review", "category": "Facilities"}, format="json")

    res = hod.get(f"{BASE}/feedback")
    assert res.status_code == 200
    assert any(f["id"] == fb["id"] for f in res.json()["results"])


def test_fr_032_submitter_notified_on_disposition(spec_client):
    """FR-032 | AFR-DEPT-045 Submitter notified on resolution and closure (CFR-DEPT-008)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    submitters = []
    for user_id, action, outcome in ((12, "close", "closed"), (22, "resolve", "resolved")):
        student, _ = spec_client("student", user_id=user_id)
        submission = student.post(f"{BASE}/feedback", {"content": "Classroom projector"}, format="json")
        assert submission.status_code == 201
        feedback_id = submission.json()["id"]
        path = f"{BASE}/feedback/{feedback_id}/action"
        reviewed = admin.post(path, {"action": "review", "category": "Facilities"}, format="json")
        assert reviewed.status_code == 200
        assert admin.post(path, {"action": action}, format="json").status_code == 200
        submitters.append((student, feedback_id, outcome))

    for student, feedback_id, outcome in submitters:
        notices = student.get(f"{BASE}/notices")
        assert notices.status_code == 200
        assert [row["message"] for row in notices.json()["results"]] == [
            f"Feedback #{feedback_id} was {outcome}.",
        ]


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
    slot_id = upload[0]["id"]

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
    slot2_id = res[1]["id"]

    res_bad_edit = admin.put(f"{BASE}/timetable/{slot2_id}", {
        "term": "Sem 1", "day": 4,
        "starts_at": "09:30:00", "ends_at": "10:30:00",
        "title": "Course 2", "kind": "class",
        "room": "Room X", "instructor_id": 11,
        "programme": "BTech", "batch_year": 2024
    }, format="json")
    assert res_bad_edit.status_code == 409
    after = admin.get(f"{BASE}/timetable")
    assert after.status_code == 200
    assert {slot["id"]: slot for slot in after.json()["results"]} == {slot["id"]: slot for slot in res}


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
    LabResource.objects.create(department="CSE", name="AI Lab", details="GPUs")
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
    DepartmentDetails.objects.create(department="CSE", official_name="Original computing department")
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/proposals", {
        "field": "official_name",
        "value": "School of Computing"
    }, format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "pending"

    det = admin.get(f"{BASE}/details").json()
    assert det["official_name"] == "Original computing department"


def test_fr_050_approved_official_change_effective(spec_client):
    """FR-050 | AFR-DEPT-040 Approved official change becomes effective (CFR-DEPT-015)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {
        "field": "official_name",
        "value": "Department of Computer Science"
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res_app = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "approve"}, format="json")
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "approved"

    det = admin.get(f"{BASE}/details").json()
    assert det["official_name"] == "Department of Computer Science"


def test_fr_051_rejected_official_change_retains_data(spec_client):
    """FR-051 | AFR-DEPT-040 Rejected official change retains current data (CFR-DEPT-015)."""
    DepartmentDetails.objects.create(department="CSE", official_name="Original department name")
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    prop = admin.post(f"{BASE}/proposals", {
        "field": "official_name",
        "value": "Bogus Name"
    }, format="json").json()

    hod, _ = spec_client("HOD (CSE)", user_id=13)
    res_rej = hod.post(f"{BASE}/proposals/{prop['id']}/action", {"action": "reject"}, format="json")
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "rejected"

    det = admin.get(f"{BASE}/details").json()
    assert det["official_name"] == "Original department name"


def test_fr_060_headship_cannot_be_independently_edited(spec_client):
    """FR-060 | AFR-DEPT-053 Headship cannot be independently edited as an official detail (CFR-DEPT-016)."""
    admin, _ = spec_client("deptadmin_cse", user_id=14)
    res = admin.post(f"{BASE}/proposals", {
        "field": "headship",
        "value": "Fake HOD"
    }, format="json")
    assert res.status_code == 400
