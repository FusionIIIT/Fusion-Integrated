from typing import Dict, List, Tuple

from modules.accesscontrol.registry import ModuleConfig

MODULE = ModuleConfig(
    code="leave",
    label="Employee Leave",
    icon="Calendar",
    base_path="/leave",
    nav_section="Services",
    sort_order=20,
    status="active",
)

NAV_ITEMS: List[Dict[str, str]] = [
    {
        "to": "/leave/apply",
        "label": "Apply Leave",
        "required_permission": "leave.request.create",
    },
    {
        "to": "/leave/my-leaves",
        "label": "My Leaves",
        "required_permission": "leave.request.view_self",
    },
    {
        "to": "/leave/substitute",
        "label": "Substitute Requests",
        "required_permission": "leave.substitute.respond",
    },
    {
        "to": "/leave/approvals",
        "label": "Approvals",
        "required_permission": "leave.request.approve",
    },
    {
        "to": "/leave/resumptions",
        "label": "Resumptions",
        "required_permission": "leave.resumption.review",
    },
    {
        "to": "/leave/admin",
        "label": "Leave Admin",
        "required_permission": "leave.admin.manage",
    },
]

PERMISSIONS: Tuple[Tuple[str, str], ...] = (
    ("leave.request.create", "Create Leave Request"),
    ("leave.request.view_self", "View Own Leave Requests"),
    ("leave.request.view", "View All Leave Requests"),
    ("leave.substitute.respond", "Respond to Substitute Requests"),
    ("leave.request.approve", "Approve Leave Requests"),
    ("leave.cancellation.request", "Request Cancellation"),
    ("leave.extension.request", "Request Extension"),
    ("leave.resumption.submit", "Submit Resumption"),
    ("leave.resumption.review", "Review Resumption"),
    ("leave.admin.manage", "Manage Leave Administration"),
    ("leave.offline.record", "Record Offline Leave"),
)

SYSTEM_PERMISSIONS: List[str] = [
    "leave.system.year_end",
    "leave.system.sla_sweep",
]

ROLE_GRANTS: Dict[str, List[str]] = {
    "faculty": [
        "leave.request.create",
        "leave.request.view_self",
        "leave.cancellation.request",
        "leave.extension.request",
    ],
    "staff": [
        "leave.request.create",
        "leave.request.view_self",
        "leave.cancellation.request",
        "leave.extension.request",
    ],
    "Unit Head": [
        "leave.request.create",
        "leave.request.view_self",
        "leave.request.approve",
        "leave.cancellation.request",
        "leave.extension.request",
    ],
    "Dean": [
        "leave.request.create",
        "leave.request.view_self",
        "leave.request.approve",
        "leave.cancellation.request",
        "leave.extension.request",
    ],
    "Registrar": [
        "leave.request.create",
        "leave.request.view_self",
        "leave.request.approve",
        "leave.cancellation.request",
        "leave.extension.request",
    ],
    "Director": [
        "leave.request.create",
        "leave.request.view_self",
        "leave.request.approve",
        "leave.cancellation.request",
        "leave.extension.request",
        "leave.resumption.review",
    ],
    "Leave Administrator": [
        "leave.request.create",
        "leave.request.view",
        "leave.request.approve",
        "leave.cancellation.request",
        "leave.extension.request",
        "leave.resumption.submit",
        "leave.resumption.review",
        "leave.admin.manage",
        "leave.offline.record",
    ],
}
