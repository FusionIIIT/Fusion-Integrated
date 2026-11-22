"""Super Admin selectors package."""

from modules.superadmin.selectors.archive import (
    get_archive_by_id,
    get_purge_request_by_id,
    list_archives,
    list_purge_requests,
)
from modules.superadmin.selectors.audit import list_audit_logs
from modules.superadmin.selectors.roles import get_role_by_id, list_handovers, list_roles
from modules.superadmin.selectors.scoping import (
    is_superadmin,
    visible_archives,
    visible_audit_logs,
    visible_parameters,
    visible_roles,
    visible_users,
)
from modules.superadmin.selectors.system_config import get_parameter_value, list_system_parameters
from modules.superadmin.selectors.users import get_user_by_id, get_user_by_institute_id, list_users

__all__ = [
    "get_archive_by_id",
    "get_parameter_value",
    "get_purge_request_by_id",
    "get_role_by_id",
    "get_user_by_id",
    "get_user_by_institute_id",
    "is_superadmin",
    "list_archives",
    "list_audit_logs",
    "list_handovers",
    "list_purge_requests",
    "list_roles",
    "list_system_parameters",
    "list_users",
    "visible_archives",
    "visible_audit_logs",
    "visible_parameters",
    "visible_roles",
    "visible_users",
]
