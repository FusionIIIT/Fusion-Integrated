"""What the server tells the shell about this module (ADR-0010)."""

MODULE = {
    "code": "department",
    "label": "Department",
    "icon": "Buildings",
    "base_path": "/department",
    "nav_section": "Academics",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "department.overview",
        "label": "Overview",
        "icon": "Buildings",
        "to": "/department/overview",
        "required_permission": "department.department.view",
        "sort_order": 10,
    },
    {
        "code": "department.announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/department/announcements",
        "required_permission": "department.announcement.view",
        "sort_order": 20,
    },
    {
        "code": "department.inventory",
        "label": "Inventory & Stock",
        "icon": "Package",
        "to": "/department/inventory",
        "required_permission": "department.inventory_item.view",
        "sort_order": 30,
    },
    {
        "code": "department.feedback",
        "label": "Feedback",
        "icon": "ChatCircleText",
        "to": "/department/feedback",
        "required_permission": "department.feedback.view",
        "sort_order": 40,
    },
    {
        "code": "department.timetable",
        "label": "Timetable",
        "icon": "CalendarBlank",
        "to": "/department/timetable",
        "required_permission": "department.timetable.view",
        "sort_order": 50,
    },
    {
        "code": "department.labs",
        "label": "Lab Resources",
        "icon": "Flask",
        "to": "/department/labs",
        "required_permission": "department.lab_resource.view",
        "sort_order": 60,
    },
    {
        "code": "department.profiles",
        "label": "People",
        "icon": "Users",
        "to": "/department/profiles",
        "required_permission": "department.profile.view",
        "sort_order": 70,
    },
    {
        "code": "department.roles",
        "label": "HOD & Dept_Admin",
        "icon": "IdentificationBadge",
        "to": "/department/roles",
        "required_permission": "department.role_assignment.view",
        "sort_order": 80,
    },
]

PERMISSIONS = [
    ("department.department.view", "See department details and headship"),
    ("department.department.update", "Update general department details"),
    ("department.official_change.view", "See proposed official changes"),
    ("department.official_change.create", "Propose an official change"),
    ("department.official_change.approve", "Approve or reject an official change"),
    ("department.announcement.view", "See relevant announcements"),
    ("department.announcement.create", "Publish an announcement"),
    ("department.announcement.update", "Edit or hide an active announcement"),
    ("department.announcement.delete", "Delete an active announcement"),
    ("department.inventory_item.view", "See inventory items and quantities"),
    ("department.inventory_item.create", "Add items and record stock receipts"),
    ("department.stock_movement.view", "See the stock movement log"),
    ("department.stock_request.view", "See stock requests in scope"),
    ("department.stock_request.create", "Request stock"),
    ("department.stock_request.approve", "Approve or reject a stock request"),
    ("department.stock_issue.create", "Issue approved stock"),
    ("department.feedback.view", "See feedback in scope"),
    ("department.feedback.create", "Submit feedback"),
    ("department.feedback.review", "Initial review and categorisation"),
    ("department.feedback_resolution.create", "Mark feedback resolved or closed"),
    ("department.timetable.view", "See timetables"),
    ("department.timetable.create", "Upload timetable slots"),
    ("department.timetable.update", "Modify or remove timetable slots"),
    ("department.lab_resource.view", "See lab resource profiles"),
    ("department.lab_resource.update", "Add and update lab resource profiles"),
    ("department.profile.view", "See department profiles at your tier"),
    ("department.profile.update", "Manage department profile records"),
    ("department.role_assignment.view", "See HOD and Dept_Admin tenures"),
    ("department.role_assignment.assign", "Record an HOD or Dept_Admin tenure"),
    ("department.role_assignment.update", "System: apply a tenure taking effect"),
]

SYSTEM_PERMISSIONS = ["department.role_assignment.update"]

SCOPE_PERMISSIONS: dict = {}

_STUDENT = [
    "department.department.view",
    "department.announcement.view",
    "department.feedback.view",
    "department.feedback.create",
    "department.timetable.view",
    "department.profile.view",
]

_FACULTY = [
    *_STUDENT,
    "department.announcement.create",
    "department.inventory_item.view",
    "department.stock_request.view",
    "department.stock_request.create",
    "department.lab_resource.view",
]

_DEPT_ADMIN = [
    "department.department.view",
    "department.department.update",
    "department.official_change.view",
    "department.official_change.create",
    "department.announcement.view",
    "department.announcement.create",
    "department.inventory_item.view",
    "department.inventory_item.create",
    "department.stock_movement.view",
    "department.stock_request.view",
    "department.stock_issue.create",
    "department.feedback.view",
    "department.feedback.review",
    "department.feedback_resolution.create",
    "department.timetable.view",
    "department.timetable.create",
    "department.timetable.update",
    "department.lab_resource.view",
    "department.lab_resource.update",
    "department.profile.view",
    "department.profile.update",
    "department.role_assignment.view",
]

_HOD = [
    "department.department.view",
    "department.official_change.view",
    "department.official_change.approve",
    "department.announcement.view",
    "department.announcement.create",
    "department.announcement.update",
    "department.announcement.delete",
    "department.inventory_item.view",
    "department.stock_movement.view",
    "department.stock_request.view",
    "department.stock_request.approve",
    "department.feedback.view",
    "department.feedback_resolution.create",
    "department.timetable.view",
    "department.lab_resource.view",
    "department.profile.view",
    "department.role_assignment.view",
]

_CENTRAL = [
    "department.department.view",
    "department.role_assignment.view",
    "department.role_assignment.assign",
]

#: Keyed by the designation name exactly as globals_designation spells it.
ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "HOD (CSE)": _HOD,
    "HOD (Design)": _HOD,
    "HOD (ECE)": _HOD,
    "HOD (Liberal Arts)": _HOD,
    "HOD (ME)": _HOD,
    "HOD (NS)": _HOD,
    "deptadmin_cse": _DEPT_ADMIN,
    "deptadmin_design": _DEPT_ADMIN,
    "deptadmin_ece": _DEPT_ADMIN,
    "deptadmin_liberalarts": _DEPT_ADMIN,
    "deptadmin_me": _DEPT_ADMIN,
    "deptadmin_ns": _DEPT_ADMIN,
    "deptadmin_sm": _DEPT_ADMIN,
    "acadadmin": _CENTRAL,
}


def readiness() -> list[str]:
    """Each unmet prerequisite, as a sentence saying what to do."""
    from modules.department.selectors.readiness import unmet_prerequisites

    return unmet_prerequisites()
