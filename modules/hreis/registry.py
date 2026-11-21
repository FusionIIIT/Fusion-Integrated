"""IAM manifest and server-driven navigation for live HR-EIS routes.

Finance uses a provisional mapping to the existing IAM 'Accounts Admin'
designation. This is a Student 1 implementation assumption, not proof that
the institute approved the assignment of financial responsibility.
"""

MODULE = {
    "code": "hreis",
    "label": "Human Resources",
    "icon": "Users",
    "base_path": "/hreis",
    "nav_section": "Administration",
    "sort_order": 30,
    "status": "active",
}

PERMISSIONS = [
    ("hreis.service_record.view", "View scoped HR service records"),
    ("hreis.service_record.create", "Create official employee service records"),
    ("hreis.service_record.update", "Maintain official employee service records"),
    ("hreis.request.view", "View scoped HR requests"),
    ("hreis.approval.view", "Open the assigned HR-EIS approval queue"),
    ("hreis.leave.create", "Submit own leave requests"),
    ("hreis.balance.manage", "Record verified, audited employee leave credits"),
    ("hreis.leave.approve", "Approve or reject assigned leave requests"),
    ("hreis.appraisal.create", "Submit own appraisal"),
    ("hreis.appraisal.assign", "Assign appraisal reviewers"),
    ("hreis.appraisal.approve", "Finalize assigned appraisals"),
    ("hreis.claim.create", "Submit own LTC/CPDA claims"),
    ("hreis.claim.review", "HR verify LTC/CPDA documentation and eligibility"),
    ("hreis.claim.approve", "Approve assigned LTC/CPDA claims"),
    ("hreis.finance.review", "Verify financial correctness of approved LTC/CPDA claims"),
    ("hreis.finance.update", "Record externally reported LTC/CPDA processing status"),
    ("hreis.policy.view", "Read effective HR policy"),
    ("hreis.policy.manage", "Create effective-dated HR policy"),
    ("hreis.audit.view", "Review restricted HR compliance trail"),
    ("hreis.notification.view", "Read own HR-EIS notifications"),
    ("hreis.notification.publish", "System generate HR notifications"),
]

SYSTEM_PERMISSIONS = [
    "hreis.notification.publish",
]

_EMPLOYEE = [
    "hreis.service_record.view",
    "hreis.request.view",
    "hreis.leave.create",
    "hreis.appraisal.create",
    "hreis.claim.create",
    "hreis.notification.view",
]
_HR = [
    "hreis.service_record.view",
    "hreis.service_record.create",
    "hreis.service_record.update",
    "hreis.balance.manage",
    "hreis.request.view",
    "hreis.appraisal.assign",
    "hreis.claim.review",
    "hreis.policy.view",
    "hreis.policy.manage",
    "hreis.audit.view",
    "hreis.notification.view",
]
_APPROVER = [
    "hreis.service_record.view",
    "hreis.request.view",
    "hreis.approval.view",
    "hreis.leave.approve",
    "hreis.appraisal.approve",
    "hreis.claim.approve",
    "hreis.notification.view",
]

ROLE_GRANTS = {
    "faculty": _EMPLOYEE,
    "staff": _EMPLOYEE,
    "hradmin": _HR,
    "Accounts Admin": [
        "hreis.finance.review",
        "hreis.finance.update",
        "hreis.request.view",
        "hreis.service_record.view",
        "hreis.notification.view",
    ],
    "HOD (CSE)": _APPROVER,
    "HOD (Design)": _APPROVER,
    "HOD (ECE)": _APPROVER,
    "HOD (Liberal Arts)": _APPROVER,
    "HOD (ME)": _APPROVER,
    "HOD (NS)": _APPROVER,
    "Registrar": _APPROVER,
    "Director": _APPROVER,
}

SCOPE_PERMISSIONS = {
    "owner": ["hreis.service_record.view", "hreis.request.view", "hreis.notification.view"],
    "current_authority": ["hreis.leave.approve", "hreis.claim.approve", "hreis.appraisal.approve"],
}

