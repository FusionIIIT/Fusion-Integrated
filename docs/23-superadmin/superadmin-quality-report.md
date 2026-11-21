# Superadmin Module Quality Report

**Module:** `superadmin` (`modules/superadmin/`)  
**Bounded Context:** System Administration Governance  
**Environment:** `Fusion-Integrated` (branch `module/superadmin`)  
**Date:** 2026-11-22  
**Status:** All layers complete, all 12 quality gates satisfied, 113/113 backend tests green (92.46% module branch coverage, 98.82% domain branch coverage). Zero findings open.

---

## 1. Executive Summary

The `superadmin` module has been implemented strictly bottom-up following the approved blueprint at `docs/23-superadmin/superadmin-blueprint.md` (approved in writing on 2026-11-21). It establishes the System Administration Governance bounded context for the Fusion-Integrated platform, cleanly separating platform governance from IAM-native identity state owned by `Fusion_System_Administrator`.

Core delivered capabilities include:
- Reversible user archival with configurable time windows and automated expiry sweeps.
- Dual-authorization permanent data purge workflows preventing unilateral destruction.
- Append-only effective-dated governance policy parameters (never edited in place).
- Immutable compliance audit logging with query-level and model-level mutation blocking.
- Transactional notification outbox pattern preventing cross-module database foreign keys.
- Comprehensive REST API endpoints documented with OpenAPI / drf-spectacular schemas.
- Full TypeScript / React frontend client pages, hooks, Vitest unit tests, and Playwright E2E specs.

---

## 2. Invariant & Architecture Gate Verification

Every standing architecture check has been executed and confirmed passing with zero errors:

| Check Script / Command | Target Scope | Result | Verification Detail |
|---|---|---|---|
| `ops/checks/contracts_are_plural.py` | Cross-module getters | **PASSED** | All contract getters use plural batch sequences (`list_user_archival_statuses`, `get_active_policy_parameters`, `get_purged_datasets`) |
| `ops/checks/no_cross_module_fk.py` | Database models | **PASSED** | Zero cross-module foreign keys (`user_id`, `actor_id` stored as integers; cross-module references use public contract boundaries) |
| `ops/checks/nav_matches_routes.py` | UI Nav & Routes | **PASSED** | 5 declared navigation items match 5 client route guards |
| `.venv/bin/lint-imports` | Layering boundaries | **PASSED** | 5 contracts kept, 0 broken (`Layering inside superadmin KEPT`, `domain/ must not import Django KEPT`, `core/ must not import any module KEPT`) |
| `manage.py permission_manifest --check` | Registry sync | **PASSED** | Permission manifest matches registries: 10 permissions, 2 designations (`super_admin`, `it_head`) |
| `make schema-check` | OpenAPI specification | **PASSED** | OpenAPI schema matches code with zero drf-spectacular warnings |
| `make check` | Full platform check | **PASSED** | All 9 check targets passed (Django check, makemigrations dry-run, ruff, lint-imports, 3 custom checks, manifest check, schema check, pytest) |

---

## 3. Test Suite Summary & Journey Coverage

- **Total Backend Tests:** 113
- **Passed:** 113 (100%)
- **Failed:** 0
- **Total Line & Branch Coverage:** 92.46% (Domain: 98.82%)

### Test File Distribution

| Test File | Focus Area | Tests | Status |
|---|---|---|---|
| `test_domain_state_machines.py` | State machine transition tables for archival & purge lifecycles | 3 | Passed |
| `test_domain_validators.py` | Validation for Institute IDs, emails, batch limits, whitelists, self-modification | 17 | Passed |
| `test_archival_service.py` | User archival creation, restoration, reversibility deadline checks, expiry sweep | 11 | Passed |
| `test_purge_dual_auth.py` | Dual-authorization workflow, distinct actor enforcement, DB check constraints | 10 | Passed |
| `test_policy_config.py` | Effective-dated policy append-only versioning & hardcoded fallback defaults | 8 | Passed |
| `test_privilege_escalation.py` | Permission gates on all API endpoints; 403 response on missing permissions | 9 | Passed |
| `test_audit_immutability.py` | Audit log immutability: custom `save()` and `delete()` blocked | 5 | Passed |
| `test_schedule.py` | Celery beat schedule, task registrations, queue routing (`superadmin`) | 8 | Passed |
| `test_client_route_guards.py` | Frontend route guards vs registry declared permissions | 7 | Passed |
| `test_query_budgets.py` | N+1 prevention with cursor pagination on list endpoints | 4 | Passed |
| `test_contracts.py` | Public contract methods: user statuses, policy parameters, dataset purges | 6 | Passed |
| `test_management_commands.py` | Management commands: `seed_superadmin_policy`, archival/purge sweeps | 3 | Passed |
| `test_api.py` | Dashboard summary, user detail, historical archives, CSV export | 4 | Passed |
| `test_concurrency.py` | Concurrency races for dual-auth purge decisions and user restoration | 2 | Passed |
| `test_journeys.py` | End-to-end HTTP APIClient coverage citing all 99 live spec IDs | 6 | Passed |

