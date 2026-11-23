"""Automated specification tests for LMS Workflows (BW-LMS-01..05, CW-LMS-01..02).

Derived strictly from WF_DESIGN.json.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.lms.models import Grade, GradeAuditLog, Material, Submission
from modules.lms.tasks import release_due_assignments, release_due_materials
from modules.lms.tests.conftest import available, draft, submit

pytestmark = pytest.mark.django_db
BASE = "/api/v1/lms"


def test_wf_001_bw_lms_01_step_1_faculty_schedules_material(world):
    """TEST-WF-001 | BW-LMS-01 Step 1 Faculty Schedules Material."""
    staff = world.actor("faculty")
    item = staff.post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Scheduled Lecture Notes"},
        format="json",
    )
    assert item.status_code == 201
    mat_id = item.json()["id"]

    future_time = timezone.now() + timedelta(days=2)
    pub = staff.post(
        f"{BASE}/materials/{mat_id}/publish/",
        {"release_at": future_time.isoformat()},
        format="json",
    )
    assert pub.status_code == 200
    assert pub.json()["state"] == "SCHEDULED"

    # Material remains inaccessible to students
    student = world.actor("student")
    assert student.get(f"{BASE}/materials/{mat_id}/").status_code == 404


def test_wf_002_bw_lms_01_step_2_system_releases_scheduled_material(world):
    """TEST-WF-002 | BW-LMS-01 Step 2 System Releases Scheduled Material."""
    staff = world.actor("faculty")
    item = staff.post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Soon to release material"},
        format="json",
    )
    mat_id = item.json()["id"]
    target_time = timezone.now() + timedelta(hours=1)
    staff.post(
        f"{BASE}/materials/{mat_id}/publish/",
        {"release_at": target_time.isoformat()},
        format="json",
    )

    # Time advances past release_at
    with freeze_time(target_time + timedelta(seconds=10)):
        released_count = release_due_materials()
        assert released_count >= 1

    mat = Material.objects.get(pk=mat_id)
    assert mat.state == "PUBLISHED"

    # Now accessible to students
    student = world.actor("student")
    res = student.get(f"{BASE}/materials/{mat_id}/")
    assert res.status_code == 200
    assert res.json()["text"] == "Soon to release material"


def test_wf_003_bw_lms_02_step_1_faculty_creates_assignment_draft(world):
    """TEST-WF-003 | BW-LMS-02 Step 1 Faculty Creates Assignment Draft."""
    row = draft(world, title="Assignment 1")
    assert row["state"] == "DRAFT"

    # Must not be visible or submittable by student
    student = world.actor("student")
    assert student.get(f"{BASE}/assignments/{row['id']}/").status_code == 404


def test_wf_004_bw_lms_02_step_2_faculty_publishes_assignment_immediately(world):
    """TEST-WF-004 | BW-LMS-02 Step 2 Faculty Publishes Assignment Immediately."""
    row = draft(world, title="Assignment 2")
    pub = world.actor("faculty").post(
        f"{BASE}/assignments/{row['id']}/publish/",
        {},
        format="json",
    )
    assert pub.status_code == 200
    assert pub.json()["state"] == "AVAILABLE"

    # Student can view assignment
    student = world.actor("student")
    res = student.get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code == 200


def test_wf_005_bw_lms_02_step_3_student_submits_assignment_on_time(world):
    """TEST-WF-005 | BW-LMS-02 Step 3 Student Submits Assignment On-Time."""
    row = available(world, title="Assignment 3")
    sub = submit(world, row, text="My completed assignment solution")
    assert sub["id"]
    assert sub["user_id"] == 2
    assert Submission.objects.filter(pk=sub["id"]).exists()


def test_wf_006_bw_lms_03_step_1_faculty_creates_assignment_draft(world):
    """TEST-WF-006 | BW-LMS-03 Step 1 Faculty Creates Assignment Draft."""
    row = draft(world, title="Assignment 4 Scheduled")
    assert row["state"] == "DRAFT"
    assert row["id"]


def test_wf_007_bw_lms_03_step_2_faculty_publishes_assignment_as_scheduled(world):
    """TEST-WF-007 | BW-LMS-03 Step 2 Faculty Publishes Assignment as Scheduled."""
    row = draft(world, title="Assignment 5")
    release_time = timezone.now() + timedelta(days=1)
    pub = world.actor("faculty").post(
        f"{BASE}/assignments/{row['id']}/publish/",
        {"release_at": release_time.isoformat()},
        format="json",
    )
    assert pub.status_code == 200
    assert pub.json()["state"] == "SCHEDULED"

    # Inaccessible to student
    student = world.actor("student")
    assert student.get(f"{BASE}/assignments/{row['id']}/").status_code == 404


def test_wf_008_bw_lms_03_step_3_system_transitions_scheduled_to_available(world):
    """TEST-WF-008 | BW-LMS-03 Step 3 System Transitions Scheduled to Available."""
    row = draft(world, title="Assignment 6")
    release_time = timezone.now() + timedelta(hours=2)
    world.actor("faculty").post(
        f"{BASE}/assignments/{row['id']}/publish/",
        {"release_at": release_time.isoformat()},
        format="json",
    )

    with freeze_time(release_time + timedelta(minutes=5)):
        count = release_due_assignments()
        assert count >= 1

    student = world.actor("student")
    res = student.get(f"{BASE}/assignments/{row['id']}/")
    assert res.status_code == 200
    assert res.json()["state"] == "AVAILABLE"


def test_wf_009_bw_lms_03_step_4_student_submits_to_released_assignment_on_time(world):
    """TEST-WF-009 | BW-LMS-03 Step 4 Student Submits to Released Assignment On-Time."""
    row = draft(world, title="Assignment 7")
    release_time = timezone.now() + timedelta(hours=1)
    world.actor("faculty").post(
        f"{BASE}/assignments/{row['id']}/publish/",
        {"release_at": release_time.isoformat()},
        format="json",
    )

    with freeze_time(release_time + timedelta(minutes=1)):
        release_due_assignments()
        sub = submit(world, row, text="Submission to scheduled assignment")
        assert sub["id"]


def test_wf_010_bw_lms_04_step_1_faculty_grades_recorded_submission(world):
    """TEST-WF-010 | BW-LMS-04 Step 1 Faculty Grades Recorded Submission."""
    row = available(world)
    submission = submit(world, row)

    res = world.actor("faculty").post(
        f"{BASE}/submissions/{submission['id']}/grade/",
        {"points": "18.00", "feedback": "Faculty draft feedback"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "DRAFT"
    assert res.json()["grader_user_id"] == 1

    # Student cannot see draft grade
    student = world.actor("student")
    grade_list = student.get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grade_list) == 0


def test_wf_011_bw_lms_04_step_2_faculty_releases_grade_and_feedback(world):
    """TEST-WF-011 | BW-LMS-04 Step 2 Faculty Releases Grade and Feedback."""
    row = available(world)
    submission = submit(world, row)
    world.actor("faculty").post(
        f"{BASE}/submissions/{submission['id']}/grade/",
        {"points": "19.00", "feedback": "Excellent work"},
        format="json",
    )

    rel = world.actor("faculty").post(
        f"{BASE}/submissions/{submission['id']}/grade/release/",
        {},
        format="json",
    )
    assert rel.status_code == 200
    assert rel.json()["state"] == "RELEASED"

    # Student can now see the released grade
    student = world.actor("student")
    grades = student.get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grades) == 1
    assert grades[0]["points"] == "19.00"
    assert grades[0]["feedback"] == "Excellent work"


def test_wf_012_bw_lms_05_step_1_ta_grades_recorded_submission(world):
    """TEST-WF-012 | BW-LMS-05 Step 1 TA Grades Recorded Submission."""
    row = available(world)
    submission = submit(world, row)

    res = world.actor("lms_ta").post(
        f"{BASE}/submissions/{submission['id']}/grade/",
        {"points": "16.00", "feedback": "TA draft review"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["state"] == "DRAFT"
    assert res.json()["grader_user_id"] == 3

    # Student cannot see draft grade
    student = world.actor("student")
    assert len(student.get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]) == 0


def test_wf_013_bw_lms_05_step_2_faculty_releases_ta_draft_grade(world):
    """TEST-WF-013 | BW-LMS-05 Step 2 Faculty Releases TA Draft Grade."""
    row = available(world)
    submission = submit(world, row)

    # TA grades
    world.actor("lms_ta").post(
        f"{BASE}/submissions/{submission['id']}/grade/",
        {"points": "17.00", "feedback": "Good effort"},
        format="json",
    )

    # Faculty releases
    rel = world.actor("faculty").post(
        f"{BASE}/submissions/{submission['id']}/grade/release/",
        {},
        format="json",
    )
    assert rel.status_code == 200
    assert rel.json()["state"] == "RELEASED"

    # Student sees released grade
    grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(grades) == 1
    assert grades[0]["points"] == "17.00"


def test_wf_014_cw_lms_01_immediate_release_full_lifecycle(world):
    """TEST-WF-014 | CW-LMS-01 Immediate Release Full Lifecycle."""
    # Step 1: Draft
    row = draft(world, title="CW-01 Immediate Assignment")
    assert row["state"] == "DRAFT"

    # Step 2: Publish immediately
    pub = world.actor("faculty").post(f"{BASE}/assignments/{row['id']}/publish/", {}, format="json")
    assert pub.status_code == 200
    assert pub.json()["state"] == "AVAILABLE"

    # Step 3: Student submits
    sub = submit(world, pub.json(), text="Complete CW-01 solution")
    assert sub["id"]
    assert Submission.objects.get(pk=sub["id"]).user_id == 2


def test_wf_015_cw_lms_01_scheduled_release_full_lifecycle(world):
    """TEST-WF-015 | CW-LMS-01 Scheduled Release Full Lifecycle."""
    # Step 1: Draft
    row = draft(world, title="CW-01 Scheduled Assignment")
    release_time = timezone.now() + timedelta(hours=3)

    # Step 2: Publish with schedule
    pub = world.actor("faculty").post(
        f"{BASE}/assignments/{row['id']}/publish/",
        {"release_at": release_time.isoformat()},
        format="json",
    )
    assert pub.status_code == 200
    assert pub.json()["state"] == "SCHEDULED"

    # Step 3: Release task triggers
    with freeze_time(release_time + timedelta(seconds=30)):
        release_due_assignments()

        # Step 4: Student submits
        sub = submit(world, row, text="CW-01 scheduled solution")
        assert sub["id"]


def test_wf_016_cw_lms_02_faculty_grading_and_release_lifecycle(world):
    """TEST-WF-016 | CW-LMS-02 Faculty Grading and Release Lifecycle."""
    row = available(world)
    sub = submit(world, row)

    # Faculty grades (DRAFT)
    g = world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "19.50", "feedback": "Solid implementation"},
        format="json",
    )
    assert g.status_code == 200
    assert g.json()["state"] == "DRAFT"

    # Faculty releases (RELEASED)
    rel = world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/release/",
        {},
        format="json",
    )
    assert rel.status_code == 200
    assert rel.json()["state"] == "RELEASED"

    # Student views released grade
    student_grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(student_grades) == 1
    assert student_grades[0]["points"] == "19.50"


def test_wf_017_cw_lms_02_ta_grading_and_faculty_release_lifecycle(world):
    """TEST-WF-017 | CW-LMS-02 TA Grading and Faculty Release Lifecycle."""
    row = available(world)
    sub = submit(world, row)

    # TA grades (DRAFT)
    g = world.actor("lms_ta").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "15.00", "feedback": "Checked by TA"},
        format="json",
    )
    assert g.status_code == 200
    assert g.json()["state"] == "DRAFT"

    # Faculty releases (RELEASED)
    rel = world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/release/",
        {},
        format="json",
    )
    assert rel.status_code == 200
    assert rel.json()["state"] == "RELEASED"

    # Student views released grade
    student_grades = world.actor("student").get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"]
    assert len(student_grades) == 1
    assert student_grades[0]["points"] == "15.00"


def test_wf_018_bw_lms_02_invalid_transition_draft_submission_refused(world):
    """TEST-WF-018 | BW-LMS-02 Invalid Transition Draft Submission Refused."""
    row = draft(world, title="Draft only assignment")

    # Student attempts to submit to Draft assignment
    res = world.actor("student").post(
        f"{BASE}/assignments/{row['id']}/submissions/",
        {"kind": "TEXT", "text": "Premature submission"},
        format="json",
    )
    assert res.status_code in (400, 403, 404, 409, 422)
    assert Submission.objects.count() == 0


def test_wf_019_bw_lms_05_guard_check_ta_release_refused(world):
    """TEST-WF-019 | BW-LMS-05 Guard Check TA Release Refused."""
    row = available(world)
    sub = submit(world, row)

    world.actor("lms_ta").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "14.00", "feedback": "TA draft"},
        format="json",
    )

    # TA attempts to release grades -> Refused (403)
    res = world.actor("lms_ta").post(
        f"{BASE}/submissions/{sub['id']}/grade/release/",
        {},
        format="json",
    )
    assert res.status_code == 403
    assert Grade.objects.get().state == "DRAFT"


def test_wf_020_bw_lms_04_post_release_grade_modification_audit_transition(world):
    """TEST-WF-020 | BW-LMS-04 Post-Release Grade Modification Audit Transition."""
    row = available(world)
    sub = submit(world, row)

    # Faculty grades and releases
    world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "15.00", "feedback": "Initial release"},
        format="json",
    )
    world.actor("faculty").post(
        f"{BASE}/submissions/{sub['id']}/grade/release/",
        {},
        format="json",
    )

    # Faculty modifies already released grade
    mod = world.actor("faculty").patch(
        f"{BASE}/submissions/{sub['id']}/grade/",
        {"points": "18.00", "feedback": "Revised after regrade request"},
        format="json",
    )
    assert mod.status_code == 200
    assert mod.json()["state"] == "RELEASED"
    assert mod.json()["points"] == "18.00"

    # Audit log entry must exist
    audit = GradeAuditLog.objects.latest("pk")
    assert audit.old_points == Decimal("15.00")
    assert audit.new_points == Decimal("18.00")
    assert audit.actor_user_id == 1
