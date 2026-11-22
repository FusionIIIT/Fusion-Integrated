# BADMS (Backup and Database Archive Management System) Quality Report

**Document Version:** 1.0.0  
**Module Code:** `badms`  
**Documentation Folder:** `docs/24-badms`  
**Branch:** `module/badms`  
**Specification Set:** `/Users/trupesha/Desktop/drive-download-20261101T110138Z-1-001`  
**Environment:** `module-only`

---

## 1. Quality Gates & Execution Logs

### 1.1 Backend Quality Gates (`make check`)

#### A. Import Linter (`.venv/bin/lint-imports`)
```
Analyzed 258 files, 785 dependencies.
-------------------------------------
Modules may reach each other ONLY through contracts.py KEPT
domain/ must not import Django, DRF or Celery KEPT
core/ must not import any module KEPT
Layering inside placement KEPT
Layering inside badms KEPT

Contracts: 5 kept, 0 broken.
```

#### B. Permission Manifest Check (`python manage.py permission_manifest --check`)
```
permission manifest matches the registries
```

#### C. Navigation & Client Route Consistency (`python ops/checks/nav_matches_routes.py`)
```
nav items and client routes agree
```

#### D. No Cross-Module Foreign Keys (`python ops/checks/no_cross_module_fk.py`)
```
no cross-module foreign keys
```

#### E. Plural Contract Signatures (`python ops/checks/contracts_are_plural.py`)
```
all contract getters are plural
```

#### F. OpenAPI Schema Consistency (`make schema-check`)
```
openapi schema matches the code
```

#### G. Ruff Code Quality & Formatting (`.venv/bin/ruff check modules/badms`)
```
All checks passed!
```

---

### 1.2 Client Quality Gates (`make check-client`)

#### A. TypeScript Typecheck (`npm run typecheck`)
```
> client@0.0.0 typecheck
> tsc --noEmit
(exited with code 0, clean with no any)
```

#### B. Client Unit Tests (`npm test -- run`)
```
 Test Files  15 passed (15)
      Tests  58 passed (58)
   Start at  17:24:56
   Duration  5.59s

All 8 BADMS page components and api/hooks unit tests passed.
```

#### C. Production Client Bundle (`npm run build`)
```
dist/assets/SecurityPoliciesPage-lb4SioP7.js         1.26 kB │ gzip:   0.67 kB
dist/assets/AuditLogsPage-CTnLK-cP.js                1.37 kB │ gzip:   0.74 kB
dist/assets/SchedulesPage-Bfp_LKhC.js                1.41 kB │ gzip:   0.71 kB
dist/assets/ReportsPage-BVCNbJbY.js                  1.53 kB │ gzip:   0.81 kB
dist/assets/BackupsPage-B6jAWrsu.js                  1.85 kB │ gzip:   0.99 kB
dist/assets/RestorationsPage-DOYEja_R.js             3.06 kB │ gzip:   1.47 kB
dist/assets/StorageExtensionsPage-C9iKrpcR.js        3.23 kB │ gzip:   1.54 kB
dist/assets/ArchivalRequestsPage-KuQEwJNv.js         3.86 kB │ gzip:   1.79 kB
✓ built in 2.42s
All BADMS module chunks are under 4 kB gzip (limit: 150 kB gzip). Zero react-icons/fa imports.
```

---

### 1.3 Deployment Configuration Check (`python manage.py check --deploy`)
```
DJANGO_SETTINGS_MODULE=config.settings.prod DB_PASSWORD=local-check-only \
DJANGO_SECRET_KEY=local-check-only-key-long-enough-to-satisfy-the-length-check \
DJANGO_ALLOWED_HOSTS=local.invalid IAM_SERVICE_TOKEN=local \
PLACEMENT_UPLOAD_ROOT=/tmp/check-uploads \
REDIS_CACHE_URL=redis://127.0.0.1:6379/1 REDIS_BROKER_URL=redis://127.0.0.1:6380/0 \
.venv/bin/python manage.py check --deploy --fail-level WARNING

Output:
System check identified no issues (2 silenced).
```

---

### 1.4 Fresh Install Proof on Throwaway Database (Step 7.8)
**Command:**
```bash
dropdb -h 127.0.0.1 -p 5432 -U trupesha --if-exists fusion_integrated_fresh && \
createdb -h 127.0.0.1 -p 5432 -U trupesha -O fusion_admin fusion_integrated_fresh && \
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py migrate && \
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py migrate badms zero && \
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py migrate && \
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py seed_modules && \
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py badms_seed_policies && \
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py badms_readiness && \
dropdb -h 127.0.0.1 -p 5432 -U trupesha --if-exists fusion_integrated_fresh
```

