MODULE = {
    "code": "hreis",
    "label": "HR Employee Information",
    "icon": "Users",
    "base_path": "/hreis",
    "nav_section": "HR",
    "sort_order": 30,
    "status": "active",
}

NAV_ITEMS = []

PERMISSIONS = [
    ("hreis.records.view", "View Employee Records"),
    ("hreis.records.manage", "Manage Employee Records"),
    ("hreis.config.manage", "Manage Configuration"),
    ("hreis.requests.submit", "Submit Request"),
    ("hreis.requests.view", "View Requests"),
    ("hreis.requests.decide", "Decide Request"),
    ("hreis.claims.verify", "Verify Claims"),
    ("hreis.claims.settle", "Settle Claims"),
    ("hreis.audit.view", "View Audit Logs"),
    ("hreis.notifications.view", "View Notifications"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "Employee": [
        "hreis.records.view",
        "hreis.requests.submit",
        "hreis.requests.view",
        "hreis.notifications.view",
    ],
    "faculty": [
        "hreis.records.view",
        "hreis.requests.submit",
        "hreis.requests.view",
        "hreis.notifications.view",
    ],
    "staff": [
        "hreis.records.view",
        "hreis.requests.submit",
        "hreis.requests.view",
        "hreis.notifications.view",
    ],
    "HR Administrator": [
        "hreis.records.view",
        "hreis.records.manage",
        "hreis.config.manage",
        "hreis.requests.submit",
        "hreis.requests.view",
        "hreis.claims.verify",
        "hreis.audit.view",
        "hreis.notifications.view",
    ],
    "HOD": [
        "hreis.records.view",
        "hreis.requests.submit",
        "hreis.requests.view",
        "hreis.requests.decide",
        "hreis.notifications.view",
    ],
    "Registrar": [
        "hreis.records.view",
        "hreis.requests.submit",
        "hreis.requests.view",
        "hreis.requests.decide",
        "hreis.notifications.view",
    ],
    "Director": [
        "hreis.records.view",
        "hreis.requests.submit",
        "hreis.requests.view",
        "hreis.requests.decide",
        "hreis.notifications.view",
    ],
    "Accountant": [
        "hreis.records.view",
        "hreis.requests.submit",
        "hreis.requests.view",
        "hreis.notifications.view",
        "hreis.claims.settle",
    ],
}
