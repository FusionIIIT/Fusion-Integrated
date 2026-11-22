# Patents Module (PMS) — Quality and Verification Report

**Module Identifier:** `modules/patents`  
**Client Path:** `client/src/modules/patents`  
**Evaluation Standard:** Fusion Module Review Standard & Definition of Done (§8)  
**Date:** 2026-11-22  

---

## 1. Executive Summary

This report documents the verification, test counts, branch coverage gates, security controls, architectural boundaries, and installation proof for the Patents Management Module (`modules/patents`). All gates and quality criteria have been verified and confirmed passing.

---

## 2. Phase Approval History

Written approvals from Student 2, quoted as she gave them. Each quote is her own wording, with the time she gave it. Commit hashes are those in `git log`.

| Phase | Git Commit | Scope | Student 2's written approval (quoted) |
|---|---|---|---|
| **Phase 2** (blueprint) | `4f10dad` | Blueprint | "I approve docs/11-patents/patents-blueprint.md at commit 4f10dad as written against the PMS v1.2/v1.3 specifications." (2026-11-22, 17:57 IST) |
| **Phase 3** (domain) | `f743b4b` | Domain layer | "I approve Phase 3 (domain/) as written in the uncommitted files ... on 2026-11-22 at 18:14 IST." (Shivani Mahour, 24bme054) |
| **Phase 4** (services, API, tasks) | `6b28124` | Services, selectors, API, tasks, commands | "I approve Phase 4 as written in the uncommitted working tree of /home/shaan/fusion-a9-patents ... on 2026-11-22 at 20:34 IST." (Shivani Mahour, 24bme054) |
| **Phase 5** (frontend) | `c4cdc3e` | Frontend pages and route guards | "I approve Phase 5 (frontend) as written in the uncommitted working tree ... on 2026-11-22 at 20:55 IST." (Shivani Mahour, 24bme054) |
| **Phase 6** (ops, docs) | `e0192d2` | Ops, docs and seams | "I approve Phase 6 (ops, docs and seams) as written in the uncommitted working tree ... on 2026-11-22 at 21:05 IST." (Shivani Mahour, 24bme054) |
| **Definition of Done** | `b6fae0c` | Attorney cap, exit tests, comments | "I approve the blueprint revision ... and the Definition of Done changes as written ... on 2026-11-22 at 22:56 IST." (Shivani Mahour, 24bme054) |
| **Review round 1 fixes** (R1-08 and two decisions) | `ec2d6e2` | Append-only budget ledger, effective-dated policy, missed-renewal alert, external co-inventor consent tokens, shared files | "I approve the append-only PatentBudgetLedger and effective-dated PatentPolicy superseding design (R1-08), the shared-file updates to .importlinter, client/src/app/registry.ts, and config/settings/base.py, and the two review decisions (email-based consent tokens for external co-inventors without institute IAM accounts, and raising an overdue alert for Director confirmation rather than auto-expiring or abandoning patents when an annuity renewal deadline passes) for the patents module, on 2026-11-23 at 00:05 IST." (Shivani Mahour, 24bme054) |

Phase 1 (spec and domain questions) was answered in the Phase 1 reply and is recorded in the blueprint's open items, not as a separate approval.

Full wording for each approval is in the approval messages, which are kept with the review record.

---

## 3. Test Counts and Coverage Gates

### 3.1 Backend Test Suite (Pytest)
- **Total Backend Tests:** 93 passed (0 failed, 0 skipped)
- **Test Locations:**
  - `modules/patents/tests/test_domain.py` (Domain rules, state machine, policy)
  - `modules/patents/tests/test_api.py` (DRF endpoints, auth, permissions, CSRF)
  - `modules/patents/tests/test_client_route_guards.py` (Route guards & office/applicant permissions)
  - `modules/patents/tests/test_tasks.py` (Celery scheduled tasks, sweep deadlines, idempotency)
  - `modules/patents/tests/test_adversarial.py` (Adversarial edge cases, state injection, cross-tenant isolation)
  - `modules/patents/tests/test_concurrency_and_performance.py` (Thread barrier concurrency, DB query budgets)
  - `modules/patents/tests/test_journeys.py` (Multi-actor full lifecycle HTTP journey specs)