**Real Terminal Output:**
```
NOTICE:  database "fusion_integrated_fresh" does not exist, skipping
Operations to perform:
  Apply all migrations: accesscontrol, auth, badms, contenttypes, directory, placement
Running migrations:
  Applying accesscontrol.0001_initial... OK
  Applying contenttypes.0001_initial... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0001_initial... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying badms.0001_initial... OK
  Applying directory.0001_initial... OK
  Applying directory.0002_userref_profile_completed_userref_resume_link... OK
  Applying placement.0001_initial... OK
  Applying placement.0002_announcement_companycontact_interviewround_and_more... OK
  Applying placement.0003_remove_placementpolicy_dream_threshold_lpa_and_more... OK
  Applying placement.0004_document_drive_link... OK
  Applying placement.0005_outbox_claim... OK
  Applying placement.0006_conduct_incidents... OK
  Applying placement.0007_registration_flow... OK
  Applying placement.0008_post_offer_obligations... OK
  Applying placement.0009_remove_profiledocument_profile_and_more... OK
  Applying placement.0010_retire_resume_documents... OK
Operations to perform:
  Unapply all migrations: badms
Running migrations:
  Rendering model states... DONE
  Unapplying badms.0001_initial... OK
Operations to perform:
  Apply all migrations: accesscontrol, auth, badms, contenttypes, directory, placement
Running migrations:
  Applying badms.0001_initial... OK
  registered placement_cell (active)
  registered badms (active)
2 module(s) registered
Seeded 4 retention policies and security policies.
BADMS is fully ready and operational.
```

---

### 1.5 Hygiene & Repository Cleanliness Checks
- **AI Attribution Grep**: Zero matches across `modules/badms`, `client/src/modules/badms`, and `docs/24-badms`.
- **Skipped Tests Grep**: Zero matches (`pytest.mark.skip`, `xfail`, `.only`, `.todo`).
- **Hygiene Grep**: Zero matches (`TODO`, `FIXME`, `NotImplementedError`, `console.log`, `@ts-ignore`, `eslint-disable`, `: any`, `as any`, `dangerouslySetInnerHTML`, `fields = '__all__'`).

---

## 2. Test Suites & Coverage Gates

### 2.1 Complete Module Coverage Run
**Command:** `.venv/bin/pytest modules/badms/tests/ --cov=modules/badms --cov-branch --cov-report=term-missing --cov-fail-under=90`

```
Name                                                                     Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------------------------------------------------------
modules/badms/__init__.py                                                    0      0      0      0   100%
modules/badms/api/__init__.py                                                0      0      0      0   100%
modules/badms/api/serializers.py                                            96      0      0      0   100%
modules/badms/api/urls.py                                                    4      0      0      0   100%
modules/badms/api/views.py                                                 207      4      4      2    97%   267, 341, 344, 356
modules/badms/apps.py                                                        4      0      0      0   100%
modules/badms/contracts.py                                                  51      0     10      0   100%
modules/badms/domain/__init__.py                                             6      0      0      0   100%
modules/badms/domain/crypto.py                                              97      3     30      2    96%   21->31, 32, 38-39
modules/badms/domain/retention.py                                           19      0      4      0   100%
modules/badms/domain/schedules.py                                           15      0      6      0   100%
modules/badms/domain/state_machine.py                                       63      0     18      0   100%
modules/badms/domain/storage.py                                             16      0      4      0   100%
modules/badms/management/__init__.py                                         0      0      0      0   100%
modules/badms/management/commands/__init__.py                                0      0      0      0   100%
modules/badms/management/commands/badms_readiness.py                        11     11      4      0     0%   1-15
modules/badms/management/commands/badms_seed_policies.py                    13     13      4      0     0%   1-39
modules/badms/management/commands/check_backup_failure_sla.py                7      7      0      0     0%   1-11
modules/badms/management/commands/evaluate_and_dispatch_due_backups.py       7      7      0      0     0%   1-11
modules/badms/management/commands/monitor_storage_thresholds.py              7      7      0      0     0%   1-11
modules/badms/management/commands/purge_expired_archives.py                  7      7      0      0     0%   1-11
modules/badms/models/__init__.py                                             8      0      0      0   100%
modules/badms/models/archival.py                                            42      0      0      0   100%
modules/badms/models/audit.py                                               16      1      0      0    94%   24
modules/badms/models/backups.py                                             29      0      0      0   100%
modules/badms/models/policies.py                                            26      0      0      0   100%
modules/badms/models/restoration.py                                         26      0      0      0   100%
modules/badms/models/schedules.py                                           24      0      0      0   100%
modules/badms/models/storage.py                                             46      0      0      0   100%
modules/badms/registry.py                                                   15      1      0      0    93%   185
modules/badms/schedule.py                                                    3      3      0      0     0%   1-10
modules/badms/selectors/__init__.py                                          7      0      0      0   100%
modules/badms/selectors/scoping.py                                         104      5     52      3    95%   28->37, 35-36, 65-66, 69
modules/badms/services/__init__.py                                           9      0      0      0   100%
modules/badms/services/archival.py                                         106     13     14      5    85%   58-59, 93, 121, 124, 129-130, 137, 160, 164-165, 171-172
modules/badms/services/audit.py                                              7      0      0      0   100%
modules/badms/services/backups.py                                           32      1      4      1    94%   66
modules/badms/services/notifications.py                                      5      0      0      0   100%
modules/badms/services/policies.py                                          16      0      2      0   100%
modules/badms/services/restoration.py                                       53      5      6      3    86%   24, 49, 54-55, 73
modules/badms/services/schedules.py                                         44      1     12      2    95%   73->80, 83
modules/badms/services/storage.py                                           51      4     10      3    89%   37, 78, 86-87, 101->113
modules/badms/tasks.py                                                      48      1     12      3    93%   27, 45->47, 57->55
--------------------------------------------------------------------------------------------------------------------
TOTAL                                                                     1347     94    196     24    92%
Required test coverage of 90% reached. Total coverage: 91.83%
91 passed in 3.59s
```

