"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "dept", "label": "Department", "icon": "Buildings",
    "base_path": "/dept", "nav_section": "Department", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "dept.announcements", "label": "Announcements",
     "icon": "FaBullhorn", "to": "/dept/announcements",
     "required_permission": "dept.announcement.view", "sort_order": 10},
    {"code": "dept.stock", "label": "Stock Requests",
     "icon": "FaBoxes", "to": "/dept/stock",
     "required_permission": "dept.inventory.view", "sort_order": 20},
    {"code": "dept.feedback", "label": "Feedback",
     "icon": "FaCommentDots", "to": "/dept/feedback",
     "required_permission": "dept.feedback.access", "sort_order": 30},
]

PERMISSIONS = [
    ("dept.announcement.view", "See announcements addressed to you"),
    ("dept.announcement.publish", "Create and publish announcements"),
    ("dept.announcement.manage", "Edit, hide or delete any announcement"),
    ("dept.inventory.view", "See inventory and stock requests"),
    ("dept.inventory.manage", "Insert inventory and log stock insertions"),
    ("dept.stock_request.create", "Request stock from the department"),
    ("dept.stock_request.view_all", "See every stock request"),
    ("dept.stock_request.decide", "Approve or reject a stock request"),
    ("dept.stock_request.issue", "Issue approved stock"),
    ("dept.stock_log.view", "Read the immutable stock movement log"),
    ("dept.feedback.access", "Reach the feedback screens"),
    ("dept.feedback.create", "Submit confidential feedback"),
    ("dept.feedback.review", "Initial review, categorise and close feedback"),
    ("dept.feedback.resolve", "Resolve or close reviewed feedback (HOD)"),
]

SYSTEM_PERMISSIONS: list[str] = []

#: Enforced by narrowing a queryset (selectors/scoping.py), not by refusing.
SCOPE_PERMISSIONS = ["dept.stock_request.view_all"]

_VIEWER = ["dept.announcement.view", "dept.feedback.access"]

_STUDENT = [*_VIEWER, "dept.feedback.create"]

_FACULTY = [
    *_VIEWER,
    "dept.announcement.publish",
    "dept.inventory.view",
    "dept.stock_request.create",
    "dept.feedback.create",
]

_DEPT_ADMIN = [
    *_VIEWER,
    "dept.announcement.publish",
    "dept.inventory.view",
    "dept.inventory.manage",
    "dept.stock_request.view_all",
    "dept.stock_request.issue",
    "dept.stock_log.view",
    "dept.feedback.review",
]

_HOD = [
    *_VIEWER,
    "dept.announcement.publish",
    "dept.announcement.manage",
    "dept.inventory.view",
    "dept.stock_request.view_all",
    "dept.stock_request.decide",
    "dept.stock_log.view",
    "dept.feedback.resolve",
]

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "dept_admin": _DEPT_ADMIN,
    "hod": _HOD,
}
