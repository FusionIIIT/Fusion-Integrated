"""What the server tells the shell about the Mess Management System module.

Nav items carry `required_permission` and the server filters before sending,
so a link a role cannot use never reaches the browser.

DRAFT: PERMISSIONS and NAV_ITEMS follow placement/registry.py exactly.
ROLE_GRANTS at the bottom must be reshaped to match placement's ROLE_GRANTS
(lines 80+ of placement/registry.py were not in the recon report).
"""
MODULE = {
    "code": "mess", "label": "Mess Management", "icon": "ForkKnife",
    "base_path": "/mess", "nav_section": "Mess", "sort_order": 20,
    "status": "active",
}

NAV_ITEMS = [
    # -- student ----------------------------------------------------------
    {"code": "mess.registration", "label": "Mess Registration",
     "icon": "Checks", "to": "/mess/registration",
     "required_permission": "mess.registration.submit", "sort_order": 5},
    {"code": "mess.menu", "label": "Weekly Menu",
     "icon": "ForkKnife", "to": "/mess/menu",
     "required_permission": "mess.menu.view", "sort_order": 10},
    {"code": "mess.bills", "label": "My Bills",
     "icon": "Receipt", "to": "/mess/bills",
     "required_permission": "mess.bill.view_self", "sort_order": 20},
    {"code": "mess.rebate", "label": "Rebate",
     "icon": "Percent", "to": "/mess/rebate",
     "required_permission": "mess.rebate.submit", "sort_order": 30},
    {"code": "mess.vacation", "label": "Vacation Survey",
     "icon": "Airplane", "to": "/mess/vacation",
     "required_permission": "mess.vacation.respond", "sort_order": 40},
    {"code": "mess.special_food", "label": "Special Food",
     "icon": "BowlFood", "to": "/mess/special-food",
     "required_permission": "mess.special_food.submit", "sort_order": 50},
    {"code": "mess.feedback", "label": "Feedback",
     "icon": "ChatCircle", "to": "/mess/feedback",
     "required_permission": "mess.feedback.submit", "sort_order": 60},
    {"code": "mess.my_requests", "label": "My Requests",
     "icon": "UserCheck", "to": "/mess/my-requests",
     "required_permission": "mess.request.view_self", "sort_order": 70},
    {"code": "mess.announcements", "label": "Announcements",
     "icon": "Megaphone", "to": "/mess/announcements",
     "required_permission": "mess.announcement.view", "sort_order": 80},

    # -- caretaker --------------------------------------------------------
    {"code": "mess.windows", "label": "Registration Windows",
     "icon": "CalendarBlank", "to": "/mess/registration-windows",
     "required_permission": "mess.registration.open_window",
     "sort_order": 105},
    {"code": "mess.registration_review", "label": "Registration Review",
     "icon": "Checks", "to": "/mess/registration-review",
     "required_permission": "mess.registration.review", "sort_order": 110},
    {"code": "mess.menu_edit", "label": "Edit Menu",
     "icon": "PencilSimple", "to": "/mess/menu-edit",
     "required_permission": "mess.menu.edit", "sort_order": 120},
    {"code": "mess.bill_review", "label": "Bill Review",
     "icon": "Receipt", "to": "/mess/bill-review",
     "required_permission": "mess.bill.review", "sort_order": 130},
    {"code": "mess.rebate_review", "label": "Rebate Review",
     "icon": "Percent", "to": "/mess/rebate-review",
     "required_permission": "mess.rebate.review", "sort_order": 140},
    {"code": "mess.vacation_surveys", "label": "Vacation Surveys",
     "icon": "Airplane", "to": "/mess/vacation-surveys",
     "required_permission": "mess.vacation.create_survey",
     "sort_order": 150},
    {"code": "mess.special_food_review", "label": "Special Food Review",
     "icon": "BowlFood", "to": "/mess/special-food-review",
     "required_permission": "mess.special_food.review", "sort_order": 160},
    {"code": "mess.feedback_view", "label": "Feedback Received",
     "icon": "ChatCircle", "to": "/mess/feedback-received",
     "required_permission": "mess.feedback.view", "sort_order": 170},
    {"code": "mess.reports", "label": "Operational Reports",
     "icon": "ChartBar", "to": "/mess/reports",
     "required_permission": "mess.report.operational", "sort_order": 180},

    # -- warden -----------------------------------------------------------
    {"code": "mess.requests_all", "label": "All Requests",
     "icon": "Users", "to": "/mess/requests",
     "required_permission": "mess.request.view_all", "sort_order": 210},
    {"code": "mess.supervisory", "label": "Supervisory Reports",
     "icon": "ChartBar", "to": "/mess/supervisory-reports",
     "required_permission": "mess.report.supervisory", "sort_order": 220},

    # -- admin ------------------------------------------------------------
    {"code": "mess.roles", "label": "Assign Roles",
     "icon": "UserGear", "to": "/mess/roles",
     "required_permission": "mess.role.assign", "sort_order": 300},
]

