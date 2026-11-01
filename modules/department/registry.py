"""What the server tells the shell about this module (ADR-0010)."""
MODULE = {
    "code": "department", "label": "Department", "icon": "Buildings",
    "base_path": "/department", "nav_section": "Department", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "department.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/department/announcements",
     "required_permission": "department.announcement.view", "sort_order": 10},
    {"code": "department.stock_requests", "label": "Stock Requests",
     "icon": "Package", "to": "/department/stock-requests",
     "required_permission": "department.stock_request.view", "sort_order": 20},
    {"code": "department.feedback", "label": "Feedback",
     "icon": "ChatText", "to": "/department/feedback",
     "required_permission": "department.feedback.view", "sort_order": 30},
    {"code": "department.timetable", "label": "Timetable",
     "icon": "CalendarBlank", "to": "/department/timetable",
     "required_permission": "department.timetable.view", "sort_order": 40},
]

PERMISSIONS = [
    ("department.department.view", "View department listings"),
    ("department.role_assignment.view", "View department role assignments"),
    ("department.role_assignment.assign", "Assign department roles"),
    ("department.announcement.view", "View department announcements"),
    ("department.announcement.create", "Create department announcements"),
    ("department.announcement.update", "Update department announcements"),
    ("department.announcement.delete", "Delete department announcements"),
    ("department.inventory.view", "View department inventory"),
    ("department.inventory.create", "Create department inventory"),
    ("department.stock_request.view", "View stock requests"),
    ("department.stock_request.create", "Create stock requests"),
    ("department.stock_request.approve", "Approve stock requests"),
    ("department.stock_request.update", "Update stock requests"),
    ("department.stock_movement.view", "View stock movements"),
    ("department.feedback.view", "View department feedback"),
    ("department.feedback.create", "Create department feedback"),
    ("department.feedback.review", "Review department feedback"),
    ("department.feedback.update", "Update department feedback"),
    ("department.timetable.view", "View department timetable"),
    ("department.timetable.create", "Create department timetable"),
    ("department.timetable.update", "Update department timetable"),
    ("department.lab.view", "View department lab information"),
    ("department.lab.update", "Update department lab information"),
    ("department.program.view", "View department program listings"),
    ("department.program.update", "Update department program listings"),
    ("department.profile.view", "View department profile"),
    ("department.profile.update", "Update department profile"),
    ("department.roster.update", "Update department roster"),
    ("department.department.update", "Update department details"),
    ("department.official_change.view", "View official change records"),
    ("department.official_change.approve", "Approve official change records"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "department.department.view", "department.announcement.view", "department.feedback.view", "department.feedback.create", "department.timetable.view", "department.program.view", "department.profile.view",
]
_FACULTY = [
    "department.department.view", "department.announcement.view", "department.announcement.create", "department.inventory.view", "department.stock_request.view", "department.stock_request.create", "department.feedback.view", "department.feedback.create", "department.timetable.view", "department.lab.view", "department.profile.view",
]
_ACADADMIN = [
    "department.department.view", "department.role_assignment.view", "department.role_assignment.assign",
]
_HOD = [
    "department.department.view", "department.announcement.view", "department.announcement.create", "department.announcement.update", "department.announcement.delete", "department.inventory.view", "department.stock_request.view", "department.stock_request.approve", "department.stock_movement.view", "department.feedback.view", "department.feedback.update", "department.timetable.view", "department.profile.view", "department.official_change.view", "department.official_change.approve",
]
_DEPT_ADMIN = [
    "department.department.view", "department.department.update", "department.announcement.view", "department.announcement.create", "department.inventory.view", "department.inventory.create", "department.stock_request.view", "department.stock_request.update", "department.stock_movement.view", "department.feedback.view", "department.feedback.review", "department.feedback.update", "department.timetable.view", "department.timetable.create", "department.timetable.update", "department.lab.view", "department.lab.update", "department.program.view", "department.program.update", "department.profile.view", "department.profile.update", "department.roster.update", "department.official_change.view",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "acadadmin": _ACADADMIN,
    "HOD (CSE)": _HOD,
    "HOD (Design)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (Liberal Arts)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (NS)": _HOD,
    "dept_admin": _DEPT_ADMIN,
    "deptadmin_cse": _DEPT_ADMIN,
    "deptadmin_design": _DEPT_ADMIN,
    "deptadmin_ece": _DEPT_ADMIN,
    "deptadmin_liberalarts": _DEPT_ADMIN,
    "deptadmin_me": _DEPT_ADMIN,
    "deptadmin_ns": _DEPT_ADMIN,
    "deptadmin_sm": _DEPT_ADMIN,
}
