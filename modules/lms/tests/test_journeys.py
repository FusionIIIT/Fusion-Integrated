from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.lms.models import Assignment, Grade, GradeAuditLog, Material, Submission
from modules.lms.tasks import release_due_assignments, release_due_materials
from modules.lms.tests.conftest import available, draft, submit

pytestmark = pytest.mark.django_db
BASE = "/api/v1/lms"


def test_uc_lms_001_access_and_uc_lms_002_manage_details(world, user_ref):
    # Source obligations: CFR-LMS-001 CFR-LMS-002 AFR-LMS-001.1 AFR-LMS-001.2 AFR-LMS-001.3
    #  AFR-LMS-002.1 AFR-LMS-002.2 BR-LMS-001 BR-LMS-002 UC-LMS-001 UC-LMS-002
    # BR-LMS-001, BR-LMS-002: registration read-only; BR-LMS-004 faculty-only edits.
    response = world.actor().patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Course syllabus", "schedule": "Monday"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["details_published_at"]
    for role in ("student", "lms_ta", "lms_observer"):
        client = world.actor(role)
        world.fake.users = {1: user_ref(1, kind="faculty"), 3: user_ref(3)}
        course = client.get(f"{BASE}/courses/").json()["results"][0]
        assert course["syllabus"] == "Course syllabus" and course["schedule"] == "Monday"
        assert {(staff["user_id"], staff["course_role"]) for staff in course["staff"]} == {
            (1, "FACULTY"),
            (3, "TA"),
        }
        assert client.get(f"{BASE}/courses/{world.other.pk}/").status_code == 404
        assert (
            client.patch(
                f"{BASE}/courses/{world.workspace.pk}/", {"syllabus": "overwrite"}, format="json"
            ).status_code
            == 403
        )
    updated = world.actor().patch(
        f"{BASE}/courses/{world.workspace.pk}/", {"syllabus": "Revised"}, format="json"
    )
    assert updated.status_code == 200 and updated.json()["syllabus"] == "Revised"


def test_uc_lms_003_manage_and_uc_lms_004_read_materials(world):
    # Source obligations: CFR-LMS-003 CFR-LMS-004 AFR-LMS-003.1 AFR-LMS-003.2 AFR-LMS-004.1
    #  AFR-LMS-004.2 AFR-LMS-004.3 BR-LMS-005 UC-LMS-003 UC-LMS-004
    # BR-LMS-003, BR-LMS-005: Observer read-only; unpublished items never exposed.
    staff = world.actor()
    section = staff.post(
        f"{BASE}/courses/{world.workspace.pk}/sections/",
        {"kind": "WEEK", "label": "Week 1"},
        format="json",
    )
    assert section.status_code == 201
    item = staff.post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Notes", "section_id": section.json()["id"]},
        format="json",
    )
    assert item.status_code == 201
    assert item.json()["section_id"] == section.json()["id"]
    pk = item.json()["id"]
    assert world.actor("student").get(f"{BASE}/materials/{pk}/").status_code == 404
    edited = world.actor().patch(
        f"{BASE}/materials/{pk}/", {"text": "Revised notes", "order": 2}, format="json"
    )
    assert edited.status_code == 200 and edited.json()["state"] == "DRAFT"
    assert edited.json()["order"] == 2 and edited.json()["section_id"] == section.json()["id"]
    assert (
        world.actor().post(f"{BASE}/materials/{pk}/publish/", {}, format="json").status_code == 200
    )
    for role in ("student", "lms_ta", "lms_observer"):
        assert world.actor(role).get(f"{BASE}/materials/{pk}/").json()["text"] == "Revised notes"


def test_uc_lms_005_post_uc_lms_006_read_announcement_and_ta_policy(world):
    # Source obligations: CFR-LMS-005 AFR-LMS-005.1 AFR-LMS-005.2 AFR-LMS-005.3 AFR-LMS-005.4
    #  BR-LMS-007 BR-LMS-008 UC-LMS-005 UC-LMS-006
    # BR-LMS-007, BR-LMS-008: timestamped, pulled course-wide; D-02 safe default.
    url = f"{BASE}/courses/{world.workspace.pk}/announcements/"
    assert world.actor("lms_ta").post(url, {"content": "TA post"}, format="json").status_code == 403
    policy_url = f"{BASE}/courses/{world.workspace.pk}/policy-versions/"
    response = world.actor().post(policy_url, {"can_ta_post_announcements": True}, format="json")
    assert response.status_code == 201 and response.json()["version"] == 2
    assert (
        world.actor()
        .get(f"{BASE}/courses/{world.workspace.pk}/policy/")
        .json()["can_ta_post_announcements"]
    )
    for role in ("faculty", "lms_ta"):
        response = world.actor(role).post(
            url, {"content": f"Announcement {role}", "author_user_id": 99}, format="json"
        )
        assert response.status_code == 201 and response.json()["created_at"]
        assert response.json()["author_user_id"] != 99
    for role in ("student", "faculty", "lms_ta", "lms_observer"):
        assert len(world.actor(role).get(url).json()["results"]) == 2
    assert (
        world.actor()
        .post(policy_url, {"can_ta_post_announcements": False}, format="json")
        .status_code
        == 201
    )
    assert world.actor("lms_ta").post(url, {"content": "Denied"}, format="json").status_code == 403


