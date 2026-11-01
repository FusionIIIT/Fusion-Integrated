"""ELM module registry — module metadata and navigation configuration."""

from django.utils.translation import gettext_lazy as _

from modules.elm.contracts import active_module_codes, build_navigation
from modules.elm.models import LeaveCategory, LeaveApplication, EmployeeLeaveBalance
from modules.core.registry import ModuleRegistry


#: Unique module code used in placement_cell and navigation
elm_module_code = "elm"

#: Human-readable label for the module
elm_module_label = _("Employee Leave Management")

#: Icon name (Fa = Font Awesome; use the module's assigned icon)
elm_module_icon = "FaLeaf"

#: Base path for this module's URLs (relative to the server base)
elm_module_base_path = "/elm"

#: Navigation section this module belongs to
elm_nav_section = "Employee"

#: Sort order for navigation placement
elm_sort_order = 20


#: Navigation items for the ELM module.
#: Each entry maps to a route in client/src/modules/elm/routes.tsx.
#: The `required_permission` field filters items based on the user's token permissions.
elm_nav_items = [
    {
        "code": "elm.request_leave",
        "label": "Request Leave",
        "icon": "FaPlus",
        "to": "/elm/request-leave",
        "required_permission": "",
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
        "to": "/elm/applications",
        "required_permission": "elm.application.view",
        "sort_order": 20,
    },
]


def elm_module_config() -> dict:
    """Return the module configuration dict for the Fusion ERP registry."""
    return {
        "code": elm_module_code,
        "label": elm_module_label,
        "icon": elm_module_icon,
        "base_path": elm_module_base_path,
        "nav_section": elm_nav_section,
        "sort_order": elm_sort_order,
        "status": "active",
        "nav_items": elm_nav_items,
    }


#: Module- level permissions used across nav_items and API gate.
elm_permissions = [
    {"code": "elm.balance.view", "label": "View leave balance"},
    {"code": "elm.history.view", "label": "View leave history"},
    {"code": "elm.application.view", "label": "View own applications"},
    {"code": "elm.application.create", "label": "Create leave application"},
    {"code": "elm.application.withdraw", "label": "Withdraw application"},
    {"code": "elm.request_leave", "label": "Request leave"},
]


def get_elm_navigation(*, granted_module_codes: Sequence[str],
                       permissions: Iterable[str]) -> list[dict]:
    """Filter and format navigation for the ELM module.

    The server-side build_navigation from accesscontrol handles module-level
    filtering. This wrapper ensures ELM nav items are included in the result.
    """
    from modules.accesscontrol.contracts import build_navigation as build_base

    # Build base navigation from the accesscontrol module
    base = build_base(granted_module_codes=granted_module_codes,
                      permissions=permissions)

    # Add ELM-specific entries if the module is granted
    module_code = elm_module_config()["code"]
    if module_code in granted_module_codes:
        # Add ELM nav items that don't have a direct base_path single link
        elm_entries = []
        for item in elm_nav_items:
            # Check if this nav item's 'to' path would be a single link
            # (same as base_path) or needs an accordion with links
            elm_entries.append({
                "code": item["code"],
                "label": item["label"],
                "icon": item["icon"],
                "to": item["to"],
                "required_permission": item["required_permission"],
            })

        # Append ELM section to each top-level section that has ELM items,
        # or create a new section if needed
        for entry in base:
            if entry["section"] == "Employee":
                entry["items"].extend(elm_entries)
                break
        else:
            # No "Employee" section found — add ELM as a new section
            base.append({
                "section": "Employee",
                "items": elm_entries,
            })

    return base


# Register the module with the central registry
ModuleRegistry.register_module(
    module_code=elm_module_code,
    config_func=elm_module_config,
    permissions=elm_permissions,
    get_navigation_func=get_elm_navigation,
)