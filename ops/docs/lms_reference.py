#!/usr/bin/env python
"""Teaching reference script for LMS (Course Management).

Maps every live BR, UC, and Workflow ID to the file and function that decides it.
Runs cleanly in CI and review checks: `python ops/docs/lms_reference.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LMS_REFERENCE_MAP = {
    # Business Rules (BR-LMS-001 through 019)
    "BR-LMS-001": (
        "modules/lms/selectors/scoping.py",
        "scope_courses_for_user",
        "Course-specific access control",
    ),
    "BR-LMS-002": (
        "modules/lms/selectors/courses.py",
        "get_user_memberships",
        "Student registration governs access",
    ),
    "BR-LMS-003": (
        "modules/lms/domain/rules.py",
        "validate_observer_restriction",
        "Observer read-only & privacy",
    ),
    "BR-LMS-004": (
        "modules/lms/domain/rules.py",
        "validate_ta_permission",
        "TA authoring restriction",
    ),
    "BR-LMS-005": (
        "modules/lms/domain/rules.py",
        "validate_material_visibility",
        "Published material visibility",
    ),
    "BR-LMS-006": (
        "modules/lms/services/courses.py",
        "release_scheduled_items",
        "Scheduled material release",
    ),
    "BR-LMS-007": (
        "modules/lms/domain/rules.py",
        "validate_ta_permission",
        "Announcement authority",
    ),
    "BR-LMS-008": (
        "modules/lms/models/announcements.py",
        "CourseAnnouncement",
        "Announcement timestamp & audience",
    ),
    "BR-LMS-009": (
        "modules/lms/domain/rules.py",
        "validate_assignment_configuration",
        "Assignment required config",
    ),
    "BR-LMS-010": (
        "modules/lms/domain/state_machine.py",
        "validate_assignment_transition",
        "Assignment draft-before-pub",
    ),
    "BR-LMS-011": (
        "modules/lms/domain/rules.py",
        "validate_material_visibility",
        "Assignment release visibility",
    ),
    "BR-LMS-012": (
        "modules/lms/domain/rules.py",
        "validate_submission_type",
        "Submission type conformity",
    ),
    "BR-LMS-013": (
        "modules/lms/domain/rules.py",
        "evaluate_submission_timeliness",
        "Baseline on-time submission",
    ),
    "BR-LMS-014": (
        "modules/lms/selectors/scoping.py",
        "scope_submissions_for_user",
        "Submission privacy",
    ),
    "BR-LMS-015": (
        "modules/lms/services/courses.py",
        "grade_submission",
        "Grading authority and attribution",
    ),
    "BR-LMS-016": (
        "modules/lms/selectors/courses.py",
        "get_student_course_grades",
        "Draft grade visibility",
    ),
    "BR-LMS-017": (
        "modules/lms/domain/rules.py",
        "validate_grade_release_authority",
        "Grade release authority",
    ),
    "BR-LMS-018": (
        "modules/lms/domain/rules.py",
        "validate_grade_visibility_for_student",
        "Released grade read-only",
    ),
    "BR-LMS-019": (
        "modules/lms/services/courses.py",
        "modify_released_grade",
        "Post-release grade audit",
    ),
    # Use Cases (UC-LMS-001 through 015)
    "UC-LMS-001": ("modules/lms/api/views.py", "CourseDetailView", "Access Course Workspace"),
    "UC-LMS-002": ("modules/lms/api/views.py", "CourseDetailView", "Manage Course Details"),
    "UC-LMS-003": (
        "modules/lms/services/courses.py",
        "upload_course_material",
        "Manage Course Materials",
    ),
    "UC-LMS-004": (
        "modules/lms/selectors/courses.py",
        "get_course_materials",
        "View Published Course Materials",
    ),
    "UC-LMS-005": (
        "modules/lms/services/courses.py",
        "post_course_announcement",
        "Post Course Announcement",
    ),
    "UC-LMS-006": (
        "modules/lms/selectors/courses.py",
        "get_course_announcements",
        "View Course Announcements",
    ),
    "UC-LMS-007": (
        "modules/lms/services/courses.py",
        "create_assignment",
        "Create or Edit Assignment",
    ),
    "UC-LMS-008": ("modules/lms/services/courses.py", "publish_assignment", "Publish Assignment"),
    "UC-LMS-009": (
        "modules/lms/selectors/courses.py",
        "get_course_assignments",
        "View/Download Published Assignment",
    ),
    "UC-LMS-010": ("modules/lms/services/courses.py", "submit_assignment", "Submit Assignment"),
    "UC-LMS-011": (
        "modules/lms/selectors/courses.py",
        "get_assignment_submissions",
        "View Submission History & Status",
    ),
    "UC-LMS-012": ("modules/lms/services/courses.py", "grade_submission", "Grade Submission"),
    "UC-LMS-013": (
        "modules/lms/services/courses.py",
        "release_assignment_grades",
        "Release Grades and Feedback",
    ),
    "UC-LMS-014": (
        "modules/lms/selectors/courses.py",
        "get_student_course_grades",
        "View Released Grade & Feedback",
    ),
    "UC-LMS-015": (
        "modules/lms/tasks.py",
        "publish_scheduled_content",
        "Process Scheduled Content Release",
    ),
    # Workflows
    "BW-LMS-01": (
        "modules/lms/tasks.py",
        "publish_scheduled_content",
        "Scheduled Course Material Release",
    ),
    "BW-LMS-02": (
        "modules/lms/services/courses.py",
        "publish_assignment",
        "Assignment Immediate Release & On-Time",
    ),
    "BW-LMS-03": (
        "modules/lms/services/courses.py",
        "publish_assignment",
        "Assignment Scheduled Release & On-Time",
    ),
    "BW-LMS-04": (
        "modules/lms/services/courses.py",
        "grade_submission",
        "Faculty Grading and Grade Release",
    ),
    "BW-LMS-05": (
        "modules/lms/services/courses.py",
        "grade_submission",
        "TA Grading and Faculty Grade Release",
    ),
    "CW-LMS-01": (
        "modules/lms/domain/state_machine.py",
        "validate_assignment_transition",
        "Assignment Publication & Submission",
    ),
    "CW-LMS-02": (
        "modules/lms/domain/state_machine.py",
        "validate_grade_transition",
        "Grading and Grade Release",
    ),
}


def main() -> int:
    missing = 0
    for req_id, (rel_path, target, _desc) in sorted(LMS_REFERENCE_MAP.items()):
        full_path = ROOT / rel_path
        if not full_path.exists():
            print(f"MISSING FILE: {rel_path} for {req_id}", file=sys.stderr)
            missing += 1
            continue
        content = full_path.read_text(encoding="utf-8")
        if target not in content:
            print(f"MISSING TARGET: {target} in {rel_path} for {req_id}", file=sys.stderr)
            missing += 1
            continue

    if missing > 0:
        print(f"LMS reference check failed with {missing} errors.", file=sys.stderr)
        return 1

    count = len(LMS_REFERENCE_MAP)
    print(f"LMS teaching reference verified: all {count} specifications trace to code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
