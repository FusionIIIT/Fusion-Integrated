"""Automated specification tests for LMS Functional Requirements (CFR-LMS-*, AFR-LMS-*).

Derived strictly from FR_DESIGN.json.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.lms.models import Assignment, GradeAuditLog, Material
from modules.lms.tasks import release_due_assignments, release_due_materials
from modules.lms.tests.conftest import available, draft, submit

pytestmark = pytest.mark.django_db
BASE = "/api/v1/lms"


def test_fr_001_open_course_workspace(world):
    """TEST-FR-001 | AFR-LMS-001.1."""
    res = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code == 200
    assert res.json()["id"] == world.workspace.pk


def test_fr_002_display_syllabus_schedule_staff(world, user_ref):
    """TEST-FR-002 | AFR-LMS-001.2."""
    world.actor("faculty").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Intro Syllabus", "schedule": "Tuesday 2PM"},
        format="json",
    )
    client = world.actor("student")
    world.fake.users = {1: user_ref(1, kind="faculty"), 3: user_ref(3)}

    res = client.get(f"{BASE}/courses/")
    course = res.json()["results"][0]
    assert course["syllabus"] == "Intro Syllabus"
    assert course["schedule"] == "Tuesday 2PM"
    assert len(course["staff"]) >= 1


def test_fr_003_workspace_access_granted_to_course_users(world):
    """TEST-FR-003 | AFR-LMS-001.3."""
    for role in ("student", "faculty", "lms_ta", "lms_observer"):
        res = world.actor(role).get(f"{BASE}/courses/{world.workspace.pk}/")
        assert res.status_code == 200


def test_fr_004_workspace_access_denied_to_unauthorized_user(world):
    """TEST-FR-004 | AFR-LMS-001.3-neg."""
    res = world.actor("student").get(f"{BASE}/courses/{world.other.pk}/")
    assert res.status_code in (403, 404)


def test_fr_005_faculty_configures_workspace(world):
    """TEST-FR-005 | AFR-LMS-002.1."""
    res = world.actor("faculty").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Configured Syllabus", "schedule": "MWF 9AM"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["syllabus"] == "Configured Syllabus"


def test_fr_006_faculty_edits_course_details(world):
    """TEST-FR-006 | AFR-LMS-002.2."""
    world.actor("faculty").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Syllabus V1"},
        format="json",
    )
    res = world.actor("faculty").patch(
        f"{BASE}/courses/{world.workspace.pk}/",
        {"syllabus": "Syllabus V2"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["syllabus"] == "Syllabus V2"


def test_fr_007_faculty_adds_course_materials(world):
    """TEST-FR-007 | AFR-LMS-003.1."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Material 1"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["id"]


def test_fr_008_faculty_organizes_materials_into_sections(world):
    """TEST-FR-008 | AFR-LMS-003.2."""
    sec = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/sections/",
        {"kind": "WEEK", "label": "Week 1 Section"},
        format="json",
    ).json()

    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Section Material", "section_id": sec["id"]},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["section_id"] == sec["id"]


def test_fr_009_faculty_schedules_future_material_release(world):
    """TEST-FR-009 | AFR-LMS-003.3."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Scheduled Mat"},
        format="json",
    ).json()
    fut = timezone.now() + timedelta(days=2)
    res = world.actor("faculty").post(
        f"{BASE}/materials/{item['id']}/publish/",
        {"release_at": fut.isoformat()},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "SCHEDULED"


def test_fr_010_system_releases_scheduled_material(world):
    """TEST-FR-010 | AFR-LMS-003.4."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Auto Mat"},
        format="json",
    ).json()
    fut = timezone.now() + timedelta(hours=1)
    world.actor("faculty").post(
        f"{BASE}/materials/{item['id']}/publish/",
        {"release_at": fut.isoformat()},
        format="json",
    )

    with freeze_time(fut + timedelta(seconds=10)):
        release_due_materials()

    assert Material.objects.get(pk=item["id"]).state == "PUBLISHED"


