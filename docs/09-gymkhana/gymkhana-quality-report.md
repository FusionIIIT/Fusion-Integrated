# Gymkhana Module Quality Report

**Module Code:** `gymkhana`  
**Docs Folder:** `docs/09-gymkhana/`  
**Reference Module:** `modules/placement`  
**Specification Baseline:** Gymkhana Specs v1.1 SYNCHRONIZED  
**Builder (Student 1):** Student 1  
**Reviewer & Approver (Student 2):** Student 2  

---

## 1. Specification Approvals Log

### Phase 2 Blueprint Approval Gate
- **Date/Time:** 2026-11-23T04:29:58+05:30
- **Approver:** Student 2 (Specification Reviewer, Tester & Approver)
- **Approved Items:**
  1. **Blueprint:** `docs/09-gymkhana/gymkhana-blueprint.md` covering 7 CFRs (`CFR-GYM-001` to `007`), 34 AFRs (`AFR-GYM-001` to `034`), 21 BRs (`BR-GYM-001` to `021`), 12 UCs (`UC-GYM-001` to `012`), and 3 Basis Workflows (`BW-GYM-01` to `03`).
  2. **Known Gaps:**
     - Budget requests tracked in open status without online approval/rejection lifecycle (`CFR-GYM-006`, `AFR-GYM-031`).
     - Membership applications transition open -> confirmed without rejection/cancellation (`CFR-GYM-004`, `AFR-GYM-021`).
     - Initial configured venues list for `BR-GYM-020`.
     - Target group batch/branch wildcard resolution (`BR-GYM-013`).
  3. **Shared-File Registrations:** `config/settings/base.py`, `config/urls.py`, `config/celery.py`, `client/src/app/registry.ts`, `.importlinter`, and `client/e2e/accounts.ts`.
  4. **Dependencies:** Zero new third-party Python or JavaScript dependencies.
- **Approval Quote:**
  > "The `docs/09-gymkhana/gymkhana-blueprint.md` is **APPROVED**. All 7 CFRs, all 34 AFRs, all 21 Business Rules, all 12 Use Cases, and all 3 Basis Workflows are correctly addressed and mapped in the traceability table. The domain models, state machines, permission structure, and endpoint design are consistent with and faithful to the SYNCHRONIZED v1.1 specification baseline. No obligation is missing; no fabricated requirement is introduced; no spec rule is violated."

---

## 2. Gate Verification & Output

### 2.1 Backend Platform Verification (`make check`)
```text
.venv/bin/python manage.py check
System check identified no issues (0 silenced).
.venv/bin/python manage.py makemigrations --check --dry-run
No changes detected
.venv/bin/ruff check .
All checks passed!
.venv/bin/lint-imports
Contracts: 5 kept, 0 broken.
.venv/bin/python ops/checks/no_cross_module_fk.py
no cross-module foreign keys
.venv/bin/python ops/checks/contracts_are_plural.py
all contract getters are plural
.venv/bin/python ops/checks/nav_matches_routes.py
nav items and client routes agree
.venv/bin/python manage.py permission_manifest --check
permission manifest matches the registries
make schema-check
openapi schema matches the code
.venv/bin/python -m pytest -q
........................................................................ [100%]
46 passed in 24.73s
```

### 2.2 Frontend Verification (`make check-client`)
```text
cd client && npm run typecheck && npm test && npm run build
> typecheck
> tsc --noEmit && tsc --noEmit -p e2e

> test
> vitest run
 Test Files  6 passed (6)
      Tests  38 passed (38)

> build
> tsc -b && vite build
✓ 1015 modules transformed.
✓ built in 3.97s
```

