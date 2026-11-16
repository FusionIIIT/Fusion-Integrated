"""ELM metadata mirrored into the Fusion IAM module/permission registry."""

from django.utils.translation import gettext_lazy as _

elm_module_code = "elm"
elm_module_label = _("Employee Leave Management")
elm_module_icon = "FaLeaf"
elm_module_base_path = "/elm"
elm_nav_section = "Employee"
elm_sort_order = 20

elm_nav_items = [
    {
        "code": "elm.request_leave",
        "label": "Request Leave",
        "icon": "FaPlus",
        "to": "/elm/request-leave",
        "required_permission": "elm.application.create",
        "sort_order": 5,
    },
    {
        "code": "elm.my-balance",
        "label": "My Balance",
        "icon": "FaWallet",
        "to": "/elm/my-balance",
        "required_permission": "elm.balance.view",
        "sort_order": 10,
    },
    {
        "code": "elm.leave-history",
        "label": "Leave History",
        "icon": "FaHistory",
        "to": "/elm/leave-history",
        "required_permission": "elm.history.view",
        "sort_order": 15,
    },
    {
        "code": "elm.applications",
        "label": "My Applications",
        "icon": "FaFile",
        "to": "/elm/my-applications",
        "required_permission": "elm.application.view",
        "sort_order": 20,
    },
]

elm_permissions = [
    {"code": "elm.balance.view", "label": "View own leave balance"},
    {"code": "elm.history.view", "label": "View own leave history"},
    {"code": "elm.application.view", "label": "View own applications"},
    {"code": "elm.application.create", "label": "Create leave application"},
    {"code": "elm.application.withdraw", "label": "Withdraw own pending application"},
    {"code": "elm.application.review", "label": "Review leave applications"},
    {"code": "elm.application.sanction", "label": "Make final leave decisions"},
    {"code": "elm.substitute.respond", "label": "Respond to substitute requests"},
    {"code": "elm.calendar.manage", "label": "Manage the leave calendar"},
    {"code": "elm.configuration.manage", "label": "Manage leave configuration"},
    {"code": "elm.records.manage", "label": "Maintain leave records"},
]


def elm_module_config():
    """Return module/navigation data for an IAM provisioning task."""
    return {
        "code": elm_module_code,
        "label": elm_module_label,
        "icon": elm_module_icon,
        "base_path": elm_module_base_path,
        "nav_section": elm_nav_section,
        "sort_order": elm_sort_order,
        "status": "active",
        "nav_items": elm_nav_items,
        "permissions": elm_permissions,
    }
