ROLES = ["ADMIN", "STUDENT", "CARETAKER", "WARDEN"]

PERMISSIONS = {
    "ADMIN": {"assign_roles"},
    "STUDENT": {
        "submit_registration",
        "submit_deregistration",
        "view_menu",
        "view_own_bills",
        "submit_rebate",
        "respond_vacation_survey",
        "submit_special_food",
        "submit_feedback",
        "view_announcements",
        "track_own_requests"
    },
    "CARETAKER": {
        "open_registration_window",
        "review_registration",
        "review_deregistration",
        "edit_menu",
        "view_menu",
        "review_bills",
        "publish_bills",
        "review_rebate",
        "create_vacation_survey",
        "view_vacation_summary",
        "review_special_food",
        "update_special_food_fulfillment",
        "publish_announcement",
        "view_announcements",
        "view_feedback",
        "generate_operational_reports"
    },
    "WARDEN": {
        "view_requests",
        "view_menu",
        "view_feedback",
        "publish_announcement",
        "view_announcements",
        "view_supervisory_reports"
    }
}

def can(role, action):
    if role not in ROLES or action not in PERMISSIONS[role]:
        return False
    return True
