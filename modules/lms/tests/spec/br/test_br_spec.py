"""Automated specification tests for LMS Business Rules (BR-LMS-001..019).

Derived strictly from BR_DESIGN.json.
"""

import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.lms.models import Grade, GradeAuditLog, Material
from modules.lms.tasks import release_due_materials
from modules.lms.tests.conftest import available, draft, submit

pytestmark = pytest.mark.django_db
BASE = "/api/v1/lms"


def test_br_001_course_access_authorized(world):
    """TEST-BR-001 | BR-LMS-001 condition-true."""
    res = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code == 200
    assert res.json()["id"] == world.workspace.pk


def test_br_002_course_access_unauthorized(world):
    """TEST-BR-002 | BR-LMS-001 condition-false."""
    res = world.actor("student").get(f"{BASE}/courses/{world.other.pk}/")
    assert res.status_code in (403, 404)


def test_br_003_student_registration_data_governs_access(world):
    """TEST-BR-003 | BR-LMS-002 condition-true."""
    res = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code == 200


def test_br_004_unregistered_student_denied(world):
    """TEST-BR-004 | BR-LMS-002 condition-false."""
    res = world.actor("student", uid=9999).get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code in (403, 404)


def test_br_005_observer_read_only_access(world):
    """TEST-BR-005 | BR-LMS-003 condition-true."""
    res = world.actor("lms_observer").get(f"{BASE}/courses/{world.workspace.pk}/")
    assert res.status_code == 200


def test_br_006_observer_write_prohibited(world):
    """TEST-BR-006 | BR-LMS-003 condition-false-write."""
    obs = world.actor("lms_observer")
    # Attempt create announcement
    ann = obs.post(f"{BASE}/courses/{world.workspace.pk}/announcements/", {"content": "Forbidden"}, format="json")
    assert ann.status_code == 403

    # Attempt create material
    mat = obs.post(f"{BASE}/courses/{world.workspace.pk}/materials/", {"kind": "NOTE", "text": "Forbidden"}, format="json")
    assert mat.status_code == 403


def test_br_007_observer_student_data_restriction(world):
    """TEST-BR-007 | BR-LMS-003 condition-false-student-data."""
    row = available(world)
    sub = submit(world, row)
    obs = world.actor("lms_observer")

    res = obs.get(f"{BASE}/submissions/{sub['id']}/")
    assert res.status_code in (403, 404)


def test_br_008_ta_view_and_grade_allowed(world):
    """TEST-BR-008 | BR-LMS-004 condition-true."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("lms_ta").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "15.00", "feedback": "TA grading"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "DRAFT"


def test_br_009_ta_assignment_authoring_prohibited(world):
    """TEST-BR-009 | BR-LMS-004 condition-false-assignment-authoring."""
    ta = world.actor("lms_ta")
    res = ta.post(
        f"{BASE}/courses/{world.workspace.pk}/assignments/",
        {
            "instructions": "TA created",
            "due_at": world.due.isoformat(),
            "submission_type": "TEXT",
            "points_possible": "10.00",
        },
        format="json",
    )
    assert res.status_code == 403


def test_br_010_ta_material_authoring_prohibited(world):
    """TEST-BR-010 | BR-LMS-004 condition-false-material-authoring."""
    ta = world.actor("lms_ta")
    res = ta.post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "TA notes"},
        format="json",
    )
    assert res.status_code == 403


def test_br_011_published_material_visible(world):
    """TEST-BR-011 | BR-LMS-005 condition-true."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Visible notes"},
        format="json",
    ).json()
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {}, format="json")

    res = world.actor("student").get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code == 200
    assert res.json()["text"] == "Visible notes"


