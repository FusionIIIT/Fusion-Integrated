# BADMS frontend API contract

The React frontend in `client/src/pages/BADMS/BADMSPages.jsx` adds the user-facing BADMS request and review workflows. The uploaded repository already provides backup, schedule, and basic archive endpoints. It does **not** currently expose the approval, storage-extension, or security-audit endpoints below, so the frontend screens that use them require matching backend implementation before end-to-end testing.

All paths are relative to the existing Axios base URL (`/api`). The backend must apply authentication, role-based authorization, department scoping, validation, and audit logging. Hiding a navigation link is not a security boundary.

## Endpoints expected by the frontend

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/badms/archive-requests/` | List the current user's requests; submit an archive request |
| GET, POST | `/badms/restore-requests/` | List restoration requests; submit a restoration request |
| GET | `/badms/approvals/?status=pending` | List approvals assigned to the current user |
| PATCH | `/badms/approvals/{id}/decision/` | Approve/reject a request with comments |
| GET, POST | `/badms/storage-requests/` | List and submit storage-extension requests |
| GET | `/badms/security/status/` | Return encryption/security posture summary |
| GET | `/badms/security/audit-logs/` | Return authorized audit events |

## Request payloads

### Archive request

```json
{
  "database_name": "student_records",
  "archive_type": "full",
  "data_classification": "internal",
  "reason": "Archive records according to the retention policy.",
  "retention_period_days": 365
}
```

### Restore request

```json
{
  "backup_id": "<backup UUID>",
  "target_database": "student_records_restore",
  "reason": "Recover records after an approved incident."
}
```

### Approval decision

```json
{
  "decision": "approved",
  "comments": "Reviewed and approved."
}
```

`decision` is `approved` or `rejected`.

### Storage-extension request

```json
{
  "current_storage_gb": 100,
  "requested_storage_gb": 150,
  "reason": "Storage usage is approaching the allocated limit."
}
```

## Suggested response fields

List endpoints may return an array or a paginated object with `results`. Request records should include `id`, `status`, `created_at` (or `submitted_at`), and the relevant submitted fields. Approval records should additionally include `request_type`, `requested_by_name`, `department`, and a short `description`/`reason`. Security status should include `encryption_enabled`, `algorithm`, `protected_database_count`, and `last_checked_at`. Audit rows should include `id`, `created_at`/`timestamp`, `actor_name`, `action`, `resource`, and `result`.

## Workflow/security requirements for backend integration

- Archive requests must be reviewed through the BADMS approval chain before archival execution.
- Restore requests must not directly invoke the existing `/backups/{id}/restore/` endpoint. Approval must be completed before restore execution.
- Approval lists and decisions must be scoped to the logged-in user's role and department by the backend.
- IT Security-only security information and audit records must be authorized server-side.
- Encryption status must reflect actual backend encryption configuration and verification; the UI must not claim AES-256 unless the backend confirms the exact implemented algorithm.
- Every request, decision, backup/restore execution, and security-sensitive action should create an audit event.
