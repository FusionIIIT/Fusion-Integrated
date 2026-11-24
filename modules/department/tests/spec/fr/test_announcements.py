"""Functional Requirement spec tests: Announcements (TC-DEPT-001..TC-DEPT-013)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from modules.department.models import Announcement, DepartmentNotification
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _publish(act, role: str, **overrides):
    payload = {
        "title": "Department Notice",
        "body": "Important department update.",
        "audience_role": "student",
        "programme": "B.Tech",
        "batch_year": 2024,
        **overrides,
    }
    return act(role).post(f"{API}/announcements", payload, format="json")


def test_tc_dept_001_authorized_publication(world, act):
    """TC-DEPT-001 | AFR-DEPT-001 authorized publication"""
    for role in ("faculty", "admin", "hod"):
        resp = _publish(act, role, title=f"Notice from {role}")
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["status"] == "active"
        ann = Announcement.objects.get(pk=body["id"])
        assert ann.status == Announcement.ACTIVE
        assert ann.author_id == uid(role)
        assert ann.audience_role == "student"
        assert ann.programme == "B.Tech"
        assert ann.batch_year == 2024
    assert Announcement.objects.filter(status=Announcement.ACTIVE).count() == 3


def test_tc_dept_002_unauthorized_student_denial(world, act):
    """TC-DEPT-002 | AFR-DEPT-001 unauthorized student denial"""
    resp = _publish(act, "student", title="Unauthorized notice")
    assert resp.status_code == 403
    assert Announcement.objects.count() == 0


def test_tc_dept_003_target_scope_notification(world, act):
    """TC-DEPT-003 | AFR-DEPT-046 target-scope notification"""
    resp = _publish(
        act,
        "faculty",
        title="B.Tech 2024 and CSE Faculty Notice",
        audience_role="all",
        programme="B.Tech",
        batch_year=2024,
    )
    assert resp.status_code == 201, resp.content

    notified = set(
        DepartmentNotification.objects.filter(topic="announcement.published").values_list(
            "recipient_user_id", flat=True
        )
    )
    # Matching in-scope CSE B.Tech 2024 student and CSE faculty are notified.
    assert uid("student") in notified
    assert uid("faculty") in notified
    assert uid("faculty2") in notified
    # Out-of-scope users (different batch year or different department) are excluded.
    assert uid("student2") not in notified
    assert uid("ece_student") not in notified
    assert uid("ece_faculty") not in notified


def test_tc_dept_004_matching_visibility_filter(world, act):
    """TC-DEPT-004 | AFR-DEPT-002 matching visibility filter"""
    created = _publish(
        act,
        "hod",
        title="B.Tech 2024 Exam Schedule",
        audience_role="student",
        programme="B.Tech",
        batch_year=2024,
    )
    assert created.status_code == 201
    ann_id = created.json()["id"]

    resp = act("student").get(f"{API}/announcements")
    assert resp.status_code == 200
    returned_ids = {item["id"] for item in resp.json()["results"]}
    assert ann_id in returned_ids


def test_tc_dept_005_mismatched_scope_exclusion(world, act):
    """TC-DEPT-005 | AFR-DEPT-002 mismatched scope exclusion"""
    mismatched_role = _publish(
        act, "hod", title="Faculty only", audience_role="faculty", programme="", batch_year=None
    )
    mismatched_program = _publish(
        act, "hod", title="M.Tech only", audience_role="student", programme="M.Tech", batch_year=2024
    )
    mismatched_year = _publish(
        act, "hod", title="2023 batch only", audience_role="student", programme="B.Tech", batch_year=2023
    )
    assert mismatched_role.status_code == 201
    assert mismatched_program.status_code == 201
    assert mismatched_year.status_code == 201

    resp = act("student").get(f"{API}/announcements")
    assert resp.status_code == 200
    returned_ids = {item["id"] for item in resp.json()["results"]}
    assert mismatched_role.json()["id"] not in returned_ids
    assert mismatched_program.json()["id"] not in returned_ids
    assert mismatched_year.json()["id"] not in returned_ids


def test_tc_dept_006_authenticated_relevant_view(world, act):
    """TC-DEPT-006 | AFR-DEPT-003 authenticated relevant view"""
    student_ann = _publish(
        act,
        "admin",
        title="Student Notice",
        body="For CSE B.Tech 2024 students.",
        audience_role="student",
        programme="B.Tech",
        batch_year=2024,
    )
    faculty_ann = _publish(
        act,
        "admin",
        title="Faculty Meeting",
        body="Department faculty meeting at 3 PM.",
        audience_role="faculty",
        programme="",
        batch_year=None,
    )
    assert student_ann.status_code == 201
    assert faculty_ann.status_code == 201

    student_resp = act("student").get(f"{API}/announcements")
    assert student_resp.status_code == 200
    student_items = {a["id"]: a for a in student_resp.json()["results"]}
    assert student_ann.json()["id"] in student_items
    assert student_items[student_ann.json()["id"]]["body"] == "For CSE B.Tech 2024 students."

    faculty_resp = act("faculty").get(f"{API}/announcements")
    assert faculty_resp.status_code == 200
    faculty_items = {a["id"]: a for a in faculty_resp.json()["results"]}
    assert faculty_ann.json()["id"] in faculty_items
    assert faculty_items[faculty_ann.json()["id"]]["body"] == "Department faculty meeting at 3 PM."


def test_tc_dept_007_unauthenticated_access_denial(world, act):
    """TC-DEPT-007 | AFR-DEPT-003 unauthenticated access denial"""
    created = _publish(act, "hod", title="Public-looking notice", audience_role="all", programme="", batch_year=None)
    assert created.status_code == 201

    anon = APIClient()
    resp = anon.get(f"{API}/announcements")
    assert resp.status_code == 401
    assert "results" not in resp.json()


def test_tc_dept_008_hod_edit_active_announcement(world, act):
    """TC-DEPT-008 | AFR-DEPT-004 HOD edit active announcement"""
    created = _publish(act, "faculty", title="Original Title", body="Original Body")
    assert created.status_code == 201
    ann_id = created.json()["id"]

    resp = act("hod").patch(
        f"{API}/announcements/{ann_id}",
        {"title": "Updated Title", "body": "Updated Body"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["body"] == "Updated Body"

    ann = Announcement.objects.get(pk=ann_id)
    assert ann.title == "Updated Title"
    assert ann.body == "Updated Body"

    student_view = act("student").get(f"{API}/announcements").json()["results"]
    by_id = {a["id"]: a for a in student_view}
    assert by_id[ann_id]["title"] == "Updated Title"
    assert by_id[ann_id]["body"] == "Updated Body"


def test_tc_dept_009_non_hod_edit_denial(world, act):
    """TC-DEPT-009 | AFR-DEPT-004 non-HOD edit denial"""
    created = _publish(act, "faculty", title="Immutable by non-HOD", body="Original text")
    assert created.status_code == 201
    ann_id = created.json()["id"]

    for role in ("faculty", "admin", "student"):
        resp = act(role).patch(
            f"{API}/announcements/{ann_id}",
            {"title": f"Hacked by {role}"},
            format="json",
        )
        assert resp.status_code == 403

    ann = Announcement.objects.get(pk=ann_id)
    assert ann.title == "Immutable by non-HOD"
    assert ann.body == "Original text"


def test_tc_dept_010_hod_hide_active_announcement(world, act):
    """TC-DEPT-010 | AFR-DEPT-005 HOD hide active announcement"""
    created = _publish(act, "faculty", title="Visible Notice")
    assert created.status_code == 201
    ann_id = created.json()["id"]

    before_ids = {a["id"] for a in act("student").get(f"{API}/announcements").json()["results"]}
    assert ann_id in before_ids

    resp = act("hod").post(f"{API}/announcements/{ann_id}/hide")
    assert resp.status_code == 200
    assert resp.json()["status"] == "hidden"
    assert Announcement.objects.get(pk=ann_id).status == Announcement.HIDDEN

    after_ids = {a["id"] for a in act("student").get(f"{API}/announcements").json()["results"]}
    assert ann_id not in after_ids


def test_tc_dept_011_non_hod_hide_denial(world, act):
    """TC-DEPT-011 | AFR-DEPT-005 non-HOD hide denial"""
    created = _publish(act, "faculty", title="Active Notice")
    assert created.status_code == 201
    ann_id = created.json()["id"]

    for role in ("faculty", "admin", "student"):
        resp = act(role).post(f"{API}/announcements/{ann_id}/hide")
        assert resp.status_code == 403

    assert Announcement.objects.get(pk=ann_id).status == Announcement.ACTIVE
    visible_ids = {a["id"] for a in act("student").get(f"{API}/announcements").json()["results"]}
    assert ann_id in visible_ids


def test_tc_dept_012_hod_delete_active_announcement(world, act):
    """TC-DEPT-012 | AFR-DEPT-006 HOD delete active announcement"""
    created = _publish(act, "faculty", title="To Be Deleted")
    assert created.status_code == 201
    ann_id = created.json()["id"]

    resp = act("hod").delete(f"{API}/announcements/{ann_id}")
    assert resp.status_code == 204
    assert Announcement.objects.get(pk=ann_id).status == Announcement.DELETED

    for role in ("student", "faculty", "hod"):
        visible_ids = {a["id"] for a in act(role).get(f"{API}/announcements").json()["results"]}
        assert ann_id not in visible_ids


def test_tc_dept_013_non_hod_delete_denial(world, act):
    """TC-DEPT-013 | AFR-DEPT-006 non-HOD delete denial"""
    created = _publish(act, "faculty", title="Cannot Delete")
    assert created.status_code == 201
    ann_id = created.json()["id"]

    for role in ("faculty", "admin", "student"):
        resp = act(role).delete(f"{API}/announcements/{ann_id}")
        assert resp.status_code == 403

    assert Announcement.objects.get(pk=ann_id).status == Announcement.ACTIVE
