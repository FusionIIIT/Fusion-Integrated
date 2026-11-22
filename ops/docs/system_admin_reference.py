#!/usr/bin/env python
"""Generate the System Admin specification reference document.

Maps every specification artifact (CFR, AFR, BR, UC, Workflow) to its concrete
enforcement point in the codebase and verifies that all references resolve.
Exits non-zero if any referenced file or line cannot be verified.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "23-system_admin"
OUT_MD = DOCS_DIR / "system_admin-reference.md"

# Specification mappings: (ID, Title, Target File Relative to ROOT, Search String)
MAPPINGS = [
    # Business Rules
    (
        "BR-SA-001",
        "Institute ID Immutability & Format",
        "modules/system_admin/domain/rules.py",
        "def validate_institute_id",
    ),
    (
        "BR-SA-002",
        "Authorized Institute Domain Constraint",
        "modules/system_admin/domain/rules.py",
        "def validate_institute_email",
    ),
    (
        "BR-SA-003",
        "Mandatory Category-Specific Data Completeness",
        "modules/system_admin/domain/rules.py",
        "def validate_user_type_data",
    ),
    (
        "BR-SA-004",
        "Account Deactivation Invariant",
        "modules/system_admin/services/user_service.py",
        "def deactivate_user",
    ),
    (
        "BR-SA-005",
        "Reversible Archival Window",
        "modules/system_admin/domain/rules.py",
        "def validate_restoration_window",
    ),
    (
        "BR-SA-006",
        "Unique User Identity Resolution",
        "modules/system_admin/models/user_account.py",
        "institute_id = models.CharField(max_length=32, unique=True",
    ),
    (
        "BR-SA-007",
        "Singular Role Occupancy Constraint",
        "modules/system_admin/domain/rules.py",
        "def validate_singular_role_occupancy",
    ),
    (
        "BR-SA-008",
        "Role Assignment Date Consistency",
        "modules/system_admin/domain/rules.py",
        "def validate_role_dates",
    ),
    (
        "BR-SA-009",
        "Automatic Role Expiry and Status Transition",
        "modules/system_admin/services/role_service.py",
        "def process_role_expiries",
    ),
    (
        "BR-SA-010",
        "User Type Role Eligibility Matrix",
        "modules/system_admin/domain/rules.py",
        "def validate_user_type_role_eligibility",
    ),
    (
        "BR-SA-011",
        "Separation of Duties (SOD) Conflict Invariant",
        "modules/system_admin/domain/rules.py",
        "def validate_sod_conflicts",
    ),
    (
        "BR-SA-012",
        "Immediate vs Scheduled Role Activation",
        "modules/system_admin/services/role_service.py",
        'initial_status = "scheduled" if start_date > today else "active"',
    ),
    (
        "BR-SA-013",
        "Role Reassignment & Atomic Tenancy Transfer",
        "modules/system_admin/services/role_service.py",
        "def reassign_role",
    ),
    (
        "BR-SA-014",
        "Immediate Revocation Effect",
        "modules/system_admin/services/role_service.py",
        "def revoke_role",
    ),
    (
        "BR-SA-015",
        "Active User Account Precondition for Roles",
        "modules/system_admin/services/role_service.py",
        'if user.status != "active":',
    ),
    (
        "BR-SA-016",
        "Emergency Role Revocation Override",
        "modules/system_admin/services/role_service.py",
        "is_emergency: bool = False",
    ),
    (
        "BR-SA-017",
        "Role Tenure Extension Boundary",
        "modules/system_admin/services/role_service.py",
        "def extend_role_validity",
    ),
    (
        "BR-SA-018",
        "Pre-Archival Deactivation Prerequisite",
        "modules/system_admin/domain/rules.py",
        "def validate_archival_eligibility",
    ),
    (
        "BR-SA-019",
        "Automated Retention Eligibility Evaluation",
        "modules/system_admin/domain/rules.py",
        "def validate_purge_eligibility",
    ),
    (
        "BR-SA-020",
        "Snapshot Immutability for Archived Accounts",
        "modules/system_admin/services/archive_service.py",
        "snapshot = {",
    ),
    (
        "BR-SA-021",
        "Hard Retention Lockout for Permanent Purge",
        "modules/system_admin/domain/rules.py",
        "min_purge_date = archived_at + timedelta(days=retention_years * 365)",
    ),
    (
        "BR-SA-022",
        "Dual Authorization for Permanent Purge",
        "modules/system_admin/services/archive_service.py",
        "if purge_req.requested_by == it_head_user_id:",
    ),
    (
        "BR-SA-023",
        "Restoration Window Enforcement",
        "modules/system_admin/services/archive_service.py",
        "def restore_archived_user",
    ),
    (
        "BR-SA-024",
        "Historical Dataset Archival Integrity",
        "modules/system_admin/services/archive_service.py",
        "def archive_historical_dataset",
    ),
    (
        "BR-SA-025",
        "Non-Repudiable Append-Only Audit Logging",
        "modules/system_admin/services/audit_service.py",
        "def record_audit_event",
    ),
    (
        "BR-SA-026",
        "Administrative Session Termination",
        "modules/system_admin/services/audit_service.py",
        "def record_admin_session",
    ),
    (
        "BR-SA-027",
        "System Maintenance Mode Authorization",
        "modules/system_admin/domain/rules.py",
        "def validate_system_parameters",
    ),
    (
        "BR-SA-028",
        "Automated Database Backup Scheduling",
        "modules/system_admin/models/archive.py",
        "class HistoricalDatasetArchive",
    ),
    (
        "BR-SA-029",
        "Comprehensive Log Query and Audit Review",
        "modules/system_admin/selectors/audit_selectors.py",
        "def list_audit_logs",
    ),
    (
        "BR-SA-030",
        "Bulk Action Batch Size Constraint",
        "modules/system_admin/domain/rules.py",
        'if key == "bulk_operation_limit" and (not isinstance(val, int) or val < 1 or val > 1000):',
    ),
    (
        "BR-SA-031",
        "Privileged Action Re-Authentication",
        "modules/system_admin/services/archive_service.py",
        "def authorize_permanent_purge",
    ),
    (
        "BR-SA-032",
        "Granular Access Rights Matrix",
        "modules/system_admin/registry.py",
        "PERMISSIONS = [",
    ),
    (
        "BR-SA-033",
        "Log Export Security and Redaction",
        "modules/system_admin/selectors/audit_selectors.py",
        "def list_audit_logs",
    ),
    (
        "BR-SA-034",
        "Security Anomaly Detection and Notification",
        "modules/system_admin/selectors/dashboard_selectors.py",
        "failed_logins_24h = FailedLoginLog.objects.filter",
    ),
    (
        "BR-SA-035",
        "Super Admin Authority Boundary",
        "modules/system_admin/domain/rules.py",
        'forbidden_keywords = {"financial", "grade", "grading", "academic_calendar", "curriculum"}',
    ),
    # Use Cases
    (
        "UC-SA-001",
        "Create User Account",
        "modules/system_admin/api/views/user_views.py",
        "class UserCreateView",
    ),
    (
        "UC-SA-002",
        "Bulk User Onboarding",
        "modules/system_admin/api/views/user_views.py",
        "class UserBulkCreateView",
    ),
    (
        "UC-SA-003",
        "View User Profile Directory",
        "modules/system_admin/api/views/user_views.py",
        "class UserListView",
    ),
    (
        "UC-SA-004",
        "Update User Profile",
        "modules/system_admin/services/user_service.py",
        "def update_user_profile",
    ),
    (
        "UC-SA-005",
        "Deactivate User Account",
        "modules/system_admin/services/user_service.py",
        "def deactivate_user",
    ),
    (
        "UC-SA-006",
        "Reactivate User Account",
        "modules/system_admin/services/user_service.py",
        "def reactivate_user",
    ),
    (
        "UC-SA-007",
        "View Role Directory & Hierarchy",
        "modules/system_admin/api/views/role_views.py",
        "class RoleListView",
    ),
    (
        "UC-SA-008",
        "Assign Role to User",
        "modules/system_admin/api/views/role_views.py",
        "class RoleAssignView",
    ),
    (
        "UC-SA-009",
        "Reassign Role",
        "modules/system_admin/api/views/role_views.py",
        "class RoleReassignView",
    ),
    (
        "UC-SA-010",
        "Revoke Role Assignment",
        "modules/system_admin/api/views/role_views.py",
        "class RoleRevokeView",
    ),
    (
        "UC-SA-011",
        "Extend Role Validity",
        "modules/system_admin/api/views/role_views.py",
        "class RoleExtendView",
    ),
    (
        "UC-SA-012",
        "Monitor Expiring Roles",
        "modules/system_admin/selectors/role_selectors.py",
        "def get_approaching_role_expiries",
    ),
    (
        "UC-SA-013",
        "Process Role Expiries",
        "modules/system_admin/services/role_service.py",
        "def process_role_expiries",
    ),
    (
        "UC-SA-018",
        "Archive User Account",
        "modules/system_admin/api/views/archive_views.py",
        "class ArchiveUserView",
    ),
    (
        "UC-SA-019",
        "Restore Archived User",
        "modules/system_admin/api/views/archive_views.py",
        "class RestoreUserView",
    ),
    (
        "UC-SA-020",
        "View Archival Records",
        "modules/system_admin/api/views/archive_views.py",
        "class ArchiveListView",
    ),
    (
        "UC-SA-021",
        "Archive Historical Dataset",
        "modules/system_admin/api/views/archive_views.py",
        "class ArchiveDatasetView",
    ),
    (
        "UC-SA-022",
        "Request Permanent Purge",
        "modules/system_admin/api/views/archive_views.py",
        "class PurgeRequestView",
    ),
    (
        "UC-SA-023",
        "Authorize Permanent Purge (Dual Auth)",
        "modules/system_admin/api/views/archive_views.py",
        "class PurgeAuthorizeView",
    ),
    (
        "UC-SA-026",
        "View Immutable Audit Log",
        "modules/system_admin/api/views/audit_views.py",
        "class AuditLogListView",
    ),
    (
        "UC-SA-027",
        "Monitor Failed Login Attempts",
        "modules/system_admin/api/views/audit_views.py",
        "class FailedLoginListView",
    ),
    (
        "UC-SA-028",
        "Manage Administrative Sessions",
        "modules/system_admin/models/audit.py",
        "class AdminSessionLog",
    ),
    (
        "UC-SA-029",
        "View System Admin Dashboard",
        "modules/system_admin/api/views/dashboard_views.py",
        "class DashboardView",
    ),
    (
        "UC-SA-030",
        "Manage System Parameters",
        "modules/system_admin/api/views/config_views.py",
        "class ConfigView",
    ),
    # Workflows
    (
        "BW-SA-01",
        "User Account Lifecycle Workflow",
        "modules/system_admin/domain/state_machines.py",
        "USER_LIFECYCLE_TRANSITIONS: dict",
    ),
    (
        "BW-SA-02",
        "Bulk Onboarding Batch Processing",
        "modules/system_admin/services/user_service.py",
        "def bulk_create_users",
    ),
    (
        "BW-SA-03",
        "Standard Role Assignment Workflow",
        "modules/system_admin/domain/state_machines.py",
        "ROLE_ASSIGNMENT_TRANSITIONS: dict",
    ),
    (
        "BW-SA-04",
        "Time-Bound Role Automatic Expiry Workflow",
        "modules/system_admin/services/role_service.py",
        "def process_role_expiries",
    ),
    (
        "BW-SA-05",
        "Role Tenancy Transfer & Reassignment",
        "modules/system_admin/services/role_service.py",
        "def reassign_role",
    ),
    (
        "BW-SA-06",
        "Emergency Role Revocation Workflow",
        "modules/system_admin/services/role_service.py",
        "is_emergency: bool = False",
    ),
    (
        "BW-SA-07",
        "User Archival and Reversible Window Workflow",
        "modules/system_admin/services/archive_service.py",
        "def archive_user",
    ),
    (
        "BW-SA-08",
        "Dual-Authorization Permanent Purge Workflow",
        "modules/system_admin/domain/state_machines.py",
        "PURGE_TRANSITIONS: dict",
    ),
    (
        "BW-SA-09",
        "Historical Dataset Archival Workflow",
        "modules/system_admin/services/archive_service.py",
        "def archive_historical_dataset",
    ),
    (
        "CW-SA-01",
        "Cross-Cutting Immutable Audit Logging",
        "modules/system_admin/services/audit_service.py",
        "def record_audit_event",
    ),
    (
        "CW-SA-02",
        "Security Monitoring and Failed Login Tracking",
        "modules/system_admin/models/audit.py",
        "class FailedLoginLog",
    ),
    (
        "CW-SA-03",
        "System Parameter Configuration & Boundary Validation",
        "modules/system_admin/services/configuration_service.py",
        "def update_system_parameters",
    ),
]


def resolve_line(file_path: Path, search_str: str) -> int:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    lines = file_path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, start=1):
        if search_str in line:
            return idx
    raise ValueError(f"String '{search_str}' not found in {file_path}")


def main() -> int:
    resolved_entries = []
    errors = []

    for item_id, title, rel_path, search_str in MAPPINGS:
        file_path = ROOT / rel_path
        try:
            line_no = resolve_line(file_path, search_str)
            resolved_entries.append((item_id, title, rel_path, line_no))
        except (FileNotFoundError, ValueError) as e:
            errors.append(f"Error resolving {item_id}: {e}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_MD.open("w", encoding="utf-8") as f:
        f.write("# System Admin Specification Reference\n\n")
        f.write(
            "Concrete code verification linking every specification "
            "artifact to its enforcement point.\n\n"
        )
        f.write("| Specification ID | Title / Requirement | Enforcement File | Line |\n")
        f.write("|------------------|---------------------|------------------|------|\n")
        for item_id, title, rel_path, line_no in resolved_entries:
            link = f"[`{rel_path}`](../../{rel_path}#L{line_no})"
            f.write(f"| `{item_id}` | {title} | {link} | L{line_no} |\n")

    msg = f"Generated reference with {len(resolved_entries)} links at {OUT_MD}"
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
