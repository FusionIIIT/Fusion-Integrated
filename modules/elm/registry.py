MODULE = {"code": "elm", "label": "Employee Leave", "icon": "CalendarBlank",
          "base_path": "/elm", "nav_section": "Employee Leave", "sort_order": 20,
          "status": "active"}

NAV_ITEMS = [
    {"code": "elm.requests", "label": "My Leave", "icon": "CalendarBlank",
     "to": "/elm/requests", "required_permission": "elm.application.self", "sort_order": 10},
    {"code": "elm.balances", "label": "Balances and History", "icon": "ChartBar",
     "to": "/elm/balances", "required_permission": "elm.application.self", "sort_order": 20},
    {"code": "elm.tasks", "label": "Assigned Tasks", "icon": "Checks",
     "to": "/elm/tasks", "required_permission": "elm.task.act", "sort_order": 30},
    {"code": "elm.notifications", "label": "Leave Notifications", "icon": "Bell",
     "to": "/elm/notifications", "required_permission": "elm.notification.self", "sort_order": 40},
    {"code": "elm.configuration", "label": "Leave Administration", "icon": "Gear",
     "to": "/elm/configuration", "required_permission": "elm.configuration.manage", "sort_order": 50},
]

PERMISSIONS = [
    ("elm.application.self", "Apply for and manage one's own leave"),
    ("elm.task.act", "Respond to an assigned leave task in the active role"),
    ("elm.notification.self", "Read one's own leave notifications"),
    ("elm.configuration.manage", "Maintain leave policy, hierarchy, calendars and SLA"),
    ("elm.record.manage", "Maintain records and synchronize already-sanctioned offline leave"),
]

_EMPLOYEE = ["elm.application.self", "elm.task.act", "elm.notification.self"]
_AUTHORITY = ["elm.task.act", "elm.notification.self"]
# PS Appendix A, BR-EL-036: IAM designations and employee basic kinds.
ROLE_GRANTS = {
    "faculty": _EMPLOYEE, "staff": _EMPLOYEE, "Employee": _EMPLOYEE,
    "Substitute": _AUTHORITY, "Unit Head": _AUTHORITY,
    "Deputy Registrar (Estt.)": _AUTHORITY, "Dean": _AUTHORITY,
    "Registrar": _AUTHORITY, "Director": _EMPLOYEE,
    "Leave Administrator": ["elm.configuration.manage", "elm.record.manage", "elm.notification.self"],
}
