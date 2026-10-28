"""Server-driven ELM navigation and permission catalogue.

Role grants use the actor labels in the source specifications as proposed
IAM designation names. Confirm/provision the exact names in globals_designation
before activating the module. See docs/09-elm/elm-blueprint.md.
"""

MODULE = {
    "code": "elm",
    "label": "Employee Leave Management",
    "icon": "CalendarCheck",
    "base_path": "/elm",
    "nav_section": "Employee Services",
    "sort_order": 30,
    "status": "draft",
}
NAV_ITEMS = [
    {
        "code": "elm.mine",
        "label": "My Leave",
        "icon": "CalendarDays",
        "to": "/elm/requests",
        "required_permission": "elm.request.view_self",
        "sort_order": 10,
    },
    {
        "code": "elm.tasks",
        "label": "Leave Tasks",
        "icon": "ClipboardCheck",
        "to": "/elm/tasks",
        "required_permission": "elm.request.review",
        "sort_order": 20,
    },
    {
        "code": "elm.policy",
        "label": "Leave Policy",
        "icon": "Settings2",
        "to": "/elm/policy",
        "required_permission": "elm.policy.manage",
        "sort_order": 30,
    },
]
PERMISSIONS = [
    ("elm.request.create", "Submit leave requests"),
    ("elm.request.modify", "Modify own pending leave requests"),
    ("elm.request.view_self", "View own leave requests and balances"),
    ("elm.request.review", "Review requests as Unit Head"),
    ("elm.request.route", "Verify and route requests through Establishment"),
    ("elm.request.sanction", "Make final sanctioning decisions"),
    ("elm.request.withdraw", "Withdraw own pending requests"),
    ("elm.request.cancel", "Request cancellation of approved leave"),
    ("elm.request.cancel_review", "Decide approved-leave cancellation"),
    ("elm.request.extend", "Request extension of ongoing leave"),
    ("elm.request.resume", "Submit resumption of duty"),
    ("elm.request.verify_resume", "Verify resumption of duty"),
    ("elm.substitute.respond", "Accept or decline substitute assignment"),
    ("elm.policy.manage", "Maintain and publish leave policy"),
    ("elm.calendar.manage", "Maintain and publish holiday/RH calendar"),
    ("elm.sla.remind", "Send SLA reminders"),
    ("elm.sla.escalate", "Escalate overdue SLA tasks"),
    ("elm.year_end.process", "Process annual leave balances"),
]
SYSTEM_PERMISSIONS = ["elm.sla.remind", "elm.sla.escalate", "elm.year_end.process"]
ROLE_GRANTS = {
    # Names are copied from the source actor inventory. Verify/provision these
    # exact designation labels in IAM before activating the module.
    "Employee": [
        "elm.request.create",
        "elm.request.modify",
        "elm.request.view_self",
        "elm.request.withdraw",
        "elm.request.cancel",
        "elm.request.extend",
        "elm.request.resume",
    ],
    "Substitute / Responsibility Holder": ["elm.substitute.respond"],
    "Unit Head": ["elm.request.review", "elm.request.verify_resume"],
    "Deputy Registrar (Estt.)": ["elm.request.route", "elm.request.verify_resume"],
    "Dean": ["elm.request.sanction", "elm.request.cancel_review"],
    "Registrar": ["elm.request.sanction", "elm.request.cancel_review"],
    "Director": ["elm.request.sanction", "elm.request.cancel_review"],
    "Leave Administrator": ["elm.request.view_self", "elm.policy.manage", "elm.calendar.manage"],
}