#: Every permission this module recognises (mirrors domain/access.py).
PERMISSIONS = [
    ("mess.role.assign", "Assign Caretaker and Warden roles"),
    ("mess.registration.submit", "Submit a mess registration"),
    ("mess.registration.open_window", "Open a registration window"),
    ("mess.registration.review", "Approve or reject registrations"),
    ("mess.deregistration.submit", "Submit a deregistration"),
    ("mess.deregistration.review", "Approve or reject deregistrations"),
    ("mess.menu.view", "See the weekly menu"),
    ("mess.menu.edit", "Edit the weekly menu"),
    ("mess.bill.view_self", "See one's own published bills"),
    ("mess.bill.review", "Review and finalize bills"),
    ("mess.bill.publish", "Publish finalized bills"),
    ("mess.rebate.submit", "Submit a rebate request"),
    ("mess.rebate.review", "Approve, modify or reject rebates"),
    ("mess.vacation.respond", "Answer a vacation survey"),
    ("mess.vacation.create_survey", "Create a vacation survey"),
    ("mess.vacation.view_summary", "See vacation response summaries"),
    ("mess.special_food.submit", "Request special food"),
    ("mess.special_food.review", "Approve or reject special food"),
    ("mess.special_food.fulfil", "Record served or cancelled special food"),
    ("mess.feedback.submit", "Submit feedback"),
    ("mess.feedback.view", "See feedback"),
    ("mess.announcement.publish", "Publish announcements"),
    ("mess.announcement.view", "See announcements"),
    ("mess.request.view_self", "Track one's own requests"),
    ("mess.request.view_all", "See all requests (view only)"),
    ("mess.report.operational", "Generate operational reports"),
    ("mess.report.supervisory", "See supervisory reports"),
]

#: Who holds what. Mirrors domain/access.py. Reshape to placement's ROLE_GRANTS.
ROLE_GRANTS = {
    "ADMIN": ["mess.role.assign"],
    "STUDENT": [
        "mess.registration.submit", "mess.deregistration.submit",
        "mess.menu.view", "mess.bill.view_self", "mess.rebate.submit",
        "mess.vacation.respond", "mess.special_food.submit",
        "mess.feedback.submit", "mess.announcement.view",
        "mess.request.view_self",
    ],
    "CARETAKER": [
        "mess.registration.open_window", "mess.registration.review",
        "mess.deregistration.review", "mess.menu.edit", "mess.menu.view",
        "mess.bill.review", "mess.bill.publish", "mess.rebate.review",
        "mess.vacation.create_survey", "mess.vacation.view_summary",
        "mess.special_food.review", "mess.special_food.fulfil",
        "mess.announcement.publish", "mess.announcement.view",
        "mess.feedback.view", "mess.report.operational",
    ],
    "WARDEN": [
        "mess.request.view_all", "mess.menu.view", "mess.feedback.view",
        "mess.announcement.publish", "mess.announcement.view",
        "mess.report.supervisory",
    ],
}
