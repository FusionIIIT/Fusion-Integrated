"""Use Case spec tests: Announcements (TC-DEPT-001..TC-DEPT-007)."""

from __future__ import annotations

import pytest

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


def test_tc_dept_001_view_relevant_active_announcements(world, act):
    """TC-DEPT-001 | UC-DEPT-001 Main Success Scenario"""
    matching = _publish(
        act,
        "hod",
        title="CSE B.Tech 2024 Lab Schedule",
        audience_role="student",
        programme="B.Tech",
        batch_year=2024,
    )
    wrong_role = _publish(
        act, "hod", title="Faculty Meeting", audience_role="faculty", programme="", batch_year=None
    )
    wrong_program = _publish(
        act, "hod", title="M.Tech Seminar", audience_role="student", programme="M.Tech", batch_year=2024
    )
    wrong_year = _publish(
        act, "hod", title="2023 Batch Notice", audience_role="student", programme="B.Tech", batch_year=2023
    )
    other_dept = _publish(
        act, "ece_hod", title="ECE Notice", audience_role="student", programme="B.Tech", batch_year=2024
    )
    hidden = _publish(
        act,
        "hod",
        title="Hidden CSE Notice",
        audience_role="student",
        programme="B.Tech",
        batch_year=2024,
    )
    for resp in (matching, wrong_role, wrong_program, wrong_year, other_dept, hidden):
        assert resp.status_code == 201, resp.content

    hidden_id = hidden.json()["id"]
    assert act("hod").post(f"{API}/announcements/{hidden_id}/hide").status_code == 200

    before_states = dict(Announcement.objects.values_list("id", "status"))

    resp = act("student").get(f"{API}/announcements")
    assert resp.status_code == 200
    returned_ids = {item["id"] for item in resp.json()["results"]}

    assert returned_ids == {matching.json()["id"]}
    assert wrong_role.json()["id"] not in returned_ids
    assert wrong_program.json()["id"] not in returned_ids
    assert wrong_year.json()["id"] not in returned_ids
    assert other_dept.json()["id"] not in returned_ids
    assert hidden_id not in returned_ids
    assert dict(Announcement.objects.values_list("id", "status")) == before_states


def test_tc_dept_002_no_relevant_active_announcement_empty_state(world, act):
    """TC-DEPT-002 | UC-DEPT-001 Alternative Flow: No relevant active announcement exists"""
    faculty_only = _publish(
        act, "hod", title="Faculty Only", audience_role="faculty", programme="", batch_year=None
    )
    wrong_year = _publish(
        act, "hod", title="2023 Notice", audience_role="student", programme="B.Tech", batch_year=2023
    )
    hidden = _publish(
        act, "hod", title="Hidden Notice", audience_role="student", programme="B.Tech", batch_year=2024
    )
    assert faculty_only.status_code == 201
    assert wrong_year.status_code == 201
    assert hidden.status_code == 201
    assert act("hod").post(f"{API}/announcements/{hidden.json()['id']}/hide").status_code == 200

    before_states = dict(Announcement.objects.values_list("id", "status"))

    resp = act("student").get(f"{API}/announcements")
    assert resp.status_code == 200
    assert resp.json()["results"] == []
    assert dict(Announcement.objects.values_list("id", "status")) == before_states


def test_tc_dept_003_publish_announcement_and_notify_target_audience(world, act):
    """TC-DEPT-003 | UC-DEPT-002 Main Success Scenario"""
    for role in ("faculty", "admin", "hod"):
        resp = _publish(
            act,
            role,
            title=f"Notice from {role}",
            body="Mandatory briefing in L-104.",
            audience_role="all",
            programme="B.Tech",
            batch_year=2024,
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body["status"] == "active"

        ann = Announcement.objects.get(pk=body["id"])
        assert ann.status == Announcement.ACTIVE
        assert ann.audience_role == "all"
        assert ann.programme == "B.Tech"
        assert ann.batch_year == 2024

        notified = set(
            DepartmentNotification.objects.filter(
                topic="announcement.published",
                dedupe_key__startswith=f"announcement.published:{ann.pk}:",
            ).values_list("recipient_user_id", flat=True)
        )
        assert uid("student") in notified
        assert uid("faculty") in notified
        assert uid("faculty2") in notified
        assert uid("student2") not in notified
        assert uid("ece_student") not in notified
        assert uid("ece_faculty") not in notified


def test_tc_dept_004_block_announcement_with_invalid_or_missing_fields(world, act):
    """TC-DEPT-004 | UC-DEPT-002 Alternative Flow: Required content or target information is invalid/missing"""
    missing_content = _publish(act, "faculty", title="   ", body="")
    assert missing_content.status_code == 422
    assert missing_content.json()["error"]["code"] == "announcement_incomplete"
    assert missing_content.json()["error"]["details"]

    invalid_role = _publish(act, "admin", audience_role="outsider")
    assert invalid_role.status_code == 422
    assert invalid_role.json()["error"]["code"] == "announcement_incomplete"

    invalid_year = _publish(act, "hod", batch_year=1800)
    assert invalid_year.status_code in (400, 422)
    assert "error" in invalid_year.json()

    assert Announcement.objects.count() == 0
    assert DepartmentNotification.objects.count() == 0


def test_tc_dept_005_hod_edit_active_announcement(world, act):
    """TC-DEPT-005 | UC-DEPT-003 Main Success Scenario / Alternative Flow: Edit"""
    created = _publish(
        act,
        "faculty",
        title="Initial Title",
        body="Initial Body",
        audience_role="student",
        programme="B.Tech",
        batch_year=2024,
    )
    assert created.status_code == 201
    ann_id = created.json()["id"]

    resp = act("hod").patch(
        f"{API}/announcements/{ann_id}",
        {
            "title": "Revised Title",
            "body": "Revised Body",
            "audience_role": "all",
            "programme": "B.Tech",
            "batch_year": 2023,
        },
        format="json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["title"] == "Revised Title"
    assert data["body"] == "Revised Body"
    assert data["audience_role"] == "all"
    assert data["batch_year"] == 2023

    ann = Announcement.objects.get(pk=ann_id)
    assert ann.title == "Revised Title"
    assert ann.body == "Revised Body"
    assert ann.audience_role == "all"
    assert ann.batch_year == 2023
    assert ann.edited_by == uid("hod")
    assert ann.edited_at is not None


def test_tc_dept_006_hod_hide_active_announcement(world, act):
    """TC-DEPT-006 | UC-DEPT-003 Alternative Flow: Hide"""
    created = _publish(act, "faculty", title="Visible Announcement")
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


def test_tc_dept_007_hod_delete_active_announcement(world, act):
    """TC-DEPT-007 | UC-DEPT-003 Alternative Flow: Delete"""
    created = _publish(act, "faculty", title="Announcement To Delete")
    assert created.status_code == 201
    ann_id = created.json()["id"]

    resp = act("hod").delete(f"{API}/announcements/{ann_id}")
    assert resp.status_code == 204
    assert Announcement.objects.get(pk=ann_id).status == Announcement.DELETED

    for role in ("student", "faculty", "hod"):
        visible_ids = {a["id"] for a in act(role).get(f"{API}/announcements").json()["results"]}
        assert ann_id not in visible_ids
