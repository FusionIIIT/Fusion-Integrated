"""Department module menu and role grants consumed by Fusion's registry tools."""

MODULE = {
    "code": "department",
    "label": "Department",
    "icon": "FaBuilding",
    "base_path": "/department",
    "nav_section": "Academic",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "department.announcements", "label": "Announcements",
     "icon": "FaBullhorn", "to": "/department/announcements",
     "required_permission": "department.announcement.view", "sort_order": 10},
    {"code": "department.inventory", "label": "Inventory",
     "icon": "FaWarehouse", "to": "/department/inventory",
     "required_permission": "department.inventory.view", "sort_order": 20},
    {"code": "department.feedback", "label": "Feedback",
     "icon": "FaCommentDots", "to": "/department/feedback",
     "required_permission": "department.feedback.view", "sort_order": 30},
    {"code": "department.resources", "label": "Resources and details",
     "icon": "FaBook", "to": "/department/resources",
     "required_permission": "department.resource.view", "sort_order": 40},
    {"code": "department.details", "label": "Department details",
     "icon": "FaInfoCircle", "to": "/department/details",
     "required_permission": "department.details.view", "sort_order": 45},
    {"code": "department.academics", "label": "Academic information",
     "icon": "FaCalendarAlt", "to": "/department/academics",
     "required_permission": "department.timetable.view", "sort_order": 50},
]

PERMISSIONS = [
    ("department.announcement.view", "View relevant announcements"),
    ("department.announcement.create", "Create announcements"),
    ("department.announcement.manage", "Edit, hide, or delete announcements"),
    ("department.inventory.view", "View department inventory"),
    ("department.inventory.manage", "Manage department inventory"),
    ("department.stock_request.create", "Request stock"),
    ("department.stock_request.review", "Review and decide stock requests"),
    ("department.stock_request.issue", "Issue approved stock requests"),
    ("department.feedback.create", "Submit department feedback"),
    ("department.feedback.view", "View feedback within the assigned scope"),
    ("department.feedback.review", "Review and disposition feedback"),
    ("department.resource.view", "View department resources"),
    ("department.resource.manage", "Manage department resources"),
    ("department.timetable.view", "View applicable timetables"),
    ("department.timetable.manage", "Manage department timetables"),
    ("department.details.view", "View department details"),
    ("department.details.manage", "Manage department details"),
    ("department.details.approve", "Approve official department changes"),
]

ROLE_GRANTS = {
    "student": [
        "department.announcement.view", "department.feedback.create",
        "department.feedback.view", "department.timetable.view",
        "department.details.view",
    ],
    "faculty": [
        "department.announcement.view", "department.announcement.create",
        "department.inventory.view", "department.stock_request.create",
        "department.feedback.create", "department.feedback.view",
        "department.resource.view",
    ],
    "dept_admin": [
        "department.announcement.view", "department.announcement.create",
        "department.inventory.view", "department.inventory.manage",
        "department.stock_request.review", "department.stock_request.issue",
        "department.feedback.view", "department.feedback.review",
        "department.resource.view", "department.resource.manage",
        "department.timetable.view", "department.timetable.manage",
        "department.details.view", "department.details.manage",
    ],
    "hod": [
        "department.announcement.view", "department.announcement.create",
        "department.announcement.manage", "department.inventory.view",
        "department.stock_request.review", "department.feedback.view",
        "department.feedback.review", "department.details.view",
        "department.details.approve",
    ],
}