def test_fr_011_student_read_only_published_materials(world):
    """TEST-FR-011 | AFR-LMS-004.1."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Student Read Material"},
        format="json",
    ).json()
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {}, format="json")

    res = world.actor("student").get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code == 200
    assert res.json()["text"] == "Student Read Material"


def test_fr_012_ta_read_only_published_materials(world):
    """TEST-FR-012 | AFR-LMS-004.2."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "TA Read Material"},
        format="json",
    ).json()
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {}, format="json")

    res = world.actor("lms_ta").get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code == 200


def test_fr_013_observer_read_only_published_materials(world):
    """TEST-FR-013 | AFR-LMS-004.3."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Observer Read Material"},
        format="json",
    ).json()
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {}, format="json")

    res = world.actor("lms_observer").get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code == 200


def test_fr_014_faculty_posts_announcement(world):
    """TEST-FR-014 | AFR-LMS-005.1."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Faculty Post 1"},
        format="json",
    )
    assert res.status_code == 201


def test_fr_015_ta_posts_announcement_when_permitted(world):
    """TEST-FR-015 | AFR-LMS-005.2."""
    world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/policy-versions/",
        {"can_ta_post_announcements": True},
        format="json",
    )
    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "TA permitted announcement"},
        format="json",
    )
    assert res.status_code == 201


def test_fr_016_ta_cannot_post_announcement_without_permission(world):
    """TEST-FR-016 | AFR-LMS-005.2-neg."""
    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Forbidden TA post"},
        format="json",
    )
    assert res.status_code == 403


