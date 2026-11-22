"""Services for the Department module."""

from modules.dept.services.announcements import create_announcement, update_announcement
from modules.dept.services.department import (
    decide_official_change,
    propose_official_change,
    update_general_department_info,
)
from modules.dept.services.feedback import (
    resolve_or_close_feedback,
    review_feedback_initial,
    submit_feedback,
)
from modules.dept.services.inventory import (
    add_stock_to_item,
    create_inventory_item,
    decide_stock_request,
    issue_stock_request,
    submit_stock_request,
)
from modules.dept.services.labs import save_lab_resource
from modules.dept.services.profiles import save_user_profile_extension
from modules.dept.services.roles import (
    assign_department_role,
    evaluate_role_transitions,
    revoke_department_role,
)
from modules.dept.services.timetable import delete_timetable_entry, save_timetable_entry

__all__ = [
    "add_stock_to_item",
    "assign_department_role",
    "create_announcement",
    "create_inventory_item",
    "decide_official_change",
    "decide_stock_request",
    "delete_timetable_entry",
    "evaluate_role_transitions",
    "issue_stock_request",
    "propose_official_change",
    "resolve_or_close_feedback",
    "review_feedback_initial",
    "revoke_department_role",
    "save_lab_resource",
    "save_timetable_entry",
    "save_user_profile_extension",
    "submit_feedback",
    "submit_stock_request",
    "update_announcement",
    "update_general_department_info",
]
