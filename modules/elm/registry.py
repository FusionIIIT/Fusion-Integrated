# ELM module registry
MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarMinus",
    "base_path": "/elm",
    "nav_section": "HR",
    "sort_order": 5,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.leave_requests",
        "label": "Leave Requests",
        "icon": "CalendarMinus",
        "to": "/elm/requests",
        "required_permission": "elm.leave_requests.view",
        "sort_order": 10,
    },
    {
        "code": "elm.leave_balances",
        "label": "Leave Balances",
        "icon": "CalendarCheck",
        "to": "/elm/balances",
        "required_permission": "elm.leave_balances.view",
        "sort_order": 20,
    },
    {
        "code": "elm.leave_types",
        "label": "Leave Types",
        "icon": "Tag",
        "to": "/elm/types",
        "required_permission": "elm.leave_types.view",
        "sort_order": 30,
    },
    {
        "code": "elm.leave_policies",
        "label": "Leave Policies",
        "icon": "FileText",
        "to": "/elm/policies",
        "required_permission": "elm.leave_policies.view",
        "sort_order": 40,
    },
]

SYSTEM_PERMISSIONS = [
    "elm.leave_requests.auto_approve",
    "elm.leave_requests.manual_approve",
    "elm.leave_balances.update",
    "elm.leave_policies.edit",
]

# Platform manifest declarations for the generated navigation/action names.
PERMISSIONS = [
    ("elm.leave_requests.view", "View leave requests"),
    ("elm.leave_balances.view", "View leave balances"),
    ("elm.leave_types.view", "View leave types"),
    ("elm.leave_policies.view", "View leave policies"),
    ("elm.leave_requests.approve", "Process generated leave-request actions"),
    ("elm.leave_balances.manage", "Update leave balances"),
    ("elm.leave_policies.manage", "Maintain generated leave configuration"),
    ("elm.leave_requests.apply", "Submit and manage own leave requests"),
    ("elm.leave_records.manage", "Maintain authorized leave records"),
    *[(code, code.rsplit(".", 1)[-1]) for code in SYSTEM_PERMISSIONS],
]
_VIEW = [item["required_permission"] for item in NAV_ITEMS]
ROLE_GRANTS = {
    "Employee": [*_VIEW, "elm.leave_requests.apply"],
    "Unit Head": [*_VIEW, "elm.leave_requests.apply", "elm.leave_requests.approve"],
    "Deputy Registrar (Estt.)": [*_VIEW, "elm.leave_requests.apply", "elm.leave_requests.approve"],
    "Dean": [*_VIEW, "elm.leave_requests.apply", "elm.leave_requests.approve"],
    "Registrar": [*_VIEW, "elm.leave_requests.apply", "elm.leave_requests.approve"],
    "Director": [*_VIEW, "elm.leave_requests.apply", "elm.leave_requests.approve"],
    "Leave Administrator": [
        *_VIEW,
        "elm.leave_requests.apply",
        "elm.leave_policies.manage",
        "elm.leave_balances.manage",
        "elm.leave_records.manage",
    ],
}
