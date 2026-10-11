"""Leave module registry entry and permissions."""
from core.registry import ModuleManifest as M, NavItem as N, Permission as P

MODULE = M(
    code="leave",
    label="Leave Management",
    icon="FaCalendarAlt",
    base_path="/leave",
    nav_section="Services",
    sort_order=210,
    status="active",
)

PERMISSIONS = [
    P("leave.request.view_self", "View own leave requests and balance"),
    P("leave.request.create",    "Apply for leave"),
    P("leave.request.delete",    "Cancel own pending request"),
    P("leave.request.view",      "View leave requests within scope"),
    P("leave.request.approve",   "Approve or reject a leave request"),
    P("leave.balance.update",    "Adjust a leave balance", dangerous=True),
    P("leave.type.manage",       "Configure leave types and entitlement rules"),
]

NAV_ITEMS = [
    N("leave.mine",    "My Leaves",    "FaCalendarCheck", "/leave/my-requests",
      required_permission="leave.request.view_self"),
    N("leave.apply",   "Apply Leave",  "FaCalendarPlus",  "/leave/apply",
      required_permission="leave.request.create"),
    N("leave.queue",   "Approvals",    "FaInbox",         "/leave/queue",
      required_permission="leave.request.approve"),
    N("leave.balances","All Balances", "FaTable",         "/leave/balances",
      required_permission="leave.balance.update"),
]

SYSTEM_PERMISSIONS: list[str] = []

ROLE_GRANTS: dict[str, list[str]] = {
    "faculty": [
        "leave.request.view_self",
        "leave.request.create",
        "leave.request.delete",
    ],
    "staff": [
        "leave.request.view_self",
        "leave.request.create",
        "leave.request.delete",
    ],
    "student": [],
    "hr_officer": [
        "leave.request.view_self",
        "leave.request.create",
        "leave.request.delete",
        "leave.request.view",
        "leave.request.approve",
        "leave.balance.update",
        "leave.type.manage",
    ],
    "director": [
        "leave.request.view",
        "leave.request.approve",
    ],
    "dean": [
        "leave.request.view",
        "leave.request.approve",
    ],
    "hod": [
        "leave.request.view",
        "leave.request.approve",
    ],
}
