#!/usr/bin/env python
"""Generate the LMS requirements traceability and code reference document.

Maps all 15 CFRs, 47 AFRs, 15 UCs, 19 BRs, and 7 WFs to exact source file and line
locations in `modules/lms/`. Exits non-zero if any requirement cannot be resolved.

Usage:
    python ops/docs/lms_reference.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_ROOT = ROOT / "modules" / "lms"
DOCS_OUT = ROOT / "docs" / "03-lms" / "lms-reference.md"

CFRS = [
    {
        "id": "CFR-LMS-001",
        "description": (
            "Dedicated course workspace access and course home display for authorized users"
        ),
        "layer": "selectors",
        "file": "selectors/workspace.py",
        "anchor": "def get_course_home_details",
    },
    {
        "id": "CFR-LMS-002",
        "description": "Configure assigned course workspace details and edit metadata",
        "layer": "services",
        "file": "services/workspace.py",
        "anchor": "def update_course_details",
    },
    {
        "id": "CFR-LMS-003",
        "description": "Manage and schedule course materials (files, links, notes)",
        "layer": "services",
        "file": "services/materials.py",
        "anchor": "def create_material",
    },
    {
        "id": "CFR-LMS-004",
        "description": "Read-only access to published course materials for authorized users",
        "layer": "selectors",
        "file": "selectors/materials.py",
        "anchor": "def list_published_materials",
    },
    {
        "id": "CFR-LMS-005",
        "description": "Post and view course-wide announcements",
        "layer": "services",
        "file": "services/announcements.py",
        "anchor": "def post_announcement",
    },
    {
        "id": "CFR-LMS-006",
        "description": "Create and edit assignments in Draft state",
        "layer": "services",
        "file": "services/assignments.py",
        "anchor": "def create_assignment",
    },
    {
        "id": "CFR-LMS-007",
        "description": "Publish assignments and control release visibility",
        "layer": "services",
        "file": "services/assignments.py",
        "anchor": "def publish_assignment",
    },
    {
        "id": "CFR-LMS-008",
        "description": "Assignment submission handling (file, text, link)",
        "layer": "services",
        "file": "services/submissions.py",
        "anchor": "def submit_assignment",
    },
    {
        "id": "CFR-LMS-009",
        "description": "Student submission status and history tracking",
        "layer": "selectors",
        "file": "selectors/submissions.py",
        "anchor": "def get_submission_by_id",
    },
    {
        "id": "CFR-LMS-010",
        "description": "Grading student submissions with points and feedback",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def grade_submission",
    },
    {
        "id": "CFR-LMS-011",
        "description": "Two-phase grade release workflow (Draft -> Published)",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def publish_grades",
    },
    {
        "id": "CFR-LMS-012",
        "description": "Student access to released grade and feedback",
        "layer": "selectors",
        "file": "selectors/grading.py",
        "anchor": "def get_submission_grade",
    },
    {
        "id": "CFR-LMS-013",
        "description": "Audit logging of post-release grade changes",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def update_grade",
    },
    {
        "id": "CFR-LMS-014",
        "description": "Teaching Assistant authority boundaries",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_grade_submission",
    },
    {
        "id": "CFR-LMS-015",
        "description": "Observer read-only isolation and student-data privacy",
        "layer": "selectors",
        "file": "selectors/scoping.py",
        "anchor": "def is_course_observer",
    },
]

AFRS = [
    {
        "id": "AFR-LMS-001.1",
        "description": "Open dedicated course workspace when selecting authorized course",
        "layer": "api",
        "file": "api/views.py",
        "anchor": "class CourseWorkspaceDetailView",
    },
    {
        "id": "AFR-LMS-001.2",
        "description": "Display course syllabus, schedule, instructors, and TAs on course home",
        "layer": "selectors",
        "file": "selectors/workspace.py",
        "anchor": "def get_course_home_details",
    },
    {
        "id": "AFR-LMS-001.3",
        "description": "Restrict course workspace access strictly to authorized/enrolled users",
        "layer": "selectors",
        "file": "selectors/scoping.py",
        "anchor": "def get_user_courses_queryset",
    },
    {
        "id": "AFR-LMS-002.1",
        "description": "Allow Faculty to configure course workspace settings",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_update_course_details",
    },
    {
        "id": "AFR-LMS-002.2",
        "description": "Allow Faculty to publish and edit course details (syllabus, schedule)",
        "layer": "services",
        "file": "services/workspace.py",
        "anchor": "def update_course_details",
    },
    {
        "id": "AFR-LMS-003.1",
        "description": "Allow Faculty to add materials as files, links, or notes",
        "layer": "domain",
        "file": "domain/validators.py",
        "anchor": "def validate_material_payload",
    },
    {
        "id": "AFR-LMS-003.2",
        "description": "Organize materials into modules or weekly sections",
        "layer": "models",
        "file": "models/materials.py",
        "anchor": "section_name = models.CharField",
    },
    {
        "id": "AFR-LMS-003.3",
        "description": "Configure future release date/time for course materials",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def validate_release_date",
    },
    {
        "id": "AFR-LMS-003.4",
        "description": "Automatically make scheduled material visible when release time is reached",
        "layer": "tasks",
        "file": "tasks.py",
        "anchor": "def process_scheduled_content_release",
    },
    {
        "id": "AFR-LMS-004.1",
        "description": "Students view published course materials in read-only form",
        "layer": "selectors",
        "file": "selectors/materials.py",
        "anchor": "def list_published_materials",
    },
    {
        "id": "AFR-LMS-004.2",
        "description": "TAs view published course materials in read-only form",
        "layer": "selectors",
        "file": "selectors/materials.py",
        "anchor": "def list_published_materials",
    },
    {
        "id": "AFR-LMS-004.3",
        "description": "Observers view published course materials in read-only form",
        "layer": "selectors",
        "file": "selectors/materials.py",
        "anchor": "def list_published_materials",
    },
    {
        "id": "AFR-LMS-005.1",
        "description": "Faculty post course-wide announcements",
        "layer": "services",
        "file": "services/announcements.py",
        "anchor": "def post_announcement",
    },
    {
        "id": "AFR-LMS-005.2",
        "description": "Permitted TAs post announcements when authorized",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_post_announcement",
    },
    {
        "id": "AFR-LMS-005.3",
        "description": "Automatically timestamp posted announcements",
        "layer": "models",
        "file": "models/announcements.py",
        "anchor": "created_at = models.DateTimeField(auto_now_add=True)",
    },
    {
        "id": "AFR-LMS-005.4",
        "description": "Make announcements visible course-wide to enrolled/linked users",
        "layer": "selectors",
        "file": "selectors/announcements.py",
        "anchor": "def list_announcements",
    },
    {
        "id": "AFR-LMS-006.1",
        "description": "Faculty create assignments for assigned courses",
        "layer": "services",
        "file": "services/assignments.py",
        "anchor": "def create_assignment",
    },
    {
        "id": "AFR-LMS-006.2",
        "description": (
            "Capture required assignment configuration (due date, instructions, points, type)"
        ),
        "layer": "domain",
        "file": "domain/validators.py",
        "anchor": "def validate_assignment_config",
    },
    {
        "id": "AFR-LMS-006.3",
        "description": "Allow Faculty to edit assignment details",
        "layer": "services",
        "file": "services/assignments.py",
        "anchor": "def update_assignment",
    },
    {
        "id": "AFR-LMS-006.4",
        "description": "Maintain assignment in Draft state before explicit publication",
        "layer": "domain",
        "file": "domain/state_machine.py",
        "anchor": "ASSIGNMENT_TRANSITIONS: tuple[Transition, ...]",
    },
    {
        "id": "AFR-LMS-007.1",
        "description": "Faculty publish draft assignments",
        "layer": "services",
        "file": "services/assignments.py",
        "anchor": "def publish_assignment",
    },
    {
        "id": "AFR-LMS-007.2",
        "description": "Apply release-date visibility control",
        "layer": "selectors",
        "file": "selectors/assignments.py",
        "anchor": "def list_assignments",
    },
    {
        "id": "AFR-LMS-007.3",
        "description": "Release scheduled assignment when release time is reached",
        "layer": "tasks",
        "file": "tasks.py",
        "anchor": "asg_count = Assignment.objects.filter",
    },
    {
        "id": "AFR-LMS-007.4",
        "description": "Students view and download assignment instructions once released",
        "layer": "selectors",
        "file": "selectors/assignments.py",
        "anchor": "def get_assignment_detail",
    },
    {
        "id": "AFR-LMS-008.1",
        "description": "Submit work conforming to configured submission type (file/text/link)",
        "layer": "domain",
        "file": "domain/validators.py",
        "anchor": "def validate_submission_payload",
    },
    {
        "id": "AFR-LMS-008.2",
        "description": "Record and timestamp baseline on-time submission",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def is_submission_ontime",
    },
    {
        "id": "AFR-LMS-009.1",
        "description": "Student views own submission history",
        "layer": "selectors",
        "file": "selectors/submissions.py",
        "anchor": "def list_course_submissions",
    },
    {
        "id": "AFR-LMS-009.2",
        "description": "Student views own submission status (submitted, late, missing)",
        "layer": "domain",
        "file": "domain/calculations.py",
        "anchor": "def compute_submission_status",
    },
    {
        "id": "AFR-LMS-010.1",
        "description": "Faculty grades individual student submissions",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def grade_submission",
    },
    {
        "id": "AFR-LMS-010.2",
        "description": "TA grades student submissions for assigned course",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_grade_submission",
    },
    {
        "id": "AFR-LMS-010.3",
        "description": "Accurately attribute all grading actions to acting user",
        "layer": "models",
        "file": "models/grading.py",
        "anchor": "graded_by = models.IntegerField",
    },
    {
        "id": "AFR-LMS-011.1",
        "description": "Hold grades in Draft state upon grading",
        "layer": "domain",
        "file": "domain/state_machine.py",
        "anchor": "GRADE_TRANSITIONS: tuple[Transition, ...]",
    },
    {
        "id": "AFR-LMS-011.2",
        "description": "Prevent students from viewing unreleased draft grades",
        "layer": "selectors",
        "file": "selectors/grading.py",
        "anchor": "def get_submission_grade",
    },
    {
        "id": "AFR-LMS-011.3",
        "description": "Allow Faculty to release grades and feedback to students",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def publish_grades",
    },
    {
        "id": "AFR-LMS-012.1",
        "description": "Student views own released grade and feedback",
        "layer": "selectors",
        "file": "selectors/grading.py",
        "anchor": "def get_submission_grade",
    },
    {
        "id": "AFR-LMS-012.2",
        "description": "Released grade is strictly read-only to Student",
        "layer": "api",
        "file": "api/views.py",
        "anchor": "class SubmissionGradeDetailView",
    },
    {
        "id": "AFR-LMS-013.1",
        "description": "Record actor identity on post-release grade modification",
        "layer": "models",
        "file": "models/grading.py",
        "anchor": "changed_by = models.IntegerField",
    },
    {
        "id": "AFR-LMS-013.2",
        "description": "Record exact timestamp of post-release grade modification",
        "layer": "models",
        "file": "models/grading.py",
        "anchor": "changed_at = models.DateTimeField(auto_now_add=True)",
    },
    {
        "id": "AFR-LMS-014.1",
        "description": "TA views course details, materials, and announcements",
        "layer": "selectors",
        "file": "selectors/scoping.py",
        "anchor": "def has_course_access",
    },
    {
        "id": "AFR-LMS-014.2",
        "description": "TA views student submissions for assigned course",
        "layer": "selectors",
        "file": "selectors/submissions.py",
        "anchor": "def list_course_submissions",
    },
    {
        "id": "AFR-LMS-014.3",
        "description": "TA cannot create, edit, or publish assignments",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_author_assignment",
    },
    {
        "id": "AFR-LMS-014.4",
        "description": "TA cannot create or edit course materials",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_author_material",
    },
    {
        "id": "AFR-LMS-014.5",
        "description": "TA cannot modify course structure or workspace settings",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_manage_workspace",
    },
    {
        "id": "AFR-LMS-015.1",
        "description": "Observer views course details, materials, announcements",
        "layer": "selectors",
        "file": "selectors/workspace.py",
        "anchor": "def get_course_home_details",
    },
    {
        "id": "AFR-LMS-015.2",
        "description": "Observer cannot view student submissions",
        "layer": "selectors",
        "file": "selectors/submissions.py",
        "anchor": "def list_course_submissions",
    },
    {
        "id": "AFR-LMS-015.3",
        "description": "Observer cannot view student grades or student-specific data",
        "layer": "selectors",
        "file": "selectors/grading.py",
        "anchor": "def list_course_grades",
    },
    {
        "id": "AFR-LMS-015.4",
        "description": "Observer has no write access anywhere in module",
        "layer": "api",
        "file": "api/permissions.py",
        "anchor": "class RequireLmsPermission",
    },
]

UCS = [
    {
        "id": "UC-LMS-001",
        "description": "Access Course Workspace",
        "layer": "api",
        "file": "api/views.py",
        "anchor": "class CourseWorkspaceDetailView",
    },
    {
        "id": "UC-LMS-002",
        "description": "Manage Course Details",
        "layer": "services",
        "file": "services/workspace.py",
        "anchor": "def update_course_details",
    },
    {
        "id": "UC-LMS-003",
        "description": "Manage Course Materials",
        "layer": "services",
        "file": "services/materials.py",
        "anchor": "def create_material",
    },
    {
        "id": "UC-LMS-004",
        "description": "View Published Course Materials",
        "layer": "selectors",
        "file": "selectors/materials.py",
        "anchor": "def list_published_materials",
    },
    {
        "id": "UC-LMS-005",
        "description": "Post Course Announcement",
        "layer": "services",
        "file": "services/announcements.py",
        "anchor": "def post_announcement",
    },
    {
        "id": "UC-LMS-006",
        "description": "View Course Announcements",
        "layer": "selectors",
        "file": "selectors/announcements.py",
        "anchor": "def list_announcements",
    },
    {
        "id": "UC-LMS-007",
        "description": "Create or Edit Assignment",
        "layer": "services",
        "file": "services/assignments.py",
        "anchor": "def create_assignment",
    },
    {
        "id": "UC-LMS-008",
        "description": "Publish Assignment",
        "layer": "services",
        "file": "services/assignments.py",
        "anchor": "def publish_assignment",
    },
    {
        "id": "UC-LMS-009",
        "description": "View or Download Published Assignment",
        "layer": "selectors",
        "file": "selectors/assignments.py",
        "anchor": "def get_assignment_detail",
    },
    {
        "id": "UC-LMS-010",
        "description": "Submit Assignment",
        "layer": "services",
        "file": "services/submissions.py",
        "anchor": "def submit_assignment",
    },
    {
        "id": "UC-LMS-011",
        "description": "View Submission History and Status",
        "layer": "selectors",
        "file": "selectors/submissions.py",
        "anchor": "def get_submission_by_id",
    },
    {
        "id": "UC-LMS-012",
        "description": "Grade Submission",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def grade_submission",
    },
    {
        "id": "UC-LMS-013",
        "description": "Release Grades and Feedback",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def publish_grades",
    },
    {
        "id": "UC-LMS-014",
        "description": "View Released Grade and Feedback",
        "layer": "selectors",
        "file": "selectors/grading.py",
        "anchor": "def get_submission_grade",
    },
    {
        "id": "UC-LMS-015",
        "description": "Process Scheduled Content Release",
        "layer": "tasks",
        "file": "tasks.py",
        "anchor": "def process_scheduled_content_release",
    },
]

BRS = [
    {
        "id": "BR-LMS-001",
        "description": "Course-specific access control",
        "layer": "selectors",
        "file": "selectors/scoping.py",
        "anchor": "def has_course_access",
    },
    {
        "id": "BR-LMS-002",
        "description": "Student registration data governs Student course access",
        "layer": "selectors",
        "file": "selectors/scoping.py",
        "anchor": "def is_student_enrolled",
    },
    {
        "id": "BR-LMS-003",
        "description": "Observer read-only and student-data restriction",
        "layer": "selectors",
        "file": "selectors/scoping.py",
        "anchor": "def is_course_observer",
    },
    {
        "id": "BR-LMS-004",
        "description": "TA authoring restriction",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_author_assignment",
    },
    {
        "id": "BR-LMS-005",
        "description": "Published material visibility",
        "layer": "selectors",
        "file": "selectors/materials.py",
        "anchor": "def list_published_materials",
    },
    {
        "id": "BR-LMS-006",
        "description": "Scheduled material release",
        "layer": "tasks",
        "file": "tasks.py",
        "anchor": "def process_scheduled_content_release",
    },
    {
        "id": "BR-LMS-007",
        "description": "Announcement posting authority",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_post_announcement",
    },
    {
        "id": "BR-LMS-008",
        "description": "Announcement timestamp and audience",
        "layer": "models",
        "file": "models/announcements.py",
        "anchor": "class CourseAnnouncement",
    },
    {
        "id": "BR-LMS-009",
        "description": "Assignment required configuration",
        "layer": "domain",
        "file": "domain/validators.py",
        "anchor": "def validate_assignment_config",
    },
    {
        "id": "BR-LMS-010",
        "description": "Assignment draft-before-publication",
        "layer": "domain",
        "file": "domain/state_machine.py",
        "anchor": "ASSIGNMENT_TRANSITIONS: tuple[Transition, ...]",
    },
    {
        "id": "BR-LMS-011",
        "description": "Assignment release-date visibility",
        "layer": "selectors",
        "file": "selectors/assignments.py",
        "anchor": "def list_assignments",
    },
    {
        "id": "BR-LMS-012",
        "description": "Submission-type conformity",
        "layer": "domain",
        "file": "domain/validators.py",
        "anchor": "def validate_submission_payload",
    },
    {
        "id": "BR-LMS-013",
        "description": "Baseline on-time submission",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def is_submission_ontime",
    },
    {
        "id": "BR-LMS-014",
        "description": "Submission ownership and privacy",
        "layer": "selectors",
        "file": "selectors/submissions.py",
        "anchor": "def list_course_submissions",
    },
    {
        "id": "BR-LMS-015",
        "description": "Grading authority and attribution",
        "layer": "models",
        "file": "models/grading.py",
        "anchor": "graded_by = models.IntegerField",
    },
    {
        "id": "BR-LMS-016",
        "description": "Draft grade visibility",
        "layer": "selectors",
        "file": "selectors/grading.py",
        "anchor": "def get_submission_grade",
    },
    {
        "id": "BR-LMS-017",
        "description": "Grade release authority",
        "layer": "domain",
        "file": "domain/rules.py",
        "anchor": "def can_release_grades",
    },
    {
        "id": "BR-LMS-018",
        "description": "Released grade read-only to Student",
        "layer": "api",
        "file": "api/views.py",
        "anchor": "class SubmissionGradeDetailView",
    },
    {
        "id": "BR-LMS-019",
        "description": "Post-release grade-change audit",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def update_grade",
    },
]

WORKFLOWS = [
    {
        "id": "BW-LMS-01",
        "description": "Scheduled Course Material Release",
        "layer": "domain",
        "file": "domain/state_machine.py",
        "anchor": "MATERIAL_TRANSITIONS: tuple[Transition, ...]",
    },
    {
        "id": "BW-LMS-02",
        "description": "Assignment Immediate Release and On-Time Submission",
        "layer": "domain",
        "file": "domain/state_machine.py",
        "anchor": "ASSIGNMENT_TRANSITIONS: tuple[Transition, ...]",
    },
    {
        "id": "BW-LMS-03",
        "description": "Assignment Scheduled Release and On-Time Submission",
        "layer": "tasks",
        "file": "tasks.py",
        "anchor": "def process_scheduled_content_release",
    },
    {
        "id": "BW-LMS-04",
        "description": "Faculty Grading and Grade Release",
        "layer": "domain",
        "file": "domain/state_machine.py",
        "anchor": "GRADE_TRANSITIONS: tuple[Transition, ...]",
    },
    {
        "id": "BW-LMS-05",
        "description": "TA Grading and Faculty Grade Release",
        "layer": "services",
        "file": "services/grading.py",
        "anchor": "def grade_submission",
    },
    {
        "id": "CW-LMS-01",
        "description": "Assignment Publication and Submission",
        "layer": "domain",
        "file": "domain/state_machine.py",
        "anchor": "def resolve_assignment_transition",
    },
    {
        "id": "CW-LMS-02",
        "description": "Grading and Grade Release",
        "layer": "domain",
        "file": "domain/state_machine.py",
        "anchor": "def resolve_grade_transition",
    },
]


def resolve_anchor(file_rel: str, anchor: str) -> int:
    target = MODULE_ROOT / file_rel
    if not target.exists():
        raise FileNotFoundError(f"Source file not found: {target}")

    with open(target, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if anchor in line:
                return lineno

    raise ValueError(f"Anchor '{anchor}' not found in {target}")


def generate_table(items: list[dict[str, str]], title: str) -> str:
    lines = [
        f"### {title}",
        "",
        "| ID | Description | Layer | Source File & Line | Status |",
        "|:---|:---|:---|:---|:---|",
    ]
    for item in items:
        lineno = resolve_anchor(item["file"], item["anchor"])
        source_link = f"[{item['file']}:{lineno}](../../modules/lms/{item['file']}#L{lineno})"
        row = (
            f"| `{item['id']}` | {item['description']} | `{item['layer']}` | "
            f"{source_link} | `VERIFIED` |"
        )
        lines.append(row)
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    try:
        cfr_table = generate_table(CFRS, "Coherent Functional Requirements (CFRs)")
        afr_table = generate_table(AFRS, "Atomic Functional Requirements (AFRs)")
        uc_table = generate_table(UCS, "Use Cases (UCs)")
        br_table = generate_table(BRS, "Business Rules (BRs)")
        wf_table = generate_table(WORKFLOWS, "Workflows (BWs & CWs)")

        content = f"""# LMS Specification Traceability & Code Reference

Generated automatically by `ops/docs/lms_reference.py`.
Total items verified: 15 CFRs, 47 AFRs, 15 UCs, 19 BRs, 7 Workflows (103 total).

{cfr_table}
{afr_table}
{uc_table}
{br_table}
{wf_table}
"""
        DOCS_OUT.parent.mkdir(parents=True, exist_ok=True)
        with open(DOCS_OUT, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")

        print(
            f"Successfully resolved all 103 specification requirements and generated {DOCS_OUT}"
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: Traceability generation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
