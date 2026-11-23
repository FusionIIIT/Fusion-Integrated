from modules.department import permissions as p
from modules.department.roles import ADMIN_DEPARTMENTS, HOD_DEPARTMENTS, STUDENT_ROLES

MODULE = {
    "code": "department", "label": "Department", "icon": "Buildings",
    "base_path": "/department", "nav_section": "Department", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "department.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/department/announcements",
     "required_permission": p.VIEW_ANNOUNCEMENT, "sort_order": 10},
    {"code": "department.inventory", "label": "Inventory", "icon": "ClipboardText",
     "to": "/department/inventory", "required_permission": p.VIEW_STOCK, "sort_order": 20},
    {"code": "department.stock_requests", "label": "Stock requests", "icon": "Checks",
     "to": "/department/stock-requests", "required_permission": p.VIEW_STOCK_REQUEST,
     "sort_order": 30},
    {"code": "department.feedback_submit", "label": "Submit feedback", "icon": "PencilSimple",
     "to": "/department/feedback", "required_permission": p.SUBMIT_FEEDBACK, "sort_order": 40},
    {"code": "department.feedback_inbox", "label": "Feedback inbox", "icon": "ClipboardText",
     "to": "/department/feedback-inbox", "required_permission": p.VIEW_FEEDBACK, "sort_order": 40},
    {"code": "department.notices", "label": "Notifications", "icon": "Megaphone",
     "to": "/department/notices", "required_permission": p.VIEW_NOTICE, "sort_order": 50},
    {"code": "department.labs", "label": "Lab resources", "icon": "Buildings",
     "to": "/department/labs", "required_permission": p.VIEW_LABS, "sort_order": 55},
    {"code": "department.timetable", "label": "Academic timetable", "icon": "CalendarBlank",
     "to": "/department/timetable", "required_permission": p.VIEW_TIMETABLE, "sort_order": 60},
    {"code": "department.details", "label": "Department details", "icon": "Buildings",
     "to": "/department/details", "required_permission": p.VIEW_DETAILS, "sort_order": 65},
]

PERMISSIONS = [
    (p.VIEW_ANNOUNCEMENT, "View relevant Department announcements"),
    (p.PUBLISH_ANNOUNCEMENT, "Publish Department announcements"),
    (p.MANAGE_ANNOUNCEMENT, "Edit, hide or delete active Department announcements"),
    (p.VIEW_STOCK, "View Department stock"),
    (p.INSERT_STOCK, "Insert Department stock"),
    (p.REQUEST_STOCK, "Request Department stock"),
    (p.REVIEW_STOCK, "Decide pending stock requests"),
    (p.ISSUE_STOCK, "Issue approved stock requests"),
    (p.VIEW_STOCK_REQUEST, "View permitted stock requests"),
    (p.SUBMIT_FEEDBACK, "Submit confidential feedback"),
    (p.VIEW_FEEDBACK, "View Department feedback"),
    (p.REVIEW_FEEDBACK, "Perform the initial feedback review"),
    (p.DISPOSE_FEEDBACK, "Resolve or close reviewed feedback"),
    (p.VIEW_NOTICE, "View Department notifications"),
    (p.VIEW_LABS, "View Department lab resources"),
    (p.UPDATE_LABS, "Update Department lab resources"),
    (p.VIEW_TIMETABLE, "View applicable Department timetable slots"),
    (p.UPDATE_TIMETABLE, "Upload and update Department timetables"),
    (p.VIEW_DETAILS, "View Department details and official proposals"),
    (p.UPDATE_DETAILS, "Update general Department information"),
    (p.PROPOSE_DETAILS, "Propose official Department changes"),
    (p.APPROVE_DETAILS, "Decide official Department changes"),
]
SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

_COMMON = [p.VIEW_ANNOUNCEMENT, p.VIEW_NOTICE]
_STOCK = [p.VIEW_STOCK, p.VIEW_STOCK_REQUEST]
_STAFF = [*_COMMON, p.PUBLISH_ANNOUNCEMENT, p.VIEW_FEEDBACK, p.DISPOSE_FEEDBACK, p.VIEW_DETAILS]
_HOD = (*_STAFF, p.VIEW_STOCK_REQUEST, p.MANAGE_ANNOUNCEMENT, p.REVIEW_STOCK, p.APPROVE_DETAILS)
_ADMIN = (*_STAFF, *_STOCK, p.INSERT_STOCK, p.ISSUE_STOCK, p.REVIEW_FEEDBACK, p.VIEW_LABS,
          p.UPDATE_LABS, p.VIEW_TIMETABLE, p.UPDATE_TIMETABLE, p.UPDATE_DETAILS, p.PROPOSE_DETAILS)

ROLE_GRANTS = {
    "faculty": [*_COMMON, *_STOCK, p.PUBLISH_ANNOUNCEMENT, p.REQUEST_STOCK, p.SUBMIT_FEEDBACK,
                p.VIEW_LABS],
    **dict.fromkeys(sorted(STUDENT_ROLES), (*_COMMON, p.SUBMIT_FEEDBACK, p.VIEW_TIMETABLE)),
    **dict.fromkeys(HOD_DEPARTMENTS, _HOD),
    **dict.fromkeys(ADMIN_DEPARTMENTS, _ADMIN),
}


def readiness():
    """Prerequisites shared by seed_modules and the read-only operator check."""
    from django.conf import settings
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes("department")
    missing = []
    if executor.migration_plan(targets):
        missing.append("Apply outstanding migrations with manage.py migrate.")
    if not settings.IAM_SERVICE_TOKEN:
        missing.append("Configure IAM_SERVICE_TOKEN with a directory service credential.")
    return missing
