"""Business Rule spec tests: Announcements (TC-DEPT-BR-001..TC-DEPT-BR-008)."""

from __future__ import annotations

import pytest

from modules.department.models import Announcement
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _publish(act, role: str, **overrides):
    payload = {
        "title": "Department Notice",
        "body": "Important department announcement.",
        "audience_role": "student",
        "programme": "B.Tech",
        "batch_year": 2024,
        **overrides,
    }
    return act(role).post(f"{API}/announcements", payload, format="json")


def test_tc_dept_br_001_permitted_roles(world, act):
    """TC-DEPT-BR-001 | BR-DEPT-001 permitted-roles"""
    for role in ("faculty", "admin", "hod"):
        resp = _publish(act, role, title=f"Notice from {role}")
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["status"] == "active"
        ann = Announcement.objects.get(pk=body["id"])
        assert ann.status == Announcement.ACTIVE
        assert ann.author_id == uid(role)
        assert ann.department.code == "CSE"

    assert Announcement.objects.filter(status=Announcement.ACTIVE).count() == 3


def test_tc_dept_br_002_prohibited_role(world, act):
    """TC-DEPT-BR-002 | BR-DEPT-001 prohibited-role"""
    resp = _publish(act, "student", title="Student attempt")
    assert resp.status_code == 403
    assert Announcement.objects.count() == 0


def test_tc_dept_br_003_matching_criteria(world, act):
    """TC-DEPT-BR-003 | BR-DEPT-002 matching-criteria"""
    created = _publish(
        act,
        "hod",
        title="B.Tech 2024 Schedule",
        body="Classes start at 09:00.",
        audience_role="student",
        programme="B.Tech",
        batch_year=2024,
    )
    assert created.status_code == 201, created.content
    ann_id = created.json()["id"]

    resp = act("student").get(f"{API}/announcements")
    assert resp.status_code == 200
    by_id = {item["id"]: item for item in resp.json()["results"]}
    assert ann_id in by_id
    assert by_id[ann_id]["title"] == "B.Tech 2024 Schedule"
    assert by_id[ann_id]["body"] == "Classes start at 09:00."
    assert by_id[ann_id]["audience_role"] == "student"
    assert by_id[ann_id]["programme"] == "B.Tech"
    assert by_id[ann_id]["batch_year"] == 2024


def test_tc_dept_br_004_non_matching_criteria(world, act):
    """TC-DEPT-BR-004 | BR-DEPT-002 non-matching-criteria"""
    btech_2024 = _publish(
        act,
        "hod",
        title="B.Tech 2024 Students Only",
        audience_role="student",
        programme="B.Tech",
        batch_year=2024,
    )
    mtech_2024 = _publish(
        act,
        "hod",
        title="M.Tech 2024 Students Only",
        audience_role="student",
        programme="M.Tech",
        batch_year=2024,
    )
    assert btech_2024.status_code == 201
    assert mtech_2024.status_code == 201
    btech_id = btech_2024.json()["id"]
    mtech_id = mtech_2024.json()["id"]

    # Role mismatch: Faculty viewing a student-targeted announcement.
    faculty_ids = {a["id"] for a in act("faculty").get(f"{API}/announcements").json()["results"]}
    assert btech_id not in faculty_ids

    # Academic-year mismatch: 2023-batch student viewing a 2024-batch announcement.
    year_mismatch_ids = {
        a["id"] for a in act("student2").get(f"{API}/announcements").json()["results"]
    }
    assert btech_id not in year_mismatch_ids

    # Program mismatch: B.Tech student viewing an M.Tech announcement.
    program_mismatch_ids = {
        a["id"] for a in act("student").get(f"{API}/announcements").json()["results"]
    }
    assert mtech_id not in program_mismatch_ids


