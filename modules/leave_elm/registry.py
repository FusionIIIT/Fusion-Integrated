MODULE = {
    "code": "leave_elm", "label": "Employee Leave Management", "icon": "CalendarBlank", "base_path": "/leave", "nav_section": "Employee", "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {"code": "leave_elm.mine", "label": "My Leave", "icon": "UserCheck", "to": "/leave/mine", "required_permission": "leave_elm.application.view_self", "sort_order": 5},
    {"code": "leave_elm.queue", "label": "Leave Queue", "icon": "CalendarBlank", "to": "/leave/queue", "required_permission": "leave_elm.task.view", "sort_order": 10},
    {"code": "leave_elm.admin", "label": "Leave Admin", "icon": "Cog", "to": "/leave/admin", "required_permission": "leave_elm.configuration.manage", "sort_order": 20},
]

PERMISSIONS = [
    ("leave_elm.application.view_self", "See own leave applications"),
    ("leave_elm.application.create", "Apply for leave"),
    ("leave_elm.application.review", "Review leave applications"),
    ("leave_elm.application.approve", "Approve leave applications"),
    ("leave_elm.substitute.respond", "Respond to substitute requests"),
    ("leave_elm.task.view", "View leave tasks"),
    ("leave_elm.configuration.manage", "Manage leave configuration"),
    ("leave_elm.record.manage", "Manage leave records"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "faculty": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view"],
    "staff": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view"],
    "Employee": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view"],
    "Unit Head": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review"],
    "Head of Department": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review"],
    "Section Head": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review"],
    "Deputy Registrar (Estt.)": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review"],
    "Establishment Reviewer": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review"],
    "reviewer": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review"],
    "Dean": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review", "leave_elm.application.approve"],
    "Registrar": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review", "leave_elm.application.approve"],
    "Director": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review", "leave_elm.application.approve"],
    "authority": ["leave_elm.application.view_self", "leave_elm.application.create", "leave_elm.substitute.respond", "leave_elm.task.view", "leave_elm.application.review", "leave_elm.application.approve"],
    "Leave Administrator": ["leave_elm.configuration.manage", "leave_elm.record.manage"],
    "Leave Admin": ["leave_elm.configuration.manage", "leave_elm.record.manage"],
    "admin": ["leave_elm.configuration.manage", "leave_elm.record.manage"],
}
