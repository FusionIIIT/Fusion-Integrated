"""LMS Course Management registry specification (ADR-0010)."""
from modules.courses.permissions import P_WORKSPACE_MANAGE, P_WORKSPACE_VIEW

MODULE = {
    "code": "courses",
    "label": "Course Management",
    "icon": "GraduationCap",
    "base_path": "/courses",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "courses.workspace",
        "label": "Course Workspace",
        "icon": "GraduationCap",
        "to": "/courses/workspace",
        "required_permission": P_WORKSPACE_VIEW,
        "sort_order": 10,
    },
]

PERMISSIONS = [
    (P_WORKSPACE_VIEW, "View enrolled or assigned course workspaces"),
    (P_WORKSPACE_MANAGE, "Configure and update course workspace details"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    P_WORKSPACE_VIEW,
]

_FACULTY = [
    P_WORKSPACE_VIEW,
    P_WORKSPACE_MANAGE,
]

_TA = [
    P_WORKSPACE_VIEW,
]

_OBSERVER = [
    P_WORKSPACE_VIEW,
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "ta": _TA,
    "observer": _OBSERVER,
    "Dean Academic": _FACULTY,
}