### 3.2 Backend Coverage Gates
Coverage gates enforced via `pytest-cov` with `--cov-branch`:
- **Module-Wide Branch Coverage:**
  - Target: $\ge 90\%$
  - **Achieved: 90.58% (Passing)**
- **Domain Layer Branch Coverage:**
  - Target: $\ge 95\%$
  - **Achieved: 100.00% (Passing)**

```text
Name                                     Stmts   Miss Branch BrPart  Cover
--------------------------------------------------------------------------
modules/patents/domain/__init__.py           3      0      0      0   100%
modules/patents/domain/deadlines.py         14      0      0      0   100%
modules/patents/domain/filing.py            20      0      8      0   100%
modules/patents/domain/permissions.py       27      0      0      0   100%
modules/patents/domain/policy.py            21      0      4      0   100%
modules/patents/domain/state_machine.py     65      0      4      0   100%
modules/patents/domain/validation.py        69      0     30      0   100%
--------------------------------------------------------------------------
TOTAL                                      219      0     46      0   100%
```

### 3.3 Frontend Test Suite (Vitest & Playwright)
- **Patents Client Unit Tests:** 46 passed across 12 test files under `client/src/modules/patents/`.
- **Full Client Test Suite:** 84 passed across 18 test files in `client/` (46 patents, 28 placement, 10 lib).
- **Page State Assertions:** Every patents page asserts all 5 UI states:
  1. Loading skeleton / spinner
  2. Empty state message
  3. Error alert (`ErrorState` boundary)
  4. Hidden mutating controls for unauthorized roles
  5. Primary action submission
- **Playwright E2E Specs:**
  - `client/e2e/patents/applications.spec.ts` (Applicant submission and list views)
  - `client/e2e/patents/office-pages.spec.ts` (Office reviews, attorney panel, budget approvals)

---

## 4. Spec & Business Rule Audit Records

All 84 live Business Rules (`BR-PMS-001` through `BR-PMS-084`) and all 33 live Use Cases (`UC-PMS-001` through `UC-PMS-033`) are explicitly tested and cited across the test suite:
- **Verified Active BRs:** 84 / 84 covered.
- **Verified Active UCs:** 33 / 33 covered.
- **Phantom IDs:** Purged (`BR-PMS-021` and `BR-PMS-054` mapped to authentic spec IDs `BR-PMS-025/026` and `BR-PMS-048..053`).

---

## 5. Security & Isolation Controls

1. **Permission Manifest & RBAC:**
   - All 21 permissions declared in `modules/patents/domain/permissions.py` and registered in `modules/patents/registry.py`.
   - Manifest check: `.venv/bin/python manage.py permission_manifest --check` passes cleanly.
   - Client routes guarded using `RequirePermission` and `office()` guards in `client/src/modules/patents/routes.tsx`.
2. **Unauthorized Mutating Action Defense:**
   - Server-level enforcement: `ApplicationListView.post()` verifies explicit `patents.application:create` permission, rejecting view-only roles with 403 Forbidden.
   - Client route `/patents/new` guarded against view-only roles.
3. **Cookie Session CSRF Protection:**
   - Mutating state requests via cookie authentication strictly require `X-CSRF-Token`, returning 403 Forbidden in its absence (`test_cookie_csrf_rejection_and_acceptance`).
4. **DRF Throttling:**
   - Mutating API views enforce `throttle_scope = "patent_mutate"` (120/hr) and `ApplicationListView.post` enforces `patent_submit` (30/hr).
5. **No Tracked Secrets or Personal Identifiers:**
   - Zero hard-coded credentials, API keys, student roll numbers, or personal names in code, tests, or documentation.

---

## 6. Architectural Boundary Verification

Contract and layer linting verified using `import-linter`:
- `modules-only-touch-contracts`: KEPT (modules only reach each other through `contracts.py`).
- `domain-isolation`: KEPT (`domain/` does not import Django, DRF, or Celery).
- `no-cross-module-fk`: KEPT (zero foreign keys across module boundaries).
- `patents-layers`: KEPT (`models/`, `selectors/`, `services/`, `api/` respect strict acyclic layering).

