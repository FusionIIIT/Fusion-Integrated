"""System Admin selectors package."""
from .archival import (
    get_archived_record,
    get_purge_request,
    list_archived_records,
    list_archived_users,
    list_purge_requests,
)
from .audit import get_audit_log_entry, list_audit_logs
from .dashboard import get_admin_dashboard_metrics
from .roles import (
    get_active_role_holders,
    get_role_definition,
    get_user_active_role_codes,
    list_role_assignments,
    list_role_definitions,
    list_roles_approaching_expiry,
    list_vacant_singular_roles,
)
from .users import (
    check_email_exists,
    check_institute_id_exists,
    get_user_by_id,
    get_user_by_institute_id,
    get_users_by_ids,
    list_basic_users,
)