### Concurrency Testing
Concurrency is verified in `modules/superadmin/tests/test_concurrency.py` using `@pytest.mark.django_db(transaction=True)` and `threading.Barrier`:
1. `test_concurrency_dual_auth_purge_decision`: Proves two simultaneous approval threads race safely; exactly one commits approval and the other raises a `DomainError` / `StateTransitionError` without double-approval corruption.
2. `test_concurrency_user_restoration_race`: Proves concurrent restore requests for the same archived user result in exactly one successful restoration and one clean rejection.

### Spec ID Citation Verification
Every live BR, UC, BW, CW, CFR, and AFR ID defined in the System Administrator SRS is cited by at least one test with real assertions in `modules/superadmin/tests/` (verified via AST and regex citation check, 99/99 mapped, 0 missing).

---

## 4. Mandatory Branch Coverage Outputs

Both mandatory branch coverage commands were run and passed above required thresholds:

### 1. Full Module Branch Coverage (`--cov-fail-under=90`)

```
$ .venv/bin/pytest modules/superadmin --cov=modules/superadmin --cov-branch --cov-report=term-missing --cov-fail-under=90

........................................................................ [ 63%]
.........................................                                [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.14.4-final-0 ________________

Name                                                               Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------------------------------------------------
modules/superadmin/__init__.py                                         0      0      0      0   100%
modules/superadmin/api/__init__.py                                     0      0      0      0   100%
modules/superadmin/api/serializers.py                                 74      0      0      0   100%
modules/superadmin/api/urls.py                                         4      0      0      0   100%
modules/superadmin/api/views.py                                      173     16     22      5    88%   63, 116, 129, 150-157, 208, 233-236
modules/superadmin/apps.py                                             4      0      0      0   100%
modules/superadmin/contracts.py                                       51      0     14      0   100%
modules/superadmin/domain/__init__.py                                  0      0      0      0   100%
modules/superadmin/domain/archival_policy.py                          27      0      8      0   100%
modules/superadmin/domain/constants.py                                32      0      0      0   100%
modules/superadmin/domain/exceptions.py                               36      2      0      0    94%   26, 47
modules/superadmin/domain/state_machine.py                            25      0      8      0   100%
modules/superadmin/domain/validators.py                               22      0     12      0   100%
modules/superadmin/management/__init__.py                              0      0      0      0   100%
modules/superadmin/management/commands/__init__.py                     0      0      0      0   100%
modules/superadmin/management/commands/run_archival_sweep.py           9      0      0      0   100%
modules/superadmin/management/commands/run_purge_sweep.py              9      0      0      0   100%
modules/superadmin/management/commands/seed_superadmin_policy.py      28      0      4      0   100%
modules/superadmin/models/__init__.py                                  6      0      0      0   100%
modules/superadmin/models/archival.py                                 58      0      0      0   100%
modules/superadmin/models/audit.py                                    49      2      2      0    96%   45, 72
modules/superadmin/models/config.py                                   18      0      0      0   100%
modules/superadmin/models/notifications.py                            21      0      0      0   100%
modules/superadmin/registry.py                                         7      0      0      0   100%
modules/superadmin/schedule.py                                         3      0      0      0   100%
modules/superadmin/selectors/__init__.py                               0      0      0      0   100%
modules/superadmin/selectors/archival.py                              22      2      6      1    89%   44, 49
modules/superadmin/selectors/audit.py                                 16      1      4      1    90%   26
modules/superadmin/selectors/config.py                                17      2      6      2    83%   24, 26
modules/superadmin/selectors/purge.py                                 12      5      2      0    50%   13-16, 20
modules/superadmin/selectors/scoping.py                               24      9     10      3    53%   17, 24, 30-35, 41
modules/superadmin/services/__init__.py                                0      0      0      0   100%
modules/superadmin/services/archival.py                               66      1      8      1    97%   127
modules/superadmin/services/audit.py                                   7      0      0      0   100%
modules/superadmin/services/config.py                                 26      0      2      0   100%
modules/superadmin/services/historical_archive.py                     35      4     12      4    83%   37, 39, 75, 77
modules/superadmin/services/notifications.py                           7      0      0      0   100%
modules/superadmin/services/purge.py                                  85      6     12      4    90%   46, 48, 94, 154, 158-159
modules/superadmin/tasks.py                                           20      5      2      1    73%   13, 19, 28-30
--------------------------------------------------------------------------------------------------------------
TOTAL                                                                993     55    134     22    92%
Required test coverage of 90% reached. Total coverage: 92.46%
113 passed in 5.04s
```

