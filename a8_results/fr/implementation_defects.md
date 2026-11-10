# Observed FR implementation defects

These findings are the 11 failing automated FR cases from the final run. They
describe the existing implementation only; production code was not modified.

| Frozen test case | Expected behavior | Observed behavior |
|---|---|---|
| `TC-FR-001` | Student participation status includes cycle `Semester-Autumn-2026`. | `/student-status` returns registration timestamps and a registered flag, but no cycle field. |
| `TC-FR-002`, `TC-FR-003`, `TC-FR-009`, `TC-FR-010` | Role assignment persists the specified start date `2026-08-01`. | The assignment API accepts an end time but does not use a supplied `starts_at`; the persisted start is the request-time timestamp. |
| `TC-FR-006`, `TC-FR-008` | An additional concurrent active Caretaker/Warden assignment is rejected without replacing the current assignment. | The API returns `201` and replaces the previous current assignment. |
| `TC-FR-052` | A Mess Warden can view monthly bills for supervisory oversight. | The Warden request is denied with `403`. |
| `TC-FR-082` | The vacation survey accepts the specified response `Yes`. | The API rejects that case-sensitive value with `409`; the implementation accepts lowercase `yes` or `no`. |
| `TC-FR-085` | Both Caretaker and Warden can retrieve vacation response summary counts. | The Caretaker request is denied with `403`; the report endpoint enforces Warden-only access. |
| `TC-FR-110` | A Mess Warden can retrieve a cross-cycle billing summary. | The Warden request is denied with `403`; `billing_summary` is behind the Caretaker-report permission path. |
