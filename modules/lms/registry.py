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
]

SYSTEM_PERMISSIONS = []

_STUDENT = ["lms.course.view"]
_FACULTY = ["lms.course.view", "lms.course.manage"]
_STAFF = ["lms.course.view"]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "staff": _STAFF,
}
