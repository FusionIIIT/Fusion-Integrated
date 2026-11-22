"""Department module registration and IAM permission declarations."""

MODULE = {
    "code": "department",
    "label": "Department",
    "icon": "Building2",
    "base_path": "/department",
    "nav_section": "Department",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "department_announcements",
        "label": "Announcements",
        "icon": "Megaphone",
        "to": "/department/announcements",
        "required_permission": "department.announcement.view",
        "sort_order": 1,
    },
    {
        "code": "department_inventory",
        "label": "Inventory",
        "icon": "Package",
        "to": "/department/inventory",
        "required_permission": "department.inventory.view",
        "sort_order": 2,
    },
    {
        "code": "department_feedback",
        "label": "Feedback",
        "icon": "MessageSquare",
        "to": "/department/feedback",
        "required_permission": "department.feedback.view",
        "sort_order": 3,
    },
    {
        "code": "department_profiles",
        "label": "Profiles",
        "icon": "Users",
        "to": "/department/profiles",
        "required_permission": "department.profile.view",
        "sort_order": 4,
    },
    {
        "code": "department_timetable",
        "label": "Timetable",
        "icon": "CalendarDays",
        "to": "/department/timetable",
        "required_permission": "department.timetable.view",
        "sort_order": 5,
    },
]

PERMISSIONS = [
    ("department.announcement.view", "View department announcements"),
    ("department.announcement.publish", "Create and publish announcements"),
    ("department.announcement.manage", "Edit, hide, and delete active announcements"),
    ("department.inventory.view", "View department inventory"),
    ("department.inventory.manage", "Manage inventory records"),
    ("department.inventory.request", "Request inventory stock"),
    ("department.inventory.approve", "Approve or reject stock requests"),
    ("department.inventory.issue", "Issue approved stock"),
    ("department.feedback.submit", "Submit department feedback"),
    ("department.feedback.view", "View permitted feedback records"),
    ("department.feedback.review", "Review and categorize feedback"),
    ("department.feedback.resolve", "Resolve or close feedback"),
    ("department.profile.view", "View permitted department profiles"),
    ("department.profile.manage", "Manage department profiles"),
    ("department.timetable.view", "View department timetable"),
    ("department.timetable.manage", "Manage department timetable"),
    ("department.resource.view", "View department resources"),
    ("department.resource.manage", "Manage department resources"),
    ("department.details.view", "View department details"),
    ("department.details.manage", "Update general department details"),
    ("department.details.approve", "Approve official department detail changes"),
]

SYSTEM_PERMISSIONS = [
    # Reserved for centrally authorized institute role administration.
    # Add a permission here only after confirming how central IAM represents it.
]

ROLE_GRANTS = {
    "HOD": [
        "department.announcement.view",
        "department.announcement.publish",
        "department.announcement.manage",
        "department.inventory.view",
        "department.inventory.approve",
        "department.feedback.view",
        "department.feedback.resolve",
        "department.profile.view",
        "department.timetable.view",
        "department.resource.view",
        "department.details.view",
        "department.details.approve",
    ],
    "Dept_Admin": [
        "department.announcement.view",
        "department.announcement.publish",
        "department.announcement.manage",
        "department.inventory.view",
        "department.inventory.manage",
        "department.inventory.issue",
        "department.feedback.view",
        "department.feedback.review",
        "department.feedback.resolve",
        "department.profile.view",
        "department.profile.manage",
        "department.timetable.view",
        "department.timetable.manage",
        "department.resource.view",
        "department.resource.manage",
        "department.details.view",
        "department.details.manage",
    ],
    "Faculty": [
        "department.announcement.view",
        "department.announcement.publish",
        "department.inventory.view",
        "department.inventory.request",
        "department.feedback.submit",
        "department.profile.view",
        "department.timetable.view",
        "department.resource.view",
        "department.details.view",
    ],
    "Student": [
        "department.announcement.view",
        "department.feedback.submit",
        "department.timetable.view",
        "department.details.view",
    ],
}