def test_br_012_unpublished_material_invisible(world):
    """TEST-BR-012 | BR-LMS-005 condition-false."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Draft notes"},
        format="json",
    ).json()

    res = world.actor("student").get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code in (403, 404)


def test_br_013_scheduled_material_unavailable_before_time(world):
    """TEST-BR-013 | BR-LMS-006 condition-false-before-time."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Future material"},
        format="json",
    ).json()
    fut = timezone.now() + timedelta(days=5)
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {"release_at": fut.isoformat()}, format="json")

    res = world.actor("student").get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code in (403, 404)


def test_br_014_scheduled_material_released_after_time(world):
    """TEST-BR-014 | BR-LMS-006 condition-true-after-time."""
    item = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Auto released material"},
        format="json",
    ).json()
    fut = timezone.now() + timedelta(hours=1)
    world.actor("faculty").post(f"{BASE}/materials/{item['id']}/publish/", {"release_at": fut.isoformat()}, format="json")

    with freeze_time(fut + timedelta(seconds=10)):
        release_due_materials()

    mat = Material.objects.get(pk=item["id"])
    assert mat.state == "PUBLISHED"
    res = world.actor("student").get(f"{BASE}/materials/{item['id']}/")
    assert res.status_code == 200


def test_br_015_faculty_announcement_allowed(world):
    """TEST-BR-015 | BR-LMS-007 condition-true-faculty."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Faculty announcement"},
        format="json",
    )
    assert res.status_code == 201
    assert res.json()["content"] == "Faculty announcement"


def test_br_016_ta_permitted_announcement_allowed(world):
    """TEST-BR-016 | BR-LMS-007 condition-true-ta-permitted."""
    # Enable TA announcement policy
    world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/policy-versions/",
        {"can_ta_post_announcements": True},
        format="json",
    )

    res = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "TA permitted notice"},
        format="json",
    )
    assert res.status_code == 201


def test_br_017_unauthorized_announcement_rejected(world):
    """TEST-BR-017 | BR-LMS-007 condition-false-unauthorized."""
    # Default policy has can_ta_post_announcements=False
    res_ta = world.actor("lms_ta").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "TA forbidden notice"},
        format="json",
    )
    assert res_ta.status_code == 403

    res_stu = world.actor("student").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Student notice"},
        format="json",
    )
    assert res_stu.status_code == 403


def test_br_018_announcement_timestamp_and_audience(world):
    """TEST-BR-018 | BR-LMS-008 condition-true."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/announcements/",
        {"content": "Timestamped news"},
        format="json",
    )
    assert res.status_code == 201
    data = res.json()
    assert data["created_at"] is not None

    # Enrolled student sees it
    listing = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/announcements/").json()
    assert any(a["id"] == data["id"] for a in listing["results"])


def test_br_019_announcement_hidden_from_non_course_users(world):
    """TEST-BR-019 | BR-LMS-008 condition-false."""
    res = world.actor("student", uid=9999).get(f"{BASE}/courses/{world.workspace.pk}/announcements/")
    assert res.status_code in (403, 404)


def test_br_020_assignment_required_configuration_valid(world):
    """TEST-BR-020 | BR-LMS-009 condition-true."""
    row = draft(world, title="Valid Config", submission_type="TEXT", points_possible="100.00")
    assert row["id"]
    assert row["state"] == "DRAFT"


def test_br_021_assignment_missing_due_date_rejected(world):
    """TEST-BR-021 | BR-LMS-009 condition-false-missing-due-date."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/assignments/",
        {
            "instructions": "Missing due date",
            "submission_type": "TEXT",
            "points_possible": "50.00",
        },
        format="json",
    )
    assert res.status_code in (400, 422)


def test_br_022_assignment_missing_submission_type_rejected(world):
    """TEST-BR-022 | BR-LMS-009 condition-false-missing-submission-type."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/assignments/",
        {
            "instructions": "Missing type",
            "due_at": world.due.isoformat(),
            "points_possible": "50.00",
        },
        format="json",
    )
    assert res.status_code in (400, 422)