def test_uc_lms_007_draft_uc_lms_008_publish_uc_lms_009_read_download(world):
    # Source obligations: CFR-LMS-006 CFR-LMS-007 AFR-LMS-006.1 AFR-LMS-006.2 AFR-LMS-006.3
    #  AFR-LMS-006.4 AFR-LMS-007.1 AFR-LMS-007.4 BR-LMS-009 BR-LMS-010 BR-LMS-011 UC-LMS-007
    #  UC-LMS-008 UC-LMS-009
    # BR-LMS-009, BR-LMS-010, BR-LMS-011; BW-LMS-02; CW-LMS-01 immediate branch.
    row = draft(world)
    pk = row["id"]
    assert row["state"] == "DRAFT"
    assert world.actor("student").get(f"{BASE}/assignments/{pk}/").status_code == 404
    assert (
        world.actor()
        .patch(f"{BASE}/assignments/{pk}/", {"instructions": "Revised"}, format="json")
        .json()["state"]
        == "DRAFT"
    )
    assert (
        world.actor().post(f"{BASE}/assignments/{pk}/publish/", {}, format="json").json()["state"]
        == "AVAILABLE"
    )
    student = world.actor("student")
    assert student.get(f"{BASE}/assignments/{pk}/").json()["instructions"] == "Revised"
    response = student.get(f"{BASE}/assignments/{pk}/download/")
    assert response.status_code == 200
    assert b"Revised" in b"".join(response.streaming_content)


def test_uc_lms_010_submit_uc_lms_011_own_history(world):
    # Source obligations: CFR-LMS-008 CFR-LMS-009 AFR-LMS-008.1 AFR-LMS-008.2 AFR-LMS-009.1
    #  AFR-LMS-009.2 BR-LMS-012 BR-LMS-013 BR-LMS-014 UC-LMS-010 UC-LMS-011 BW-LMS-02 CW-LMS-01
    # BR-LMS-012, BR-LMS-013, BR-LMS-014; D-01/D-05; BW-LMS-02; CW-LMS-01.
    row = available(world)
    url = f"{BASE}/assignments/{row['id']}/submissions/"
    student = world.actor("student")
    bad = student.post(url, {"kind": "LINK", "url": "https://example.org/work"}, format="json")
    assert bad.status_code == 422 and Submission.objects.count() == 0
    response = student.post(url, {"kind": "TEXT", "text": "My work", "user_id": 99}, format="json")
    assert response.status_code == 201 and response.json()["user_id"] == 2
    assert student.get(url).json()["results"][0]["text"] == "My work"
    again = student.post(url, {"kind": "TEXT", "text": "Again"}, format="json")
    assert again.status_code == 409 and again.json()["error"]["code"] == "SUBMISSION_ALREADY_EXISTS"
    assert Submission.objects.count() == 1


@pytest.mark.parametrize("role", ["faculty", "lms_ta"])
def test_uc_lms_012_grade_uc_lms_013_release_uc_lms_014_own_grade(world, role):
    # Source obligations: CFR-LMS-010 CFR-LMS-011 CFR-LMS-012 CFR-LMS-013 AFR-LMS-010.1
    #  AFR-LMS-010.2 AFR-LMS-010.3 AFR-LMS-011.1 AFR-LMS-011.2 AFR-LMS-011.3 AFR-LMS-012.1
    #  AFR-LMS-012.2 AFR-LMS-013.1 AFR-LMS-013.2 BR-LMS-015 BR-LMS-016 BR-LMS-017 BR-LMS-018
    #  BR-LMS-019 UC-LMS-012 UC-LMS-013 UC-LMS-014 BW-LMS-04 BW-LMS-05 CW-LMS-02
    # BR-LMS-015 through BR-LMS-019; BW-LMS-04 / BW-LMS-05; CW-LMS-02 both branches.
    row = available(world)
    submission = submit(world, row)
    grade_url = f"{BASE}/submissions/{submission['id']}/grade/"
    response = world.actor(role).post(
        grade_url, {"points": "15.00", "feedback": "Private draft"}, format="json"
    )
    assert response.status_code == 200 and response.json()["state"] == "DRAFT"
    assert response.json()["grader_user_id"] == (1 if role == "faculty" else 3)
    assert response.json()["points"] == "15.00"
    url = f"{BASE}/courses/{world.workspace.pk}/grades/"
    assert world.actor("student").get(url).json()["results"] == []
    assert (
        "Private draft"
        not in world.actor("student")
        .get(f"{BASE}/submissions/{submission['id']}/")
        .content.decode()
    )
    assert world.actor("lms_ta").post(grade_url + "release/", {}, format="json").status_code == 403
    assert (
        world.actor().post(grade_url + "release/", {}, format="json").json()["state"] == "RELEASED"
    )
    assert world.actor("student").get(url).json()["results"][0]["feedback"] == "Private draft"
    assert (
        world.actor("student").patch(grade_url, {"points": "20"}, format="json").status_code == 403
    )
    assert (
        world.actor("lms_ta")
        .patch(grade_url, {"points": "19", "feedback": "forbidden"}, format="json")
        .status_code
        == 403
    )
    assert (
        world.actor()
        .patch(grade_url, {"points": "18", "feedback": "Corrected"}, format="json")
        .json()["state"]
        == "RELEASED"
    )
    audit = GradeAuditLog.objects.latest("pk")
    assert (audit.old_points, audit.new_points, audit.old_feedback, audit.new_feedback) == (
        Decimal(15),
        Decimal(18),
        "Private draft",
        "Corrected",
    )
    assert audit.actor_user_id == 1 and audit.changed_at
    assert Grade.objects.get().state == "RELEASED" and GradeAuditLog.objects.count() == 3