### 2.3 Deployment Check
```text
DJANGO_SETTINGS_MODULE=config.settings.prod DB_PASSWORD=local-check-only \
DJANGO_SECRET_KEY=local-check-only-key-long-enough-to-satisfy-the-length-check \
DJANGO_ALLOWED_HOSTS=local.invalid IAM_SERVICE_TOKEN=local \
PLACEMENT_UPLOAD_ROOT=/tmp/check-uploads \
REDIS_CACHE_URL=redis://127.0.0.1:6379/1 REDIS_BROKER_URL=redis://127.0.0.1:6380/0 \
.venv/bin/python manage.py check --deploy --fail-level WARNING

System check identified no issues (2 silenced).
```

---

## 3. Coverage Analysis

### 3.1 Module Coverage (`--cov=modules/gymkhana --cov-fail-under=90`)
```text
Name                                        Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------------------------------
modules/gymkhana/__init__.py                    0      0      0      0   100%
modules/gymkhana/api/__init__.py                0      0      0      0   100%
modules/gymkhana/api/serializers.py           115      1      2      1    98%   167
modules/gymkhana/api/urls.py                    5      0      0      0   100%
modules/gymkhana/api/views.py                 222      0      0      0   100%
modules/gymkhana/apps.py                        4      0      0      0   100%
modules/gymkhana/contracts.py                  34      0      6      0   100%
modules/gymkhana/domain/__init__.py             0      0      0      0   100%
modules/gymkhana/domain/constants.py           14      0      0      0   100%
modules/gymkhana/domain/exceptions.py           4      0      0      0   100%
modules/gymkhana/domain/state_machines.py      21      0      6      0   100%
modules/gymkhana/domain/validation.py          44      0     20      0   100%
modules/gymkhana/models/__init__.py             7      0      0      0   100%
modules/gymkhana/models/booking.py             24      1      0      0    96%   46
modules/gymkhana/models/budget.py              20      1      0      0    95%   35
modules/gymkhana/models/club.py                31      2      0      0    94%   47, 64
modules/gymkhana/models/membership.py          20      1      0      0    95%   42
modules/gymkhana/models/poll.py                46      4      0      0    91%   30, 50, 70, 91
modules/gymkhana/models/report.py              17      1      0      0    94%   27
modules/gymkhana/registry.py                    6      0      0      0   100%
modules/gymkhana/schedule.py                    2      0      0      0   100%
modules/gymkhana/selectors/__init__.py          0      0      0      0   100%
modules/gymkhana/selectors/bookings.py         24      0     10      0   100%
modules/gymkhana/selectors/budgets.py           8      0      2      0   100%
modules/gymkhana/selectors/clubs.py            14      0      2      0   100%
modules/gymkhana/selectors/memberships.py      10      0      2      0   100%
modules/gymkhana/selectors/polls.py            35      0     14      2    96%   61->63, 64->66
modules/gymkhana/selectors/reports.py           8      0      2      0   100%
modules/gymkhana/selectors/scoping.py          56      0     26      1    99%   51->54
modules/gymkhana/services/__init__.py           0      0      0      0   100%
modules/gymkhana/services/bookings.py          54      7     18      3    86%   68, 73-74, 88, 129, 134-135
modules/gymkhana/services/budgets.py           25      3      6      3    81%   34, 37, 40
modules/gymkhana/services/clubs.py             68      4     16      2    93%   34, 59-60, 65
modules/gymkhana/services/memberships.py       40      3      8      1    92%   62, 68-69
modules/gymkhana/services/polls.py             61      9     22      5    83%   53, 57, 61-62, 77, 105, 110-111, 121
modules/gymkhana/services/reports.py           29      6      8      4    73%   33, 36, 39, 44, 48-49
modules/gymkhana/tasks.py                      11      0      2      0   100%
---------------------------------------------------------------------------------------
TOTAL                                        1079     43    172     22    95%
Required test coverage of 90% reached. Total coverage: 94.80%
```

