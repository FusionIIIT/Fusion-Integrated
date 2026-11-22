MODULE = {
    "code": "hreis",
    "label": "HR Employee Information",
    "icon": "UsersThree",
    "base_path": "/hreis",
    "nav_section": "HR",
    "sort_order": 35,
    "status": "active",
}

PERMISSIONS = [
    ("hreis.employee.view", "View employee service records in authorized scope"),
    ("hreis.employee.manage", "Create and update official employee service records"),
    ("hreis.request.view", "View HR requests in authorized scope"),
    ("hreis.request.create", "Submit HR requests"),
    ("hreis.request.review", "Verify, route, and decide HR requests"),
    ("hreis.request.assign", "Assign appraisal reviewers"),
    ("hreis.request.manage", "Manage HR workflow policy and requests"),
    ("hreis.claim.update", "Record approved claim financial processing"),
    ("hreis.leave_balance.view", "View leave balances in authorized scope"),
    ("hreis.leave_balance.manage", "Record leave balance adjustments"),
    ("hreis.policy.manage", "Create effective-dated HR policy versions"),
    ("hreis.audit.view", "View authorized HR audit records"),
    ("hreis.notification.view", "View own HR notifications"),
    ("hreis.policy.view", "View effective HR policies"),
]

SYSTEM_PERMISSIONS = []

ROLE_GRANTS = {
    "faculty": [
        "hreis.employee.view",
        "hreis.request.create",
        "hreis.request.view",
        "hreis.notification.view",
    ],
    "staff": [
        "hreis.employee.view",
        "hreis.request.create",
        "hreis.request.view",
        "hreis.notification.view",
    ],
    "hradmin": [
        "hreis.employee.view",
        "hreis.employee.manage",
        "hreis.request.view",
        "hreis.request.review",
        "hreis.request.assign",
        "hreis.request.manage",
        "hreis.leave_balance.view",
        "hreis.leave_balance.manage",
        "hreis.policy.view",
        "hreis.policy.manage",
        "hreis.audit.view",
    ],
    "SectionHead_HR": [
        "hreis.request.view",
        "hreis.request.review",
        "hreis.policy.view",
    ],
    "Accounts Admin": [
        "hreis.request.view",
        "hreis.claim.update",
    ],
    "Director": ["hreis.request.view", "hreis.request.review"],
    "Registrar": ["hreis.request.view", "hreis.request.review"],
    "HOD (CSE)": ["hreis.request.view", "hreis.request.review"],
    "HOD (ECE)": ["hreis.request.view", "hreis.request.review"],
    "HOD (ME)": ["hreis.request.view", "hreis.request.review"],
    "HOD (Design)": ["hreis.request.view", "hreis.request.review"],
    "HOD (NS)": ["hreis.request.view", "hreis.request.review"],
    "HOD (Liberal Arts)": ["hreis.request.view", "hreis.request.review"],
}

NAV_ITEMS = []
SCOPE_PERMISSIONS = []
