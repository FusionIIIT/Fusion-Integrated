"""Server-driven module metadata for Department."""
MODULE = {
    "code": "department",
    "label": "Department",
    "icon": "FaBuilding",
    "base_path": "/department",
    "nav_section": "Department",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "department.overview",
        "label": "Department Info",
        "icon": "FaBuilding",
        "to": "/department/overview",
        "required_permission": "department.profile.view",
        "sort_order": 10,
    },
    {
        "code": "department.announcements",
        "label": "Announcements",
        "icon": "FaBullhorn",
        "to": "/department/announcements",
        "required_permission": "department.profile.view",
        "sort_order": 20,
    },
    {
        "code": "department.inventory",
        "label": "Inventory & Stock",
        "icon": "FaClipboardList",
        "to": "/department/inventory",
        "required_permission": "department.stock_request.create",
        "sort_order": 30,
    },
    {
        "code": "department.feedback",
        "label": "Feedback",
        "icon": "FaClipboardCheck",
        "to": "/department/feedback",
        "required_permission": "department.feedback.submit",
        "sort_order": 40,
    },
    {
        "code": "department.timetable",
        "label": "Timetable",
        "icon": "FaCalendarAlt",
        "to": "/department/timetable",
        "required_permission": "department.profile.view",
        "sort_order": 50,
    },
    {
        "code": "department.faculty_staff",
        "label": "Faculty & Staff",
        "icon": "FaUsers",
        "to": "/department/faculty-staff",
        "required_permission": "department.profile.view",
        "sort_order": 60,
    },
    {
        "code": "department.resources",
        "label": "Lab Resources",
        "icon": "FaThLarge",
        "to": "/department/resources",
        "required_permission": "department.resource.view",
        "sort_order": 70,
    },
]

PERMISSIONS = [
    ("department.announcement.publish", "Publish announcements"),
    ("department.inventory.manage", "Insert and track inventory"),
    ("department.stock_request.create", "Submit stock requests"),
    ("department.feedback.submit", "Submit confidential feedback"),
    ("department.profile.view", "View department profiles"),
    ("department.timetable.manage", "Upload and modify timetables"),
    ("department.resource.view", "View lab resource profiles"),
    ("department.detail.update", "Update general department information"),
    ("department.detail.propose", "Propose official department-detail changes"),
]

SYSTEM_PERMISSIONS = []

_STUDENT = [
    "department.feedback.submit",
    "department.profile.view",
    "department.resource.view",
]
_FACULTY = [
    "department.announcement.publish",
    "department.stock_request.create",
    "department.feedback.submit",
    "department.profile.view",
    "department.resource.view",
]
_DEPT_ADMIN = [
    "department.announcement.publish",
    "department.inventory.manage",
    "department.feedback.submit",
    "department.profile.view",
    "department.timetable.manage",
    "department.resource.view",
    "department.detail.update",
    "department.detail.propose",
]
_HOD = [
    "department.detail.propose",
    "department.detail.update",
    "department.announcement.publish",
    "department.stock_request.create",
    "department.feedback.submit",
    "department.profile.view",
    "department.resource.view",
    "department.timetable.manage",
]

ROLE_GRANTS = {
    "student": _STUDENT,
    "faculty": _FACULTY,
    "department_admin": _DEPT_ADMIN,
    "department_head": _HOD,
}
