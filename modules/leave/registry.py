"""Leave module registration and permission manifest."""

MODULE_CODE = "leave"

PERMISSIONS = [
    ("leave.apply", "Can apply for leave and view own leave status"),
    ("leave.view_own", "Can view own leave applications, balances, and ledger"),
    ("leave.review_substitute", "Can review and respond to substitute requests"),
    ("leave.review_unit_head", "Can review leave requests as Department / Unit Head"),
    ("leave.review_establishment", "Can verify and route requests as Establishment Section"),
    ("leave.sanction", "Can make final leave sanction decisions (Dean / Registrar / Director)"),
    ("leave.admin_manage", "Can manage leave policies, calendars, and offline synchronization"),
]

ROLE_GRANTS = {
    "student": [],
    "faculty": ["leave.apply", "leave.view_own", "leave.review_substitute"],
    "staff": ["leave.apply", "leave.view_own", "leave.review_substitute"],
    "hod": ["leave.apply", "leave.view_own", "leave.review_substitute", "leave.review_unit_head"],
    "dr_establishment": ["leave.apply", "leave.view_own", "leave.review_establishment"],
    "dean": ["leave.apply", "leave.view_own", "leave.sanction"],
    "registrar": ["leave.apply", "leave.view_own", "leave.sanction"],
    "director": ["leave.apply", "leave.view_own", "leave.sanction"],
    "leave_admin": ["leave.apply", "leave.view_own", "leave.admin_manage"],
}