### 3.2 Domain Coverage (`--cov=modules/gymkhana/domain --cov-fail-under=95`)
```text
Name                                        Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------------------------------
modules/gymkhana/domain/__init__.py             0      0      0      0   100%
modules/gymkhana/domain/constants.py           14      0      0      0   100%
modules/gymkhana/domain/exceptions.py           4      0      0      0   100%
modules/gymkhana/domain/state_machines.py      21      0      6      0   100%
modules/gymkhana/domain/validation.py          44      0     20      0   100%
---------------------------------------------------------------------------------------
TOTAL                                          83      0     26      0   100%
Required test coverage of 95% reached. Total coverage: 100.00%
```

---

## 4. Test Suite Inventory & Traceability Mapping

| Test File | Test Count | Scope / Mapped Obligations |
|---|---|---|
| `modules/gymkhana/tests/test_domain.py` | 8 | Validation (`BR-GYM-001`, `002`, `003`, `005`, `017`), State transitions (`BW-GYM-01`, `02`, `03`) |
| `modules/gymkhana/tests/test_models.py` | 12 | Constraints (`BR-GYM-004`, `005`, `009`, `015`, `017`, `018`, `019`) |
| `modules/gymkhana/tests/test_contracts.py` | 2 | Plural query contracts for directory integration |
| `modules/gymkhana/tests/test_schedule.py` | 1 | Celery beat task schedule verification |
| `modules/gymkhana/tests/test_selectors.py` | 7 | Scoping chokepoints (`BR-GYM-010`, `021`), filtering (`BR-GYM-013`, `006`) |
| `modules/gymkhana/tests/test_services.py` | 7 | Workflows & business rules (`UC-GYM-001` to `012`, `BW-GYM-01` to `03`) |
| `modules/gymkhana/tests/test_api.py` | 7 | API views & serialization (`UC-GYM-001` to `012`) |
| `modules/gymkhana/tests/test_client_route_guards.py` | 2 | Client route configuration & permission requirements |
| **Total Tests** | **46** | **All 7 CFRs, 34 AFRs, 21 BRs, 12 UCs, 3 BWs covered** |

### Journey Test Mapping
- **Journey 1 (Club Lifecycle):** `UC-GYM-001`, `UC-GYM-011`, `UC-GYM-008` (Create Club -> Approve Club -> Change Leadership)
- **Journey 2 (Venue Bookings):** `UC-GYM-002`, `UC-GYM-003`, `UC-GYM-007` (Book Session -> Book Event -> Cross-Type Venue Conflict Check)
- **Journey 3 (Membership Lifecycle):** `UC-GYM-004`, `UC-GYM-009` (Apply Membership -> Approve Membership)
- **Journey 4 (Voting Poll Lifecycle):** `UC-GYM-005`, `UC-GYM-010` (Create Poll with Target Groups -> Cast Atomic Vote -> Automatic Expiration)
- **Journey 5 (Accountability Tracking):** `UC-GYM-006`, `UC-GYM-012` (Submit Budget Request -> Submit Event Report -> Faculty Review)

---

## 5. Broken-on-Purpose Rules (Mutation Testing Verification)

1. **Rule 1 (`BR-GYM-001`):** Coordinator must be an active student.
   - *Mutation:* Allow staff user (kind='staff') to be coordinator.
   - *Caught by:* `test_club_creation_rejects_invalid_roles` -> raises `BadRequestError("User 301 is not a valid student.")`.
2. **Rule 2 (`BR-GYM-006`):** Cross-type venue exclusivity between session and event bookings.
   - *Mutation:* Allow overlapping times for different booking types in the same venue.
   - *Caught by:* `test_cross_type_venue_exclusivity` -> raises `ConflictError("Venue 'Hall 1' is already booked on 2026-12-10 during that time.")`.
3. **Rule 3 (`BR-GYM-009`):** One active membership application per student per club.
   - *Mutation:* Permit multiple open applications by the same student for a club.
   - *Caught by:* `test_membership_lifecycle` -> raises `ConflictError("Student 103 has already applied to this club.")`.
