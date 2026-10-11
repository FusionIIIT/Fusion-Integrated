"""ELM module registry — permissions, navigation, and module configuration.

Registers the Employee Leave Management module with the accesscontrol system,
defines its permissions, navigation items, and module-level grants.
"""

from modules.accesscontrol.models import Module, NavItem
from modules.elm.models import LeaveCategory


#: Permissions this module recognises
PERMISSIONS = [
    ("elm.leave.application.create", "Create a new leave application"),
    ("elm.leave.application.view", "View own leave applications"),
    ("elm.leave.application.view_any", "View any leave application"),
    ("elm.leave.balance.view", "View own leave balances"),
    ("elm.leave.balance.manage", "Manage leave balances (admin)"),
    ("elm.leave.histroy.view", "View own leave history"),
    ("elm.leave.withdraw", "Withdraw a pending leave request"),
    ("elm.leave.cancel-request", "Request cancellation of approved leave"),
    ("elm.leave.extension-request", "Request extension of ongoing leave"),
    ("elm.leave.resumption.submit", "Submit resumption of duty"),
    ("elm.leave.resumption.review", "Review resumption of duty"),
    ("elm.leave.print", "Obtain printable/exportable leave application"),
    ("elm.policy.config", "Configure leave policy parameters"),
    ("elm.holiday.calendar", "Maintain and publish holiday/RH calendar"),
    ("elm.offline.sync", "Record already-sanctioned offline leave"),
    ("elm.records.maintain", "Maintain authorized leave records"),
    ("elm.sla.thresholds.configure", "Configure SLA reminder/escalation thresholds"),
    ("elm.substitute.nominate", "Nominate a substitute for responsibility coverage"),
    ("elm.substitute.replace", "Nominate a replacement substitute after decline"),
    ("elm.yearend.execute", "Execute year-end leave processing"),
    ("elm.sla.process", "Process SLA threshold event"),
]

SYSTEM_PERMISSIONS = [
    "elm.yearend.execute",  # May be restricted to specific roles
    "elm.sla.process",      # Configurable threshold processing
]


#: Keyed by designation name for role-based module grants
#: In production, these would be keyed by actual designation names from IAM
ROLE_GRANTS = {
    # Example grants - actual designation names would come from the institute's
    # designation configuration
    "faculty": ["elm.leave.application.view", "elm.leave.balance.view",
                "elm.leave.print", "elm.holiday.calendar"],
    "staff": ["elm.leave.application.create", "elm.leave.application.view",
              "elm.leave.balance.view", "elm.leave.withdraw",
              "elm.leave.print"],
    "unit_head": ["elm.leave.application.view", "elm.leave.balance.view",
                  "elm.leave.histroy.view", "elm.policy.config",
                  "elm.offline.sync", "elm.records.maintain"],
    "leave_administrator": ["elm.leave.balance.manage", "elm.policy.config",
                            "elm.holiday.calendar", "elm.offline.sync",
                            "elm.records.maintain", "elm.yearend.execute",
                            "elm.sla.thresholds.configure"],
    "deputy_registrar": ["elm.leave.application.view", "elm.leave.balance.view",
                         "elm.leave.histroy.view", "elm.policy.config",
                         "elm.offline.sync", "elm.records.maintain",
                         "elm.yearend.execute", "elm.sla.process"],
    "director": ["elm.leave.application.view", "elm.leave.balance.view",
                 "elm.leave.histroy.view", "elm.yearend.execute",
                 "elm.sla.process"],
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
            required_permission="elm.leave.application.create",
            sort_order=10,
        ),
        # View own balances
        NavItem(
            code="elm_balances",
            label="Leave Balances",
            icon="FaBalanceScale",
            to="/elm/balances",
            required_permission="elm.leave.balance.view",
            sort_order=20,
        ),
        # View history
        NavItem(
            code="elm_history",
            label="Leave History",
            icon="FaHistory",
            to="/elm/history",
            required_permission="elm.leave.histroy.view",
            sort_order=30,
        ),
        # Printable export
        NavItem(
            code="elm_print",
            label="Print Application",
            icon="FaPrint",
            to="/elm/print",
            required_permission="elm.leave.print",
            sort_order=40,
        ),
        # SLA configuration (admin only)
        NavItem(
            code="elm_sla",
            label="SLA Thresholds",
            icon="FaClock",
            to="/elm/sla/thresholds",
            required_permission="elm.sla.thresholds.configure",
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
        entry = {"code": "modules.elm", "label": "Employee Leave Management",
                 "icon": "FaUserInjured"}
        # Check if we need links or just a section header
        has_links = any(
            item.required_permission in perms
            for item in elm_nav_items
            if item.required_permission
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
    from modules.accesscontrol.models import Module
    return list(Module.objects.filter(
        code="modules.elm", status="active"
    ).values_list("code", flat=True))