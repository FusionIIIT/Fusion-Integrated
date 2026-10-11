"""ELM module visibility, navigation, and IAM permission grants."""

MODULE = {
    "code": "elm",
    "label": "Employee Leave",
    "icon": "Calendar",
    "base_path": "/elm",
    "nav_section": "Human Resources",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.mine",
        "label": "My Leave",
        "icon": "Calendar",
        "to": "/elm/mine",
        "required_permission": "elm.leave_request.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.queue",
        "label": "Approval Queue",
        "icon": "ClipboardCheck",
        "to": "/elm/queue",
        "required_permission": "elm.workflow.view",
        "sort_order": 20,
    },
]

PERMISSIONS = [
    ("elm.leave_request.view_self", "View own leave and balances"),
    ("elm.leave_request.create", "Submit leave requests"),
    ("elm.leave_request.withdraw", "Withdraw pending leave requests"),
    ("elm.substitute.respond", "Respond to or replace a substitute assignment"),
    ("elm.workflow.view", "View assigned leave workflow tasks"),
    ("elm.workflow.review", "Review leave requests as Unit Head"),
    ("elm.workflow.route", "Verify and route higher-sanction requests"),
    ("elm.workflow.sanction", "Make final leave decisions"),
    ("elm.configuration.manage", "Manage leave policy, employee units, and approval routes"),
    ("elm.calendar.manage", "Maintain and publish the holiday/RH calendar"),
    ("elm.record.manage", "Maintain authorized leave records"),
]

SYSTEM_PERMISSIONS = []

_EMPLOYEE = [
    "elm.leave_request.view_self",
    "elm.leave_request.create",
    "elm.leave_request.withdraw",
    "elm.substitute.respond",
]
_UNIT_HEAD = [*_EMPLOYEE, "elm.workflow.view", "elm.workflow.review"]
_SANCTIONER = [*_UNIT_HEAD, "elm.workflow.route", "elm.workflow.sanction"]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "unit_head": _UNIT_HEAD,
    "establishment_officer": _SANCTIONER,
    "deputy_registrar_estt": _SANCTIONER,
    "Deputy Registrar (Estt.)": _SANCTIONER,
    "dean": _SANCTIONER,
    "Dean": _SANCTIONER,
    "registrar": _SANCTIONER,
    "Registrar": _SANCTIONER,
    "director": _SANCTIONER,
    "Director": _SANCTIONER,
    "leave_administrator": [
        *_EMPLOYEE,
        "elm.workflow.view",
        "elm.configuration.manage",
        "elm.calendar.manage",
        "elm.record.manage",
    ],
}