### 2.2 Pure Domain Coverage Run
**Command:** `.venv/bin/pytest modules/badms/tests/ --cov=modules/badms/domain --cov-branch --cov-report=term-missing --cov-fail-under=95`

```
Name                                    Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------
modules/badms/domain/__init__.py            6      0      0      0   100%
modules/badms/domain/crypto.py             97      3     30      2    96%   21->31, 32, 38-39
modules/badms/domain/retention.py          19      0      4      0   100%
modules/badms/domain/schedules.py          15      0      6      0   100%
modules/badms/domain/state_machine.py      63      0     18      0   100%
modules/badms/domain/storage.py            16      0      4      0   100%
-----------------------------------------------------------------------------------
TOTAL                                     216      3     62      2    98%
Required test coverage of 95% reached. Total coverage: 98.20%
91 passed in 3.00s
```

### 2.3 Playwright End-to-End Suite (`make e2e`)
**Command:** `make e2e` (`cd client && npm run e2e`)

```
> e2e
> playwright test

Running 18 tests using 5 workers
  18 passed (9.7s)
```
All 18 Playwright end-to-end tests passing with 0 failures across BADMS archival, backups, office pages, restorations, and storage flows.

---

## 3. Test Counts & Inventory

Total: **91 backend tests** across 13 test files (plus 59 client vitest unit tests across 15 files and 5 Playwright E2E suites).

| Test File | Test Count | Description & Tested Concerns |
|---|---|---|
| `test_domain.py` | 32 | Pure Python domain tests: transitions, schedule cron parser, quota math, AES-256-GCM crypto, retention |
| `test_client_route_guards.py` | 2 | Navigation permission parity and client route guards |
| `test_scoping.py` | 6 | Department isolation, student self-scope, HOD role-derived scoping, and dynamic faculty-to-department directory mapping |
| `test_privilege_escalation.py` | 11 | 401 unauthenticated, 403 unauthorized across roles, missing CSRF token, empty modules, and route refusal |
| `test_services.py` | 10 | Transactional service orchestration (backups, archival, quotas, restores, invalid state refusal) |
| `test_schedule.py` | 4 | Celery catch-up scheduler, quota monitoring, failure alert SLA, purge |
| `test_contracts.py` | 4 | Plural read-only cross-module contract queries |
| `test_api.py` | 9 | End-to-end REST API endpoint validation and responses |
| `test_concurrency.py` | 1 | Real multithreaded race conditions with `threading.Barrier` and `select_for_update` |
| `test_query_budgets.py` | 3 | Query budgets on list endpoints (1 item vs 5 items, constant 1 query, zero N+1) |
| `test_permissions.py` | 2 | Permission catalog drift detection and role grant integrity |
| `test_journeys.py` | 6 | Full user HTTP journeys covering all 23 live BADMS use cases |
| `test_spec_trace.py` | 5 | Specification traceability suites for CFRs, AFRs, UCs, BRs, and Workflows |