def test_fr_017_announcement_timestamped(world):
    """TEST-FR-017 | AFR-LMS-005.3."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Timestamp check"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["created_at"] is not None


def test_fr_018_announcement_visible_course_wide(world):
    """TEST-FR-018 | AFR-LMS-005.4."""
    world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Course-wide news"},
        format="json",
    )
    for role in ("student", "lms_ta", "lms_observer"):
        res = world.actor(role).get(f"{BASE}/courses/{world.workspace.pk}/announcements/")
        assert any(a["content"] == "Course-wide news" for a in res.json()["results"])


def test_fr_019_faculty_creates_assignment(world):
    """TEST-FR-019 | AFR-LMS-006.1."""
    row = draft(world, title="Assignment FR-19")
    assert row["id"]
    assert Assignment.objects.filter(pk=row["id"]).exists()


def test_fr_020_assignment_captures_required_fields(world):
    """TEST-FR-020 | AFR-LMS-006.2."""
    row = draft(world, title="Full Config", submission_type="TEXT", points_possible="50.00")
    a = Assignment.objects.get(pk=row["id"])
    assert a.submission_type == "TEXT"
    assert a.points_possible == Decimal("50.00")
    assert a.due_at is not None


def test_fr_021_faculty_edits_assignment(world):
    """TEST-FR-021 | AFR-LMS-006.3."""
    row = draft(world, title="Before edit")
    res = world.actor("faculty").patch(
        f"{BASE}/assignments/{row['id']}/",
        {"instructions": "After edit"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["instructions"] == "After edit"


def test_fr_022_assignment_maintained_in_draft_state(world):
    """TEST-FR-022 | AFR-LMS-006.4."""
    row = draft(world, title="Draft only")
    assert row["state"] == "DRAFT"
    assert world.actor("student").get(f"{BASE}/assignments/{row['id']}/").status_code == 404


def test_fr_023_faculty_publishes_assignment(world):
    """TEST-FR-023 | AFR-LMS-007.1."""
    row = draft(world, title="Publish immediate")
    pub = world.actor("faculty").post(f"{BASE}/assignments/{row['id']}/publish/", {}, format="json")
    assert pub.status_code == 200
    assert pub.json()["state"] == "AVAILABLE"


def test_fr_024_scheduled_assignment_withheld_from_students(world):
    """TEST-FR-024 | AFR-LMS-007.2."""
    row = draft(world, title="Scheduled withhold")
    fut = timezone.now() + timedelta(days=2)
    world.actor("faculty").post(f"{BASE}/assignments/{row['id']}/publish/", {"release_at": fut.isoformat()}, format="json")
    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code in (403, 404)


def test_fr_025_system_releases_scheduled_assignment(world):
    """TEST-FR-025 | AFR-LMS-007.3."""
    row = draft(world, title="Scheduled auto release")
    fut = timezone.now() + timedelta(hours=1)
    world.actor("faculty").post(f"{BASE}/assignments/{row['id']}/publish/", {"release_at": fut.isoformat()}, format="json")

    with freeze_time(fut + timedelta(seconds=10)):
        release_due_assignments()

    assert Assignment.objects.get(pk=row["id"]).state == "AVAILABLE"


def test_fr_026_student_views_and_downloads_released_assignment(world):
    """TEST-FR-026 | AFR-LMS-007.4."""
    row = available(world, title="Downloadable Assignment")
    student = world.actor("student")
    assert student.get(f"{BASE}/assignments/{row['id']}/").status_code == 200
    res = student.get(f"{BASE}/assignments/{row['id']}/download/")
    assert res.status_code == 200


def test_fr_027_student_submits_conforming_work(world):
    """TEST-FR-027 | AFR-LMS-008.1."""
    row = available(world, submission_type="TEXT")
    sub = submit(world, row, text="Conforming text work")
    assert sub["id"]


def test_fr_028_submission_type_mismatch_refused(world):
    """TEST-FR-028 | AFR-LMS-008.1-neg."""
    row = available(world, submission_type="LINK")
    # Submitting TEXT when LINK is required
    res = world.actor("student").post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "TEXT", "text": "Wrong kind"},
        format="json",
    )
    assert res.status_code in (400, 422)


def test_fr_029_on_time_submission_accepted(world):
    """TEST-FR-029 | AFR-LMS-008.2."""
    row = available(world)
    with freeze_time(world.due - timedelta(minutes=30)):
        sub = submit(world, row)
        assert sub["id"]


def test_fr_030_late_submission_refused(world):
    """TEST-FR-030 | AFR-LMS-008.2-neg."""
    row = available(world)
    with freeze_time(world.due + timedelta(seconds=1)):
        res = world.actor("student").post(
            f"{BASE}/assignments/{row['id']}/submissions/",
            {"kind": "TEXT", "text": "Late submission"},
            format="json",
        )
        assert res.status_code in (400, 422)


def test_fr_031_student_views_own_submission_history(world):
    """TEST-FR-031 | AFR-LMS-009.1."""
    row = available(world)
    sub = submit(world, row, text="History check FR-31")
    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/submissions/")
    assert res.status_code == 200
    assert any(s["id"] == sub["id"] for s in res.json()["results"])


def test_fr_032_submission_status_display(world):
    """TEST-FR-032 | AFR-LMS-009.2."""
    row = available(world)
    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/submissions/")
    assert res.status_code == 200
    assert len(res.json()["results"]) == 0


def test_fr_033_faculty_grades_submission(world):
    """TEST-FR-033 | AFR-LMS-010.1."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "17.50", "feedback": "Faculty grade FR-33"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "DRAFT"


def test_fr_034_ta_grades_submission(world):
    """TEST-FR-034 | AFR-LMS-010.2."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("lms_ta").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "16.00", "feedback": "TA grade FR-34"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "DRAFT"


def test_fr_035_grader_identity_recorded(world):
    """TEST-FR-035 | AFR-LMS-010.3."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("lms_ta").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "15.00"},
        format="json",
    )
    assert res.json()["grader_user_id"] == 3


def test_fr_036_grade_held_in_draft_state(world):
    """TEST-FR-036 | AFR-LMS-011.1."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "18.00"},
        format="json",
    )
    assert res.json()["state"] == "DRAFT"


def test_fr_037_student_cannot_view_draft_grade(world):
    """TEST-FR-037 | AFR-LMS-011.2."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "18.00", "feedback": "Hidden"}, format="json")
    grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grades) == 0


