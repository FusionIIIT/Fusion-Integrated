"""Permission declarations; grants must be provisioned through Fusion IAM."""

MODULE_CODE = "iaa"

PERMISSIONS = [
    ("iaa.request.create", "Create expense/voucher drafts"),
    ("iaa.request.view_self", "View own expense/voucher requests"),
    ("iaa.request.view", "View role-scoped expense/voucher requests"),
    ("iaa.request.submit", "Submit expense/voucher requests"),
    ("iaa.finance.validate", "Validate financial requests"),
    ("iaa.finance.record", "Record internal processing completion"),
    ("iaa.approval.decide", "Approve or reject assigned requests"),
    ("iaa.approval.escalate", "Process escalated approvals"),
    ("iaa.ta.create", "Submit travel allowance claims"),
    ("iaa.ta.view_self", "View own travel allowance claims"),
    ("iaa.ta.view", "View role-scoped travel allowance claims"),
    ("iaa.ta.verify", "Verify travel allowance claims"),
    ("iaa.anomaly.flag", "Flag material anomalies"),
    ("iaa.anomaly.resolve", "Resolve assigned anomalies"),
    ("iaa.audit.review", "Review financial records for audit"),
    ("iaa.observation.respond", "Respond to assigned observations"),
    ("iaa.observation.verify", "Verify observation responses"),
    ("iaa.report.view", "View role-scoped IAA reports"),
    ("iaa.report.export", "Export role-scoped IAA reports"),
    ("iaa.notification.view", "View assigned IAA notifications"),
    ("iaa.admin.configure", "Configure IAA roles and policies"),
    ("iaa.role.switch", "Switch active IAA role"),
]

ROLE_PERMISSIONS = {
    "basic_user": {
        "iaa.request.create", "iaa.request.view_self", "iaa.request.view", "iaa.request.submit",
        "iaa.ta.create", "iaa.ta.view_self", "iaa.ta.view", "iaa.observation.respond",
        "iaa.role.switch", "iaa.notification.view",
    },
    "finance_staff": {
        "iaa.request.view", "iaa.finance.validate", "iaa.finance.record",
        "iaa.ta.view", "iaa.ta.verify", "iaa.anomaly.flag", "iaa.anomaly.resolve", "iaa.report.view",
        "iaa.report.export", "iaa.notification.view", "iaa.role.switch",
    },
    "hod": {"iaa.request.view", "iaa.ta.view", "iaa.approval.decide", "iaa.anomaly.resolve", "iaa.report.view", "iaa.notification.view"},
    "dean": {"iaa.request.view", "iaa.ta.view", "iaa.approval.decide", "iaa.anomaly.resolve", "iaa.report.view", "iaa.notification.view"},
    "director": {"iaa.request.view", "iaa.ta.view", "iaa.approval.decide", "iaa.anomaly.resolve", "iaa.report.view", "iaa.notification.view"},
    "auditor": {
        "iaa.request.view", "iaa.ta.view",
        "iaa.audit.review", "iaa.anomaly.flag", "iaa.anomaly.resolve",
        "iaa.observation.verify", "iaa.report.view", "iaa.report.export",
        "iaa.notification.view", "iaa.role.switch",
    },
    # Deliberately no operational data or approval permissions.
    "system_admin": {"iaa.admin.configure", "iaa.role.switch"},
}



