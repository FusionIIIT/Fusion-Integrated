"""Automated specification tests for LMS Use Cases (UC-LMS-001..015).

Derived strictly from UC_DESIGN.json.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.lms.models import GradeAuditLog, Material
from modules.lms.tasks import release_due_assignments, release_due_materials
from modules.lms.tests.conftest import available, draft, submit

pytestmark = pytest.mark.django_db
BASE = "/api/v1/lms"


def test_uc_001_access_course_workspace(world):
    """TEST-UC-001 | UC-LMS-001 Main Flow."""
    res = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code == 200
    assert res.json()["id"] == world.workspace.pk


def test_uc_002_access_unauthorized_course_denied(world):
    """TEST-UC-002 | UC-LMS-001 Alternative Flow."""
    res = world.actor("student").get(f"{BASE}/courses/{world.other.pk}/")
    assert res.status_code in (403, 404)


def test_uc_003_access_unregistered_workspace_denied(world):
    """TEST-UC-003 | UC-LMS-001 Exception Flow."""
    res = world.actor("student", uid=9999).get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code in (403, 404)


def test_uc_004_manage_course_details(world):
    """TEST-UC-004 | UC-LMS-002 Main Flow."""
    res = world.actor("faculty").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Initial Syllabus", "schedule": "Mon/Wed 10:00"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["syllabus"] == "Initial Syllabus"


def test_uc_005_edit_published_course_details(world):
    """TEST-UC-005 | UC-LMS-002 Alternative Flow."""
    world.actor("faculty").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Old Syllabus"},
        format="json",
    )
    res = world.actor("faculty").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Updated Syllabus"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["syllabus"] == "Updated Syllabus"


def test_uc_006_unauthorized_course_details_edit_rejected(world):
    """TEST-UC-006 | UC-LMS-002 Exception Flow."""
    res_ta = world.actor("lms_ta").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "TA Overwrite"},
        format="json",
    )
    assert res_ta.status_code == 403

    res_stu = world.actor("student").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Student Overwrite"},
        format="json",
    )
    assert res_stu.status_code == 403


def test_uc_007_manage_course_materials_immediate(world):
    """TEST-UC-007 | UC-LMS-003 Main Flow."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Immediate Lesson Note"},
        format="json",
    )
    assert item.status_code == 201
    mat_id = item.json()["id"]

    pub = world.actor("faculty").post(f"{BASE}/materials/{mat_id}/publish/", {}, format="json")
    assert pub.status_code == 200
    assert pub.json()["state"] == "PUBLISHED"


def test_uc_008_manage_course_materials_scheduled(world):
    """TEST-UC-008 | UC-LMS-003 Main Flow Scheduled."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Scheduled Lesson Note"},
        format="json",
    )
    assert item.status_code == 201
    mat_id = item.json()["id"]
    fut = timezone.now() + timedelta(days=2)

    pub = world.actor("faculty").post(
        f"{BASE}/materials/{mat_id}/publish/",
        {"release_at": fut.isoformat()},
        format="json",
    )
    assert pub.status_code == 200
    assert pub.json()["state"] == "SCHEDULED"


def test_uc_009_edit_existing_material(world):
    """TEST-UC-009 | UC-LMS-003 Alternative Flow."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Draft Material Text"},
        format="json",
    ).json()

    res = world.actor("faculty").patch(
        f"{BASE}/materials/{item['id']}/",
        {"text": "Revised Material Text", "order": 3},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["text"] == "Revised Material Text"


def test_uc_010_material_write_by_non_faculty_rejected(world):
    """TEST-UC-010 | UC-LMS-003 Exception Flow."""
    res_ta = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "TA write attempt"},
        format="json",
    )
    assert res_ta.status_code == 403

    res_stu = world.actor("student").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Student write attempt"},
        format="json",
    )
    assert res_stu.status_code == 403