def test_br_023_assignment_invalid_points_rejected(world):
    """TEST-BR-023 | BR-LMS-009 condition-false-invalid-points."""
    res = world.actor("faculty").post(
        f"{BASE}/courses/{world.workspace.pk}/assignments/",
        {
            "instructions": "Invalid points",
            "due_at": world.due.isoformat(),
            "submission_type": "TEXT",
            "points_possible": "-10.00",
        },
        format="json",
    )
    assert res.status_code in (400, 422)


def test_br_024_assignment_draft_invisible_to_students(world):
    """TEST-BR-024 | BR-LMS-010 condition-true-draft."""
    row = draft(world, title="Draft A")
    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code in (403, 404)


def test_br_025_assignment_publishes_from_draft(world):
    """TEST-BR-025 | BR-LMS-010 condition-true-published."""
    row = draft(world, title="Draft to publish")
    pub = world.actor("faculty").post(f"{BASE}/assignments/{row['id']}/publish/", {}, format="json")
    assert pub.status_code == 200
    assert pub.json()["state"] == "AVAILABLE"


def test_br_026_assignment_scheduled_invisible_to_students(world):
    """TEST-BR-026 | BR-LMS-011 condition-false-scheduled."""
    row = draft(world, title="Scheduled A")
    fut = timezone.now() + timedelta(days=2)
    world.actor("faculty").post(f"{BASE}/assignments/{row['id']}/publish/", {"release_at": fut.isoformat()}, format="json")

    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code in (403, 404)


def test_br_027_assignment_released_accessible_to_students(world):
    """TEST-BR-027 | BR-LMS-011 condition-true-released."""
    row = available(world, title="Released A")
    res = world.actor("student").get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code == 200
    assert res.json()["state"] == "AVAILABLE"


def test_br_028_submission_conforms_to_file_type(world):
    """TEST-BR-028 | BR-LMS-012 condition-true-file."""
    row = available(world, submission_type="FILE")
    f = io.BytesIO(b"file content")
    f.name = "solution.pdf"
    res = world.actor("student").post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "FILE", "file": f},
        format="multipart",
    )
    assert res.status_code == 201


def test_br_029_submission_conforms_to_text_type(world):
    """TEST-BR-029 | BR-LMS-012 condition-true-text."""
    row = available(world, submission_type="TEXT")
    res = world.actor("student").post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "TEXT", "text": "Valid text answer"},
        format="json",
    )
    assert res.status_code == 201


def test_br_030_submission_conforms_to_link_type(world):
    """TEST-BR-030 | BR-LMS-012 condition-true-link."""
    row = available(world, submission_type="LINK")
    res = world.actor("student").post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "LINK", "url": "https://github.com/project/repo"},
        format="json",
    )
    assert res.status_code == 201


def test_br_031_submission_type_mismatch_rejected(world):
    """TEST-BR-031 | BR-LMS-012 condition-false-mismatch."""
    row = available(world, submission_type="FILE")
    # Submitting TEXT when FILE is required
    res = world.actor("student").post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "TEXT", "text": "Wrong type"},
        format="json",
    )
    assert res.status_code in (400, 422)


def test_br_032_baseline_on_time_submission(world):
    """TEST-BR-032 | BR-LMS-013 condition-true-on-time."""
    row = available(world)
    with freeze_time(world.due - timedelta(hours=2)):
        sub = submit(world, row, text="On time work")
        assert sub["id"]


def test_br_033_student_views_own_submission(world):
    """TEST-BR-033 | BR-LMS-014 condition-true-own-submission."""
    row = available(world)
    sub = submit(world, row, text="My own submission")
    res = world.actor("student").get(f"{BASE}/submissions/{sub['id']}/")
    assert res.status_code == 200
    assert res.json()["text"] == "My own submission"


