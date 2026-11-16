MODULE = {
    "code": "health_center", "label": "Health Center", "icon": "FirstAidKit",
    "base_path": "/phc", "nav_section": "Health Center", "sort_order": 40,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "health_center.schedule.view", "label": "Doctor Schedule",
     "icon": "CalendarBlank", "to": "/phc",
     "required_permission": "health_center.schedule.view", "sort_order": 10},
    {"code": "health_center.records", "label": "My Medical Records",
     "icon": "UserCheck", "to": "/phc/records",
     "required_permission": "health_center.record.view_self", "sort_order": 20},
    {"code": "health_center.manage-schedule", "label": "Manage Schedules",
     "icon": "CalendarPlus", "to": "/phc/manage-schedule",
     "required_permission": "health_center.schedule.manage", "sort_order": 30},
    {"code": "health_center.visits", "label": "Record Visit",
     "icon": "Stethoscope", "to": "/phc/visits",
     "required_permission": "health_center.record.manage", "sort_order": 40},
]

PERMISSIONS = [
    ("health_center.schedule.view", "View doctor schedules"),
    ("health_center.schedule.manage", "Create and modify schedules"),
    ("health_center.record.view_self", "View own medical records"),
    ("health_center.record.manage", "Record new visits and update history"),
]

ROLE_GRANTS = {
    "student": [
        "health_center.schedule.view",
        "health_center.record.view_self",
    ],
    "faculty": [
        "health_center.schedule.view",
        "health_center.record.view_self",
    ],
    "staff": [
        "health_center.schedule.view",
        "health_center.record.view_self",
    ],
    "phc_staff": [
        "health_center.schedule.view",
        "health_center.schedule.manage",
        "health_center.record.view_self",
        "health_center.record.manage",
    ],
}
