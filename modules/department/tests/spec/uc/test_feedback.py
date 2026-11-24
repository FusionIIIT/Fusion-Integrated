"""Use Case spec tests: Feedback (TC-DEPT-013..TC-DEPT-017, TC-DEPT-027..TC-DEPT-028)."""

from __future__ import annotations

import pytest
from django.db import DatabaseError
from rest_framework.test import APIClient

from modules.department.models import DepartmentNotification, Feedback
from modules.department.services import notifications as notification_service
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _submit(act, role: str = "student", subject: str = "Lab issue", body: str = "Projector broken."):
    return act(role).post(
        f"{API}/feedback",
        {"subject": subject, "body": body},
        format="json",
    )


def _assert_confidential(act, fb_id: int) -> None:
    for unauthorized in ("student2", "faculty"):
        list_resp = act(unauthorized).get(f"{API}/feedback")
        assert list_resp.status_code == 200
        assert fb_id not in {item["id"] for item in list_resp.json()["results"]}
        assert act(unauthorized).get(f"{API}/feedback/{fb_id}").status_code == 404


def test_tc_dept_013_submit_confidential_feedback_and_notify_dept_admin(world, act):
    """TC-DEPT-013 | UC-DEPT-007 Main Success Scenario"""
    resp = _submit(act, role="student", subject="Lab Wi-Fi", body="Signal drops during labs.")
    assert resp.status_code == 201, resp.content
    fb_id = resp.json()["id"]

    fb = Feedback.objects.get(pk=fb_id)
    assert fb.status == "new"
    assert fb.submitter_id == uid("student")

    _assert_confidential(act, fb_id)
    assert act("hod").get(f"{API}/feedback/{fb_id}").status_code == 404

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.created", recipient_user_id=uid("admin")
    )
    assert notifs.count() == 1
    assert str(fb_id) in notifs.first().subject


def test_tc_dept_014_feedback_submission_failure_leaves_no_partial_record(world, act, monkeypatch):
    """TC-DEPT-014 | UC-DEPT-007 Exception Flow: Submission fails"""
    # 1. Incomplete submission fails before persistence.
    invalid_resp = _submit(act, role="student", subject="   ", body="")
    assert invalid_resp.status_code == 422
    assert invalid_resp.json()["error"]["code"] == "feedback_incomplete"
    assert Feedback.objects.count() == 0
    assert DepartmentNotification.objects.count() == 0

    # 2. Mid-transaction persistence failure rolls back atomically so no partial Feedback is saved.
    def _fail_enqueue(*args, **kwargs):
        raise DatabaseError("Simulated persistence failure")

    monkeypatch.setattr(notification_service, "enqueue", _fail_enqueue)
    act("student")  # prime IAM stub for student
    client = APIClient(raise_request_exception=False)
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    failed_resp = client.post(
        f"{API}/feedback",
        {"subject": "Transient failure", "body": "Should roll back cleanly."},
        format="json",
    )
    assert failed_resp.status_code == 500
    assert Feedback.objects.count() == 0
    assert DepartmentNotification.objects.count() == 0


def test_tc_dept_015_dept_admin_initial_review_categorize_and_resolve(world, act):
    """TC-DEPT-015 | UC-DEPT-008 Main Success Scenario"""
    fb_id = _submit(act, role="student", subject="Projector", body="Lamp burnt out.").json()["id"]

    resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "facilities", "disposition": "resolved", "note": "Lamp replaced."},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert data["category"] == "facilities"
    assert data["status"] == "resolved"
    assert data["reviewed_at"] is not None

    fb = Feedback.objects.get(pk=fb_id)
    assert fb.reviewed_by == uid("admin")
    assert fb.reviewed_at is not None
    assert fb.category == "facilities"
    assert fb.status == "resolved"

    _assert_confidential(act, fb_id)

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    )
    assert notifs.count() == 1
    assert "resolved" in notifs.first().subject.lower()


def test_tc_dept_016_dept_admin_close_simple_issue_during_initial_review(world, act):
    """TC-DEPT-016 | UC-DEPT-008 Alternative Flow: Simple issue closed during initial review"""
    fb_id = _submit(act, role="student", subject="Chalk", body="Need chalk in L-102.").json()["id"]

    resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "facilities", "disposition": "closed", "note": "Chalk restocked."},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == "closed"

    fb = Feedback.objects.get(pk=fb_id)
    assert fb.reviewed_by == uid("admin")
    assert fb.reviewed_at is not None
    assert fb.status == "closed"

    _assert_confidential(act, fb_id)

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    )
    assert notifs.count() == 1
    assert "closed" in notifs.first().subject.lower()


def test_tc_dept_017_dept_admin_initial_review_leaves_feedback_non_terminal(world, act):
    """TC-DEPT-017 | UC-DEPT-008 Alternative Flow: Feedback remains non-terminal after initial review"""
    fb_id = _submit(act, role="student", subject="Syllabus", body="Clarify grading rubric.").json()["id"]

    resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "academic"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == "under_review"
    assert resp.json()["category"] == "academic"

    fb = Feedback.objects.get(pk=fb_id)
    assert fb.reviewed_by == uid("admin")
    assert fb.reviewed_at is not None
    assert fb.status == "under_review"
    assert fb.category == "academic"

    # Now accessible for HOD oversight under UC-DEPT-014.
    hod_detail = act("hod").get(f"{API}/feedback/{fb_id}")
    assert hod_detail.status_code == 200
    assert hod_detail.json()["id"] == fb_id

    # No terminal resolution/closure notification sent to submitter.
    assert not DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    ).exists()


def test_tc_dept_027_hod_oversee_and_resolve_reviewed_feedback(world, act):
    """TC-DEPT-027 | UC-DEPT-014 Main Success Scenario"""
    fb_id = _submit(act, role="student", subject="Lab AC", body="AC not cooling.").json()["id"]
    assert (
        act("admin")
        .post(f"{API}/feedback/{fb_id}/review", {"category": "infrastructure"}, format="json")
        .status_code
        == 200
    )

    detail = act("hod").get(f"{API}/feedback/{fb_id}")
    assert detail.status_code == 200

    resolve = act("hod").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "resolved", "note": "Serviced by maintenance."},
        format="json",
    )
    assert resolve.status_code == 200, resolve.content
    assert resolve.json()["status"] == "resolved"

    fb = Feedback.objects.get(pk=fb_id)
    assert fb.status == "resolved"
    assert fb.disposed_by == uid("hod")
    assert fb.disposed_at is not None

    _assert_confidential(act, fb_id)

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    )
    assert notifs.count() == 1
    assert "resolved" in notifs.first().subject.lower()


def test_tc_dept_028_hod_reviews_feedback_without_changing_terminal_status(world, act):
    """TC-DEPT-028 | UC-DEPT-014 Alternative Flow: HOD reviews without changing terminal status"""
    fb_id = _submit(act, role="student", subject="Timetable", body="Lab clash.").json()["id"]
    assert (
        act("admin")
        .post(f"{API}/feedback/{fb_id}/review", {"category": "academic"}, format="json")
        .status_code
        == 200
    )

    detail = act("hod").get(f"{API}/feedback/{fb_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "under_review"

    note_resp = act("hod").post(
        f"{API}/feedback/{fb_id}/notes",
        {"body": "Discussing with timetable coordinator."},
        format="json",
    )
    assert note_resp.status_code == 201

    fb = Feedback.objects.get(pk=fb_id)
    assert fb.status == "under_review"
    assert fb.disposed_at is None

    _assert_confidential(act, fb_id)
    assert not DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    ).exists()
