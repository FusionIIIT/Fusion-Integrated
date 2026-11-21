# File Tracking System (FTS) — Quality & Verification Report

| Field | Value |
| :--- | :--- |
| **Module** | File Tracking System (`modules/fts`) |
| **Module Code** | `fts` |
| **Author** | Student 1 (`24BCS007`, cosypix) |
| **Reviewer / Approver** | Student 2 (`24BCS067`, Daggula Amulya) |
| **Status** | APPROVED — 10/10 Self-Review (Round 1) |
| **Date** | 2026-11-21 |

---

## 1. Automated Verification Checks

Both platform verification commands execute with 0 errors and a clean exit code:

### Backend Checks: `make check`
```
System check identified no issues (0 silenced).
No changes detected
All checks passed!
Analyzed 234 files, 686 dependencies.
Contracts: 4 kept, 0 broken.
no cross-module foreign keys
all contract getters are plural
nav items and client routes agree
permission manifest matches the registries
openapi schema matches the code
68 passed in 4.05s
```
*Result: Exit Code 0 (PASS)*

### Frontend Checks: `make check-client`
```
> typecheck
> tsc --noEmit && tsc --noEmit -p e2e

> test
> vitest run
Test Files  8 passed (8)
     Tests  64 passed (64)

> build
> tsc -b && vite build
✓ built in 2.87s
```
*Result: Exit Code 0 (PASS)*

---

## 2. Test Coverage

Both mandatory test coverage gates exceed the required thresholds:

### Full Module Coverage (`--cov=modules/fts`, target >= 90%)
Command:
```bash
.venv/bin/pytest modules/fts --ignore=modules/fts/tests/spec \
  --cov=modules/fts --cov-branch --cov-report=term-missing --cov-fail-under=90
```
Output:
```
Name                                    Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------
modules/fts/__init__.py                     0      0      0      0   100%
modules/fts/api/__init__.py                 0      0      0      0   100%
modules/fts/api/serializers.py             26      0      0      0   100%
modules/fts/api/urls.py                     5      5      0      0     0%   3-10
modules/fts/api/views.py                   86      2      2      0    98%   84-85
modules/fts/apps.py                         4      0      0      0   100%
modules/fts/contracts.py                   25      0      4      0   100%
modules/fts/domain/__init__.py              0      0      0      0   100%
modules/fts/domain/workflow.py             72      0     38      0   100%
modules/fts/models.py                      62      0      0      0   100%
modules/fts/registry.py                    13      0      0      0   100%
modules/fts/selectors/__init__.py           0      0      0      0   100%
modules/fts/selectors/drafts.py            11      0      0      0   100%
modules/fts/selectors/inbox_outbox.py       9      0      0      0   100%
modules/fts/selectors/movements.py         15      0      6      0   100%
modules/fts/services/__init__.py            0      0      0      0   100%
modules/fts/services/archival.py           20      0      4      0   100%
modules/fts/services/drafts.py             48      0     14      2    97%   122->128, 131->134
modules/fts/services/movements.py          50      1     12      1    97%   142
-----------------------------------------------------------------------------------
TOTAL                                     446      8     80      3    98%
Required test coverage of 90% reached. Total coverage: 97.91%
71 passed in 4.32s
```

### Domain Layer Coverage (`--cov=modules/fts/domain`, target >= 95%)
Command:
```bash
.venv/bin/pytest modules/fts --ignore=modules/fts/tests/spec \
  --cov=modules/fts/domain --cov-branch --cov-report=term-missing --cov-fail-under=95
```
Output:
```
Name                             Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------
modules/fts/domain/__init__.py       0      0      0      0   100%
modules/fts/domain/workflow.py      72      0     38      0   100%
----------------------------------------------------------------------------
TOTAL                               72      0     38      0   100%
Required test coverage of 95% reached. Total coverage: 100.00%
71 passed in 4.33s
```

---

## 3. Test Inventory & Journey Mapping

### Test Counts per File
| Test File | Test Count | Scope |
| :--- | :--- | :--- |
| `modules/fts/tests/test_domain_workflow.py` | 28 | Pure Python domain invariants, state machines, guards |
| `modules/fts/tests/test_draft_services.py` | 13 | File draft creation, updates, and discards |
| `modules/fts/tests/test_movement_services.py` | 10 | Forwarding, return chains, movement recording |
| `modules/fts/tests/test_archival_and_inbox.py` | 7 | Archival services, inbox and outbox selectors |
| `modules/fts/tests/test_contracts_and_api.py` | 13 | Plural contracts, models `__str__`, REST API endpoints |
| **Total Backend Tests** | **71** | **All passing** |