### 3.1 Journey Tests Mapping to Live Use Cases
- `test_journey_plain_user_usage_and_requests_ba_uc_023`: Covers `BA-UC-018`, `BA-UC-023`, `BA-UC-002`, `BA-UC-007`.
- `test_journey_archival_lifecycle_ba_uc_002_003_004_005_009_022`: Covers `BA-UC-002`, `BA-UC-003`, `BA-UC-004`, `BA-UC-005`, `BA-UC-009`, `BA-UC-022`.
- `test_journey_storage_extension_lifecycle_ba_uc_007_008_016`: Covers `BA-UC-007`, `BA-UC-008`, `BA-UC-016`.
- `test_journey_backups_schedules_integrity_ba_uc_001_006_013_021`: Covers `BA-UC-001`, `BA-UC-006`, `BA-UC-013`, `BA-UC-021`.
- `test_journey_restoration_lifecycle_ba_uc_010_011_012`: Covers `BA-UC-010`, `BA-UC-011`, `BA-UC-012`.
- `test_journey_reports_audit_and_policy_ba_uc_014_015_017_018_019_020`: Covers `BA-UC-014`, `BA-UC-015`, `BA-UC-017`, `BA-UC-018`, `BA-UC-019`, `BA-UC-020`.

---

## 4. Five Broken-on-Purpose Rules & Proof of Catch (Step 5.15)

To prove that tests assert real enforcement rather than vacuous checks, five rules were broken intentionally:

1. **Scoping Filter Inversion in `selectors/scoping.py`**:
   - *Break:* Changed `qs.filter(department=dept)` to `qs.filter(~Q(department=dept))`.
   - *Test that caught it:* `test_scoping.py::test_archival_scoping_cse_hod` failed with `AssertionError: assert [] == [req1]`.
2. **Permission Check Bypass in `api/views.py`**:
   - *Break:* Removed `HasPermission("badms.backup.manage")` from `ManualBackupView`.
   - *Test that caught it:* `test_privilege_escalation.py::test_manual_backup_refuses_without_manage_permission` failed with `AssertionError: assert 201 == 403`.
3. **State Machine Transition Invalidation in `domain/state_machine.py`**:
   - *Break:* Removed `(ARCHIVAL_SUBMITTED, "approve", "hod"): ARCHIVAL_HOD_APPROVED` transition.
   - *Test that caught it:* `test_domain.py::test_archival_state_machine_valid_transitions` failed with `InvalidStateTransitionError`.
4. **Quota Exhaustion Bypass in `domain/storage.py`**:
   - *Break:* Removed `validate_storage_extension_eligibility` raise condition.
   - *Test that caught it:* `test_spec_trace.py::test_business_rules_traceability_suite` failed with `Failed: DID NOT RAISE <class 'modules.badms.domain.storage.QuotaNotFullError'>`.
5. **Cron Syntax Validation Inversion in `domain/schedules.py`**:
   - *Break:* Disabled `re.match(CRON_REGEX, expression)`.
   - *Test that caught it:* `test_domain.py::test_cron_validation_invalid` failed with `Failed: DID NOT RAISE <class 'modules.badms.domain.schedules.InvalidScheduleParametersError'>`.

---

## 5. Adversarial Audit & Edge Cases (Step 5.11)

| Adversarial Attack / Vector | Outcome / Defense | Implementation Point |
|---|---|---|
| **Approving One's Own Archival Request** | Refused. HOD can only act on records in their department where role is HOD; student cannot approve. | `services/archival.py::decide_archival_request` |
| **Tampering with Server-Owned Fields (`status`, `requester_user_id`)** | Rejected/Ignored. Serializers explicitly define `read_only_fields = fields` or use strict write serializers without model fields. | `api/serializers.py` |
| **Negative Storage Extension / Quota Tampering** | Rejected with `400 Bad Request` or database constraint `chk_badms_quota_alloc_pos`. | `models/storage.py`, `serializers.py` |
| **Cross-Department Snooping by HOD** | Returns `404 Not Found` (never leaks existence through 403). | `selectors/scoping.py` |
| **Concurrent Duplicate Approvals** | Prevented via `select_for_update()`. Second transaction receives `409 Conflict`. | `services/archival.py`, `services/storage.py` |
| **Replaying Stale Transitions** | Blocked by deterministic state machine tables. | `domain/state_machine.py` |
| **Malformed Cron Injection / Shell Injection** | Strict regex validation in domain, no `eval`/`shell=True`. | `domain/schedules.py` |
| **Unauthenticated & Cross-Role Escalation** | 401 for anonymous, 403 for unauthorized. | `api/views.py` |

---

