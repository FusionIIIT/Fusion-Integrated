"""What the server tells the shell about this module (ADR-0010)."""

from __future__ import annotations

MODULE = {
    "code": "lms",
    "label": "Course Management",
    "icon": "BookOpen",
    "base_path": "/lms",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "lms.courses",
        "label": "My Courses",
        "icon": "Books",
        "to": "/lms/courses",
        "required_permission": "lms.workspace.view",
        "sort_order": 10,
    },
    {
        "code": "lms.materials",
        "label": "Course Materials",
        "icon": "FileText",
        "to": "/lms/materials",
        "required_permission": "lms.material.view",
        "sort_order": 20,
    },
    {
        "code": "lms.announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/lms/announcements",
        "required_permission": "lms.announcement.view",
        "sort_order": 30,
    },
    {
        "code": "lms.assignments",
        "label": "Assignments",
        "icon": "ClipboardText",
        "to": "/lms/assignments",
        "required_permission": "lms.assignment.view",
        "sort_order": 40,
    },
    {
        "code": "lms.grades",
        "label": "My Grades",
        "icon": "GraduationCap",
        "to": "/lms/grades",
        "required_permission": "lms.grade.view",
        "sort_order": 50,
    },
    {
        "code": "lms.grading",
        "label": "Submissions & Grading",
        "icon": "CheckSquare",
        "to": "/lms/grading",
        "required_permission": "lms.submission.review",
        "sort_order": 60,
    },
]

PERMISSIONS = [
    ("lms.workspace.view", "View course workspace, syllabus, schedule, and instructors"),
    ("lms.workspace.update", "Configure course workspace settings and details"),
    ("lms.material.view", "View and download published course materials"),
    ("lms.material.create", "Upload course materials and configure release schedules"),
    ("lms.material.update", "Edit course materials"),
    ("lms.material.delete", "Remove course materials"),
    ("lms.material.publish", "Publish course materials immediately or on schedule"),
    ("lms.announcement.view", "Read course announcements"),
    ("lms.announcement.create", "Post course announcements"),
    ("lms.announcement.update", "Edit course announcements"),
    ("lms.announcement.delete", "Delete course announcements"),
    ("lms.assignment.view", "View published assignments and instructions"),
    ("lms.assignment.create", "Create draft assignments"),
    ("lms.assignment.update", "Edit draft assignments"),
    ("lms.assignment.delete", "Delete assignments"),
    ("lms.assignment.publish", "Publish assignments immediately or on schedule"),
    ("lms.submission.view", "View assignment submissions within authorized scope"),
    ("lms.submission.create", "Submit assignment work conforming to configured type"),
    ("lms.submission.review", "Review and evaluate student submissions for assigned courses"),
    ("lms.grade.view", "View assignment grades within authorized scope"),
    ("lms.grade.create", "Enter draft grades and feedback for submissions"),
    ("lms.grade.update", "Modify draft or published grades"),
    ("lms.grade.publish", "Publish grades and feedback to students"),
]

#: System permissions for background workers with no human designation.
SYSTEM_PERMISSIONS = []

_STUDENT = [
    "lms.workspace.view",
    "lms.material.view",
    "lms.announcement.view",
    "lms.assignment.view",
    "lms.submission.view",
    "lms.submission.create",
    "lms.grade.view",
]

_TA = [
    "lms.workspace.view",
    "lms.material.view",
    "lms.announcement.view",
    "lms.announcement.create",
    "lms.assignment.view",
    "lms.submission.view",
    "lms.submission.review",
    "lms.grade.view",
    "lms.grade.create",
    "lms.grade.update",
]

_OBSERVER = [
    "lms.workspace.view",
    "lms.material.view",
    "lms.announcement.view",
    "lms.assignment.view",
]

_FACULTY = [
    "lms.workspace.view",
    "lms.workspace.update",
    "lms.material.view",
    "lms.material.create",
    "lms.material.update",
    "lms.material.delete",
    "lms.material.publish",
    "lms.announcement.view",
    "lms.announcement.create",
    "lms.announcement.update",
    "lms.announcement.delete",
    "lms.assignment.view",
    "lms.assignment.create",
    "lms.assignment.update",
    "lms.assignment.delete",
    "lms.assignment.publish",
    "lms.submission.view",
    "lms.submission.review",
    "lms.grade.view",
    "lms.grade.create",
    "lms.grade.update",
    "lms.grade.publish",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "teaching_assistant": _TA,
    "course_observer": _OBSERVER,
    "faculty": _FACULTY,
    "Professor": _FACULTY,
    "Associate Professor": _FACULTY,
    "Assistant Professor": _FACULTY,
}
