"""ELM module registry — permissions, navigation, and module configuration.

Registers the Employee Leave Management module with the accesscontrol system,
defines its permissions, navigation items, and module-level grants.
"""

from modules.accesscontrol.models import Module, NavItem

MODULE = {
    "code": "modules.elm",
    "label": "Employee Leave Management",
    "icon": "Leaf",
    "base_path": "/elm",
    "nav_section": "Employee Leave Management",
    "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    {
        "code": "elm.apply",
        "label": "Apply for Leave",
        "icon": "Leaf",
        "to": "/elm/apply",
        "required_permission": "modules.elm.application.create",
        "sort_order": 10,
    },
    {
        "code": "elm.balances",
        "label": "Leave Balances",
        "icon": "Scale",
        "to": "/elm/balances",
        "required_permission": "modules.elm.balance.view",
        "sort_order": 20,
    },
    {
        "code": "elm.history",
        "label": "Leave History",
        "icon": "History",
        "to": "/elm/history",
        "required_permission": "modules.elm.history.view",
        "sort_order": 30,
    },
    {
        "code": "elm.print",
        "label": "Print Application",
        "icon": "Printer",
        "to": "/elm/print",
        "required_permission": "modules.elm.application.print",
        "sort_order": 40,
    },
    {
        "code": "elm.approvals",
        "label": "Leave Approvals",
        "icon": "ClipboardCheck",
        "to": "/elm/approvals",
        "required_permission": "modules.elm.workflow.review",
        "sort_order": 50,
    },
    {
        "code": "elm.routing",
        "label": "Approval Routing",
        "icon": "Settings",
        "to": "/elm/routing",
        "required_permission": "modules.elm.workflow.configure",
        "sort_order": 60,
    },
    {
        "code": "elm.sla",
        "label": "SLA Thresholds",
        "icon": "Clock",
        "to": "/elm/sla/thresholds",
        "required_permission": "modules.elm.sla.configure_thresholds",
        "sort_order": 90,
    },
    {
        "code": "elm.year_end",
        "label": "Year-End Processing",
        "icon": "Calendar",
        "to": "/elm/year-end",
        "required_permission": "modules.elm.yearend.execute",
        "sort_order": 100,
    },
]

#: Permissions this module recognises
PERMISSIONS = [
    ("modules.elm.application.create", "Create a new leave application"),
    ("modules.elm.application.view", "View own leave applications"),
    ("modules.elm.balance.view", "View own leave balances"),
    ("modules.elm.history.view", "View own leave history"),
    ("modules.elm.leave.withdraw", "Withdraw a pending leave request"),
    ("modules.elm.leave.cancel_request", "Request cancellation of approved leave"),
    ("modules.elm.leave.extension_request", "Request extension of ongoing leave"),
    ("modules.elm.resumption.submit", "Submit resumption of duty"),
    ("modules.elm.resumption.review", "Review resumption of duty"),
    ("modules.elm.workflow.review", "Review leave approval workflow items"),
    ("modules.elm.workflow.configure", "Configure leave approval routing roles"),
    ("modules.elm.application.print", "Obtain printable/exportable leave application"),
    ("modules.elm.policy.configure", "Configure leave policy parameters"),
    ("modules.elm.calendar.manage", "Maintain and publish holiday/RH calendar"),
    ("modules.elm.offline.record", "Record already-sanctioned offline leave"),
    ("modules.elm.records.maintain", "Maintain authorized leave records"),
    ("modules.elm.sla.configure_thresholds", "Configure SLA reminder/escalation thresholds"),
    ("modules.elm.substitute.replace", "Nominate a replacement substitute after decline"),
    ("modules.elm.yearend.execute", "Execute year-end leave processing"),
    ("modules.elm.sla.process", "Process SLA threshold event"),
]

SYSTEM_PERMISSIONS = [
    "modules.elm.sla.process",  # Event-triggered SLA handler
    "modules.elm.yearend.execute",
]


