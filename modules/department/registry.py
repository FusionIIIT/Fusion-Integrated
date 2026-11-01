"""Department module registry (ADR-0010).

Declares module metadata, navigation items, permission taxonomy, and role grants.
The IAM seeds these into globals_designation and filters screens on the server.
"""

MODULE = {
    "code": "department",
    "label": "Department",
    "icon": "Building",
    "base_path": "/department",
    "nav_section": "Academics",
    "sort_order": 25,
    "status": "active",
}

NAV_ITEMS = [
    # -- Student / PG views ----------------------------------------------------
    {
        "code": "department.seminar_request",
        "label": "Request Seminar",
        "icon": "FaGraduationCap",
        "to": "/department/seminar-request",
        "required_permission": "department.seminar.request",
        "sort_order": 10,
    },
    {
        "code": "department.my_seminars",
        "label": "My Seminars",
        "icon": "FaUserGraduate",
        "to": "/department/my-seminars",
        "required_permission": "department.seminar.view_self",
        "sort_order": 20,
    },

    # -- Department Administrator / HOD views ----------------------------------
    {
        "code": "department.pending_seminars",
        "label": "Pending Seminars",
        "icon": "FaClipboardCheck",
        "to": "/department/pending-seminars",
        "required_permission": "department.seminar.schedule",
        "sort_order": 30,
    },

    # -- General / Shared views ------------------------------------------------
    {
        "code": "department.calendar",
        "label": "Seminar Schedule",
        "icon": "FaCalendarAlt",
        "to": "/department/calendar",
        "required_permission": "department.seminar.view",
        "sort_order": 40,
    },
    {
        "code": "department.allocations",
        "label": "Allocations",
        "icon": "FaUsersCog",
        "to": "/department/allocations",
        "required_permission": "department.allocation.view",
        "sort_order": 50,
    },
    {
        "code": "department.announcements",
        "label": "Announcements",
        "icon": "FaBullhorn",
        "to": "/department/announcements",
        "required_permission": "department.announcement.view",
        "sort_order": 60,
    },
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = [
    ("department.seminar.request", "Submit graduate seminar scheduling request"),
    ("department.seminar.view_self", "View one's own seminar requests"),
    ("department.seminar.view", "View scheduled graduate seminars"),
    ("department.seminar.schedule", "Schedule graduate seminars and record history"),
    ("department.seminar.view_all", "View all seminar requests and scheduling history"),
    ("department.allocation.view", "View TA and thesis supervisor allocations"),
    ("department.allocation.manage", "Manage TA and supervisor allocations"),
    ("department.announcement.view", "View department announcements"),
    ("department.announcement.publish", "Publish department announcements"),
]

#: Performed by background tasks or system services
SYSTEM_PERMISSIONS: list[str] = []

#: Enforced by widening selectors rather than hard 403 on an endpoint
SCOPE_PERMISSIONS = [
    "department.seminar.view_all",
]

# Role -> permission mappings
_STUDENT = [
    "department.seminar.request",
    "department.seminar.view_self",
    "department.seminar.view",
    "department.allocation.view",
    "department.announcement.view",
]

_FACULTY = [
    "department.seminar.view",
    "department.allocation.view",
    "department.announcement.view",
]

_ADMIN = [
    "department.seminar.request",
    "department.seminar.view_self",
    "department.seminar.view",
    "department.seminar.schedule",
    "department.seminar.view_all",
    "department.allocation.view",
    "department.allocation.manage",
    "department.announcement.view",
    "department.announcement.publish",
]

_LEADERSHIP = [
    "department.seminar.view",
    "department.seminar.view_all",
    "department.allocation.view",
    "department.announcement.view",
]

#: Keyed by designation name as it exists in globals_designation
ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "department_admin": _ADMIN,
    "HOD": _ADMIN,
    "Dean Academic": _LEADERSHIP,
    "acadadmin": _LEADERSHIP,
}