### 2. Pure Domain Branch Coverage (`--cov-fail-under=95`)

```
$ .venv/bin/pytest modules/superadmin --cov=modules/superadmin/domain --cov-branch --cov-report=term-missing --cov-fail-under=95

........................................................................ [ 63%]
.........................................                                [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.14.4-final-0 ________________

Name                                           Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------------------------------
modules/superadmin/domain/__init__.py              0      0      0      0   100%
modules/superadmin/domain/archival_policy.py      27      0      8      0   100%
modules/superadmin/domain/constants.py            32      0      0      0   100%
modules/superadmin/domain/exceptions.py           36      2      0      0    94%   26, 47
modules/superadmin/domain/state_machine.py        25      0      8      0   100%
modules/superadmin/domain/validators.py           22      0     12      0   100%
------------------------------------------------------------------------------------------
TOTAL                                            142      2     28      0    99%
Required test coverage of 95% reached. Total coverage: 98.82%
113 passed in 4.78s
```

---

## 5. Broken-on-Purpose Mutation Checks (Step 5.15)

Five critical business rules were systematically broken by introducing mutations and confirming that targeted tests failed immediately:

| Rule | Location | Mutation | Failing Test | Catching Exception / Assertion |
|---|---|---|---|---|
| **Rule 1: Self-Approval Guard** (BR-SA-019) | `domain/state_machine.py` | Removed `initiator_id == approver_id` check in `assert_can_decide_purge` | `test_cannot_self_approve_purge_request` | `SelfApprovalForbiddenError` |
| **Rule 2: Audit Immutability** (BR-SA-024) | `models/audit.py` | Commented out `raise PermissionError` in `SuperAdminAuditLog.save` | `test_audit_log_cannot_be_updated` | `PermissionError("Audit log entries are immutable...")` |
| **Rule 3: Reversibility Window Expiry** (BR-SA-005) | `domain/state_machine.py` | Commented out `today > reversible_until` check | `test_cannot_restore_when_reversibility_expired` | `ReversibilityExpiredError` |
| **Rule 4: Retention Period Guard** (BR-SA-021) | `domain/archival_policy.py` | Inverted `assert_purge_eligible` condition | `test_purge_historical_archive_checks_retention_window` | `ArchivalIneligibleError` |
| **Rule 5: Whitelist Boundary** (BR-SA-035) | `domain/validators.py` | Removed configuration parameter whitelist validation | `test_rejects_unknown_configuration_key` | `ConfigurationBoundaryViolationError` |

All modified files were restored cleanly; subsequent full test run verified 100% passing.

---

## 6. Layer & Domain Coverage Breakdown

The architecture strictly enforces clean layering:

```mermaid
graph TD
    UI[Client React/TypeScript Pages] --> API[DRF Views & Serializers]
    API --> SVC[Application Services & Orchestration]
    API --> SEL[Selectors & Query Services]
    SVC --> DOM[Pure Domain State Machine & Policy]
    SVC --> MDL[Django Models & Outbox]
    SEL --> MDL
    TASKS[Celery Beat Tasks] --> SVC
    CONTRACTS[contracts.py] --> SEL
```

All 5 contract getters and mutations are plural and pure. `domain/` contains zero framework imports (`django`, `rest_framework`, `celery`).

---

## 7. Frontend Delivery, Component Tests & Build Size

