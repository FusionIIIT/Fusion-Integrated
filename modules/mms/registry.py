"""What the server tells the shell about the MMS module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""

MODULE = {
    "code": "mms",
    "label": "Mess Management System",
    "icon": "FaCircle",
    "base_path": "/mms",
    "nav_section": "MMS",
    "sort_order": 20,
    "status": "planned",
}

NAV_ITEMS = [
    # -- student -----------------------------------------------------------
    {
        "code": "mms.special-food-request",
        "label": "Special Food Request",
        "icon": "FaCircle",
        "to": "/mms/special-food-request",
        "required_permission": "mms.special_food.create",
        "sort_order": 5,
    },
    {
        "code": "mms.my-requests",
        "label": "My Requests",
        "icon": "FaCircle",
        "to": "/mms/requests",
        "required_permission": "mms.request.view_self",
        "sort_order": 10,
    },
    {
        "code": "mms.my-bills",
        "label": "My Bills",
        "icon": "FaCircle",
        "to": "/mms/bills",
        "required_permission": "mms.billing.view_self",
        "sort_order": 15,
    },
    {
        "code": "mms.menu",
        "label": "Weekly Menu",
        "icon": "FaCircle",
        "to": "/mms/menu",
        "required_permission": "mms.menu.view",
        "sort_order": 20,
    },
    {
        "code": "mms.feedback",
        "label": "Feedback",
        "icon": "FaCircle",
        "to": "/mms/feedback",
        "required_permission": "mms.feedback.create",
        "sort_order": 25,
    },
    {
        "code": "mms.survey-response",
        "label": "Vacation Survey",
        "icon": "FaCircle",
        "to": "/mms/survey-response",
        "required_permission": "mms.survey_response.create",
        "sort_order": 30,
    },
    # -- caretaker ---------------------------------------------------------
    {
        "code": "mms.registration-approvals",
        "label": "Registration Approvals",
        "icon": "FaCircle",
        "to": "/mms/registration-approvals",
        "required_permission": "mms.registration.review",
        "sort_order": 55,
    },
    {
        "code": "mms.deregistration-approvals",
        "label": "Deregistration Approvals",
        "icon": "FaCircle",
        "to": "/mms/deregistration-approvals",
        "required_permission": "mms.deregistration.review",
        "sort_order": 60,
    },
    {
        "code": "mms.rebate-approvals",
        "label": "Rebate Approvals",
        "icon": "FaCircle",
        "to": "/mms/rebate-approvals",
        "required_permission": "mms.rebate.review",
        "sort_order": 65,
    },
    {
        "code": "mms.special-food-approvals",
        "label": "Special Food Approvals",
        "icon": "FaCircle",
        "to": "/mms/special-food-approvals",
        "required_permission": "mms.special_food.review",
        "sort_order": 70,
    },
    {
        "code": "mms.menu-management",
        "label": "Menu Management",
        "icon": "FaCircle",
        "to": "/mms/menu-management",
        "required_permission": "mms.menu.manage",
        "sort_order": 75,
    },
    {
        "code": "mms.billing-review",
        "label": "Billing Review",
        "icon": "FaCircle",
        "to": "/mms/billing-review",
        "required_permission": "mms.billing.review",
        "sort_order": 80,
    },
    {
        "code": "mms.survey-management",
        "label": "Vacation Survey",
        "icon": "FaCircle",
        "to": "/mms/survey-management",
        "required_permission": "mms.survey.create",
        "sort_order": 85,
    },
    {
        "code": "mms.survey-summary",
        "label": "Survey Summary",
        "icon": "FaCircle",
        "to": "/mms/survey-summary",
        "required_permission": "mms.survey.view_summary",
        "sort_order": 90,
    },
    {
        "code": "mms.announcements",
        "label": "Announcements",
        "icon": "FaCircle",
        "to": "/mms/announcements",
        "required_permission": "mms.announcement.publish",
        "sort_order": 95,
    },
    {
        "code": "mms.feedback-review",
        "label": "Feedback Review",
        "icon": "FaCircle",
        "to": "/mms/feedback-review",
        "required_permission": "mms.feedback.view",
        "sort_order": 100,
    },
    {
        "code": "mms.operational-reports",
        "label": "Operational Reports",
        "icon": "FaCircle",
        "to": "/mms/operational-reports",
        "required_permission": "mms.report.operational",
        "sort_order": 105,
    },
    # -- warden ------------------------------------------------------------
    {
        "code": "mms.warden-menu",
        "label": "Weekly Menu",
        "icon": "FaCircle",
        "to": "/mms/menu",
        "required_permission": "mms.menu.view",
        "sort_order": 110,
    },
    {
        "code": "mms.warden-announcement-history",
        "label": "Announcement History",
        "icon": "FaCircle",
        "to": "/mms/announcements/history",
        "required_permission": "mms.announcement.view",
        "sort_order": 115,
    },
    {
        "code": "mms.warden-feedback-review",
        "label": "Feedback Review",
        "icon": "FaCircle",
        "to": "/mms/feedback-review",
        "required_permission": "mms.feedback.view",
        "sort_order": 120,
    },
    {
        "code": "mms.supervisory-reports",
        "label": "Supervisory Reports",
        "icon": "FaCircle",
        "to": "/mms/supervisory-reports",
        "required_permission": "mms.report.supervisory",
        "sort_order": 125,
    },
    # -- mess admin --------------------------------------------------------
    {
        "code": "mms.role-assignment",
        "label": "Role Assignment",
        "icon": "FaCircle",
        "to": "/mms/role-assignment",
        "required_permission": "mms.role.assign",
        "sort_order": 130,
    },
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
#: Verbs are from the closed list in docs/02-iam/rbac-model.md.
PERMISSIONS = [
    ("mms.role.assign", "Assign or reassign the active Caretaker and Warden"),
    ("mms.registration.window.manage", "Open the registration window"),
    ("mms.registration.create", "Submit a mess registration request"),
    ("mms.registration.review", "Approve or reject registration requests"),
    ("mms.deregistration.create", "Submit a mess deregistration request"),
    ("mms.deregistration.review", "Approve or reject deregistration requests"),
    ("mms.deregistration.manage", "System: activate an approved deregistration"),
    ("mms.menu.view", "View the weekly menu"),
    ("mms.menu.manage", "Add, delete or modify weekly menu items"),
    ("mms.billing.view_self", "View one's own monthly bills and balance"),
    ("mms.billing.review", "Review generated monthly bills"),
    ("mms.billing.approve", "Finalize generated monthly bills"),
    ("mms.billing.publish", "Publish finalized monthly bills"),
    ("mms.billing.manage", "System: generate monthly bills"),
    ("mms.rebate.create", "Submit a mess rebate request"),
    ("mms.rebate.review", "Approve or reject rebate requests"),
    ("mms.rebate.update", "Modify rebate dates before approval"),
    ("mms.survey.create", "Create a vacation food continuity survey"),
    ("mms.survey.manage", "System: default-No and reminder for surveys"),
    ("mms.survey.view_summary", "View the vacation survey response summary"),
    ("mms.survey_response.create", "Respond Yes or No to a vacation survey"),
    ("mms.special_food.create", "Submit a special food request"),
    ("mms.special_food.review", "Approve or reject special food requests"),
    ("mms.special_food.update", "Record Served or Cancelled fulfillment"),
    ("mms.special_food.manage", "System: default-reject undecided requests"),
    ("mms.announcement.publish", "Publish mess-related announcements"),
    ("mms.announcement.view", "View announcement history"),
    ("mms.feedback.create", "Submit text feedback"),
    ("mms.feedback.view", "View feedback entries"),
    ("mms.report.supervisory", "View supervisory reports"),
    ("mms.report.operational", "Generate operational reports"),
    ("mms.request.view_self", "View one's own request status and history"),
    ("mms.notification.manage", "System: drain the notification outbox"),
]

#: Performed by a service or scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = [
    "mms.deregistration.manage",
    "mms.survey.manage",
    "mms.billing.manage",
    "mms.special_food.manage",
    "mms.notification.manage",
]

#: Enforced by narrowing a queryset in selectors rather than by refusing a request.
SCOPE_PERMISSIONS = [
    "mms.billing.review",
    "mms.billing.view_self",
    "mms.feedback.view",
]

_STUDENT = [
    "mms.registration.create",
    "mms.deregistration.create",
    "mms.menu.view",
    "mms.billing.view_self",
    "mms.rebate.create",
    "mms.survey_response.create",
    "mms.special_food.create",
    "mms.announcement.view",
    "mms.feedback.create",
    "mms.request.view_self",
]

_CARETAKER = [
    "mms.registration.window.manage",
    "mms.registration.review",
    "mms.deregistration.review",
    "mms.menu.view",
    "mms.menu.manage",
    "mms.billing.review",
    "mms.billing.approve",
    "mms.billing.publish",
    "mms.rebate.review",
    "mms.rebate.update",
    "mms.survey.create",
    "mms.survey.view_summary",
    "mms.special_food.review",
    "mms.special_food.update",
    "mms.announcement.publish",
    "mms.announcement.view",
    "mms.feedback.view",
    "mms.report.operational",
    "mms.request.view_self",
]

_WARDEN = [
    "mms.menu.view",
    "mms.billing.view_self",
    "mms.survey.view_summary",
    "mms.announcement.publish",
    "mms.announcement.view",
    "mms.feedback.view",
    "mms.report.supervisory",
    "mms.request.view_self",
]

_MESS_ADMIN = [
    "mms.role.assign",
]

#: Keyed by the designation name exactly as it is used as a role.
#: `Mess Caretaker`, `Mess Warden` and `Mess Admin` are roles this module
#: introduces (free text per role-assignment-guide.md); `student` is a basic
#: kind held by definition.
ROLE_GRANTS = {
    "student": _STUDENT,
    "Mess Caretaker": _CARETAKER,
    "Mess Warden": _WARDEN,
    "Mess Admin": _MESS_ADMIN,
}
