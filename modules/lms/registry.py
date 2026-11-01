"""Fusion's role, permission, module and navigation declaration for LMS."""

MODULE = {
    "code": "lms", "label": "LMS Course Management", "icon": "BookOpen",
    "base_path": "/lms", "nav_section": "Learning", "sort_order": 30,
    "status": "planned",
}

NAV_ITEMS = [
    {"code": "lms.courses", "label": "Courses", "icon": "BookOpen",
     "to": "/lms/courses", "required_permission": "lms.course.view",
     "sort_order": 10},
]

PERMISSIONS = [
    ("lms.course.view", "View an authorized course workspace"),
    ("lms.course.manage", "Manage assigned course details and structure"),
    ("lms.material.view", "View authorized course materials"),
    ("lms.material.manage", "Manage course materials"),
    ("lms.announcement.view", "View course announcements"),
    ("lms.announcement.create", "Post course announcements where permitted"),
    ("lms.assignment.view", "View released assignments"),
    ("lms.assignment.manage", "Create and edit course assignments"),
    ("lms.assignment.publish", "Publish course assignments"),
    ("lms.submission.create", "Submit assignment work"),
    ("lms.submission.view_self", "View one's own submission history"),
    ("lms.submission.view", "View course submissions for grading"),
    ("lms.grade.view_self", "View one's own released grades"),
    ("lms.grade.manage", "Grade course submissions where permitted"),
    ("lms.grade.release", "Release grades and feedback to students"),
    ("lms.material.release", "System release of scheduled course materials"),
    ("lms.assignment.release", "System release of scheduled assignments"),
]

_STUDENT = [
    "lms.course.view", "lms.material.view", "lms.announcement.view",
    "lms.assignment.view", "lms.submission.create", "lms.submission.view_self",
    "lms.grade.view_self",
]
_FACULTY = [p for p, _ in PERMISSIONS if p not in {
    "lms.submission.create", "lms.submission.view_self", "lms.grade.view_self",
    "lms.material.release", "lms.assignment.release",
}]
_TA = [
    "lms.course.view", "lms.material.view", "lms.announcement.view",
    "lms.announcement.create", "lms.submission.view", "lms.grade.manage",
]
_OBSERVER = ["lms.course.view", "lms.material.view", "lms.announcement.view"]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "teaching_assistant": _TA,
    "observer": _OBSERVER,
}

# Scheduled content publication is performed by the LMS worker, not a user.
SYSTEM_PERMISSIONS = ["lms.material.release", "lms.assignment.release"]


def readiness() -> list[str]:
    from django.conf import settings

    if not settings.LMS_COURSE_ACCESS_PROVIDER:
        return ["Configure the read-only academic course access provider"]
    return []
