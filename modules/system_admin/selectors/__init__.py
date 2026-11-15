"""Selectors package for system_admin."""
from modules.system_admin.selectors.archival import (
    get_archived_user,
    get_expired_reversible_user_records,
    get_historical_archive,
    get_purge_request,
    list_archived_users,
    list_historical_archives,
    list_purge_requests,
)
from modules.system_admin.selectors.audit import (
    generate_audit_report_dataset,
    query_audit_logs,
    query_user_activity_logs,
)
from modules.system_admin.selectors.config import (
    get_all_permitted_parameters,
    get_system_parameter,
)
from modules.system_admin.selectors.dashboard import (
    get_super_admin_dashboard_metrics,
)
from modules.system_admin.selectors.roles import (
    get_assignments_approaching_expiry,
    get_assignments_pending_activation,
    get_assignments_pending_expiry,
    get_previous_holder_audit_access,
    get_role_availability,
    get_role_definition,
    get_user_active_assignments,
    get_user_assignments,
    list_role_definitions,
)
from modules.system_admin.selectors.security import (
    get_active_admin_session,
    get_consecutive_failed_logins,
    get_session_by_token_hash,
    get_two_factor_credential,
)
from modules.system_admin.selectors.users import (
    get_deactivated_users_eligible_for_archival,
    get_user_by_id,
    get_user_by_institute_id,
    get_user_by_username,
    get_user_profile,
    get_user_status_history,
    list_users,
)

__all__ = [
    "generate_audit_report_dataset",
    "get_active_admin_session",
    "get_archived_user",
    "get_assignments_approaching_expiry",
    "get_assignments_pending_activation",
    "get_assignments_pending_expiry",
    "get_consecutive_failed_logins",
    "get_deactivated_users_eligible_for_archival",
    "get_expired_reversible_user_records",
    "get_historical_archive",
    "get_previous_holder_audit_access",
    "get_purge_request",
    "get_role_availability",
    "get_role_definition",
    "get_session_by_token_hash",
    "get_super_admin_dashboard_metrics",
    "get_system_parameter",
    "get_all_permitted_parameters",
    "get_two_factor_credential",
    "get_user_active_assignments",
    "get_user_assignments",
    "get_user_by_id",
    "get_user_by_institute_id",
    "get_user_by_username",
    "get_user_profile",
    "get_user_status_history",
    "list_archived_users",
    "list_historical_archives",
    "list_purge_requests",
    "list_role_definitions",
    "list_users",
    "query_audit_logs",
    "query_user_activity_logs",
]