def test_uc_011_view_published_material(world):
    """TEST-UC-011 | UC-LMS-004 Main Flow."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Read-only published note"},
        format="json",
    ).json()
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {}, format="json")

    for role in ("student", "lms_ta", "lms_observer"):
        res = world.actor(role).get(f"{BASE}/materials/{item['id']}/")
        assert res.status_code == 200
        assert res.json()["text"] == "Read-only published note"


def test_uc_012_scheduled_material_hidden_until_released(world):
    """TEST-UC-012 | UC-LMS-004 Alternative Flow."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Unreleased note"},
        format="json",
    ).json()
    fut = timezone.now() + timedelta(days=3)
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {"release_at": fut.isoformat()}, format="json")

    res = world.actor("student").get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code in (403, 404)


def test_uc_013_unauthorized_material_view_denied(world):
    """TEST-UC-013 | UC-LMS-004 Exception Flow."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Course material"},
        format="json",
    ).json()
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {}, format="json")

    res = world.actor("student", uid=9999).get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code in (403, 404)


def test_uc_014_faculty_post_announcement(world):
    """TEST-UC-014 | UC-LMS-005 Main Flow."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Faculty announcement UC-14"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["created_at"] is not None


def test_uc_015_ta_post_announcement_when_permitted(world):
    """TEST-UC-015 | UC-LMS-005 Alternative Flow."""
    world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/policy-versions/",
        {"can_ta_post_announcements": True},
        format="json",
    )

    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "TA announcement UC-15"},
        format="json",
    )
    assert res.status_code == 201


def test_uc_016_unauthorized_announcement_posting_rejected(world):
    """TEST-UC-016 | UC-LMS-005 Exception Flow."""
    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Unauthorized TA announcement"},
        format="json",
    )
    assert res.status_code == 403


def test_uc_017_view_course_announcements(world):
    """TEST-UC-017 | UC-LMS-006 Main Flow."""
    world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Broadcast message"},
        format="json",
    )

    for role in ("student", "lms_ta", "lms_observer"):
        res = world.actor(role).get(f"{BASE}/courses/{world.workspace.pk}/announcements/")
        assert res.status_code == 200
        assert any(a["content"] == "Broadcast message" for a in res.json()["results"])


def test_uc_018_unauthorized_announcements_view_denied(world):
    """TEST-UC-018 | UC-LMS-006 Exception Flow."""
    res = world.actor("student", uid=9999).get(f"{BASE}/courses/{world.workspace.pk}/announcements/")
    assert res.status_code in (403, 404)


def test_uc_019_create_assignment_draft(world):
    """TEST-UC-019 | UC-LMS-007 Main Flow."""
    row = draft(world, title="Assignment Draft UC-19")
    assert row["state"] == "DRAFT"
    assert row["id"]


