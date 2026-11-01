"""IAA module contract consumed by Fusion's permission manifest seeder."""
MODULE = {
    "code": "internal_audit_accounts",
    "label": "Institute Accounts & Audits",
    "icon": "ClipboardCheck",
    "base_path": "/iaa",
    "nav_section": "Administration",
    "sort_order": 40,
    "status": "active",
}

# UI navigation is intentionally empty in this backend-first increment.
# Add links only when matching client routes are implemented.
NAV_ITEMS = []

PERMISSIONS = [
    ("internal_audit_accounts.request.create", "Create expense/voucher requests"),
    ("internal_audit_accounts.request.view", "View operational requests"),
    ("internal_audit_accounts.finance.review", "Review and validate requests"),
    ("internal_audit_accounts.request.approve", "Approve or reject requests"),
    ("internal_audit_accounts.audit.manage", "Manage anomalies and audit observations"),
    ("internal_audit_accounts.policy.manage", "Manage financial-year and approval policy configuration"),
]

SYSTEM_PERMISSIONS = []
SCOPE_PERMISSIONS = []

# These labels follow the IAA v1.3 actor catalogue. Confirm the exact
# designation strings in the target IAM before running permission seeding.
ROLE_GRANTS = {
    "Basic User": ["internal_audit_accounts.request.create"],
    "Finance Staff": [
        "internal_audit_accounts.request.view",
        "internal_audit_accounts.finance.review",
    ],
    "HoD": [
        "internal_audit_accounts.request.view",
        "internal_audit_accounts.request.approve",
    ],
    "Dean": [
        "internal_audit_accounts.request.view",
        "internal_audit_accounts.request.approve",
    ],
    "Director": [
        "internal_audit_accounts.request.view",
        "internal_audit_accounts.request.approve",
    ],
    "Auditor": [
        "internal_audit_accounts.request.view",
        "internal_audit_accounts.audit.manage",
    ],
    # BR-004: configuration access is operationally separate from financial
    # request visibility and approval. This grant must not be widened.
    "System Admin": ["internal_audit_accounts.policy.manage"],
}
