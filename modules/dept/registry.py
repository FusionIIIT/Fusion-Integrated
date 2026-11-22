"""Department module navigation, permissions, and role mappings (ADR-0010)."""

from __future__ import annotations

MODULE = {
    "code": "dept",
    "label": "Department",
    "icon": "Building",
    "base_path": "/dept",
    "nav_section": "Academics",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "dept.announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/dept/announcements",
        "required_permission": "dept.announcement.view",
        "sort_order": 10,
    },
    {
        "code": "dept.inventory",
        "label": "Inventory",
        "icon": "Package",
        "to": "/dept/inventory",
        "required_permission": "dept.inventory.view",
        "sort_order": 20,
    },
    {
        "code": "dept.stock_requests",
        "label": "Stock Requests",
        "icon": "ClipboardText",
        "to": "/dept/stock-requests",
        "required_permission": "dept.stock_request.view",
        "sort_order": 30,
    },
    {
        "code": "dept.feedback",
        "label": "Feedback",
        "icon": "ChatCircleText",
        "to": "/dept/feedback",
        "required_permission": "dept.feedback.view",
        "sort_order": 40,
    },
    {
        "code": "dept.timetables",
        "label": "Timetables",
        "icon": "CalendarBlank",
        "to": "/dept/timetables",
        "required_permission": "dept.timetable.view",
        "sort_order": 50,
    },
    {
        "code": "dept.labs",
        "label": "Lab Resources",
        "icon": "Desktop",
        "to": "/dept/labs",
        "required_permission": "dept.lab_resource.view",
        "sort_order": 60,
    },
    {
        "code": "dept.profiles",
        "label": "Profiles",
        "icon": "Users",
        "to": "/dept/profiles",
        "required_permission": "dept.profile.view",
        "sort_order": 70,
    },
    {
        "code": "dept.details",
        "label": "Department Details",
        "icon": "Building",
        "to": "/dept/details",
        "required_permission": "dept.detail.view",
        "sort_order": 80,
    },
    {
        "code": "dept.roles",
        "label": "Role Governance",
        "icon": "IdentificationBadge",
        "to": "/dept/roles",
        "required_permission": "dept.role_assignment.view",
        "sort_order": 90,
    },
]

PERMISSIONS = [
    # Announcements
    ("dept.announcement.view", "View relevant department announcements"),
    ("dept.announcement.create", "Create and publish department announcements"),
    ("dept.announcement.manage", "Edit, hide, or delete active announcements (HOD)"),
    # Inventory & Stock
    ("dept.inventory.view", "View department stock catalog and transaction history"),
    ("dept.inventory.create", "Insert stock catalog items and stock quantities"),
    ("dept.stock_request.view", "View department stock requests"),
    ("dept.stock_request.create", "Submit department stock requests (Faculty)"),
    ("dept.stock_request.approve", "Approve or reject stock requests (HOD)"),
    ("dept.stock_request.issue", "Issue approved stock and decrement inventory (Dept_Admin)"),
    # Feedback
    ("dept.feedback.view", "View feedback within authorized departmental scope"),
    ("dept.feedback.create", "Submit confidential feedback"),
    ("dept.feedback.review", "Initial review and categorization of feedback (Dept_Admin)"),
    ("dept.feedback.resolve", "Resolve or close department feedback (Dept_Admin / HOD)"),
    # Timetables
    ("dept.timetable.view", "View department timetables"),
    ("dept.timetable.manage", "Upload and modify conflict-free timetables (Dept_Admin)"),
    # Lab Resources
    ("dept.lab_resource.view", "View department lab resource profiles"),
    ("dept.lab_resource.manage", "Manage lab resource records and equipment (Dept_Admin)"),
    # Profiles
    ("dept.profile.view", "View department directory profiles governed by privacy matrix"),
    ("dept.profile.manage", "Manage department user profiles (Dept_Admin)"),
    # Department Details
    ("dept.detail.view", "View department details and policies"),
    ("dept.detail.update", "Update general details and propose official changes (Dept_Admin)"),
    ("dept.detail.approve", "Approve or reject official department changes (HOD)"),
    # Role Governance
    ("dept.role_assignment.view", "View department HOD and Dept_Admin assignments"),
    ("dept.role_assignment.manage", "Assign or revoke department roles (Institute Admin)"),
]

SYSTEM_PERMISSIONS: list[str] = []

SCOPE_PERMISSIONS = [
    "dept.announcement.view",
    "dept.inventory.view",
    "dept.stock_request.view",
    "dept.feedback.view",
    "dept.timetable.view",
    "dept.lab_resource.view",
    "dept.profile.view",
    "dept.detail.view",
]

_HOD = [
    "dept.announcement.view",
    "dept.announcement.create",
    "dept.announcement.manage",
    "dept.inventory.view",
    "dept.stock_request.view",
    "dept.stock_request.approve",
    "dept.feedback.view",
    "dept.feedback.resolve",
    "dept.timetable.view",
    "dept.lab_resource.view",
    "dept.profile.view",
    "dept.detail.view",
    "dept.detail.approve",
    "dept.role_assignment.view",
]

_DEPT_ADMIN = [
    "dept.announcement.view",
    "dept.announcement.create",
    "dept.inventory.view",
    "dept.inventory.create",
    "dept.stock_request.view",
    "dept.stock_request.issue",
    "dept.feedback.view",
    "dept.feedback.review",
    "dept.feedback.resolve",
    "dept.timetable.view",
    "dept.timetable.manage",
    "dept.lab_resource.view",
    "dept.lab_resource.manage",
    "dept.profile.view",
    "dept.profile.manage",
    "dept.detail.view",
    "dept.detail.update",
    "dept.role_assignment.view",
]

_FACULTY = [
    "dept.announcement.view",
    "dept.announcement.create",
    "dept.stock_request.view",
    "dept.stock_request.create",
    "dept.feedback.create",
    "dept.timetable.view",
    "dept.lab_resource.view",
    "dept.profile.view",
    "dept.detail.view",
]

_STUDENT = [
    "dept.announcement.view",
    "dept.feedback.create",
    "dept.timetable.view",
    "dept.profile.view",
    "dept.detail.view",
]

_ADMIN = [
    "dept.role_assignment.view",
    "dept.role_assignment.manage",
    "dept.detail.view",
]

ROLE_GRANTS = {
    "HOD": _HOD,
    "Dept_Admin": _DEPT_ADMIN,
    "faculty": _FACULTY,
    "student": _STUDENT,
    "Institute Admin": _ADMIN,
}