def test_br_034_student_cannot_view_other_submission(world):
    """TEST-BR-034 | BR-LMS-014 condition-false-other-submission."""
    row = available(world)
    sub = submit(world, row)

    # User 999 attempting to view user 2's submission
    res = world.actor("student", uid=999).get(f"{BASE}/submissions/{sub['id']}/")
    assert res.status_code in (403, 404)


def test_br_035_faculty_grading_attribution(world):
    """TEST-BR-035 | BR-LMS-015 condition-true-faculty-attribution."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "19.00", "feedback": "Faculty attribution test"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["grader_user_id"] == 1


def test_br_036_ta_grading_attribution(world):
    """TEST-BR-036 | BR-LMS-015 condition-true-ta-attribution."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("lms_ta").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "14.50", "feedback": "TA attribution test"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["grader_user_id"] == 3


def test_br_037_unauthorized_user_cannot_grade(world):
    """TEST-BR-037 | BR-LMS-015 condition-false-unauthorized."""
    row = available(world)
    sub = submit(world, row)
    res = world.actor("student").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "20.00", "feedback": "Self grading"},
        format="json",
    )
    assert res.status_code == 403


def test_br_038_conflict_of_interest_self_grading_rejected(world):
    """TEST-BR-038 | BR-LMS-015 condition-false-self-grading."""
    row = available(world)
    # TA submits as student with user_id=3
    sub = world.actor("student", uid=3).post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "TEXT", "text": "TA student submission"},
        format="json",
    ).json()

    # TA attempts to grade own submission -> Refused
    res = world.actor("lms_ta", uid=3).post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "20.00", "feedback": "Attempt self grading"},
        format="json",
    )
    assert res.status_code in (403, 422)


def test_br_039_draft_grade_hidden_from_student(world):
    """TEST-BR-039 | BR-LMS-016 condition-true-draft-hidden."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "16.00", "feedback": "Secret draft feedback"},
        format="json",
    )

    grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grades) == 0


def test_br_040_released_grade_visible_to_student(world):
    """TEST-BR-040 | BR-LMS-016 condition-true-released-visible."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "17.00", "feedback": "Released feedback"},
        format="json",
    )
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grades) == 1
    assert grades[0]["feedback"] == "Released feedback"


def test_br_041_faculty_grade_release_allowed(world):
    """TEST-BR-041 | BR-LMS-017 condition-true-faculty."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "12.00"}, format="json")
    res = world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")
    assert res.status_code == 200
    assert res.json()["state"] == "RELEASED"


def test_br_042_ta_grade_release_prohibited(world):
    """TEST-BR-042 | BR-LMS-017 condition-false-ta."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "12.00"}, format="json")
    res = world.actor("lms_ta").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")
    assert res.status_code == 403


def test_br_043_released_grade_read_only_to_student(world):
    """TEST-BR-043 | BR-LMS-018 condition-true-read-only."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "18.00"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    res = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/")
    assert res.status_code == 200
    assert res.json()["results"][0]["points"] == "18.00"


def test_br_044_student_cannot_modify_grade(world):
    """TEST-BR-044 | BR-LMS-018 condition-false-no-student-write."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "18.00"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    res = world.actor("student").patch(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "20.00"},
        format="json",
    )
    assert res.status_code == 403
    assert Grade.objects.get().points == Decimal("18.00")


def test_br_045_post_release_grade_change_audit(world):
    """TEST-BR-045 | BR-LMS-019 condition-true-audit-record."""
    row = available(world)
    sub = submit(world, row)
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/", {"points": "15.00", "feedback": "Original"}, format="json")
    world.actor("faculty").post(f"{BASE}/submissions/{sub['id']}/grade/release/", {}, format="json")

    res = world.actor("faculty").patch(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "19.00", "feedback": "Upgraded"},
        format="json",
    )
    assert res.status_code == 200
    audit = GradeAuditLog.objects.latest("pk")
    assert audit.old_points == Decimal("15.00")
    assert audit.new_points == Decimal("19.00")
    assert audit.actor_user_id == 1