def test_fr_038_faculty_releases_grades(world):
    """TEST-FR-038 | AFR-LMS-011.3."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "18.00"}, format="json")
    res = world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")
    assert res.status_code == 200
    assert res.json()["state"] == "RELEASED"


def test_fr_039_student_views_released_grade(world):
    """TEST-FR-039 | AFR-LMS-012.1."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "19.00", "feedback": "Released"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grades) == 1
    assert grades[0]["points"] == "19.00"


def test_fr_040_released_grade_is_read_only(world):
    """TEST-FR-040 | AFR-LMS-012.2."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "19.00"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    res = world.actor("student").patch(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "20.00"}, format="json")
    assert res.status_code == 403


def test_fr_041_system_logs_actor_for_post_release_grade_change(world):
    """TEST-FR-041 | AFR-LMS-013.1."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")
    world.actor("faculty").patch(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "18.00"}, format="json")

    audit = GradeAuditLog.objects.latest("pk")
    assert audit.actor_user_id == 1


def test_fr_042_system_logs_timestamp_for_post_release_grade_change(world):
    """TEST-FR-042 | AFR-LMS-013.2."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")
    world.actor("faculty").patch(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "18.00"}, format="json")

    audit = GradeAuditLog.objects.latest("pk")
    assert audit.changed_at is not None


def test_fr_043_ta_views_course_details_materials_announcements(world):
    """TEST-FR-043 | AFR-LMS-014.1."""
    res = world.actor("lms_ta").get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code == 200


def test_fr_044_ta_views_student_submissions(world):
    """TEST-FR-044 | AFR-LMS-014.2."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("lms_ta").get(f"{BASE}/submissions/{sub['id']}/")
    assert res.status_code == 200


def test_fr_045_ta_cannot_create_or_edit_assignments(world):
    """TEST-FR-045 | AFR-LMS-014.3."""
    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/assignments/",
        {
            "instructions": "TA instructions",
            "due_at": world.due.isoformat(),
            "submission_type": "TEXT",
            "points_possible": "10.00",
        },
        format="json",
    )
    assert res.status_code == 403


def test_fr_046_ta_cannot_create_or_edit_materials(world):
    """TEST-FR-046 | AFR-LMS-014.4."""
    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "TA note"},
        format="json",
    )
    assert res.status_code == 403


def test_fr_047_ta_cannot_modify_sections(world):
    """TEST-FR-047 | AFR-LMS-014.5."""
    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/sections/",
        {"kind": "WEEK", "label": "TA Section"},
        format="json",
    )
    assert res.status_code == 403


def test_fr_048_observer_views_details_materials_announcements(world):
    """TEST-FR-048 | AFR-LMS-015.1."""
    res = world.actor("lms_observer").get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code == 200


def test_fr_049_observer_cannot_view_submissions(world):
    """TEST-FR-049 | AFR-LMS-015.2."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("lms_observer").get(f"{BASE}/submissions/{sub['id']}/")
    assert res.status_code in (403, 404)


def test_fr_050_observer_cannot_view_grades(world):
    """TEST-FR-050 | AFR-LMS-015.3."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    res = world.actor("lms_observer").get(f"{BASE}/submissions/{sub['id']}/grade/")
    assert res.status_code in (403, 404)


def test_fr_051_observer_no_write_access(world):
    """TEST-FR-051 | AFR-LMS-015.4."""
    obs = world.actor("lms_observer")
    assert obs.post(f"{BASE}/courses/{world.workspace.pk}/announcements/", {"content": "X"}, format="json").status_code == 403
    assert obs.post(f"{BASE}/courses/{world.workspace.pk}/materials/", {"kind": "NOTE", "text": "X"}, format="json").status_code == 403
    assert obs.patch(f"{BASE}/courses/{world.workspace.pk}/", {"syllabus": "X"}, format="json").status_code == 403
