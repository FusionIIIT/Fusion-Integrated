"""LMS module registry, navigation items, and RBAC permissions."""

MODULE = {
    "code": "lms",
    "label": "LMS (Courses)",
    "icon": "FaBook",
    "base_path": "/lms",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "lms.courses",
        "label": "Course Workspace",
        "icon": "FaBook",
        "to": "/lms/courses",
        "required_permission": "lms.course.view",
        "sort_order": 10,
    },
]

PERMISSIONS = [
    ("lms.course.view", "View courses and course home workspaces"),
    ("lms.course.manage", "Configure and edit course workspace details"),
    ("lms.material.view", "View published course materials"),
    ("lms.material.manage", "Create, edit, organize, and schedule course materials"),
    ("lms.announcement.view", "View course announcements"),
    ("lms.announcement.manage", "Post and manage course announcements"),
    ("lms.assignment.view", "View published course assignments"),
    ("lms.assignment.manage", "Create, edit, and publish course assignments"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.view",
    "lms.assignment.view",
]
_FACULTY = [
    "lms.course.view",
    "lms.course.manage",
    "lms.material.view",
    "lms.material.manage",
    "lms.announcement.view",
    "lms.announcement.manage",
    "lms.assignment.view",
    "lms.assignment.manage",
]
_STAFF = [
    "lms.course.view",
    "lms.material.view",
    "lms.announcement.view",
    "lms.assignment.view",
]


ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "staff": _STAFF,
}