NAV_ITEMS = [
    {
        "code": "hreis.my_record",
        "label": "My Service Record",
        "icon": "IdentificationCard",
        "to": "/hreis/my-record",
        "required_permission": "hreis.service_record.view",
        "sort_order": 10,
    },
    {
        "code": "hreis.requests",
        "label": "HR Requests",
        "icon": "ClipboardText",
        "to": "/hreis/requests",
        "required_permission": "hreis.request.view",
        "sort_order": 20,
    },
    {
        "code": "hreis.leave",
        "label": "Leave Requests",
        "icon": "Calendar",
        "to": "/hreis/leave",
        "required_permission": "hreis.leave.create",
        "sort_order": 22,
    },
    {
        "code": "hreis.claims",
        "label": "LTC and CPDA",
        "icon": "Wallet",
        "to": "/hreis/claims",
        "required_permission": "hreis.claim.create",
        "sort_order": 24,
    },
    {
        "code": "hreis.appraisals",
        "label": "Annual Appraisals",
        "icon": "ClipboardText",
        "to": "/hreis/appraisals",
        "required_permission": "hreis.appraisal.create",
        "sort_order": 26,
    },
    {
        "code": "hreis.approvals",
        "label": "Assigned Approvals",
        "icon": "Checks",
        "to": "/hreis/approvals",
        "required_permission": "hreis.approval.view",
        "sort_order": 28,
    },
    {
        "code": "hreis.finance",
        "label": "Financial Processing",
        "icon": "Wallet",
        "to": "/hreis/finance",
        "required_permission": "hreis.finance.review",
        "sort_order": 29,
    },
    {
        "code": "hreis.administration",
        "label": "HR Administration",
        "icon": "Users",
        "to": "/hreis/administration",
        "required_permission": "hreis.service_record.update",
        "sort_order": 30,
    },
    {
        "code": "hreis.notifications",
        "label": "HR Notifications",
        "icon": "Bell",
        "to": "/hreis/notifications",
        "required_permission": "hreis.notification.view",
        "sort_order": 40,
    },
    {
        "code": "hreis.audit",
        "label": "HR Audit",
        "icon": "ShieldCheck",
        "to": "/hreis/audit",
        "required_permission": "hreis.audit.view",
        "sort_order": 50,
    },
]

def readiness() -> list[str]:
    """Explain missing authoritative policy prerequisites before HR-EIS is activated.

    The HR specification intentionally contains no institutional quotas, dated
    appraisal window or approval matrix. Never replace those with sample defaults.
    """
    from django.utils import timezone

    from modules.hreis.models import HRPolicyVersion

    now = timezone.now()
    required = {
        "leave": ("routes", "eligibility"),
        "appraisal": ("routes", "submission_window"),
        "ltc": ("routes",),
        "cpda": ("routes",),
    }
    missing = []
    for family, fields in required.items():
        active = list(
            HRPolicyVersion.objects.filter(
                family=family, effective_from__lte=now,
            ).order_by("-effective_from", "-version")[:2]
        )
        if not active or (
            active[0].effective_until is not None
            and active[0].effective_until <= now
        ):
            missing.append(
                f"Publish an approved, currently effective {family.upper()} "
                "policy using HR-EIS policy management."
            )
            continue
        if len(active) > 1:
            previous = active[1]
            superseded = (
                previous.effective_until is None
                and active[0].effective_from > previous.effective_from
                and active[0].version > previous.version
            )
            overlapping = previous.effective_until is None or previous.effective_until > now
            if overlapping and not superseded:
                missing.append(
                    f"Resolve overlapping effective {family.upper()} policy versions."
                )
                continue
        parameters = active[0].parameters
        absent = [
            key for key in fields
            if not isinstance(parameters, dict)
            or not isinstance(parameters.get(key), (list, dict))
            or not parameters[key]
        ]
        if absent:
            missing.append(
                f"Complete {family.upper()} policy v{active[0].version}: "
                f"configure {', '.join(absent)} from approved institutional rules."
            )
    return missing
