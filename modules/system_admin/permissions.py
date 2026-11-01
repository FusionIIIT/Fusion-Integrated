"""System Admin module permissions declaration.

Following Fusion RBAC convention: <module>.<resource>.<action>.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class P:
    code: str
    label: str
    dangerous: bool = False


MODULE_CODE = "system_admin"

PERMISSIONS = [
    # User lifecycle permissions
    P("system_admin.user.view", "View basic user profiles and directory listings"),
    P("system_admin.user.create", "Create basic student, faculty, or staff accounts"),
    P("system_admin.user.update", "Update editable basic user profile fields"),
    P("system_admin.user.deactivate", "Deactivate basic user accounts"),
    P("system_admin.user.reactivate", "Reactivate deactivated basic user accounts"),
    P("system_admin.user.bulk_manage", "Execute bulk CSV user creation and bulk status updates"),

    # Role lifecycle permissions
    P("system_admin.role.view", "View role definitions, metadata, and current/past holders"),
    P("system_admin.role.assign", "Assign additional roles to eligible users"),
    P("system_admin.role.reassign", "Reassign active roles to new holders with work handover"),
    P("system_admin.role.revoke", "Revoke active roles before scheduled end date"),
    P("system_admin.role.extend", "Extend validity end date of time-bound roles"),
    P("system_admin.role.switch", "Switch active role context during user session"),

    # Archival & Purge permissions
    P("system_admin.archive.view", "Search and view permitted archived user and system records"),
    P("system_admin.archive.create", "Archive eligible deactivated users and historical data", dangerous=True),
    P("system_admin.archive.restore", "Restore archived users within reversible window or data"),
    P("system_admin.archive.export", "Export archived records for offline compliance or external storage"),
    P("system_admin.purge.request", "Request permanent purge of retention-expired data", dangerous=True),
    P("system_admin.purge.authorize", "Dual-authorize permanent purge of archived data (IT Head)", dangerous=True),

    # Audit & Monitoring permissions
    P("system_admin.audit.view", "Inspect immutable audit logs and activity metadata"),
    P("system_admin.audit.report", "Generate and export audit reports and dashboards"),

    # System Configuration permissions
    P("system_admin.config.view", "View permitted system administrative parameters"),
    P("system_admin.config.update", "Update permitted system administrative parameters", dangerous=True),
    P("system_admin.session.manage", "Monitor and terminate operator/super admin sessions"),
]