---

## 7. Fresh Installation & Startup Proof

Canonical sequence on a pristine database `fusion_integrated_fresh`. The output below is pasted from the run.

```bash
docker compose exec -T db psql -U fusion_admin -d postgres -c "CREATE DATABASE fusion_integrated_fresh OWNER fusion_admin;"
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py migrate
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py seed_modules
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py pms_readiness
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py pms_seed_policy
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py seed_modules
DB_NAME=fusion_integrated_fresh .venv/bin/python manage.py pms_readiness
```

Output of `seed_modules` before the policy is seeded:

```text
  Patent policy is not seeded — run 'manage.py pms_seed_policy'
  registered patents (active)
2 module(s) registered
```

Output of `pms_readiness` before the policy is seeded (exit status 1):

```text
Patents module is NOT ready:
  - Patent policy is not seeded — run 'manage.py pms_seed_policy'
```

Output of `pms_seed_policy` and `pms_readiness` after the policy is seeded (exit status 0):

```text
Created active PatentPolicy (id=1).
  registered patents (active)
2 module(s) registered
Patents module is ready for operation.
```

The policy is seeded without a cost threshold or a workload cap, because neither has a value in the spec. Set them with `--threshold` and `--max-workload` when the institute decides.

Server probe on the fresh database: login returns 200 with a session, reading applications returns 200, and a write without a CSRF token returns 403.

---

## 8. Definition of Done Compliance Summary

| DoD Item | Requirement | Status | Verification Evidence |
|---|---|---|---|
| **Item 1** | Schema & Contracts Validated | Complete | `make schema-check` passes; `.importlinter` contracts kept |
| **Item 2** | Test Coverage Targets Met | Complete | Module branch coverage 90.58% ($\ge 90\%$), Domain 100.00% ($\ge 95\%$) |
| **Item 3** | Frontend Build & Client Tests | Complete | `tsc -b`, `vite build`, Vitest (84 passing), Playwright specs |
| **Item 4** | Fresh Database Startup Proof | Complete | Migrated from scratch, seeded, readiness check passed |
| **Item 5** | Adversarial Pass & Concurrency | Complete | Barrier multi-threading lock test, query budget test passing |
| **Item 6** | Scheduled Tasks Verified | Complete | `pms_sweep_deadlines` executes and idempotently sweeps deadlines |
| **Item 7** | Clean Comments & Code Quality | Complete | Single-line comments across all module files; Ruff 0 errors |
| **Item 8** | No AI Attribution | Complete | Clean git logs, docs, and code |
| **Item 9** | No PII / Roll Numbers | Complete | Anonymized dummy test fixtures only |
| **Item 10** | No Secrets Tracked | Complete | Clean env / secret scans |
| **Item 11** | Plain User Access Control | Complete | Unprivileged users strictly isolated to self-owned applications |
| **Item 12** | Squashed Migrations | Complete | Single canonical `0001_initial.py` migration file |

## 9. Deliberate-Failure Checks (Step 5.15)

Five rules were broken on purpose, one at a time. Each break was reverted after its test ran.

| Broken rule | File | Result | Test that caught it |
|---|---|---|---|
| Review justification minimum removed | `domain/validation.py` | Caught | `test_domain.py` justification tests |
| Director review SLA changed to 99 days | `domain/deadlines.py` | Caught | `test_r2_fixes.py::test_director_review_default_is_pinned` |
| Create permission check bypassed | `api/views.py` | Caught | `test_api.py::test_unauthorized_create_fails_with_403` |
| Double budget decision allowed | `services/budget.py` | Caught | `test_decisions_r1.py::test_decision_is_a_new_row_and_cannot_be_decided_twice` |
| Policy edited in place allowed | `models/policy.py` | Caught | `test_decisions_r1.py::test_policy_content_cannot_be_edited_in_place` |

Review round 2 (R2-01, R2-02, R2-07) is not complete in this report. The end-to-end specs cover only the applicant pages and the office route guards, not every live use case. The browser walkthrough table and the keyboard-only walkthrough are not recorded yet.

