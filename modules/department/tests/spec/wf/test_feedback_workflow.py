"""Workflow spec tests: Confidential Feedback Lifecycle (TC-WF-07..TC-WF-12)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from modules.department.models import DepartmentNotification, Feedback
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _submit(act, role: str, subject: str = "Lab issue", body: str = "Details of the issue."):
    return act(role).post(
        f"{API}/feedback",
        {"subject": subject, "body": body},
        format="json",
    )


def test_tc_wf_07_feedback_dept_admin_closed_path(world, act):
    """TC-WF-07 | BW-DEPT-03 dept-admin-closed path (CW-DEPT-02 steps 1-2-3A)"""
    assert Feedback.objects.count() == 0

    # 1. Student submits confidential feedback (UC-DEPT-007).
    submit_resp = _submit(act, role="student", subject="Whiteboard markers", body="Empty markers.")
    assert submit_resp.status_code == 201, submit_resp.content
    fb_id = submit_resp.json()["id"]
    assert Feedback.objects.get(pk=fb_id).status == "new"
    assert (
        DepartmentNotification.objects.filter(
            topic="feedback.created", recipient_user_id=uid("admin")
        ).count()
        == 1
    )

    # 2. Dept_Admin performs initial review and categorizes the feedback (UC-DEPT-008).
    review_resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "facilities"},
        format="json",
    )
    assert review_resp.status_code == 200, review_resp.content
    assert review_resp.json()["status"] == "under_review"
    assert Feedback.objects.get(pk=fb_id).status == "under_review"

    # 3. Dept_Admin selects terminal outcome Closed (UC-DEPT-008).
    close_resp = act("admin").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "closed", "note": "Restocked markers."},
        format="json",
    )
    assert close_resp.status_code == 200, close_resp.content
    assert close_resp.json()["status"] == "closed"
    assert Feedback.objects.get(pk=fb_id).status == "closed"

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    )
    assert notifs.count() == 1
    assert "closed" in notifs.first().subject.lower()


def test_tc_wf_08_feedback_dept_admin_resolved_path(world, act):
    """TC-WF-08 | BW-DEPT-03 dept-admin-resolved path (CW-DEPT-02 steps 1-2-3A)"""
    assert Feedback.objects.count() == 0

    # 1. Faculty submits confidential feedback (UC-DEPT-007).
    submit_resp = _submit(act, role="faculty", subject="Projector cable", body="HDMI cable loose.")
    assert submit_resp.status_code == 201, submit_resp.content
    fb_id = submit_resp.json()["id"]
    assert Feedback.objects.get(pk=fb_id).status == "new"
    assert (
        DepartmentNotification.objects.filter(
            topic="feedback.created", recipient_user_id=uid("admin")
        ).count()
        == 1
    )

    # 2. Dept_Admin performs initial review and categorizes the feedback (UC-DEPT-008).
    review_resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "facilities"},
        format="json",
    )
    assert review_resp.status_code == 200, review_resp.content
    assert review_resp.json()["status"] == "under_review"
    assert Feedback.objects.get(pk=fb_id).status == "under_review"

    # 3. Dept_Admin selects terminal outcome Resolved (UC-DEPT-008).
    resolve_resp = act("admin").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "resolved", "note": "Replaced HDMI cable."},
        format="json",
    )
    assert resolve_resp.status_code == 200, resolve_resp.content
    assert resolve_resp.json()["status"] == "resolved"
    assert Feedback.objects.get(pk=fb_id).status == "resolved"

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("faculty")
    )
    assert notifs.count() == 1
    assert "resolved" in notifs.first().subject.lower()


def test_tc_wf_09_feedback_hod_oversight_resolved_path(world, act):
    """TC-WF-09 | BW-DEPT-04 hod-oversight-resolved path (CW-DEPT-02 steps 1-2-3B)"""
    assert Feedback.objects.count() == 0

    # 1. Student submits confidential feedback (UC-DEPT-007).
    submit_resp = _submit(act, role="student", subject="Lab schedule", body="Overlap with seminar.")
    assert submit_resp.status_code == 201, submit_resp.content
    fb_id = submit_resp.json()["id"]
    assert Feedback.objects.get(pk=fb_id).status == "new"
    assert (
        DepartmentNotification.objects.filter(
            topic="feedback.created", recipient_user_id=uid("admin")
        ).count()
        == 1
    )

    # 2. Dept_Admin performs initial review and categorizes without closing (UC-DEPT-008).
    review_resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "academic"},
        format="json",
    )
    assert review_resp.status_code == 200, review_resp.content
    assert review_resp.json()["status"] == "under_review"
    assert Feedback.objects.get(pk=fb_id).status == "under_review"

    # 3. HOD accesses the reviewed feedback for oversight and marks it Resolved (UC-DEPT-014).
    hod_detail = act("hod").get(f"{API}/feedback/{fb_id}")
    assert hod_detail.status_code == 200
    assert hod_detail.json()["id"] == fb_id

    resolve_resp = act("hod").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "resolved", "note": "Adjusted seminar slot."},
        format="json",
    )
    assert resolve_resp.status_code == 200, resolve_resp.content
    assert resolve_resp.json()["status"] == "resolved"
    assert Feedback.objects.get(pk=fb_id).status == "resolved"

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    )
    assert notifs.count() == 1
    assert "resolved" in notifs.first().subject.lower()


def test_tc_wf_10_feedback_hod_oversight_closed_path(world, act):
    """TC-WF-10 | BW-DEPT-04 hod-oversight-closed path (CW-DEPT-02 steps 1-2-3B)"""
    assert Feedback.objects.count() == 0

    # 1. Faculty submits confidential feedback (UC-DEPT-007).
    submit_resp = _submit(act, role="faculty", subject="Lab software", body="License renewal.")
    assert submit_resp.status_code == 201, submit_resp.content
    fb_id = submit_resp.json()["id"]
    assert Feedback.objects.get(pk=fb_id).status == "new"
    assert (
        DepartmentNotification.objects.filter(
            topic="feedback.created", recipient_user_id=uid("admin")
        ).count()
        == 1
    )

    # 2. Dept_Admin performs initial review and categorizes without closing (UC-DEPT-008).
    review_resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "infrastructure"},
        format="json",
    )
    assert review_resp.status_code == 200, review_resp.content
    assert review_resp.json()["status"] == "under_review"
    assert Feedback.objects.get(pk=fb_id).status == "under_review"

    # 3. HOD accesses the reviewed feedback for oversight and marks it Closed (UC-DEPT-014).
    hod_detail = act("hod").get(f"{API}/feedback/{fb_id}")
    assert hod_detail.status_code == 200
    assert hod_detail.json()["id"] == fb_id

    close_resp = act("hod").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "closed", "note": "Covered under institute license."},
        format="json",
    )
    assert close_resp.status_code == 200, close_resp.content
    assert close_resp.json()["status"] == "closed"
    assert Feedback.objects.get(pk=fb_id).status == "closed"

    notifs = DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("faculty")
    )
    assert notifs.count() == 1
    assert "closed" in notifs.first().subject.lower()


def test_tc_wf_11_feedback_unauthenticated_submitter_guard(world):
    """TC-WF-11 | CW-DEPT-02 step 1 ineligible-submitter guard (BR-DEPT-008)"""
    anon_client = APIClient()
    resp = anon_client.post(
        f"{API}/feedback",
        {"subject": "Anonymous", "body": "Should be rejected."},
        format="json",
    )
    assert resp.status_code == 401
    assert Feedback.objects.count() == 0
    assert not DepartmentNotification.objects.filter(
        topic="feedback.created", recipient_user_id=uid("admin")
    ).exists()


def test_tc_wf_12_feedback_premature_hod_oversight_guard(world, act):
    """TC-WF-12 | CW-DEPT-02 step 3B premature-hod-oversight guard (BR-DEPT-018)"""
    fb_id = _submit(act, role="student", subject="Unreviewed", body="Awaiting review.").json()["id"]
    assert Feedback.objects.get(pk=fb_id).status == "new"

    # HOD attempts to access, resolve, and close the New feedback directly (UC-DEPT-014).
    access_resp = act("hod").get(f"{API}/feedback/{fb_id}")
    assert access_resp.status_code in (403, 404)

    resolve_resp = act("hod").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "resolved", "note": "Premature resolve"},
        format="json",
    )
    assert resolve_resp.status_code in (403, 404, 409)

    close_resp = act("hod").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "closed", "note": "Premature close"},
        format="json",
    )
    assert close_resp.status_code in (403, 404, 409)

    assert Feedback.objects.get(pk=fb_id).status == "new"
    assert not DepartmentNotification.objects.filter(
        topic="feedback.disposed", recipient_user_id=uid("student")
    ).exists()