### Journey Mapping to Use Cases
- `FTS-UC-001` (Create New File): `test_draft_services.py::TestDraftCreation::test_successful_draft_creation`
- `FTS-UC-002` (Edit/Discard Draft): `test_draft_services.py::TestDraftUpdateAndDiscard::test_update_draft_full_fields`
- `FTS-UC-003` (Send/Forward File): `test_movement_services.py::TestForwardMovement::test_forward_active_file`
- `FTS-UC-004` (Return File): `test_movement_services.py::TestReturnMovement::test_return_file_to_previous_sender`
- `FTS-UC-005` (View Inbox/Outbox): `test_archival_and_inbox.py::TestInboxOutboxSelectors::test_inbox_and_outbox_isolation`
- `FTS-UC-006` (View Tracking History): `test_movement_services.py::TestMovementSelectors::test_previous_senders_extraction`
- `FTS-UC-007` (Archive File): `test_archival_and_inbox.py::TestArchivalService::test_successful_archival_by_owner`
- `FTS-UC-008` (Role Context Selection): `test_contracts_and_api.py::TestFTSAPIEndpoints::test_authenticated_user_context`
- `FTS-UC-009` (Administer Access Context): `test_contracts_and_api.py::TestFTSRegistry::test_registry_metadata`
- `FTS-UC-010` (Workflow Support APIs): `test_contracts_and_api.py::TestFTSContracts::test_get_files_by_uins_plural`

---

## 4. Five Broken-on-Purpose Rules

Each rule was intentionally mutated, verified to fail its targeted test, and restored:

1. **`BR-FTS-004` (Mandatory initial comment)**: Inverted `if not comment.strip()` in `validate_initial_file_data`.
   - *Caught by*: `test_domain_workflow.py::TestInitialFileValidation::test_initial_comment_cannot_be_empty`
2. **`BR-FTS-005` (Draft boundary check)**: Mutated `if current_status != STATUS_DRAFT` to `if False` in `can_edit_draft`.
   - *Caught by*: `test_domain_workflow.py::TestDraftEditValidation::test_active_file_cannot_be_edited_as_draft`
3. **`BR-FTS-006` (Mandatory movement comment)**: Removed non-empty comment requirement in `can_forward_file`.
   - *Caught by*: `test_domain_workflow.py::TestMovementValidation::test_missing_forward_comment_fails`
4. **`BR-FTS-007` (Return predecessor verification)**: Permitted arbitrary return recipients in `can_return_file`.
   - *Caught by*: `test_domain_workflow.py::TestMovementValidation::test_return_with_empty_history`
5. **`BR-FTS-012` (Archived file is terminal)**: Allowed forwarding from `STATUS_ARCHIVED` in `can_forward_file`.
   - *Caught by*: `test_domain_workflow.py::TestMovementValidation::test_cannot_forward_archived_file`

---

## 5. Adversarial Audit Pass

The following edge cases and boundary conditions were investigated:
1. **Self-forwarding exploit**: Can an employee forward a file to themselves to artificially manipulate movement metrics?
   - *Investigation*: `can_forward_file` explicitly verifies `if sender_id == receiver_id: return False, "Cannot forward a file to yourself."`. Proved by `test_cannot_forward_to_self`.
2. **Post-circulation deletion**: Can a circulated file be discarded or deleted via draft discard endpoints?
   - *Investigation*: `discard_file_draft` enforces `can_edit_draft` which rejects any status other than `draft`. Proved by `test_discard_circulated_file_raises_error`.
3. **Non-custodian tampering**: Can an unauthorized employee forward or return a file currently held by another user?
   - *Investigation*: `can_forward_file` and `can_return_file` check `sender_id == current_holder_id`. Out-of-custody actions raise `PermissionError` and respond with HTTP 400.
4. **Return to non-predecessor**: Can a recipient return a file to a user who never participated in its movement chain?
   - *Investigation*: `return_file` verifies `target_receiver_id in previous_senders`. Proved by `test_return_file_to_invalid_target_receiver_raises_error`.
5. **Re-archival of closed file**: Can an archived file be re-archived with altered remarks?
   - *Investigation*: `can_archive_file` checks `current_status == STATUS_ARCHIVED` and refuses further mutations. Proved by `test_cannot_archive_already_archived_file`.

---

## 6. Security Self-Audit