def test_uc_020_edit_draft_assignment(world):
    """TEST-UC-020 | UC-LMS-007 Alternative Flow."""
    row = draft(world, title="Original Title")
    res = world.actor("faculty").patch(
        f"{BASE}/assignments/{row['id']}/",
        {"instructions": "Updated Instructions"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["instructions"] == "Updated Instructions"
    assert res.json()["state"] == "DRAFT"


def test_uc_021_non_faculty_assignment_authoring_rejected(world):
    """TEST-UC-021 | UC-LMS-007 Exception Flow."""
    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/assignments/",
        {
            "instructions": "TA draft",
            "due_at": world.due.isoformat(),
            "submission_type": "TEXT",
            "points_possible": "20.00",
        },
        format="json",
    )
    assert res.status_code == 403


def test_uc_022_publish_assignment_immediately(world):
    """TEST-UC-022 | UC-LMS-008 Main Flow."""
    row = draft(world, title="Assignment Immediate UC-22")
    res = world.actor("faculty").post(f"{BASE}/assignments/{row['id']}/publish/", {}, format="json")
    assert res.status_code == 200
    assert res.json()["state"] == "AVAILABLE"


def test_uc_023_publish_assignment_scheduled(world):
    """TEST-UC-023 | UC-LMS-008 Alternative Flow."""
    row = draft(world, title="Assignment Scheduled UC-23")
    fut = timezone.now() + timedelta(days=1)
    res = world.actor("faculty").post(
        f"{BASE}/assignments/{row['id']}/publish/",
        {"release_at": fut.isoformat()},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "SCHEDULED"


def test_uc_024_publish_invalid_assignment_rejected(world):
    """TEST-UC-024 | UC-LMS-008 Exception Flow."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/assignments/",
        {"instructions": "No due date"},
        format="json",
    )
    assert res.status_code in (400, 422)


def test_uc_025_student_views_published_assignment(world):
    """TEST-UC-025 | UC-LMS-009 Main Flow."""
    row = available(world, title="Published Assignment UC-25")
    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code == 200
    assert res.json()["id"] == row["id"]


def test_uc_026_student_cannot_view_scheduled_assignment(world):
    """TEST-UC-026 | UC-LMS-009 Alternative Flow."""
    row = draft(world, title="Scheduled Assignment UC-26")
    fut = timezone.now() + timedelta(days=2)
    world.actor("faculty").post(f"{BASE}/assignments/{row['id']}/publish/", {"release_at": fut.isoformat()}, format="json")

    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code in (403, 404)


def test_uc_027_unauthorized_assignment_view_denied(world):
    """TEST-UC-027 | UC-LMS-009 Exception Flow."""
    row = available(world)
    res = world.actor("student", uid=9999).get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code in (403, 404)


def test_uc_028_student_submits_assignment_on_time(world):
    """TEST-UC-028 | UC-LMS-010 Main Flow."""
    row = available(world, submission_type="TEXT")
    sub = submit(world, row, text="On-time solution text")
    assert sub["id"]
    assert sub["user_id"] == 2


def test_uc_029_inconsistent_submission_type_rejected(world):
    """TEST-UC-029 | UC-LMS-010 Exception Flow."""
    row = available(world, submission_type="LINK")
    # Missing required 'url' parameter for LINK submission
    res = world.actor("student").post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "LINK"},
        format="json",
    )
    assert res.status_code in (400, 422)


def test_uc_030_non_enrolled_user_cannot_submit(world):
    """TEST-UC-030 | UC-LMS-010 Exception Flow Auth."""
    row = available(world)
    res = world.actor("student", uid=9999).post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "TEXT", "text": "Unauthorized submit"},
        format="json",
    )
    assert res.status_code in (403, 404)


def test_uc_031_student_views_own_submission_history(world):
    """TEST-UC-031 | UC-LMS-011 Main Flow."""
    row = available(world)
    sub = submit(world, row, text="History check")
    res = world.actor("student").get(f"{BASE}/submissions/{sub['id']}/")
    assert res.status_code == 200
    assert res.json()["id"] == sub["id"]


def test_uc_032_student_unsubmitted_status(world):
    """TEST-UC-032 | UC-LMS-011 Alternative Flow."""
    row = available(world)
    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/submissions/")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 0


def test_uc_033_student_access_other_submission_denied(world):
    """TEST-UC-033 | UC-LMS-011 Exception Flow."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("student", uid=999).get(f"{BASE}/submissions/{sub['id']}/")
    assert res.status_code in (403, 404)


def test_uc_034_faculty_grades_submission(world):
    """TEST-UC-034 | UC-LMS-012 Main Flow."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "18.00", "feedback": "Faculty grading UC-34"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "DRAFT"
    assert res.json()["grader_user_id"] == 1


def test_uc_035_ta_grades_submission(world):
    """TEST-UC-035 | UC-LMS-012 Main Flow TA."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("lms_ta").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "17.00", "feedback": "TA grading UC-35"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "DRAFT"
    assert res.json()["grader_user_id"] == 3


def test_uc_036_modify_released_grade_creates_audit_record(world):
    """TEST-UC-036 | UC-LMS-012 Alternative Flow."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    res = world.actor("faculty").patch(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "19.00", "feedback": "Audit update"},
        format="json",
    )
    assert res.status_code == 200
    audit = GradeAuditLog.objects.latest("pk")
    assert audit.old_points == Decimal("15.00")
    assert audit.new_points == Decimal("19.00")


def test_uc_037_unauthorized_user_grading_rejected(world):
    """TEST-UC-037 | UC-LMS-012 Exception Flow."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("student").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "20.00"},
        format="json",
    )
    assert res.status_code == 403


def test_uc_038_self_grading_conflict_rejected(world):
    """TEST-UC-038 | UC-LMS-012 Exception Flow Conflict."""
    row = available(world)
    sub = world.actor("student", uid=3).post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "TEXT", "text": "TA submitted work"},
        format="json",
    ).json()

    res = world.actor("lms_ta", uid=3).post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "20.00"},
        format="json",
    )
    assert res.status_code in (403, 422)