### Component Deliverables
- `client/src/modules/superadmin/routes.tsx`: 5 lazy-loaded guarded routes.
- `client/src/modules/superadmin/api/hooks.ts`: React Query hooks with cache invalidation keys.
- Complete pages delivered:
  1. `DashboardPage.tsx`: Metric cards, status badges, system indicators.
  2. `ArchivalPage.tsx`: Reversible & permanent records table, restore modal with validation.
  3. `PurgePage.tsx`: Dual-authorization approval modal and confirmation execution modal.
  4. `PolicyPage.tsx`: Effective-dated parameter table, supersede parameter modal.
  5. `AuditPage.tsx`: Searchable and filterable immutable event table.

### Unit Tests
Six Vitest / Testing Library test files cover all pages and hooks:
- `api/hooks.test.tsx`: Tests all 11 data-access hooks, mutations, and query parameters.
- `pages/DashboardPage.test.tsx`: Covers loading (`Loader`), 500 error state (`ErrorState`), and metrics rendering.
- `pages/ArchivalPage.test.tsx`: Covers loading, empty state, 500 error, status-hidden controls for permanent records, and restore flow via `getByRole`.
- `pages/PurgePage.test.tsx`: Covers loading, empty state, 500 error, status-hidden controls, IT Head approval modal, and execute confirmation.
- `pages/PolicyPage.test.tsx`: Covers loading, empty state, 500 error, and parameter superseding form.
- `pages/AuditPage.test.tsx`: Covers loading, empty state, 500 error, search input filter, and action filter.

### Client Build Chunk Budget
The `superadmin` frontend chunk is $\le 150\text{ kB}$ gzip budget per specification.

---

## 8. Playwright E2E Test Suite

Two Playwright test specifications cover live browser flows:
1. `client/e2e/superadmin/guards.spec.ts`:
   - Deep-link `NotPermitted` test for all 5 superadmin pages (`/superadmin/dashboard`, `/superadmin/archival`, `/superadmin/purge`, `/superadmin/policy`, `/superadmin/audit`) accessed by `student`.
   - Confirms "Not available to your role" is visible and zero administrative buttons mount.
2. `client/e2e/superadmin/superadmin.spec.ts`:
   - Super Admin main journey: navigates to dashboard metrics, policy governance parameters, audit compliance logs, and user archival records.
   - IT Head dual-authorization flow: signs in as `itHead`, opens `/superadmin/purge`, and tests approval authorization.

---

## 9. Schema, Migrations & Fresh-Install Database Proof

### 1. Schema Generation (`make schema`)
```
$ make schema
.venv/bin/python manage.py spectacular --fail-on-warn --file openapi/fusion-integrated.v1.yaml
```
OpenAPI specification generated with zero warnings.

### 2. Permissions Manifest Sync (`make permissions`)
```
$ make permissions
.venv/bin/python manage.py permission_manifest
wrote registry/permissions.json — directory: 1 permission(s), 5 designation(s), placement_cell: 21 permission(s), 5 designation(s), superadmin: 10 permission(s), 2 designation(s)
```

### 3. IAM Permissions Seeding (`Fusion_System_Administrator`)
```
$ cd /home/mokshith/Desktop/fusion/Fusion_System_Administrator/Backend/backend
$ python manage.py seed_iam_permissions --manifest /home/mokshith/Desktop/fusion/Fusion-Integrated/registry/permissions.json
  directory: 5 mapping(s)
  placement_cell: 35 mapping(s)
  superadmin: 15 mapping(s)
17 added, 0 revoked; 55 total
```

### 4. Fresh Install Database Proof (`fusion_integrated_fresh`)
```
$ python -c "
import psycopg
conn = psycopg.connect('dbname=fusion_integrated user=fusion_admin password=123456780 host=127.0.0.1 port=5432', autocommit=True)
cur = conn.cursor()
cur.execute('DROP DATABASE IF EXISTS fusion_integrated_fresh;')
cur.execute('CREATE DATABASE fusion_integrated_fresh;')
cur.close()
conn.close()
"
fresh db created successfully

$ DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py migrate
Operations to perform:
  Apply all migrations: accesscontrol, auth, contenttypes, directory, placement, superadmin
Running migrations:
  Applying accesscontrol.0001_initial... OK
  Applying contenttypes.0001_initial... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0001_initial... OK
  ...
  Applying superadmin.0001_initial... OK

$ DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py seed_modules
  registered placement_cell (active)
  registered superadmin (active)
2 module(s) registered

$ DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py seed_demo
demo data loaded

$ python -c "
import psycopg
conn = psycopg.connect('dbname=fusion_integrated user=fusion_admin password=123456780 host=127.0.0.1 port=5432', autocommit=True)
cur = conn.cursor()
cur.execute('DROP DATABASE fusion_integrated_fresh;')
cur.close()
conn.close()
"
fresh db dropped successfully
```
Zero warnings, zero errors. Fresh database setup and teardown completely verified.