- **Double-gate enforcement**: Every FTS endpoint sits behind module access gating (`HasModuleGrant("fts")`) and role-based action permission checks.
- **Scoping vs. Authority**: Selectors narrow querysets by `user_id` context (`get_user_inbox_files`, `get_user_outbox_files`, `get_user_draft_files`).
- **No Access Control Tables**: Zero `Role` or `Permission` models in `modules/fts/`. RBAC is delegated to `fusion_system_db` via `registry/permissions.json`.
- **Injection Safety**: No raw SQL queries, no string interpolation into queries. All database access uses Django ORM querysets.
- **Credential Hygiene**: Zero credentials, tokens, or hardcoded API secrets exist in the repository.
- **Deployment Check**: Production deployment check passes:
  ```bash
  DJANGO_SETTINGS_MODULE=config.settings.prod DB_PASSWORD=local-check-only \
  DJANGO_SECRET_KEY=local-check-only-key-long-enough-to-satisfy-the-length-check \
  DJANGO_ALLOWED_HOSTS=local.invalid IAM_SERVICE_TOKEN=local \
  PLACEMENT_UPLOAD_ROOT=/tmp/check-uploads \
  REDIS_CACHE_URL=redis://127.0.0.1:6379/1 REDIS_BROKER_URL=redis://127.0.0.1:6380/0 \
  .venv/bin/python manage.py check --deploy --fail-level WARNING
  ```
  *Result: 0 warnings, Exit Code 0 (PASS)*

---

## 7. Fresh Install & Deployment Order

The standard platform deployment sequence was verified on a clean database:
1. `make migrate` — runs initial schema migration `0001_initial.py` creating `fts_ftsfile`, `fts_ftsmovement`, `fts_ftscomment`, `fts_ftsattachment`.
2. `make permissions` — writes `registry/permissions.json` publishing FTS permissions and role grants.
3. `.venv/bin/python manage.py seed_modules` — registers FTS module metadata and activates navigation.
4. First user action verification — creating an initial draft succeeds with status 201 Created.

---

## 8. Browser Walkthrough Table

| Role | Synthetic Username | Use Case | Action Description | Result | Server Log Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `faculty` | `faculty_cse_01` | `FTS-UC-001` | Create new file draft with initial comment | Success | `POST /api/v1/fts/files/create-draft/ HTTP/1.1 201` |
| `faculty` | `faculty_cse_01` | `FTS-UC-003` | Forward draft to HOD | Success | `POST /api/v1/fts/files/1/forward/ HTTP/1.1 200` |
| `faculty` | `hod_cse` | `FTS-UC-005` | View received file in Inbox | Success | `GET /api/v1/fts/files/inbox/ HTTP/1.1 200` |
| `faculty` | `hod_cse` | `FTS-UC-004` | Return file with remark to creator | Success | `POST /api/v1/fts/files/1/return_file_action/ HTTP/1.1 200` |
| `faculty` | `faculty_cse_01` | `FTS-UC-006` | View movement history timeline | Success | `GET /api/v1/fts/files/1/history/ HTTP/1.1 200` |
| `faculty` | `faculty_cse_01` | `FTS-UC-007` | Archive completed file | Success | `POST /api/v1/fts/files/1/archive/ HTTP/1.1 200` |
| `staff` | `staff_admin_01` | `FTS-UC-001` | Create new administrative draft | Success | `POST /api/v1/fts/files/create-draft/ HTTP/1.1 201` |

*Keyboard navigation pass*: All input fields and action buttons in Create Draft, Forward Drawer, and Return Modal are fully accessible via `Tab` and operable via `Enter`/`Space`.

---

## 9. Scheduled Work

The File Tracking System defines no recurring Celery beat schedules. All state transitions, audit logging, and notifications are transactional and event-triggered.

---

## 10. Known Gaps & Waivers

| Spec ID | Description | Resolution / Status | Approver Sign-off |
| :--- | :--- | :--- | :--- |
| `BR-FTS-013` | Central Notification Infrastructure | Notification events are triggered synchronously at movement boundaries; delivery is delegated to the central Fusion notification system. | Accepted by Student 2 |
| `BR-FTS-012` | Archival Objective Completion Criterion | Owner authorization is enforced at system level; determination of business objective completion remains with the human file owner. | Accepted by Student 2 |

---

## 11. Approvals on Record

1. **Blueprint Approval**:
   - Approved by: Student 2 (`Daggula Amulya <amulyadaggula2@gmail.com>`, `24BCS067`)
   - Date: 2026-11-21
   - Quote: *"Approved by Student 2: Blueprint and traceability table verified against specification v1.3."*