def test_uc_039_faculty_releases_draft_grades(world):
    """TEST-UC-039 | UC-LMS-013 Main Flow."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00"}, format="json")
    res = world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")
    assert res.status_code == 200
    assert res.json()["state"] == "RELEASED"


def test_uc_040_ta_cannot_release_grades(world):
    """TEST-UC-040 | UC-LMS-013 Exception Flow."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00"}, format="json")
    res = world.actor("lms_ta").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")
    assert res.status_code == 403


def test_uc_041_student_views_released_grade(world):
    """TEST-UC-041 | UC-LMS-014 Main Flow."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "18.50", "feedback": "Good"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grades) == 1
    assert grades[0]["points"] == "18.50"


def test_uc_042_student_cannot_view_draft_grade(world):
    """TEST-UC-042 | UC-LMS-014 Alternative Flow."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00"}, format="json")

    grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grades) == 0


def test_uc_043_student_access_other_student_grade_denied(world):
    """TEST-UC-043 | UC-LMS-014 Exception Flow."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    res = world.actor("student", uid=999).get(f"{BASE}/submissions/{sub['id']}/grade/")
    assert res.status_code in (403, 404)


def test_uc_044_process_scheduled_material_release(world):
    """TEST-UC-044 | UC-LMS-015 Main Flow Material."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Scheduled release note"},
        format="json",
    ).json()
    rel_time = timezone.now() + timedelta(hours=1)
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {"release_at": rel_time.isoformat()}, format="json")

    with freeze_time(rel_time + timedelta(seconds=10)):
        release_due_materials()

    mat = Material.objects.get(pk=item["id"])
    assert mat.state == "PUBLISHED"


def test_uc_045_process_scheduled_assignment_release(world):
    """TEST-UC-045 | UC-LMS-015 Main Flow Assignment."""
    row = draft(world, title="Scheduled Assignment UC-45")
    rel_time = timezone.now() + timedelta(hours=1)
    world.actor("faculty").post(
        f"{BASE}/assignments/{row['id']}/publish/",
        {"release_at": rel_time.isoformat()},
        format="json",
    )

    with freeze_time(rel_time + timedelta(seconds=10)):
        release_due_assignments()

    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code == 200
    assert res.json()["state"] == "AVAILABLE"


def test_uc_046_withdrawn_scheduled_content_not_released(world):
    """TEST-UC-046 | UC-LMS-015 Alternative Flow."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "To be withdrawn"},
        format="json",
    ).json()
    rel_time = timezone.now() + timedelta(hours=1)
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {"release_at": rel_time.isoformat()}, format="json")

    # Faculty deletes/withdraws material before release time
    world.actor("faculty").delete(f"{BASE}/materials/{item['id']}/")

    with freeze_time(rel_time + timedelta(seconds=10)):
        release_due_materials()

    assert not Material.objects.filter(pk=item["id"], state="PUBLISHED").exists()


def test_uc_047_release_processing_failure_keeps_unavailable(world):
    """TEST-UC-047 | UC-LMS-015 Exception Flow."""
    row = draft(world, title="Assignment UC-47")
    rel_time = timezone.now() + timedelta(hours=1)
    world.actor("faculty").post(
        f"{BASE}/assignments/{row['id']}/publish/",
        {"release_at": rel_time.isoformat()},
        format="json",
    )

    # Before scheduled time arrives, release task will not release it
    release_due_assignments()
    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code in (403, 404)