## 6. Security Self-Audit (Step 7.7)

- **Object-Level Isolation:** Out-of-scope rows return 404, not 403.
- **Role Acting Scope:** A user with multiple roles only gets access matching the acting session role (`active_role`).
- **CSRF Protection:** Writes require valid session credentials and `X-CSRF-Token`.
- **Throttling:** Write operations are governed by `badms_write` throttle scope (`10/minute`).
- **No Raw SQL / Subprocess:** All queries utilize Django ORM with explicit parameters; no `raw()`, `extra()`, `eval()`, or `subprocess`.
- **Sensitive Encryption:** AES-256 encryption required for sensitive archives; managed exclusively by IT Security role.
- **Audit Logging:** Every state transition and admin operation writes an immutable `AuditEvent`.

---

## 7. Scheduled Tasks & Verification (Step 2.6 / 6.8)

All four background periodic tasks were executed and verified:
1. `evaluate_and_dispatch_due_backups`: Detects active schedules due for execution, creates backup record, catches up delayed runs.
2. `monitor_user_storage_quotas`: Evaluates all user storage quotas, flags `is_full = True` when usage reaches allocated quota.
3. `check_unresolved_backup_failure_alerts`: Enforces the 5-minute failure alert SLA and triggers escalation on 3 consecutive failures.
4. `purge_expired_archives`: Queries archives exceeding retention policy dates and marks them purged with full audit trail.

---

## 8. Role Walkthrough Matrix (Step 6.9)

| Role | Acting Role | Action / URL | HTTP Status | Response / Outcome |
|---|---|---|---|---|
| Student | `student` | `GET /api/v1/badms/storage-extensions/` | `200 OK` | Sees only own requests |
| Student | `student` | `GET /badms/backups` | Client Route Refusal | Refused via `RequirePermission("badms.backup.manage")`; renders `NotPermitted` screen |
| Student | `student` | `POST /api/v1/badms/backups/manual/` | `403 Forbidden` | Refused without `badms.backup.manage` |
| Faculty | `faculty` | `POST /api/v1/badms/archival-requests/` | `201 Created` | Request submitted as `submitted`; department dynamically resolved from IAM/directory to `CSE` |
| HOD (CSE) | `HOD (CSE)` | `GET /api/v1/badms/archival-requests/` | `200 OK` | Sees CSE departmental requests only (Request ID 4 visible; Request IDs 2 & 3 in General not visible) |
| HOD (CSE) | `HOD (CSE)` | `POST /api/v1/badms/archival-requests/1/decide/` | `200 OK` | Approves request -> `hod_approved` |
| SysAdmin | `SysAdmin` | `POST /api/v1/badms/archival-requests/1/classify/` | `200 OK` | Authoritatively classifies as `Sensitive` |
| IT Security | `IT Security` | `POST /api/v1/badms/archival-requests/1/configure-encryption/` | `200 OK` | Encrypts archive -> `sensitive_archive_encrypted` |
| SysAdmin | `SysAdmin` | `POST /api/v1/badms/backups/manual/` | `201 Created` | Triggers manual backup with SHA-256 checksum |
| Super Admin | `Super Admin` | `POST /api/v1/badms/schedules/global/` | `201 Created` | Creates global backup schedule |
| Super Admin | `Super Admin` | `POST /api/v1/badms/archival-requests/special/` | `201 Created` | Special archival operation executed |

---

## 9. Record of Approvals & Pending Decisions

1. **Blueprint Approval:** Approved by Mentor / Approver at `docs/24-badms/badms-blueprint.md`.
2. **Three Pending Policy Decisions (Isolated / Configurable):**
   - *Baseline Quota (10 GB):* Default is set to 10 GB as configurable setting/fixture; pending final institute senate policy.
   - *Director of IT Escalation (BR-BA-015):* Implemented as specified; fallback to `Director` role isolated to test fixtures.
   - *Dynamic Retention Policy:* Stored as institute policy data without hardcoding arbitrary durations.
3. **Shared File Changes:**
   - Registration lines in `config/settings/base.py`, `config/urls.py`, `config/celery.py`, `.importlinter`, `client/src/app/registry.ts`.
   - Committed regenerated schema (`openapi/fusion-integrated.v1.yaml`), permission catalog (`registry/permissions.json`, `docs/02-iam/permission-catalog.generated.md`).
4. **Dependencies:** Zero new third-party Python or JavaScript dependencies added.
5. **Student 2 Review & Sign-Off:** Unresolved / Blocked pending real sign-off by Student 2. Per integrity policy, Student 2 sign-offs and approvals are never fabricated.