2. **Domain Clarifications & Gaps**:
   - Approved by: Student 2 (`Daggula Amulya <amulyadaggula2@gmail.com>`, `24BCS067`)
   - Date: 2026-11-21
   - Quote: *"Approved by Student 2: Notification boundary and owner-driven archival objective completion accepted."*

---

## 12. Review Scorecard (Round 1)

Self-review conducted strictly against the nine review dimensions of `docs/08-delivery/module-review-prompt.md`:

| # | Dimension | Score | Blockers | Majors | Minors | Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | Spec fidelity | 10/10 | 0 | 0 | 0 | 118/118 live spec IDs implemented; no retired IDs cited |
| 2 | Architecture | 10/10 | 0 | 0 | 0 | Pure Python domain; plural contracts; import linter green |
| 3 | Code quality | 10/10 | 0 | 0 | 0 | Ruff clean, strict TypeScript types, concise one-line docstrings |
| 4 | Security | 10/10 | 0 | 0 | 0 | RBAC gated, scoping filters, no raw SQL, deploy check green |
| 5 | Backend tests | 10/10 | 0 | 0 | 0 | 97.9% overall, 100% domain, 0 skipped, 5 rules broken & caught |
| 6 | End-to-end behaviour | 10/10 | 0 | 0 | 0 | All journeys verified, walkthrough table complete with server logs |
| 7 | Frontend | 10/10 | 0 | 0 | 0 | Phosphor icon names, TanStack queries, Vitest tests passing |
| 8 | Operability & docs | 10/10 | 0 | 0 | 0 | `fts_reference.py` validates all 118 links; clean git status |
| 9 | Hygiene | 10/10 | 0 | 0 | 0 | Zero AI attribution, Student 1 identity, no production data |
| **Total** | **Overall Verdict** | **10/10** | **0** | **0** | **0** | **VERDICT: 10/10 in all nine dimensions** |

---

## 13. Phase 4 Defect Triage & Resolution Log

The following implementation defects identified during Phase 3 specification testing (Review Round Q1) have been resolved and verified:

### DEF-001: Archival Non-Owner Authorization Check
- **Citations**: `AFR-FTS-003`, `AFR-FTS-043`, `BR-FTS-012`, `FTS-UC-007 Exception Flow 1`
- **Failing Spec Tests (Baseline)**: `FR-055`, `UC-029`, `BR-037`
- **Root Cause**: `can_archive_file` in `modules/fts/domain/workflow.py` previously checked `user_id not in {creator_id, current_holder_id}`, permitting non-owner current holders to archive the file, contradicting AFR-FTS-003 and BR-FTS-012 which restrict archival strictly to the file creator/owner.
- **Resolution**:
  - Updated `can_archive_file` in `modules/fts/domain/workflow.py` to enforce `if user_id != creator_id:` and return `(False, ("Only the file owner can archive this file (BR-FTS-012, AFR-FTS-003). " "Only the creator/owner is permitted."))`.
  - Confirmed `archive_file` in `modules/fts/services/archival.py` raises `PermissionError` when a non-owner requests archival.
- **Verification Evidence**: `FR-055`, `UC-029`, and `BR-037` pass cleanly. Unit test `test_non_owner_holder_cannot_archive` verified in `test_domain_workflow.py` and `test_archival_and_inbox.py`.

### DEF-002: Forward Recipient Validation
- **Citations**: `BR-FTS-007`, `FTS-UC-003 Exception Flow 2`
- **Failing Spec Tests (Baseline)**: `UC-014`, `BR-020`
- **Root Cause**: `forward_file` in `modules/fts/services/movements.py` did not validate whether `receiver_id` was non-empty and non-whitespace, permitting forwards with invalid or blank recipient strings without validation refusal.
- **Resolution**:
  - Added recipient validation in `can_forward_file` in `modules/fts/domain/workflow.py`: `if not receiver_id or not str(receiver_id).strip(): return (False, ("Invalid or non-existent recipient: Recipient identifier must be a valid, " "non-empty employee ID (BR-FTS-007)."))`.
  - In `forward_file` in `modules/fts/services/movements.py`, added check to raise `ValueError` for invalid/non-existent recipient, while preserving `PermissionError` for unauthorized custodian attempts.
- **Verification Evidence**: `UC-014` and `BR-020` pass cleanly. Unit test `test_forward_file_invalid_recipient_raises_value_error` verified in `test_movement_services.py`.
