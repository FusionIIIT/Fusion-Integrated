from modules.department.permissions import VIEW_ANNOUNCEMENT

MODULE = {
    "code": "department", "label": "Department", "icon": "Buildings",
    "base_path": "/department", "nav_section": "Department", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "department.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/department/announcements",
     "required_permission": VIEW_ANNOUNCEMENT, "sort_order": 10},
]

PERMISSIONS = [(VIEW_ANNOUNCEMENT, "View relevant Department announcements")]
SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

ROLE_GRANTS = {
    "faculty": [VIEW_ANNOUNCEMENT],
    "student": [VIEW_ANNOUNCEMENT],
}
