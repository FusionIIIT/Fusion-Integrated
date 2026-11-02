# BADMS frontend API contract

The frontend is integrated into the existing Fusion System Administrator React/Vite client and uses the existing `axiosInstance` (same-origin `/api`, cookie authentication). It does not implement authentication, role grants, encryption, approval authority, or data archival in the browser.

The following endpoints are required from the backend. They are **not present in the supplied backend snapshot** and must be implemented by the backend owner before end-to-end workflow testing.

| Method | Endpoint | Purpose |
|---|---|---|
| GET, POST | `/api/badms/archive-requests/` | List the current user's requests; create a request with multipart attachment |
| GET, POST | `/api/badms/restore-requests/` | List and create restoration requests |
| GET | `/api/badms/approval-queue/` | Return requests actionable by the authenticated user |
| POST | `/api/badms/approval-queue/{id}/decision/` | Record `decision` (`approve` or `reject`) and `comments` |
| GET, POST | `/api/badms/storage-requests/` | List and submit storage extension requests |
| GET | `/api/badms/security/status/` | Return encryption status, algorithm, protected record count and last verification |
| GET | `/api/badms/security/audit-logs/` | Return security audit events |
| GET | `/api/badms/failure-alerts/` | Return backup failures, consecutive failure count, escalation target and alert status |

## Expected request fields

### Archive request (multipart/form-data)

- `file_name`
- `archive_date`
- `owners`
- `file_type`
- `reason`
- `initial_classification` (`Routine` by default, or `Sensitive`)
- `attachment` (optional file)

If the classification is missing, the backend must default it to `Routine`. The backend must validate the archival quota and required fields and reject invalid submissions; the UI displays the API validation response.

### Restoration request (JSON)

- `backup_id`
- `target_database`
- `classification` (`Routine` or `Sensitive`)
- `reason`

Non-Sensitive restoration follows the standard approval path. Sensitive restoration requires SysAdmin approval before execution.

### Storage extension request (JSON)

- `current_storage_gb`
- `requested_storage_gb`
- `reason`

The backend must enforce eligibility (quota full) and route the request to the HoD for a decision.

## Workflow and authorization responsibilities

- HoD: approve/reject archival requests originating from the same department; decide storage-extension requests.
- SysAdmin: determine the authoritative archival classification and approve Sensitive restoration requests.
- IT Security: review Sensitive archival requests and verify the AES-256 security path.
- Backend: enforce all role, department, quota, workflow-stage, file-validation, and security checks. Hiding a button or selecting a role in React is not authorization.
- Frontend: show the request's `status` and `current_stage` returned by the server; it must not advance workflow stages locally.

Suggested list response shape: an array or `{ "results": [...] }`. Each request should include `id`, `status`, `current_stage`, `created_at` and the fields relevant to its type. Approval-queue items should additionally include `request_type`, `department`, `classification`, `file_name` (when applicable), and `reason`.

## Backup and schedule screens

The existing Fusion client already provides manual backup, scheduled backup, schedule preview, pause/resume, backup history and restore APIs under `/backups/`, `/schedules/` and `/restores/`. The BADMS UI reuses these existing pages and API functions rather than duplicating them. The failure-alert view is an additional read-only BADMS view and requires the endpoint listed above.