def test_tc_dept_br_005_valid_complete_submission(world, act):
    """TC-DEPT-BR-005 | BR-DEPT-003 valid-complete-submission"""
    resp = act("faculty").post(
        f"{API}/announcements",
        {
            "title": "Lab Orientation",
            "body": "Mandatory safety orientation in Lab-1.",
            "audience_role": "student",
            "programme": "B.Tech",
            "batch_year": 2024,
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["status"] == "active"
    assert Announcement.objects.filter(pk=body["id"], status=Announcement.ACTIVE).exists()


def test_tc_dept_br_006_missing_or_invalid_fields(world, act):
    """TC-DEPT-BR-006 | BR-DEPT-003 missing-or-invalid-fields"""
    invalid_payloads = [
        # Empty content (title / body).
        {
            "title": "   ",
            "body": "Body text",
            "audience_role": "student",
            "programme": "B.Tech",
            "batch_year": 2024,
        },
        {
            "title": "Valid Title",
            "body": "   ",
            "audience_role": "student",
            "programme": "B.Tech",
            "batch_year": 2024,
        },
        # Missing content fields.
        {
            "audience_role": "student",
            "programme": "B.Tech",
            "batch_year": 2024,
        },
        # Missing target-scope role.
        {
            "title": "Valid Title",
            "body": "Valid body",
        },
        # Invalid target-scope role.
        {
            "title": "Valid Title",
            "body": "Valid body",
            "audience_role": "outsider",
            "programme": "B.Tech",
            "batch_year": 2024,
        },
        # Invalid batch year.
        {
            "title": "Valid Title",
            "body": "Valid body",
            "audience_role": "student",
            "programme": "B.Tech",
            "batch_year": 1990,
        },
    ]

    for payload in invalid_payloads:
        resp = act("faculty").post(f"{API}/announcements", payload, format="json")
        assert resp.status_code in (400, 422), (payload, resp.status_code, resp.content)

    assert Announcement.objects.count() == 0


def test_tc_dept_br_007_permitted_hod(world, act):
    """TC-DEPT-BR-007 | BR-DEPT-004 permitted-hod"""
    edit_id = _publish(act, "faculty", title="To Edit", body="Original").json()["id"]
    hide_id = _publish(act, "faculty", title="To Hide", body="Active").json()["id"]
    del_id = _publish(act, "faculty", title="To Delete", body="Active").json()["id"]

    edit_resp = act("hod").patch(
        f"{API}/announcements/{edit_id}",
        {"title": "Edited by HOD", "body": "Updated content"},
        format="json",
    )
    assert edit_resp.status_code == 200, edit_resp.content
    edited = Announcement.objects.get(pk=edit_id)
    assert edited.title == "Edited by HOD"
    assert edited.body == "Updated content"

    hide_resp = act("hod").post(f"{API}/announcements/{hide_id}/hide")
    assert hide_resp.status_code == 200, hide_resp.content
    assert Announcement.objects.get(pk=hide_id).status == Announcement.HIDDEN

    del_resp = act("hod").delete(f"{API}/announcements/{del_id}")
    assert del_resp.status_code == 204, del_resp.content
    assert Announcement.objects.get(pk=del_id).status == Announcement.DELETED

    student_visible = {a["id"] for a in act("student").get(f"{API}/announcements").json()["results"]}
    assert edit_id in student_visible
    assert hide_id not in student_visible
    assert del_id not in student_visible


def test_tc_dept_br_008_prohibited_non_hod(world, act):
    """TC-DEPT-BR-008 | BR-DEPT-004 prohibited-non-hod"""
    created = _publish(act, "faculty", title="Protected Notice", body="Original body")
    assert created.status_code == 201
    ann_id = created.json()["id"]

    for role in ("faculty", "admin", "student"):
        assert (
            act(role)
            .patch(f"{API}/announcements/{ann_id}", {"title": f"Changed by {role}"}, format="json")
            .status_code
            == 403
        )
        assert act(role).post(f"{API}/announcements/{ann_id}/hide").status_code == 403
        assert act(role).delete(f"{API}/announcements/{ann_id}").status_code == 403

    ann = Announcement.objects.get(pk=ann_id)
    assert ann.status == Announcement.ACTIVE
    assert ann.title == "Protected Notice"
    assert ann.body == "Original body"
