#!/usr/bin/env python3
"""Generate docs/23-superadmin/superadmin-reference.md from live codebase symbols.

Links every live BR, UC, BW, CW, CFR, and AFR id to its enforcing file:line.
Exits non-zero if any target file or search pattern does not resolve.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "23-superadmin"
OUT_MD = DOCS_DIR / "superadmin-reference.md"

# Format: (Spec ID, Title/Requirement, File relative to repo root, Pattern/Symbol to find)
SPEC_MAPPINGS = [
    # Business Rules
    (
        "BR-SA-001",
        "Institute identity uniqueness and validation",
        "modules/superadmin/domain/validators.py",
        "def validate_institute_id",
    ),
    (
        "BR-SA-002",
        "Valid institute email domain (@iiitdmj.ac.in)",
        "modules/superadmin/domain/validators.py",
        "def validate_institute_email",
    ),
    (
        "BR-SA-003",
        "Required attributes captured in archival snapshot",
        "modules/superadmin/models/archival.py",
        "metadata_snapshot = models.JSONField",
    ),
    (
        "BR-SA-004",
        "User archival eligibility (deactivated, 0 pending tx)",
        "modules/superadmin/domain/archival_policy.py",
        "def assess_user_archival_eligibility",
    ),
    (
        "BR-SA-005",
        "Archived user reversible restoration window default",
        "modules/superadmin/domain/archival_policy.py",
        "def calculate_reversible_deadline",
    ),
    (
        "BR-SA-017",
        "Historical data archival eligibility & date bounds",
        "modules/superadmin/services/historical_archive.py",
        "def create_historical_archive",
    ),
    (
        "BR-SA-018",
        "Pre-archive backup cryptographic checksum check",
        "modules/superadmin/services/historical_archive.py",
        "backup_checksum: str",
    ),
    (
        "BR-SA-019",
        "Archive data retention period enforcement",
        "modules/superadmin/models/archival.py",
        "retention_expires_at = models.DateField",
    ),
    (
        "BR-SA-020",
        "Archived data access mode (strictly read-only)",
        "modules/superadmin/selectors/archival.py",
        "def list_archived_users",
    ),
    (
        "BR-SA-021",
        "Permanent purge eligibility (retention elapsed)",
        "modules/superadmin/domain/archival_policy.py",
        "def assert_purge_eligible",
    ),
    (
        "BR-SA-022",
        "Dual authorization for permanent purge",
        "modules/superadmin/domain/state_machine.py",
        "class PurgeStateMachine",
    ),
    (
        "BR-SA-023",
        "Role/archival notification outbox timing",
        "modules/superadmin/services/notifications.py",
        "def queue_notification",
    ),
    (
        "BR-SA-024",
        "Failed login threshold alert configuration",
        "modules/superadmin/domain/constants.py",
        "CONFIG_KEY_FAILED_LOGIN_ALERT_THRESHOLD",
    ),
    (
        "BR-SA-025",
        "Immutable compliance audit log entry retention",
        "modules/superadmin/models/audit.py",
        "class SuperAdminAuditLog",
    ),
    (
        "BR-SA-026",
        "Super Admin operational content isolation",
        "modules/superadmin/selectors/scoping.py",
        "def scope_archived_users",
    ),
    (
        "BR-SA-028",
        "Denial of self-modification of admin privileges",
        "modules/superadmin/domain/validators.py",
        "def validate_no_self_modification",
    ),
    (
        "BR-SA-029",
        "Critical purge destructive execution confirmation",
        "modules/superadmin/services/purge.py",
        "def execute_purge",
    ),
    (
        "BR-SA-030",
        "Bulk operations batch size limit check",
        "modules/superadmin/domain/validators.py",
        "def validate_bulk_size",
    ),
    (
        "BR-SA-033",
        "Audit log export formatting",
        "modules/superadmin/api/views.py",
        "class AuditLogExportView",
    ),
    (
        "BR-SA-035",
        "System policy parameter key whitelist",
        "modules/superadmin/domain/validators.py",
        "def validate_configuration_key",
    ),
    (
        "ISS-SA-004",
        "30-Day Reversible Archival Window Governance",
        "modules/superadmin/domain/constants.py",
        "DEFAULT_POLICY_VALUES",
    ),
    # Use Cases
    (
        "UC-SA-014",
        "Identify and Filter Eligible Inactive Users",
        "modules/superadmin/selectors/archival.py",
        "def list_archived_users",
    ),
    (
        "UC-SA-015",
        "Archive Inactive User Account",
        "modules/superadmin/services/archival.py",
        "def archive_user",
    ),
    (
        "UC-SA-016",
        "Archive Historical Institute Module Data",
        "modules/superadmin/services/historical_archive.py",
        "def create_historical_archive",
    ),
    (
        "UC-SA-017",
        "View Archived User and Data Records",
        "modules/superadmin/selectors/archival.py",
        "def get_archived_user",
    ),
    (
        "UC-SA-018",
        "Restore Archived User Account within Window",
        "modules/superadmin/services/archival.py",
        "def restore_archived_user",
    ),
    (
        "UC-SA-019",
        "Restore Historical Module Data from Archive",
        "modules/superadmin/services/historical_archive.py",
        "def restore_historical_archive",
    ),
    (
        "UC-SA-020",
        "Generate Archival Compliance and Status Report",
        "modules/superadmin/selectors/audit.py",
        "def get_dashboard_metrics",
    ),
    (
        "UC-SA-021",
        "Download Archived Dataset Backup File",
        "modules/superadmin/models/archival.py",
        "backup_file_path = models.CharField",
    ),
    (
        "UC-SA-022",
        "Initiate Permanent Data Purge Request",
        "modules/superadmin/services/purge.py",
        "def create_purge_request",
    ),
    (
        "UC-SA-023",
        "Authorize or Reject Permanent Data Purge Request",
        "modules/superadmin/services/purge.py",
        "def decide_purge_request",
    ),
    (
        "UC-SA-024",
        "View Immutable System Audit Log",
        "modules/superadmin/selectors/audit.py",
        "def list_audit_logs",
    ),
    (
        "UC-SA-025",
        "Export System Audit Log to CSV",
        "modules/superadmin/api/views.py",
        "class AuditLogExportView",
    ),
    (
        "UC-SA-026",
        "View Admin Dashboard & Operational Metrics",
        "modules/superadmin/api/views.py",
        "class DashboardView",
    ),
    (
        "UC-SA-027",
        "Configure System Policy Parameters",
        "modules/superadmin/services/config.py",
        "def supersede_policy_param",
    ),
    (
        "UC-SA-031",
        "Finalize User as Permanently Non-Restorable",
        "modules/superadmin/services/archival.py",
        "def expire_reversibility_sweep",
    ),
    # Workflows
    (
        "CW-SA-01",
        "Permanent Data Purge Authorization Lifecycle",
        "modules/superadmin/domain/state_machine.py",
        "PURGE_TRANSITIONS",
    ),
    (
        "CW-SA-03",
        "Deactivated User Resolution & Archive Lifecycle",
        "modules/superadmin/domain/state_machine.py",
        "ARCHIVAL_TRANSITIONS",
    ),
    (
        "BW-SA-01",
        "Permanent Data Purge — Approved Path",
        "modules/superadmin/services/purge.py",
        "def execute_purge",
    ),
    (
        "BW-SA-02",
        "Permanent Data Purge — Rejected Path",
        "modules/superadmin/services/purge.py",
        "def decide_purge_request",
    ),
    (
        "BW-SA-07",
        "Archived User Restoration Within Reversible Window",
        "modules/superadmin/services/archival.py",
        "def restore_archived_user",
    ),
    (
        "BW-SA-08",
        "Archived User Reversibility Window Expiry",
        "modules/superadmin/services/archival.py",
        "def expire_reversibility_sweep",
    ),
    (
        "BW-SA-09",
        "Historical Data Archive and Restore",
        "modules/superadmin/services/historical_archive.py",
        "def restore_historical_archive",
    ),
    # Core Functional Requirements (CFR)
    (
        "CFR-SA-001",
        "User archival verification & status persistence",
        "modules/superadmin/services/archival.py",
        "def archive_user",
    ),
    (
        "CFR-SA-002",
        "Archived record identity immutability",
        "modules/superadmin/models/archival.py",
        "class ArchivedUserRecord",
    ),
    (
        "CFR-SA-004",
        "Identity format and validation rules",
        "modules/superadmin/domain/validators.py",
        "def validate_institute_id",
    ),
    (
        "CFR-SA-010",
        "User archival lifecycle and restoration window",
        "modules/superadmin/domain/state_machine.py",
        "class ArchivalStateMachine",
    ),
    (
        "CFR-SA-011",
        "Historical dataset archive lifecycle",
        "modules/superadmin/services/historical_archive.py",
        "def create_historical_archive",
    ),
    (
        "CFR-SA-012",
        "Historical dataset restoration",
        "modules/superadmin/services/historical_archive.py",
        "def restore_historical_archive",
    ),
    (
        "CFR-SA-013",
        "Permanent purge initiation & retention gate",
        "modules/superadmin/services/purge.py",
        "def create_purge_request",
    ),
    (
        "CFR-SA-014",
        "Dual authorization purge approval workflow",
        "modules/superadmin/services/purge.py",
        "def decide_purge_request",
    ),
    (
        "CFR-SA-015",
        "Permanent purge execution and data destruction",
        "modules/superadmin/services/purge.py",
        "def execute_purge",
    ),
    (
        "CFR-SA-016",
        "Purge request expiration sweep",
        "modules/superadmin/services/purge.py",
        "def expire_purge_requests_sweep",
    ),
    (
        "CFR-SA-017",
        "Immutable audit log event generation",
        "modules/superadmin/services/audit.py",
        "def record_audit_event",
    ),
    (
        "CFR-SA-018",
        "Audit log query and CSV export",
        "modules/superadmin/api/views.py",
        "class AuditLogExportView",
    ),
    (
        "CFR-SA-019",
        "Administrative dashboard KPI metrics",
        "modules/superadmin/selectors/audit.py",
        "def get_dashboard_metrics",
    ),
    (
        "CFR-SA-020",
        "Effective-dated policy versioning",
        "modules/superadmin/services/config.py",
        "def supersede_policy_param",
    ),
    (
        "CFR-SA-021",
        "Administrative permission gates",
        "modules/superadmin/registry.py",
        "PERMISSIONS",
    ),
    (
        "CFR-SA-022",
        "Administrative roles and grants",
        "modules/superadmin/registry.py",
        "ROLE_GRANTS",
    ),
    (
        "CFR-SA-023",
        "Notification outbox transactional queueing",
        "modules/superadmin/services/notifications.py",
        "def queue_notification",
    ),
    # Atomic Functional Requirements (AFR)
    (
        "AFR-SA-001",
        "Institute ID format verification",
        "modules/superadmin/domain/validators.py",
        "INSTITUTE_ID_REGEX",
    ),
    (
        "AFR-SA-002",
        "Institutional email domain regex",
        "modules/superadmin/domain/validators.py",
        "INSTITUTE_EMAIL_REGEX",
    ),
    (
        "AFR-SA-025",
        "User archival record initialization",
        "modules/superadmin/services/archival.py",
        "ArchivedUserRecord.objects.create",
    ),
    (
        "AFR-SA-026",
        "Deactivation status requirement check",
        "modules/superadmin/domain/archival_policy.py",
        "if not is_deactivated",
    ),
    (
        "AFR-SA-027",
        "Pending transactions verification check",
        "modules/superadmin/domain/archival_policy.py",
        "if has_pending_transactions:",
    ),
    (
        "AFR-SA-028",
        "Reversible restoration window deadline check",
        "modules/superadmin/domain/archival_policy.py",
        "def calculate_reversible_deadline",
    ),
    (
        "AFR-SA-029",
        "Archived user search and filtering",
        "modules/superadmin/selectors/archival.py",
        "def list_archived_users",
    ),
    (
        "AFR-SA-030",
        "Duplicate archival conflict prevention",
        "modules/superadmin/services/archival.py",
        'raise ConflictError("This user is already archived."',
    ),
    (
        "AFR-SA-031",
        "Historical dataset archive creation",
        "modules/superadmin/services/historical_archive.py",
        "HistoricalDataArchive.objects.create",
    ),
    (
        "AFR-SA-032",
        "Backup checksum mandatory validation",
        "modules/superadmin/services/historical_archive.py",
        "if not backup_checksum:",
    ),
    (
        "AFR-SA-033",
        "Archive date bounds validation",
        "modules/superadmin/services/historical_archive.py",
        "if date_range_end < date_range_start:",
    ),
    (
        "AFR-SA-034",
        "Archived user detail retrieval",
        "modules/superadmin/selectors/archival.py",
        "def get_archived_user",
    ),
    (
        "AFR-SA-035",
        "Historical archive detail retrieval",
        "modules/superadmin/selectors/archival.py",
        "def get_historical_archive",
    ),
    (
        "AFR-SA-036",
        "Archived user restoration transition",
        "modules/superadmin/domain/state_machine.py",
        '(ARCHIVAL_STATUS_REVERSIBLE, "restore", "super_admin")',
    ),
    (
        "AFR-SA-037",
        "Restoration metadata persistence",
        "modules/superadmin/services/archival.py",
        "record.status = next_status",
    ),
    (
        "AFR-SA-038",
        "Reversibility window expiration enforcement",
        "modules/superadmin/domain/state_machine.py",
        "raise ReversibilityExpiredError",
    ),
    (
        "AFR-SA-039",
        "Historical dataset restore flag update",
        "modules/superadmin/services/historical_archive.py",
        "archive.is_restored = True",
    ),
    (
        "AFR-SA-040",
        "Historical dataset restore audit logging",
        "modules/superadmin/services/historical_archive.py",
        "AUDIT_ACTION_DATASET_RESTORED",
    ),
    (
        "AFR-SA-041",
        "Historical dataset restore conflict guard",
        "modules/superadmin/services/historical_archive.py",
        'raise ConflictError("This dataset has already been restored.")',
    ),
    (
        "AFR-SA-044",
        "Premature purge retention check",
        "modules/superadmin/domain/archival_policy.py",
        "def assert_purge_eligible",
    ),
    (
        "AFR-SA-045",
        "Purge request initiation persistence",
        "modules/superadmin/services/purge.py",
        "PurgeRequest.objects.create",
    ),
    (
        "AFR-SA-046",
        "Duplicate pending purge request guard",
        "modules/superadmin/services/purge.py",
        'raise ConflictError("A pending purge request already exists',
    ),
    (
        "AFR-SA-047",
        "Dual-auth distinct actor enforcement",
        "modules/superadmin/domain/state_machine.py",
        "raise SelfApprovalForbiddenError()",
    ),
    (
        "AFR-SA-048",
        "Purge request IT Head decision transition",
        "modules/superadmin/domain/state_machine.py",
        '(PURGE_STATUS_PENDING_IT_HEAD, "approve_purge", "it_head")',
    ),
    (
        "AFR-SA-049",
        "Permanent purge physical destruction",
        "modules/superadmin/services/purge.py",
        "archive.is_purged = True",
    ),
    (
        "AFR-SA-050",
        "Purge request TTL expiration sweep",
        "modules/superadmin/services/purge.py",
        "def expire_purge_requests_sweep",
    ),
    (
        "AFR-SA-051",
        "Archival event notification dispatch",
        "modules/superadmin/services/archival.py",
        "queue_notification(",
    ),
    (
        "AFR-SA-052",
        "Audit log query with actor/action filters",
        "modules/superadmin/selectors/audit.py",
        "def list_audit_logs",
    ),
    (
        "AFR-SA-053",
        "Audit log streaming CSV formatting",
        "modules/superadmin/api/views.py",
        "writer = csv.writer(response)",
    ),
    (
        "AFR-SA-054",
        "Governance dashboard KPI aggregation",
        "modules/superadmin/selectors/audit.py",
        "def get_dashboard_metrics",
    ),
    (
        "AFR-SA-055",
        "Audit log immutable record creation",
        "modules/superadmin/services/audit.py",
        "def record_audit_event",
    ),
    (
        "AFR-SA-056",
        "System policy parameter version supersede",
        "modules/superadmin/services/config.py",
        "previous.effective_to = now",
    ),
    (
        "AFR-SA-057",
        "System policy active lookup with fallback",
        "modules/superadmin/selectors/config.py",
        "def get_active_policy_value",
    ),
    (
        "AFR-SA-058",
        "System policy parameter key validation",
        "modules/superadmin/domain/validators.py",
        "def validate_configuration_key",
    ),
    (
        "AFR-SA-081A",
        "Celery beat reversibility window sweep task",
        "modules/superadmin/tasks.py",
        "def expire_reversibility_window_task",
    ),
    (
        "AFR-SA-081B",
        "Bulk operation batch size validation",
        "modules/superadmin/domain/validators.py",
        "def validate_bulk_size",
    ),
    (
        "AFR-SA-081C",
        "Bulk limit exception instantiation",
        "modules/superadmin/domain/exceptions.py",
        "class BulkLimitExceededError",
    ),
    (
        "AFR-SA-081D",
        "Self-modification forbidden check",
        "modules/superadmin/domain/validators.py",
        "def validate_no_self_modification",
    ),
    (
        "AFR-SA-082",
        "Scheduled notification outbox drain task",
        "modules/superadmin/tasks.py",
        "def drain_notification_outbox_task",
    ),
]


def resolve_link(file_rel: str, pattern: str) -> tuple[int, str]:
    target_path = ROOT / file_rel
    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {file_rel}")
    lines = target_path.read_text(encoding="utf-8").splitlines()
    for idx, line in enumerate(lines, start=1):
        if pattern in line:
            return idx, f"{file_rel}#L{idx}"
    raise ValueError(f"Pattern '{pattern}' not found in {file_rel}")


def main() -> int:
    resolved_rows = []
    errors = []

    for spec_id, title, file_rel, pattern in SPEC_MAPPINGS:
        try:
            line_no, link = resolve_link(file_rel, pattern)
            resolved_rows.append((spec_id, title, f"[{file_rel}:{line_no}](../../{link})"))
        except (FileNotFoundError, ValueError) as exc:
            errors.append(f"[{spec_id}] {exc}")

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    content_lines = [
        "# Superadmin Module Specification Reference",
        "",
        "This document is automatically generated by `ops/docs/superadmin_reference.py`.",
        "It maps every live Business Rule (BR), Use Case (UC), Workflow (CW/BW),",
        "Core Functional Requirement (CFR), and Atomic Functional Requirement (AFR)",
        "to its enforcing source code location (`file:line`).",
        "",
        "| Specification ID | Description / Requirement | Code Enforcement Location |",
        "|---|---|---|",
    ]

    for spec_id, title, link in resolved_rows:
        content_lines.append(f"| **{spec_id}** | {title} | {link} |")

    content_lines.append("")
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(content_lines), encoding="utf-8")
    print(f"Successfully generated {OUT_MD} with {len(resolved_rows)} live spec mappings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
