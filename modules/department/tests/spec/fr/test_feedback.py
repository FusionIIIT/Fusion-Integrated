"""Functional Requirement spec tests: Feedback (TC-DEPT-038..TC-DEPT-051)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from modules.department.models import DepartmentNotification, Feedback
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _submit(act, role: str = "student", subject: str = "Lab issue", body: str = "Projector broken."):
    return act(role).post(
        f"{API}/feedback",
        {"subject": subject, "body": body},
        format="json",
    )


def test_tc_dept_038_authenticated_student_and_faculty_feedback_submission(world, act):
    """TC-DEPT-038 | AFR-DEPT-017 authenticated Student and Faculty feedback submission"""
    student_resp = _submit(act, role="student", subject="Student feedback", body="Needs better Wi-Fi.")
    faculty_resp = _submit(act, role="faculty", subject="Faculty feedback", body="Whiteboard markers.")
    assert student_resp.status_code == 201, student_resp.content
    assert faculty_resp.status_code == 201, faculty_resp.content
    assert Feedback.objects.filter(pk=student_resp.json()["id"], submitter_id=uid("student")).exists()
    assert Feedback.objects.filter(pk=faculty_resp.json()["id"], submitter_id=uid("faculty")).exists()


def test_tc_dept_039_unauthenticated_feedback_submission_denial(world, act):
    """TC-DEPT-039 | AFR-DEPT-017 unauthenticated feedback submission denial"""
    anon = APIClient()
    resp = anon.post(
        f"{API}/feedback",
        {"subject": "Anonymous", "body": "Should be rejected."},
        format="json",
    )
    assert resp.status_code == 401
    assert Feedback.objects.count() == 0


def test_tc_dept_040_confidentiality_enforcement_against_unauthorized_viewers(world, act):
    """TC-DEPT-040 | AFR-DEPT-018 confidentiality enforcement against unauthorized viewers"""
    created = _submit(act, role="student", subject="Confidential concern", body="Private details.")
    assert created.status_code == 201
    fb_id = created.json()["id"]

    for role in ("student2", "faculty"):
        list_resp = act(role).get(f"{API}/feedback")
        assert list_resp.status_code == 200
        returned_ids = {f["id"] for f in list_resp.json()["results"]}
        assert fb_id not in returned_ids

        detail_resp = act(role).get(f"{API}/feedback/{fb_id}")
        assert detail_resp.status_code == 404


def test_tc_dept_041_dept_admin_notification_on_new_feedback(world, act):
    """TC-DEPT-041 | AFR-DEPT-044 Dept_Admin notification on new feedback"""
    created = _submit(act, role="student")
    assert created.status_code == 201
    fb_id = created.json()["id"]

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.created", recipient_user_id=uid("admin")
    )
    assert notifs.count() == 1
    assert str(fb_id) in notifs.first().subject


def test_tc_dept_042_dept_admin_initial_review(world, act):
    """TC-DEPT-042 | AFR-DEPT-019 Dept_Admin initial review"""
    fb_id = _submit(act, role="student").json()["id"]

    resp = act("admin").post(f"{API}/feedback/{fb_id}/review", {}, format="json")
    assert resp.status_code == 200, resp.content
    assert resp.json()["status"] == "under_review"
    fb = Feedback.objects.get(pk=fb_id)
    assert fb.status == "under_review"
    assert fb.reviewed_by == uid("admin")
    assert fb.reviewed_at is not None


def test_tc_dept_043_non_dept_admin_initial_review_denial(world, act):
    """TC-DEPT-043 | AFR-DEPT-019 non-Dept_Admin initial review denial"""
    fb_id = _submit(act, role="student").json()["id"]

    for role in ("student", "faculty", "hod"):
        resp = act(role).post(f"{API}/feedback/{fb_id}/review", {}, format="json")
        assert resp.status_code == 403

    fb = Feedback.objects.get(pk=fb_id)
    assert fb.status == "new"
    assert fb.reviewed_at is None


def test_tc_dept_044_dept_admin_feedback_categorization(world, act):
    """TC-DEPT-044 | AFR-DEPT-020 Dept_Admin feedback categorization"""
    fb_id = _submit(act, role="student").json()["id"]

    resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "facilities"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["category"] == "facilities"
    assert Feedback.objects.get(pk=fb_id).category == "facilities"


def test_tc_dept_045_dept_admin_close_simple_feedback_during_initial_review(world, act):
    """TC-DEPT-045 | AFR-DEPT-021 Dept_Admin close simple feedback during initial review"""
    fb_id = _submit(act, role="student", subject="Chalk out", body="Room L-101 needs chalk.").json()["id"]

    resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "facilities", "disposition": "closed", "note": "Restocked immediately."},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
    assert Feedback.objects.get(pk=fb_id).status == "closed"


def test_tc_dept_046_dept_admin_and_hod_terminal_resolution_or_closure(world, act):
    """TC-DEPT-046 | AFR-DEPT-022 Dept_Admin and HOD terminal resolution or closure"""
    cases = [
        ("admin", "resolved"),
        ("admin", "closed"),
        ("hod", "resolved"),
        ("hod", "closed"),
    ]
    for actor, outcome in cases:
        fb_id = _submit(act, role="student", subject=f"{actor}-{outcome}").json()["id"]
        assert (
            act("admin")
            .post(f"{API}/feedback/{fb_id}/review", {"category": "academic"}, format="json")
            .status_code
            == 200
        )
        resp = act(actor).post(
            f"{API}/feedback/{fb_id}/dispose",
            {"outcome": outcome, "note": f"Marked {outcome} by {actor}"},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        assert resp.json()["status"] == outcome
        assert Feedback.objects.get(pk=fb_id).status == outcome


def test_tc_dept_047_unauthorized_user_resolution_denial(world, act):
    """TC-DEPT-047 | AFR-DEPT-022 unauthorized user resolution denial"""
    fb_id = _submit(act, role="student").json()["id"]
    assert (
        act("admin")
        .post(f"{API}/feedback/{fb_id}/review", {"category": "other"}, format="json")
        .status_code
        == 200
    )

    for role in ("student", "faculty"):
        for outcome in ("resolved", "closed"):
            resp = act(role).post(
                f"{API}/feedback/{fb_id}/dispose",
                {"outcome": outcome},
                format="json",
            )
            assert resp.status_code == 403

    assert Feedback.objects.get(pk=fb_id).status == "under_review"


def test_tc_dept_048_hod_access_after_initial_review(world, act):
    """TC-DEPT-048 | AFR-DEPT-023 HOD access after initial review"""
    fb_id = _submit(act, role="student", subject="Lab AC", body="AC not cooling.").json()["id"]
    assert (
        act("admin")
        .post(f"{API}/feedback/{fb_id}/review", {"category": "infrastructure"}, format="json")
        .status_code
        == 200
    )

    detail = act("hod").get(f"{API}/feedback/{fb_id}")
    assert detail.status_code == 200
    assert detail.json()["subject"] == "Lab AC"

    resolve = act("hod").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "resolved", "note": "Serviced by IWD."},
        format="json",
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "resolved"


def test_tc_dept_049_hod_access_before_initial_review_restricted(world, act):
    """TC-DEPT-049 | AFR-DEPT-023 HOD access before initial review restricted"""
    fb_id = _submit(act, role="student", subject="Unreviewed", body="Still new.").json()["id"]

    list_resp = act("hod").get(f"{API}/feedback")
    assert list_resp.status_code == 200
    assert fb_id not in {f["id"] for f in list_resp.json()["results"]}

    assert act("hod").get(f"{API}/feedback/{fb_id}").status_code == 404
    assert (
        act("hod")
        .post(f"{API}/feedback/{fb_id}/dispose", {"outcome": "resolved"}, format="json")
        .status_code
        == 404
    )
    assert Feedback.objects.get(pk=fb_id).status == "new"


def test_tc_dept_050_submitter_notification_on_resolved(world, act):
    """TC-DEPT-050 | AFR-DEPT-045 submitter notification on Resolved"""
    fb_id = _submit(act, role="student").json()["id"]
    assert (
        act("admin")
        .post(f"{API}/feedback/{fb_id}/review", {"category": "facilities"}, format="json")
        .status_code
        == 200
    )
    assert (
        act("hod")
        .post(f"{API}/feedback/{fb_id}/dispose", {"outcome": "resolved", "note": "Fixed"}, format="json")
        .status_code
        == 200
    )

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    )
    assert notifs.count() == 1
    assert "resolved" in notifs.first().subject.lower()


def test_tc_dept_051_submitter_notification_on_closed(world, act):
    """TC-DEPT-051 | AFR-DEPT-045 submitter notification on Closed"""
    fb_id = _submit(act, role="student").json()["id"]
    assert (
        act("admin")
        .post(
            f"{API}/feedback/{fb_id}/review",
            {"category": "facilities", "disposition": "closed", "note": "Closed"},
            format="json",
        )
        .status_code
        == 200
    )

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    )
    assert notifs.count() == 1
    assert "closed" in notifs.first().subject.lower()