def test_uc_lms_015_scheduled_material_and_assignment_release(world, monkeypatch):
    # Source obligations: AFR-LMS-003.3 AFR-LMS-003.4 AFR-LMS-007.2 AFR-LMS-007.3 BR-LMS-006
    #  UC-LMS-015 BW-LMS-01 BW-LMS-03
    # BR-LMS-006/011; BW-LMS-01/BW-LMS-03; CW-LMS-01 scheduled branch.
    monkeypatch.setattr("modules.lms.tasks.release_content.apply_async", lambda **kwargs: None)
    assignment = draft(world)
    material = (
        world.actor()
        .post(
            f"{BASE}/courses/{world.workspace.pk}/materials/",
            {"kind": "LINK", "url": "https://example.org/lesson"},
            format="json",
        )
        .json()
    )
    now = timezone.now()
    at = now + timedelta(minutes=1)
    for kind, row in (("assignments", assignment), ("materials", material)):
        response = world.actor().post(
            f"{BASE}/{kind}/{row['id']}/publish/", {"release_at": at.isoformat()}, format="json"
        )
        assert response.status_code == 200 and response.json()["state"] == "SCHEDULED"
        assert world.actor("student").get(f"{BASE}/{kind}/{row['id']}/").status_code == 404
    assert release_due_assignments() == 0 and release_due_materials() == 0
    with freeze_time(at):
        assert release_due_assignments() == 1 and release_due_materials() == 1
        assert release_due_assignments() == 0 and release_due_materials() == 0
        assert (
            world.actor("student").get(f"{BASE}/assignments/{assignment['id']}/").status_code == 200
        )
        assert world.actor("student").get(f"{BASE}/materials/{material['id']}/").status_code == 200
        submit(world, assignment)
    assert Assignment.objects.get().state == "AVAILABLE"
    assert Material.objects.get().state == "PUBLISHED"


def test_assignment_mutability_after_submissions_and_grades(world):
    row = available(world)
    submitted = submit(world, row)
    url = f"{BASE}/assignments/{row['id']}/"
    for data in (
        {"submission_type": "LINK"},
        {"due_at": (world.due - timedelta(hours=1)).isoformat()},
    ):
        assert world.actor().patch(url, data, format="json").status_code == 422
    extended = world.actor().patch(
        url,
        {"due_at": (world.due + timedelta(days=1)).isoformat(), "instructions": "Updated"},
        format="json",
    )
    assert extended.status_code == 200
    assert (
        world.actor()
        .post(f"{BASE}/submissions/{submitted['id']}/grade/", {"points": "10"}, format="json")
        .status_code
        == 200
    )
    assert world.actor().patch(url, {"points_possible": "30"}, format="json").status_code == 422
    assert Assignment.objects.get().points_possible == Decimal(20)


def test_submission_at_deadline_and_late_refusal(world):
    row = available(world)
    with freeze_time(world.due + timedelta(microseconds=1)):
        response = world.actor("student").post(
            f"{BASE}/assignments/{row['id']}/submissions/",
            {"kind": "TEXT", "text": "Late"},
            format="json",
        )
        assert (
            response.status_code == 422
            and response.json()["error"]["code"] == "SUBMISSION_DUE_DATE_EXCEEDED"
        )
    with freeze_time(world.due):
        submitted = submit(world, row)
        assert Submission.objects.get(pk=submitted["id"]).submitted_at == world.due
