"""Business Rule spec tests: Feedback (TC-DEPT-BR-016..019, TC-DEPT-BR-032..035)."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from modules.department.models import Feedback
from modules.department.tests.conftest import uid

pytestmark = pytest.mark.django_db
API = "/api/v1/department"


def _submit(act, role: str = "student", subject: str = "Lab issue", body: str = "Projector broken."):
    return act(role).post(
        f"{API}/feedback",
        {"subject": subject, "body": body},
        format="json",
    )


def test_tc_dept_br_016_permitted_student_and_faculty(world, act):
    """TC-DEPT-BR-016 | BR-DEPT-008 permitted-student-and-faculty"""
    stu_resp = _submit(act, role="student", subject="Student concern", body="Wi-Fi drops in lab.")
    fac_resp = _submit(act, role="faculty", subject="Faculty concern", body="Need whiteboard pens.")
    assert stu_resp.status_code == 201, stu_resp.content
    assert fac_resp.status_code == 201, fac_resp.content

    assert Feedback.objects.filter(pk=stu_resp.json()["id"], submitter_id=uid("student")).exists()
    assert Feedback.objects.filter(pk=fac_resp.json()["id"], submitter_id=uid("faculty")).exists()


def test_tc_dept_br_017_prohibited_unauthorized_or_unauthenticated(world, act):
    """TC-DEPT-BR-017 | BR-DEPT-008 prohibited-unauthorized-or-unauthenticated"""
    anon = APIClient()
    anon_resp = anon.post(
        f"{API}/feedback",
        {"subject": "Unauthenticated", "body": "Should fail."},
        format="json",
    )
    assert anon_resp.status_code == 401

    for role in ("admin", "hod"):
        resp = _submit(act, role=role, subject=f"From {role}", body="Not eligible.")
        assert resp.status_code == 403

    assert Feedback.objects.count() == 0


def test_tc_dept_br_018_permitted_dept_admin_and_hod(world, act):
    """TC-DEPT-BR-018 | BR-DEPT-009 permitted-dept-admin-and-hod"""
    simple_id = _submit(act, role="student", subject="Simple issue", body="Need chalk.").json()["id"]
    escalated_id = _submit(act, role="student", subject="Complex issue", body="AC broken.").json()[
        "id"
    ]

    # Dept_Admin closes simple issue during initial review.
    admin_close = act("admin").post(
        f"{API}/feedback/{simple_id}/review",
        {"category": "facilities", "disposition": "closed", "note": "Restocked."},
        format="json",
    )
    assert admin_close.status_code == 200, admin_close.content
    assert admin_close.json()["status"] == "closed"
    assert Feedback.objects.get(pk=simple_id).status == "closed"

    # Dept_Admin completes initial review, then HOD resolves the feedback.
    assert (
        act("admin")
        .post(f"{API}/feedback/{escalated_id}/review", {"category": "infrastructure"}, format="json")
        .status_code
        == 200
    )
    hod_resolve = act("hod").post(
        f"{API}/feedback/{escalated_id}/dispose",
        {"outcome": "resolved", "note": "Repaired by maintenance."},
        format="json",
    )
    assert hod_resolve.status_code == 200, hod_resolve.content
    assert hod_resolve.json()["status"] == "resolved"
    assert Feedback.objects.get(pk=escalated_id).status == "resolved"


def test_tc_dept_br_019_prohibited_other_roles(world, act):
    """TC-DEPT-BR-019 | BR-DEPT-009 prohibited-other-roles"""
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


def test_tc_dept_br_032_permitted_confidential_access(world, act):
    """TC-DEPT-BR-032 | BR-DEPT-017 permitted-confidential-access"""
    fb_id = _submit(
        act, role="student", subject="Confidential matter", body="Private classroom issue."
    ).json()["id"]
    assert (
        act("admin")
        .post(f"{API}/feedback/{fb_id}/review", {"category": "academic"}, format="json")
        .status_code
        == 200
    )

    for role in ("student", "admin", "hod"):
        resp = act(role).get(f"{API}/feedback/{fb_id}")
        assert resp.status_code == 200, (role, resp.content)
        data = resp.json()
        assert data["subject"] == "Confidential matter"
        assert data["body"] == "Private classroom issue."


def test_tc_dept_br_033_prohibited_unauthorized_exposure(world, act):
    """TC-DEPT-BR-033 | BR-DEPT-017 prohibited-unauthorized-exposure"""
    secret_body = "Unique confidential feedback string 9981"
    fb_id = _submit(act, role="student", subject="Private Concern", body=secret_body).json()["id"]

    for role in ("student2", "faculty"):
        assert act(role).get(f"{API}/feedback/{fb_id}").status_code == 404
        fb_list = act(role).get(f"{API}/feedback")
        assert fb_list.status_code == 200
        assert fb_id not in {item["id"] for item in fb_list.json()["results"]}

        # Feedback content must not appear in general department information views.
        dept_resp = act(role).get(f"{API}/departments/CSE")
        assert dept_resp.status_code == 200
        assert secret_body not in dept_resp.content.decode()

        ann_resp = act(role).get(f"{API}/announcements")
        assert ann_resp.status_code == 200
        assert secret_body not in ann_resp.content.decode()


def test_tc_dept_br_034_dept_admin_initial_review_then_hod_access(world, act):
    """TC-DEPT-BR-034 | BR-DEPT-018 dept-admin-initial-review-then-hod-access"""
    fb_id = _submit(act, role="student", subject="Lab ventilation", body="Exhaust fan noisy.").json()[
        "id"
    ]
    assert Feedback.objects.get(pk=fb_id).status == "new"

    review_resp = act("admin").post(
        f"{API}/feedback/{fb_id}/review",
        {"category": "facilities"},
        format="json",
    )
    assert review_resp.status_code == 200, review_resp.content
    fb = Feedback.objects.get(pk=fb_id)
    assert fb.status == "under_review"
    assert fb.category == "facilities"
    assert fb.reviewed_by == uid("admin")

    hod_view = act("hod").get(f"{API}/feedback/{fb_id}")
    assert hod_view.status_code == 200
    assert hod_view.json()["subject"] == "Lab ventilation"

    hod_resolve = act("hod").post(
        f"{API}/feedback/{fb_id}/dispose",
        {"outcome": "resolved", "note": "Replaced fan."},
        format="json",
    )
    assert hod_resolve.status_code == 200
    assert hod_resolve.json()["status"] == "resolved"


def test_tc_dept_br_035_bypass_initial_review_blocked(world, act):
    """TC-DEPT-BR-035 | BR-DEPT-018 bypass-initial-review-blocked"""
    fb_id = _submit(act, role="student", subject="Unreviewed item", body="Still new.").json()["id"]

    assert fb_id not in {item["id"] for item in act("hod").get(f"{API}/feedback").json()["results"]}
    assert act("hod").get(f"{API}/feedback/{fb_id}").status_code == 404
    assert (
        act("hod")
        .post(f"{API}/feedback/{fb_id}/dispose", {"outcome": "resolved"}, format="json")
        .status_code
        == 404
    )
    assert (
        act("hod")
        .post(f"{API}/feedback/{fb_id}/dispose", {"outcome": "closed"}, format="json")
        .status_code
        == 404
    )
    assert Feedback.objects.get(pk=fb_id).status == "new"