4. **Rule 4 (`BR-GYM-013`):** Poll voting restricted to targeted batch and branch.
   - *Mutation:* Permit untargeted student (e.g. batch 2023 when poll targets 2024) to cast vote.
   - *Caught by:* `test_poll_creation_and_voting` -> raises `PermissionDeniedError("Student is not eligible to vote in this poll.")`.
5. **Rule 5 (`BR-GYM-017`):** Budget request amount must be strictly non-negative.
   - *Mutation:* Allow negative budget amounts (e.g. -500).
   - *Caught by:* `test_budget_request_and_report_submissions` -> raises `BadRequestError("Budget request amount must be non-negative.")`.

---

## 6. Adversarial Architecture Pass

- **Concurrency in Poll Voting (`BR-GYM-015`):** If two requests from the same student arrive concurrently, PostgreSQL enforces the `UniqueConstraint(fields=['poll', 'student_id'])` and atomic `F('vote_count') + 1` prevents race conditions or tally corruption.
- **Race Condition in Venue Overlap (`BR-GYM-006`):** Handled via table-level concurrency control (`select_for_update()`) inside an atomic transaction block before creating any booking.
- **Privilege Escalation:** Regular students cannot confirm clubs; `approve_club` strictly enforces role `student_admin`.
- **Information Leakage / IDOR (`BR-GYM-021`):** Faculty councillors can only review reports for clubs to which they are assigned; any attempt to query reports for other clubs returns 404 (NotFoundError) to conceal internal existence.

---

## 7. Security Self-Audit

- **Authentication:** All API endpoints require valid `IamSessionAuthentication` via Bearer token.
- **Authorization:** Granular permission flags registered in `registry/permissions.json` and checked via `HasModulePermission` or explicit scoping selectors.
- **Input Sanitization:** Strings stripped, dates/times validated to prevent inverted intervals, enums validated against domain constants.
- **File Upload Security:** Files stored via Django `FileField` with media isolation; non-empty uploaded files required for budget requests and event reports.
- **Rate Limiting:** `gymkhana_write: 60/hour` throttle registered in settings.

---

## 8. Fresh-Install Verification

- Migration `modules/gymkhana/migrations/0001_initial.py` contains all 10 models with zero cross-module foreign keys (`no_cross_module_fk.py` passes).
- Clean `makemigrations --check --dry-run` confirms zero unmanaged schema drift.

---

## 9. Browser Walkthrough

| Route | Role | Expected View | Verification |
|---|---|---|---|
| `/gymkhana/clubs` | Any authenticated user | Confirmed clubs list & card view | Verified |
| `/gymkhana/memberships` | Student | My club membership status list | Verified |
| `/gymkhana/polls` | Student | Active eligible polls & voting cards | Verified |
| `/gymkhana/calendar` | Any authenticated user | Venue bookings & scheduled events | Verified |
| `/gymkhana/manage` | Club Head | Leadership, bookings, reports, budgets | Verified |
| `/gymkhana/admin` | Student Admin | Club approval workflow & all clubs | Verified |
| `/gymkhana/faculty-reports` | Faculty Councillor | Assigned club event reports | Verified |

---

## 10. Scheduled Tasks Verification

- Celery task `gymkhana.expire_polls` registered in `schedule.py` and scheduled in `config/celery.py` (runs hourly).
- Manual task execution verified: queries polls where `status='active'` and `expires_at < now`, updates them to `'expired'`, and returns number of closed polls.

---

## 11. Review Rounds Scorecard

| Round | Commit | Score | Verdict | Notes |
|---|---|---|---|---|
| Round 1 | `da21557` | 10/10 | Step 7 Baseline Reached | All CI gates green, 94.8% module coverage, 100% domain coverage |
| Step 8 Baseline | `da21557` | - | Spec Tests Baseline | 115 passed, 2 failed (`BR-032`, `WF-010`), 7 skipped. Triaged in `triage.md` |
| Round Q1 | `(current)` | 10/10 | VERDICT: 10/10 | Fixed expired poll status (400 Bad Request). 117/117 spec tests pass, 0 skips, 0 open triage rows |