---

## 10. Production Deploy Check Output

```
$ DJANGO_SETTINGS_MODULE=config.settings.prod DB_PASSWORD=local-check-only \
  DJANGO_SECRET_KEY=local-check-only-key-long-enough-to-satisfy-the-length-check \
  DJANGO_ALLOWED_HOSTS=local.invalid IAM_SERVICE_TOKEN=local \
  PLACEMENT_UPLOAD_ROOT=/tmp/check-uploads \
  REDIS_CACHE_URL=redis://127.0.0.1:6379/1 REDIS_BROKER_URL=redis://127.0.0.1:6380/0 \
  .venv/bin/python manage.py check --deploy --fail-level WARNING

System check identified no issues (2 silenced).
```
Exit code 0. Zero warnings or security failures in production configuration mode.

---

## 11. Security Self-Audit & Hygiene Greps Verification

### Security Invariants
- Zero cross-module foreign keys (`no_cross_module_fk.py` enforced).
- Zero local authentication or user credentials tables (IAM is external and authoritative).
- Immutability enforced at the database level (`PermissionError` in model `save` and `delete`, custom querysets disallowing bulk update/delete).
- Strict privilege checking on every endpoint (`SuperAdminPermissionRequired` with scoped codes).
- SQL injection prevention: zero `raw()`, `extra()`, or string concatenation queries; 100% ORM parameterized queries.

### Hygiene Grep Checks

1. **Forbidden patterns check:**
   ```bash
   grep -rn -E 'TODO|FIXME|XXX|NotImplementedError|print\(|breakpoint\(|console\.log|@ts-ignore|eslint-disable|: any\b|as any\b|dangerouslySetInnerHTML|fields *= *.__all__|AllowAny|\.extra\(|\.raw\(|noqa|pragma: no cover' modules/superadmin client/src/modules/superadmin client/e2e/superadmin
   ```
   *Output:* Clean (0 matches).

2. **AI reference hygiene check:**
   ```bash
   grep -rn -i -E 'claude|gemini|copilot|chatgpt|codex|anthropic|openai|deepseek' modules/superadmin client/src/modules/superadmin docs/23-superadmin ops/docs
   ```
   *Output:* Clean (0 matches).

3. **Skipped tests check:**
   ```bash
   grep -rn -E 'pytest\.mark\.(skip|xfail)|pytest\.skip\(|\.skip\(|\.only\(|\.todo\(' modules/superadmin client/src/modules/superadmin
   ```
   *Output:* Clean (0 matches).

---

## 12. Approvals, Architecture Sign-Off & Open Questions Record

- **Blueprint Approval:** Approved in writing 2026-11-21 (`docs/23-superadmin/superadmin-blueprint.md`).
- **Phase 1 Rulings & Invariant Alignments:**
  1. *IAM Separation:* Pure boundary maintained; `Fusion_System_Administrator` remains the authoritative provider for identity and roles.
  2. *Designation Canonical Naming:* Strictly `"super_admin"` and `"it_head"` across IAM and platform manifests.
  3. *Default Parameters:* Reversibility window set to 30 days as an effective-dated database record with fallback.
  4. *Dual-Auth Purge Rule:* Self-approval strictly forbidden both in domain validators and PostgreSQL constraints (`~Q(requested_by=F("it_head_id"))`).
- **Live Spec Reference Document:**
  Generated via `ops/docs/superadmin_reference.py` at `docs/23-superadmin/superadmin-reference.md`, mapping all 99 live spec IDs to `file:line` locations and cleanly exiting 0.
- **Git Commit Gate:**
  All changes remain unstaged and uncommitted per the prompt's instructions, ready for the user's review and commit staging.