#: Keyed by designation name for role-based module grants
#: In production, these would be keyed by actual designation names from IAM
ROLE_GRANTS = {
    # Example grants - actual designation names would come from the institute's
    # designation configuration
    "faculty": [
        "modules.elm.application.create",
        "modules.elm.application.view",
        "modules.elm.balance.view",
        "modules.elm.history.view",
        "modules.elm.leave.withdraw",
        "modules.elm.leave.cancel_request",
        "modules.elm.leave.extension_request",
        "modules.elm.resumption.submit",
        "modules.elm.application.print",
        "modules.elm.substitute.replace",
    ],
    "staff": [
        "modules.elm.application.create",
        "modules.elm.application.view",
        "modules.elm.balance.view",
        "modules.elm.history.view",
        "modules.elm.leave.withdraw",
        "modules.elm.leave.cancel_request",
        "modules.elm.leave.extension_request",
        "modules.elm.resumption.submit",
        "modules.elm.application.print",
        "modules.elm.substitute.replace",
    ],
    "unit_head": [
        "modules.elm.resumption.review",
        "modules.elm.application.view",
        "modules.elm.balance.view",
        "modules.elm.history.view",
        "modules.elm.workflow.review",
        "modules.elm.policy.configure",
        "modules.elm.offline.record",
        "modules.elm.records.maintain",
    ],
    "leave_administrator": [
        "modules.elm.workflow.configure",
        "modules.elm.policy.configure",
        "modules.elm.calendar.manage",
        "modules.elm.offline.record",
        "modules.elm.records.maintain",
        "modules.elm.sla.configure_thresholds",
    ],
    "deputy_registrar": [
        "modules.elm.workflow.review",
        "modules.elm.resumption.review",
        "modules.elm.application.view",
        "modules.elm.balance.view",
        "modules.elm.history.view",
        "modules.elm.policy.configure",
        "modules.elm.offline.record",
        "modules.elm.records.maintain",
    ],
    "director": [
        "modules.elm.workflow.review",
        "modules.elm.resumption.review",
        "modules.elm.application.view",
        "modules.elm.balance.view",
        "modules.elm.history.view",
    ],
}


def build_navigation(*, granted_module_codes=None, permissions=None):
    """Build navigation for the ELM module, already filtered and in render shape.

    The client does zero filtering — it cannot draw a module the server did not
    send.
    """
    from modules.accesscontrol.contracts import build_navigation as _build

    perms = set(permissions or [])
    granted = set(granted_module_codes or [])

    # ELM-specific navigation items
    elm_nav_items = [
        # Leave application
        NavItem(
            code="elm.apply_leave",
            label="Apply for Leave",
            icon="FaLeaf",
            to="/elm/apply",
            required_permission="modules.elm.application.create",
            sort_order=10,
        ),
        # View own balances
        NavItem(
            code="elm_balances",
            label="Leave Balances",
            icon="FaBalanceScale",
            to="/elm/balances",
            required_permission="modules.elm.balance.view",
            sort_order=20,
        ),
        # View history
        NavItem(
            code="elm_history",
            label="Leave History",
            icon="FaHistory",
            to="/elm/history",
            required_permission="modules.elm.history.view",
            sort_order=30,
        ),
        # Printable export
        NavItem(
            code="elm_print",
            label="Print Application",
            icon="FaPrint",
            to="/elm/print",
            required_permission="modules.elm.application.print",
            sort_order=40,
        ),
        NavItem(
            code="elm_approvals",
            label="Leave Approvals",
            icon="FaClipboardCheck",
            to="/elm/approvals",
            required_permission="modules.elm.workflow.review",
            sort_order=50,
        ),
        NavItem(
            code="elm_routing",
            label="Approval Routing",
            icon="FaCogs",
            to="/elm/routing",
            required_permission="modules.elm.workflow.configure",
            sort_order=60,
        ),
        # SLA configuration (admin only)
        NavItem(
            code="elm_sla",
            label="SLA Thresholds",
            icon="FaClock",
            to="/elm/sla/thresholds",
            required_permission="modules.elm.sla.configure_thresholds",
            sort_order=90,
        ),
    ]

    # Build using the base accesscontrol builder, then add ELM-specific items
    base_result = _build(
        granted_module_codes=granted or [],
        permissions=perms,
    )

    # Add ELM module entry if granted
    if granted and "modules.elm" in granted:
        entry = {
            "code": "modules.elm",
            "label": "Employee Leave Management",
            "icon": "FaUserInjured",
        }
        # Check if we need links or just a section header
        has_links = any(
            item.required_permission in perms for item in elm_nav_items if item.required_permission
        )
        if has_links:
            entry["links"] = [
                {"code": n.code, "label": n.label, "icon": n.icon, "to": n.to}
                for n in elm_nav_items
                if not n.required_permission or n.required_permission in perms
            ]
        else:
            entry["to"] = elm_nav_items[0].to if elm_nav_items else "/elm/apply"
        base_result.append(entry)

    return base_result


def active_module_codes():
    """Return codes of active ELM module entries in the database."""
    return list(
        Module.objects.filter(code="modules.elm", status="active").values_list("code", flat=True)
    )
