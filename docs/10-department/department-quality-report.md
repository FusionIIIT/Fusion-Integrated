# Department: quality report

Branch `module/department`, cut from `main` at `5595be6`. Every number below came from runs made
after the last code change (the change to Q2 and the review Q1 fixes included). Spec: `06-DEPT` v1.2.

## 1. Gates

`make check`, exit 0:

```text
System check identified no issues (0 silenced).
Contracts: 5 kept, 0 broken.   (includes "Layering inside department KEPT")
no cross-module foreign keys
all contract getters are plural
nav items and client routes agree
permission manifest matches the registries
openapi schema matches the code
1192 passed, 27 subtests passed         (whole repository, .venv/bin/python -m pytest; includes the 200 spec tests)
```

`make check-client`, exit 0: `tsc --noEmit` (app and e2e) clean; `Test Files 15 passed (15)`,
`Tests 106 passed (106)`; `✓ built in 2.20s`. The largest department chunk is `InventoryPage`, 1.99 kB gzip.

`make e2e`, exit 0: `28 passed (20.3s)`, run on the final code, with no 5xx and no 403 in the `runserver` log of that run (`grep -c '" 403 '` printed 0). This is 19 department tests and the 9 existing ones, with
`E2E_IAM_DIR` set and the grants in §8.

Deploy check, with the production settings exactly as Step 7.7 gives them:
`System check identified no issues (2 silenced).` Both silences predate this branch.

`python ops/docs/department_reference.py`: `wrote docs/10-department/department-reference.md (121 ids)`.

## 2. Coverage

```text
pytest modules/department --ignore=modules/department/tests/spec --cov=modules/department --cov-branch --cov-fail-under=90
TOTAL  1841 stmts  24 miss  282 branches  18 partial  98%   Total coverage: 98.02%

pytest modules/department --ignore=modules/department/tests/spec --cov=modules/department/domain --cov-branch --cov-fail-under=95
TOTAL   211 stmts   0 miss   74 branches   0 partial  100%  Total coverage: 100.00%
```

`pyproject.toml` excludes `tests/` and `migrations/` from coverage, and neither appears in the report.

## 3. Tests

567 department backend tests, without `tests/spec/` (the 200 spec tests are in `spec-tests/triage.md`):

| File | Tests | What it covers |
|---|---|---|
| `test_domain.py` | 74 | Every rule branch, with no database. Every illegal transition is generated from the tables. |
| `test_acting_role.py` | 65 | Only the acting role counts. For all 21 office write endpoints: the HOD, Dept_Admin and central holder acting in a plain role are refused, and nothing in any table changes. An outgoing HOD or Dept_Admin is refused every write in their office role and in a plain one (BR-DEPT-024). The negative twin succeeds in the office role. `context` reports the acting role. |
| `test_journeys.py` | 35 | Every live UC through HTTP only (below). A student never sees another programme's slots (R5-02). |
| `test_privilege_escalation.py` | 287 | Every one of the 25 write endpoints answers 429 on the repeat at a one-per-minute rate (R6-01). For each of the 41 endpoints, each view asks for exactly the permission its endpoint needs, and: module grant without the permission is 403; permission without the module grant is 403; no session is 401; a plain staff user gets nothing; a student is refused office endpoints. Also `HEAD` and `OPTIONS` need the read permission, an unmapped method is refused, the role switch, per-office verbs, central-only assignment, designation without tenure, CSRF, and that permission codes match the registry. |
| `test_scoping_isolation.py` | 18 | A deleted announcement is gone from the HOD's list and detail, and faculty never see a deactivated profile (R6-02). Another department's rows are absent from lists and 404 by id. A principal holding student, faculty and both office designations, acting as a student or as faculty, gets an empty list from every office-only list (R4-02). Feedback is confidential. A status filter cannot widen scope. Students never see alumni or inactive profiles. Vacancy warnings follow the viewer's departments. |
| `test_edge_cases.py` | 50 | A tenure that would cut the incumbent short is refused and saves nothing (R5-01); an ended tenure that overlaps nothing cannot be revived (R5-03); a timetable batch over 500 slots is 400 (R5-05). 404 for a department code the column could never hold (a NUL byte, a space, 13 letters), 400 for bad filters (a NUL byte included), out-of-range numbers and ids, and over-long strings (every string the write serializers accept, announcements, official changes and tenures included, is checked against its column, and a notice subject fits even with the longest department prefix), 409 for conflicts, 422 for rule refusals, 429 throttling, the ledger's immutability, and every adversarial question below. |
| `test_concurrency.py` | 8 | Real threads on a `Barrier`, with `transaction=True`: issue race, double issue, double decision, overlapping tenures, transitions twice, delivery twice. The database triggers refuse an overlapping tenure written around the service (raced) and a clashing slot written directly. |
| `test_query_budgets.py` | 12 | The same query count with 2 rows and with 20, for all 11 list endpoints, plus prefetched notes. |
| `test_schedule.py` | 16 | The same notice queued twice is stored once, and a failed send never stores an address (R6-05). Beat entries merged and routed; each task twice in a row; readiness, seeding and command output; vacant and ending roles named (Q1); the headship contract. |
| `test_client_route_guards.py` | 2 | Every client route is guarded with its own nav item's permission. |

Client: 68 department vitest tests, 65 across the 8 pages and 3 for the hooks. Each page tests loading, empty, a 500 error, a
missing control, its main action with the server's refusal, and an owning office that lacks the
permission being shown no control. An HOD acting as faculty is shown no HOD control though the
session holds the permissions.

Journeys mapped to use cases (`test_journeys.py`):

| UC | Test(s) |
|---|---|
| UC-DEPT-001 | `test_uc_dept_001_student_sees_only_relevant_announcements`, `..._alternate_no_relevant_announcement_gives_empty_list` |
| UC-DEPT-002 | `test_uc_dept_002_faculty_publishes_and_relevant_students_are_notified`, `..._alternate_incomplete_announcement_is_blocked` |
| UC-DEPT-003 | `test_uc_dept_003_hod_edits_hides_and_deletes_active_announcements` |
| UC-DEPT-004/005/006 | `test_uc_dept_004_005_006_stock_requested_approved_issued`, `test_uc_dept_004_alternate_insufficient_stock_is_not_advanced`, `test_uc_dept_005_rejected_outcome_notifies_faculty` |
| UC-DEPT-007 | `test_uc_dept_007_student_submits_confidential_feedback`, `..._exception_failed_submission_records_nothing` |
| UC-DEPT-008 | `test_uc_dept_008_dept_admin_reviews_then_resolves`, `..._alternate_simple_issue_closed_during_initial_review`, `..._alternate_reviewed_feedback_stays_open_for_hod` |
| UC-DEPT-009 | `test_uc_dept_009_dept_admin_uploads_and_modifies_timetable`, `..._alternate_conflict_blocks_save` |
| UC-DEPT-010/012 | `test_uc_dept_010_general_details_saved_directly`, `..._alternate_validation_failure_saves_nothing`, `test_uc_dept_010_012_official_change_approved_becomes_effective`, `test_uc_dept_012_rejected_official_change_keeps_current_data` |
| UC-DEPT-011 | `test_uc_dept_011_faculty_views_lab_resources_and_own_issued_history`, `..._alternate_empty_views` |
| UC-DEPT-014 | `test_uc_dept_014_hod_oversight_note_and_closure` |
| UC-DEPT-015/016 | `test_uc_dept_015_profile_tiers_by_viewer`, `test_uc_dept_016_dept_admin_manages_profiles` |
| UC-DEPT-017 | `test_uc_dept_017_dept_admin_updates_lab_profile` |
| UC-DEPT-018 | `test_uc_dept_018_student_sees_programme_info_and_own_timetable`, `..._alternate_nothing_published_gives_empty` |
| UC-DEPT-019 | `test_uc_dept_019_dept_admin_inserts_stock_and_it_is_logged`, `..._alternate_invalid_stock_data_changes_nothing` |
| UC-DEPT-020/022 | `test_uc_dept_020_022_hod_reassignment_takes_effect_and_headship_follows`, `test_uc_dept_022_outgoing_holder_loses_access_immediately`, `test_uc_dept_020_dept_admin_reassignment_bw_dept_08`, `test_uc_dept_020_alternate_cardinality_violation_is_blocked` |

All 121 live ids are cited literally in `modules/department/tests`. No retired id is cited anywhere
in the module.

## 4. Rules broken on purpose

Each file was copied outside the repository, broken, and run against the whole module, then copied
back. All six ran in one run, which ended `after restore: 512 passed`.

| Rule broken | Change | Caught by |
|---|---|---|
| Acting role (Step 5.1, BR-DEPT-024) | `require_acting` never refuses | 6 tests, for example `test_an_office_holder_acting_in_a_plain_role_cannot_write[admin-post-inventory-items-…]` |
| Scoping (BR-DEPT-018) | HOD queryset stops excluding `new` feedback | `test_uc_dept_014_hod_oversight_note_and_closure`, `test_feedback_is_visible_only_to_its_submitter_and_the_handling_office` |
| Permission gate (every endpoint) | `get_permissions` returns only the module gate | 76 tests, for example `test_module_grant_without_the_permission_is_403[…]` |
| Limit check (BR-DEPT-015) | `requested > available + 1000` | `test_uc_dept_004_alternate_insufficient_stock_is_not_advanced`, `test_br_dept_015_refusals[6-5-insufficient_stock]` |
| State transition (BR-DEPT-007) | Table gains `pending_hod → issued` | `test_a_pending_request_cannot_be_issued_before_the_hod_decides`, `test_cw_dept_01_stock_lifecycle_table` |
| Uniqueness (BR-DEPT-022) | `overlapping()` returns nothing | `test_uc_dept_020_alternate_cardinality_violation_is_blocked`, `test_two_overlapping_tenures_recorded_at_once_leave_one`, `test_ended_tenure_cannot_be_changed_and_extension_cannot_overlap` |

Round 4 breaks, each run against the whole module and copied back:

| Rule broken | Change | Caught by |
|---|---|---|
| Acting-role scoping (R4-02) | `inventory_items_for` drops its role check | `test_r4_02_a_dual_designation_principal_lists_only_the_acting_roles_rows[student-inventory-items]` |
| Acting-role scoping | the same for stock movements, official changes, tenures and labs, one at a time | the same test, for that list |
| Path input (R4-01) | `_dept` stops checking the code | `test_r4_01_a_hostile_department_code_is_404_not_500[C%00SE]` |

Round 5 breaks, each run against the whole module or page and copied back:

| Rule broken | Change | Caught by |
|---|---|---|
| Cardinality (R5-01) | the cut-short refusal in `_hand_over` never fires | `test_r5_01_a_tenure_inside_the_incumbents_cannot_cut_it_short` |
| Timetable scope (R5-02) | the student programme filter also matches `programme__gt=""` | `test_uc_dept_018_student_never_sees_another_programmes_slots` |
| Ended tenure (R5-03) | `if tenure.valid_to <= now:` becomes `if False:` | `test_r5_03_an_ended_tenure_that_overlaps_nothing_cannot_be_revived` |
| Row-action refusals (R5-04) | each of `hide`, `remove` (Announcements), `decide`, `issue`, request list (Inventory), `decide` (Overview), `update` (Profiles) and `remove` (Timetable) dropped from its `ActionError`, one at a time | one page test each, for example "shows the server's refusal when issuing fails" |
| Client gates | Labs "Edit", Inventory "Issue", Feedback "Review" and Roles "Change end" ungated, after the page split | 1–2 page tests each |

Round 6 breaks, each run against the whole module and copied back:

| Rule broken | Change | Caught by |
|---|---|---|
| Write throttle (R6-01) | `throttle_scope = None` on `StockRequestDecideView` | `test_r6_01_every_write_endpoint_is_throttled[post-stock-requests/1/decide-…]` |
| Deleted announcements (R6-02) | the HOD branch of `announcements_for` returns `qs` | `test_r6_02_a_deleted_announcement_is_gone_from_the_hods_list_and_detail` |
| Inactive profiles (R6-02) | the faculty branch of `profiles_for` returns `qs` | `test_r6_02_faculty_never_see_a_deactivated_profile` |
| Outbox dedupe (R6-05) | `ignore_conflicts=False` | `test_r6_05_the_same_notice_queued_twice_is_stored_once` |

## 5. Adversarial pass

| Question | Found | Done |
|---|---|---|
| Can an approver approve their own record? | Possible by design (Q14 approved: one HOD per department, so a guard would strand the request). | The decider is recorded on every decision. |
| Can a thing appear in its own approval queue? | Only the HOD's own Faculty request, by Q14. | As above. |
| Can a balance go negative? | Two approved requests could exceed stock at issuance. | `select_for_update` on the item, `CheckConstraint(current_quantity >= 0)`, 409 `stock_exhausted` (Q13); real-thread race test. |
| Can something be back-dated without limit? | A tenure could have started in the past. | 422 `backdated_tenure` past a 5-minute grace; an end date cannot move into the past. |
| Can a required third party be unavailable? | A department may have no HOD or Dept_Admin in effect (Q1, Q4). | Fails closed: no one acts in that role. `check_department_readiness` and the Roles page (`GET role-assignments/vacancies`) name every vacant role and every role ending within 30 days with no successor. |
| Can someone act on another department's row by id? | No. | Every write starts from `selectors/scoping.py`; 404 tests for every write endpoint. |
| Can a closed or rejected record still change? | No. | 409 for re-decide, re-issue, re-review, re-dispose; hidden or deleted announcements are frozen. |
| Can a profile expose a real person under another kind? | **Found in round 3 (R3-01):** an alumni profile could name any user's account, showing their name and email to faculty. | An alumni profile can no longer name an account: refused by the service (422 `alumni_has_no_login`) and by the database constraint `dept_profile_login_iff_not_alumni`. |
| Can a successor leave a role empty? | **Found in round 3 (R3-03):** a successor could be recorded to start after the current tenure ends. | A new tenure must start no later than the latest recorded one ends (422 `would_leave_gap`). A role with no current or future holder can still be filled from any start (Q1). |
| Does the same request twice take effect twice? | No. | Conditional state moves under row locks; concurrency tests for issue and decide. |
| Can a write that skips the services break an invariant? | Found in round 1 (R1-04): overlap rules were Python-only. | Triggers in `0001_initial` refuse an overlapping tenure or clashing slot under a per-department advisory lock; tested directly and under a race. |
| Can hostile input cause a 500? | Found in round 1 (R1-01, R1-02), in round 2 (R2-03, R2-04: an over-long name proposal failed at approval; long website or email), and in round 3 (R3-02: a full-length title overflowed its notice subject): `HEAD` skipped the permission gate, and huge numbers reached the database. | `HEAD`/`OPTIONS` use the read permission and unmapped methods are refused; every integer input and URL id is bounded; a name proposal is limited to its column; notice subjects are trimmed to their column; a test checks every accepted string against its column. |
| Does an ordinary user work? (Step 5.2) | **Found a defect:** a real student acts as `ug_student` and a real faculty member as their rank (`Assistant Professor`), so the first build gave them no department. | The basic kind now decides Student or Faculty. Tests use the real IAM shape; checked against the live IAM as `stu00002`. |
| Does the role switch leak? | **Found in round 2 (R2-01, R2-02):** the IAM sends the union of every held role's permissions, and only the state-table writes checked the acting role. An HOD acting as faculty, or an HOD whose tenure had ended, could edit and hide announcements. A Dept_Admin holder without a tenure could write inventory. | Every write now checks the acting role. Announcements are a state table, and the rest call `require_acting`. `test_acting_role.py` covers every write endpoint for every office and for outgoing holders. The client shows office controls only to the acting office (`GET context`). |
| Can a profile leak sensitive data? | No such field is stored. | Tier test asserts none appears. |

## 6. Security self-audit

| Item | Result |
|---|---|
| Both gates on every view | Every view is a `DepartmentView`, and every write also checks the acting role (`test_acting_role.py`): `HasModuleGrant("department")` and then the method's permission. `HEAD` and `OPTIONS` need the read permission; a method with no permission named is refused. No `AllowAny`; no view overrides authentication (asserted by a test). |
| Explicit serializer fields | Every serializer lists its `fields`; every server-owned field is read-only. |
| Scope on every read and body id | Every list and detail read starts in `selectors/scoping.py`. Body ids (`item`, `department`) are resolved through scoping or a locked lookup, never used raw. Every integer input (a timetable slot's `instructor_user_id` included) and URL id is bounded to its column, so an out-of-range value is a 400 or 404, never a 500. |
| No raw SQL, `eval`, `pickle`, `subprocess` on input | None. |
| Uploads | None in this module. |
| Throttling | Every write carries `throttle_scope = "department_write"` (120/hour); 429 is tested. |
| Logs | Ids and counts only. |
| Error bodies | The platform envelope only. |
| CSRF | A cookie write without `X-CSRF-Token` is 403; tested. |
| Client | No `dangerouslySetInnerHTML`, no token in storage; every call goes through `lib/http.ts`. |
| Dependencies | None added. |
| Deploy check | `System check identified no issues (2 silenced).` |

Platform finding, not changed (it is in `core/`, a shared file): `core/api/exceptions.py` rebuilds
the error response, which drops DRF's `Retry-After` header on a 429. `api-conventions.md` requires
that header, so this affects every module. Raised for whoever owns `core/`.

## 7. Fresh install

Throwaway database `fusion_integrated_fresh`. Postgres runs locally here, so `createdb` and `dropdb`
were used directly instead of `docker compose exec`. `DB_NAME` was set on every line.

```text
migrate                         -> migrate OK
migrate department zero         -> Unapplying department.0001_initial... OK
migrate                         -> Applying department.0001_initial... OK
seed_modules                    -> department: registered but NOT active — 1 prerequisite(s) unmet:
                                   No departments exist yet. Run `python manage.py seed_departments` to create them.
check_department_readiness      -> - No departments exist yet. Run `python manage.py seed_departments` to create them.
                                   CommandError: Department module has 1 unmet prerequisite(s).
seed_departments                -> Seeded departments (7 created, 7 total).
seed_modules                    -> registered department (active)
check_department_readiness      -> ! CSE has no HOD in effect. Record a tenure on the HOD & Dept_Admin page.
                                   … one line per vacant role, 14 in all, ending with:
                                   ! SM has no HOD in effect. The ERP has no HOD designation for SM yet (blueprint Q4).
                                   ! SM has no Dept_Admin in effect. Record a tenure on the HOD & Dept_Admin page.
                                   Department module is ready.
run_department_tasks            -> Role transitions applied: 0. Notifications: sent=0 failed=0 reclaimed=0.
triggers present                -> department_tenure_no_overlap, department_slot_no_clash
```

The CLI part above was re-run after the round 3 rebuild of `0001_initial`; the two triggers and `dept_profile_login_iff_not_alumni` were present.

IAM seeded from this branch's manifest (`seed_iam_permissions --manifest …/registry/permissions.json`):
`82 added, 116 revoked; 316 total`. The revoked grants were left over from an earlier local build
of the same module code.

First user action, against a server started on the fresh database (`DB_NAME=fusion_integrated_fresh`):

```text
[22/Nov/2026 20:26:22] "POST /api/v1/auth/login HTTP/1.1" 200 91
[22/Nov/2026 20:26:22] "GET /api/v1/me HTTP/1.1" 200 2056
[22/Nov/2026 20:26:22] "POST /api/v1/department/feedback HTTP/1.1" 201 277
```

The database was then dropped.

## 8. Browser walkthrough

Synthetic `fusion-dev.dump` accounts. Each row is a Playwright journey, run on its own against
`make dev` on 8002 with `npx playwright test e2e/department/<spec> --workers=1`. Each passed, and each
fails on any console error, uncaught error or 5xx. Under each row is **every** `/api/v1/` line
`runserver` logged during that run, reads and writes alike, on the final code. None is a 5xx or a 403.

**Accounts and grants `make e2e` needs.** Global setup grants them when `E2E_IAM_DIR` points at the
`Fusion_System_Administrator` checkout. To grant them by hand, from `Fusion_System_Administrator/Backend/backend`:
`./../venv/bin/python manage.py assign_role --user <username> --designation "<designation>"`.

| Username | Designation needed |
|---|---|
| stf00019 | `deptadmin_cse` |
| fac00049 | `HOD (CSE)` (already in the ERP) |
| stf00002 | `acadadmin` (already in the ERP) |
| stf00062 | `placement_officer` (Placement's own spec) |
| stu00002, fac00002 | none |

In this IAM, `assign_role` writes only the IAM's own projection, and an identity sync from the ERP
later drops those grants. Grant them again before each run, or set `E2E_IAM_DIR`.

| Role (account) | Use cases | Spec | Result |
|---|---|---|---|
| Institute Admin `acadadmin` (stf00002) | UC-DEPT-020, UC-DEPT-022 | `roles.spec.ts` | pass |

```text
[23/Nov/2026 04:38:47] "GET /api/v1/me HTTP/1.1" 401 161
[23/Nov/2026 04:38:48] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:38:48] "GET /api/v1/me HTTP/1.1" 200 1962
[23/Nov/2026 04:38:48] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:38:48] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:38:48] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:38:48] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:38:48] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:38:48] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:38:49] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:38:49] "GET /api/v1/department/role-assignments HTTP/1.1" 200 1913
[23/Nov/2026 04:38:49] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:38:49] "GET /api/v1/department/role-assignments?limit=100 HTTP/1.1" 200 1913
[23/Nov/2026 04:38:49] "GET /api/v1/department/departments HTTP/1.1" 200 1424
[23/Nov/2026 04:38:49] "POST /api/v1/department/role-assignments HTTP/1.1" 201 209
[23/Nov/2026 04:38:49] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:38:49] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:38:49] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:38:49] "GET /api/v1/department/departments HTTP/1.1" 200 1424
[23/Nov/2026 04:38:50] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:38:50] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:38:50] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:38:50] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:38:50] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:38:51] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:38:51] "GET /api/v1/department/departments HTTP/1.1" 200 1424
[23/Nov/2026 04:38:51] "GET /api/v1/department/departments/CSE HTTP/1.1" 200 308
```

| Role (account) | Use cases | Spec | Result |
|---|---|---|---|
| Faculty `Assistant Professor` (fac00002), Student `ug_student` (stu00002), HOD `HOD (CSE)` (fac00049) | UC-DEPT-002, UC-DEPT-001, UC-DEPT-003 | `announcements.spec.ts` | pass |

```text
[23/Nov/2026 04:39:12] "GET /api/v1/me HTTP/1.1" 401 161
[23/Nov/2026 04:39:13] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:39:13] "GET /api/v1/me HTTP/1.1" 200 1962
[23/Nov/2026 04:39:13] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:39:13] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:39:13] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:39:13] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:39:13] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:39:13] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:39:14] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:39:14] "GET /api/v1/department/announcements HTTP/1.1" 200 42
[23/Nov/2026 04:39:14] "POST /api/v1/department/announcements HTTP/1.1" 201 260
[23/Nov/2026 04:39:14] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:39:14] "GET /api/v1/department/announcements HTTP/1.1" 200 302
[23/Nov/2026 04:39:14] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:39:15] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:39:15] "GET /api/v1/department/announcements HTTP/1.1" 200 302
[23/Nov/2026 04:39:15] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:39:15] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:39:15] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:39:15] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:39:15] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:39:16] "GET /api/v1/department/context HTTP/1.1" 200 33
[23/Nov/2026 04:39:16] "GET /api/v1/department/announcements HTTP/1.1" 200 2339
[23/Nov/2026 04:39:16] "POST /api/v1/department/announcements/8/hide HTTP/1.1" 200 290
[23/Nov/2026 04:39:16] "GET /api/v1/department/context HTTP/1.1" 200 33
[23/Nov/2026 04:39:16] "GET /api/v1/department/announcements HTTP/1.1" 200 2369
```

| Role (account) | Use cases | Spec | Result |
|---|---|---|---|
| Dept_Admin `deptadmin_cse` (stf00019), Faculty (fac00002), HOD (fac00049) | UC-DEPT-019, UC-DEPT-004, UC-DEPT-005, UC-DEPT-006, UC-DEPT-011 | `stock.spec.ts` | pass |

```text
[23/Nov/2026 04:39:37] "GET /api/v1/me HTTP/1.1" 401 161
[23/Nov/2026 04:39:38] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:39:38] "GET /api/v1/me HTTP/1.1" 200 1962
[23/Nov/2026 04:39:38] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:39:38] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:39:38] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:39:38] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:39:38] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:39:38] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:39:39] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:39:39] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:39:39] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:39:39] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:39:39] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:39:39] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:39:39] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:39:39] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:39:40] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:39:40] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1030
[23/Nov/2026 04:39:40] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2323
[23/Nov/2026 04:39:40] "GET /api/v1/department/stock-movements HTTP/1.1" 200 2740
[23/Nov/2026 04:39:40] "POST /api/v1/department/inventory-items HTTP/1.1" 201 127
[23/Nov/2026 04:39:40] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:39:40] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1158
[23/Nov/2026 04:39:40] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2323
[23/Nov/2026 04:39:40] "GET /api/v1/department/stock-movements HTTP/1.1" 200 2925
[23/Nov/2026 04:39:40] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:39:41] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:39:41] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1158
[23/Nov/2026 04:39:41] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2323
[23/Nov/2026 04:39:41] "POST /api/v1/department/stock-requests HTTP/1.1" 201 270
[23/Nov/2026 04:39:41] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:39:41] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1158
[23/Nov/2026 04:39:41] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2594
[23/Nov/2026 04:39:42] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:39:42] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1158
[23/Nov/2026 04:39:42] "GET /api/v1/department/context HTTP/1.1" 200 33
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2594
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-movements HTTP/1.1" 200 2925
[23/Nov/2026 04:39:42] "POST /api/v1/department/stock-requests/8/decide HTTP/1.1" 200 297
[23/Nov/2026 04:39:42] "GET /api/v1/department/context HTTP/1.1" 200 33
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-movements HTTP/1.1" 200 2925
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2621
[23/Nov/2026 04:39:42] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1158
[23/Nov/2026 04:39:42] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:39:42] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1158
[23/Nov/2026 04:39:42] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2621
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-movements HTTP/1.1" 200 2925
[23/Nov/2026 04:39:42] "POST /api/v1/department/stock-requests/8/issue HTTP/1.1" 200 325
[23/Nov/2026 04:39:42] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1157
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-movements HTTP/1.1" 200 3104
[23/Nov/2026 04:39:42] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2649
[23/Nov/2026 04:39:42] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:39:42] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:39:42] "GET /api/v1/department/inventory-items HTTP/1.1" 200 1157
[23/Nov/2026 04:39:42] "GET /api/v1/department/stock-requests HTTP/1.1" 200 2649
```

| Role (account) | Use cases | Spec | Result |
|---|---|---|---|
| Student (stu00002), Dept_Admin (stf00019), HOD (fac00049) | UC-DEPT-007, UC-DEPT-008, UC-DEPT-014 | `feedback.spec.ts` | pass |

```text
[23/Nov/2026 04:40:04] "GET /api/v1/me HTTP/1.1" 401 161
[23/Nov/2026 04:40:04] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:40:04] "GET /api/v1/me HTTP/1.1" 200 1962
[23/Nov/2026 04:40:04] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:40:04] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:40:04] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:40:04] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:40:04] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:40:05] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:40:05] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:40:05] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:40:05] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:40:05] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:40:06] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:40:06] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:40:06] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:40:06] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:40:06] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:40:06] "GET /api/v1/department/feedback HTTP/1.1" 200 4659
[23/Nov/2026 04:40:07] "POST /api/v1/department/feedback HTTP/1.1" 201 288
[23/Nov/2026 04:40:07] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:40:07] "GET /api/v1/department/feedback HTTP/1.1" 200 4948
[23/Nov/2026 04:40:07] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:40:07] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:40:07] "GET /api/v1/department/feedback HTTP/1.1" 200 4948
[23/Nov/2026 04:40:07] "POST /api/v1/department/feedback/15/review HTTP/1.1" 200 327
[23/Nov/2026 04:40:07] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:40:07] "GET /api/v1/department/feedback HTTP/1.1" 200 4987
[23/Nov/2026 04:40:08] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:40:08] "GET /api/v1/department/context HTTP/1.1" 200 33
[23/Nov/2026 04:40:08] "GET /api/v1/department/feedback HTTP/1.1" 200 3003
[23/Nov/2026 04:40:09] "POST /api/v1/department/feedback/15/dispose HTTP/1.1" 200 376
[23/Nov/2026 04:40:09] "GET /api/v1/department/context HTTP/1.1" 200 33
[23/Nov/2026 04:40:09] "GET /api/v1/department/feedback HTTP/1.1" 200 3052
[23/Nov/2026 04:40:09] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:40:09] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:40:09] "GET /api/v1/department/feedback HTTP/1.1" 200 5036
```

| Role (account) | Use cases | Spec | Result |
|---|---|---|---|
| Dept_Admin (stf00019), Student (stu00002), Faculty (fac00002) | UC-DEPT-009, UC-DEPT-018, UC-DEPT-017, UC-DEPT-016, UC-DEPT-015 | `resources.spec.ts` | pass |

```text
[23/Nov/2026 04:40:30] "GET /api/v1/me HTTP/1.1" 401 161
[23/Nov/2026 04:40:31] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:40:31] "GET /api/v1/me HTTP/1.1" 200 1962
[23/Nov/2026 04:40:31] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:40:31] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:40:31] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:40:31] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:40:31] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:40:32] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:40:32] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:40:32] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:40:32] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:40:32] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:40:32] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:40:32] "GET /api/v1/department/timetable-slots HTTP/1.1" 200 1485
[23/Nov/2026 04:40:33] "POST /api/v1/department/timetable-slots HTTP/1.1" 201 213
[23/Nov/2026 04:40:33] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:40:33] "GET /api/v1/department/timetable-slots HTTP/1.1" 200 1697
[23/Nov/2026 04:40:33] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:40:33] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:40:33] "GET /api/v1/department/timetable-slots HTTP/1.1" 200 1697
[23/Nov/2026 04:40:34] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:40:34] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:40:34] "GET /api/v1/department/departments HTTP/1.1" 200 277
[23/Nov/2026 04:40:34] "GET /api/v1/department/departments/CSE HTTP/1.1" 200 308
[23/Nov/2026 04:40:34] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:40:34] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:40:34] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:40:34] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:40:35] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:40:35] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:40:35] "GET /api/v1/department/lab-resources HTTP/1.1" 200 1147
[23/Nov/2026 04:40:35] "POST /api/v1/department/lab-resources HTTP/1.1" 201 157
[23/Nov/2026 04:40:35] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:40:35] "GET /api/v1/department/lab-resources HTTP/1.1" 200 1305
[23/Nov/2026 04:40:36] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:40:36] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:40:36] "GET /api/v1/department/lab-resources HTTP/1.1" 200 1305
[23/Nov/2026 04:40:36] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:40:37] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:40:37] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2123
[23/Nov/2026 04:40:37] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1737
[23/Nov/2026 04:40:37] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:40:37] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:40:37] "GET /api/v1/department/profiles HTTP/1.1" 200 2183
[23/Nov/2026 04:40:38] "POST /api/v1/department/profiles HTTP/1.1" 201 305
[23/Nov/2026 04:40:38] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:40:38] "GET /api/v1/department/profiles HTTP/1.1" 200 2489
[23/Nov/2026 04:40:38] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:40:38] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:40:38] "GET /api/v1/department/profiles HTTP/1.1" 200 1617
```

| Role (account) | Use cases | Spec | Result |
|---|---|---|---|
| Dept_Admin (stf00019), HOD (fac00049) | UC-DEPT-010, UC-DEPT-012 | `details.spec.ts` | pass |

```text
[23/Nov/2026 04:40:59] "GET /api/v1/me HTTP/1.1" 401 161
[23/Nov/2026 04:41:00] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:00] "GET /api/v1/me HTTP/1.1" 200 1962
[23/Nov/2026 04:41:00] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:00] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:41:00] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:41:00] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:41:00] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:00] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:01] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:41:01] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2122
[23/Nov/2026 04:41:01] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1586
[23/Nov/2026 04:41:01] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:02] "GET /api/v1/department/context HTTP/1.1" 200 36
[23/Nov/2026 04:41:02] "GET /api/v1/department/role-assignments HTTP/1.1" 200 2122
[23/Nov/2026 04:41:02] "GET /api/v1/department/role-assignments/vacancies HTTP/1.1" 200 1586
[23/Nov/2026 04:41:02] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:41:02] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:41:02] "GET /api/v1/department/departments HTTP/1.1" 200 277
[23/Nov/2026 04:41:02] "GET /api/v1/department/departments/CSE HTTP/1.1" 200 308
[23/Nov/2026 04:41:02] "GET /api/v1/department/official-changes HTTP/1.1" 200 2204
[23/Nov/2026 04:41:03] "POST /api/v1/department/official-changes HTTP/1.1" 201 281
[23/Nov/2026 04:41:03] "GET /api/v1/department/official-changes HTTP/1.1" 200 2486
[23/Nov/2026 04:41:03] "GET /api/v1/department/context HTTP/1.1" 200 40
[23/Nov/2026 04:41:03] "GET /api/v1/department/departments HTTP/1.1" 200 277
[23/Nov/2026 04:41:03] "GET /api/v1/department/departments/CSE HTTP/1.1" 200 308
[23/Nov/2026 04:41:03] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:41:03] "GET /api/v1/department/context HTTP/1.1" 200 33
[23/Nov/2026 04:41:03] "GET /api/v1/department/departments HTTP/1.1" 200 277
[23/Nov/2026 04:41:03] "GET /api/v1/department/departments/CSE HTTP/1.1" 200 308
[23/Nov/2026 04:41:03] "GET /api/v1/department/official-changes HTTP/1.1" 200 2486
[23/Nov/2026 04:41:03] "POST /api/v1/department/official-changes/8/decide HTTP/1.1" 200 312
[23/Nov/2026 04:41:03] "GET /api/v1/department/context HTTP/1.1" 200 33
[23/Nov/2026 04:41:03] "GET /api/v1/department/official-changes HTTP/1.1" 200 2517
[23/Nov/2026 04:41:03] "GET /api/v1/department/departments HTTP/1.1" 200 277
[23/Nov/2026 04:41:03] "GET /api/v1/department/departments/CSE HTTP/1.1" 200 308
```

| Role (account) | Use cases | Spec | Result |
|---|---|---|---|
| Student (stu00002), **keyboard only** | UC-DEPT-007 | `keyboard.spec.ts` | pass |

```text
[23/Nov/2026 04:41:25] "GET /api/v1/me HTTP/1.1" 401 161
[23/Nov/2026 04:41:25] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:25] "GET /api/v1/me HTTP/1.1" 200 1962
[23/Nov/2026 04:41:25] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:25] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:41:25] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:41:25] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:41:25] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:26] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:26] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:41:26] "GET /api/v1/department/feedback HTTP/1.1" 200 5036
[23/Nov/2026 04:41:26] "POST /api/v1/department/feedback HTTP/1.1" 201 283
[23/Nov/2026 04:41:26] "GET /api/v1/department/context HTTP/1.1" 200 37
[23/Nov/2026 04:41:26] "GET /api/v1/department/feedback HTTP/1.1" 200 5320
```

| Role (account) | Use cases | Spec | Result |
|---|---|---|---|
| Student (stu00002), Institute Admin (stf00002) | Guarded routes (9) | `guarded-pages.spec.ts` | pass |

```text
[23/Nov/2026 04:41:48] "GET /api/v1/me HTTP/1.1" 401 161
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 1962
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 1633
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 2042
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 2107
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:49] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:50] "GET /api/v1/me HTTP/1.1" 200 2056
[23/Nov/2026 04:41:50] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:50] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:50] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:51] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:51] "GET /api/v1/me HTTP/1.1" 200 829
[23/Nov/2026 04:41:51] "GET /api/v1/me HTTP/1.1" 200 829
```

The guarded-pages row has only `/api/v1/me` and sign-in lines: a guarded page shows `NotPermitted`
and never calls the department API.

**Keyboard alone.** `keyboard.spec.ts` does the whole feedback flow with `page.keyboard` only, and
never touches the mouse:
1. Tab to "Expand sidebar", then "Department", then the "Feedback" link, pressing Enter on each.
2. Tab to "Submit feedback" and press Enter.
3. Tab to the labelled Subject and Feedback fields and type into them.
4. Tab to Save and press Enter.
5. Assert the 201 and the saved card.

Every control on that path is reached by Tab and labelled. Its log lines are in the row above.

Defects found while making these specs pass, both fixed: the stock request's item picker could be
cleared, after which "Submit request" did nothing; and dialogs showed an empty body while closing.

## 9. Scheduled tasks run by hand

`run_department_tasks` on the fresh database: `Role transitions applied: 0. Notifications: sent=0
failed=0 reclaimed=0.` On the test database with four unstamped tenures:
`Role transitions applied: 4` (`test_run_department_tasks_runs_both`). A second run applies 0, and
one `role.effective` notice is queued per tenure (`test_role_transition_task_twice_in_a_row_takes_effect_once`).

## 10. Accepted known gaps

| Spec id | Gap | Reason | Approval |
|---|---|---|---|
| BR-DEPT-024, AFR-DEPT-049, AFR-DEPT-050 | Inside DEPT the switch-over is immediate. The IAM designation, and so the sidebar link, is changed separately with `assign_role`. | The IAM has no write endpoint, and a module may not write the ERP (blueprint Q1). | Q1, below |
| BR-DEPT-022, AFR-DEPT-051, AFR-DEPT-052 | Never more than one holder. Zero is possible before the first tenure or after one ends with no successor. | Only the central authority can record a successor (Q1). | Q1, below |
| AFR-DEPT-026 | Course membership comes from the timetable: a Student whose programme and batch year match a slot the Faculty member teaches. There is no real roster. | No course-roster endpoint on the IAM's `main` (Q2). Change to Q2 in the blueprint. | Q2 and its change, below |
| BR-DEPT-022 (SM), HOD-gated ids for SM | SM has no HOD. | `HOD (SM)` does not exist in `globals_designation` (Q4). | Q4, below |

## 11. Approvals

All from Student 2, on WhatsApp, 2026-11-22 19:41 IST (shown as edited):

> "I approve the Department blueprint and Q1-Q14 as proposed, including the changes outside the module's folders." [name and roll number omitted]

This covers:
- the blueprint;
- every proposal in Q1 to Q14, including the gaps above;
- the changes outside the module's folders: registration lines in `config/settings/base.py`,
  `config/urls.py`, `config/celery.py`, `.importlinter` and `client/src/app/registry.ts`; the
  regenerated `openapi/fusion-integrated.v1.yaml`, `registry/permissions.json` and
  `docs/02-iam/permission-catalog.generated.md`; the new entries in `client/e2e/accounts.ts`;
  and `ops/docs/department_reference.py`.

Also from Student 2, on WhatsApp, 2026-11-23 03:26 IST:

> "I agree with all six proposed answers: (1) HOD sees all department announcements, (2) Faculty relevance by role only, (3) notes visible to the submitter, (4) notes allowed after closure, (5) no notice to the outgoing holder, (6) ready with vacancy warnings." [roll number omitted]

This answers the six questions raised in review rounds 1–3 (blueprint, "Questions raised in
review"). Each answer keeps the current behaviour, so no code changed for them.

After review round 6, from Student 2, on WhatsApp, 2026-11-23 18:05 IST:

> "I accept the round 6 fixes for R6-01 to R6-05, with nothing waived. On the reviewer's questions: (1) keep Q14, no self-decision guard on stock requests; (2) the 50-line limit applies to functions, not to describe blocks in tests; (3) a failed email's stored error must not keep an address, as built."

This is the written fix-or-waive decision after six rounds: every round 6 finding is fixed, none is
waived, and the three round 6 questions are answered as proposed (§12).

After the spec-test baseline, from Student 2, on WhatsApp, 2026-11-24 21:51 IST, in reply to the
proposed change to Q2 (blueprint, "Change to Q2 (spec tests)"):

> "Approved"

This approves the change to Q2 in the blueprint. Timetable slots name an instructor, and a Faculty member sees a Student whose
programme and batch year match a slot they teach at the DETAILED tier (AFR-DEPT-026). This ends
the three `NOT_AUTOMATED` spec tests (`triage.md`). It adds a column and
an index to the module's single `0001_initial` migration and changes the regenerated
`openapi/fusion-integrated.v1.yaml`.

No dependency was added.

## 12. Review rounds

| Round | Commit | Spec | Arch | Code | Security | Tests | E2E | Frontend | Ops | Hygiene | Open findings |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `db12b6a` | 7 | 7 | 8 | 4 | 10 | 1 | 6 | 8 | 5 | 16 (9 Major, 7 Minor) |
| 2 | `b32b996` | 3 | 9 | 9 | 3 | 7 | 6 | 6 | 8 | 10 | 13 (3 Blocker, 4 Major, 6 Minor) |
| 3 | `916b6b0` | 7 | 10 | 10 | 3 | 4 | 10 | 7 | 10 | 10 | 6 (2 Blocker, 4 Major) |
| 4 | `6b52d64` | 10 | 10 | 8 | 7 | 7 | 10 | 10 | 10 | 10 | 4 (2 Major, 2 Minor) |
| 5 | `ad7558e` | 7 | 10 | 9 | 9 | 4 | 10 | 7 | 8 | 10 | 8 (4 Major, 4 Minor) |
| 6 | `c04569e` | 10 | 10 | 10 | 10 | 3 | 10 | 9 | 9 | 10 | 5 (2 Major, 3 Minor) |
| 7 | `34b8ab5` | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 0 |
| Q1 | `1c60e90` | 3 | 10 | 9 | 7 | 10 | 10 | 10 | 4 | 3 | 6 (2 Blocker, 3 Major, 1 Minor) |

What round 1 found, and what changed:

| Finding | Change |
|---|---|
| R1-01 | `HEAD` and `OPTIONS` use the read permission; an unmapped method is refused (`DenyAll`). Tests added. |
| R1-02 | Every integer input is bounded, and URL ids are limited to 9 digits. Tests added. |
| R1-03 | Vacancy warnings in `check_department_readiness` and on the Roles page (`GET role-assignments/vacancies`). Tests added. |
| R1-04 | Database triggers for tenure overlap and slot clashes, in `0001_initial`. Tests added. |
| R1-05 | §8: each row has its own `runserver` lines. |
| R1-06 | Deep-link specs for every guarded route that a granted role lacks. |
| R1-07 | `make e2e` passes again (26); §8 records the grants it needs and why they disappear. |
| R1-08 | Sign-in and navigation done by keyboard; the form submission is still open (§8). |
| R1-09 | The approver is named by role only; the quote has no name or roll number. |
| R1-10 | `StringIO` replaces the open `/dev/null` handles; both `noqa` lines are gone. |
| R1-11 | Every flagged refusal now says what to do next. |
| R1-12 | `Feedback.category` is the category union or `""`. |
| R1-13 | The blueprint shows `/department/overview` and records the round 1 changes. |
| R1-14 | §4 comes from a single run (400). |
| R1-15 | The next commit message gives its reason. |
| R1-16 | The migration header and the reference doc no longer match the attribution grep. |

What round 2 found, and what changed:

| Finding | Change |
|---|---|
| R2-01, R2-02 | Every write checks the acting role. Announcements go through a state table; the rest call `require_acting`. An outgoing holder is refused in every role. |
| R2-03 | A name proposal is limited to 120 characters (422 at proposal); approval cannot fail on length. |
| R2-04 | `website` and `contact_email` are limited to their columns; a test checks every accepted string against its column. |
| R2-05 | The tenure spec records a tenure through the UI on every run, in its own minute, and asserts the 201 and the saved values. |
| R2-06 | `keyboard.spec.ts` completes the feedback flow by keyboard alone. |
| R2-07 | §8 pastes every request line for each row. |
| R2-08 | The profile schema marks tier-only fields optional and the three nullable ones nullable, matching `types.ts`. |
| R2-09 | The lab POST documents `DeptLabResourceEdit`. |
| R2-10 | `announcement_reaches`, `in_effect`, `ROLE_MAINTAINERS` and `SYSTEM` are deleted. |
| R2-11 | The blueprint records the timetable list as the one unpaginated list, returned whole. |
| R2-12 | Announcement status moves are a declarative table. |
| R2-13 | `test_acting_role.py` covers every write endpoint, for each office and for outgoing holders. |

What round 3 found, and what changed:

| Finding | Change |
|---|---|
| R3-01 | An alumni profile cannot name an account (service and database). |
| R3-02 | Notice subjects are trimmed to their column; announcement inputs are declared at their column lengths. |
| R3-03 | A successor tenure cannot start after the latest recorded one ends. |
| R3-04 | A test checks that every view asks for exactly its endpoint's permission; the reviewer's break (lab update weakened to view) now fails it. |
| R3-05 | The string-length test covers the announcement serializers, and a test publishes a full-length title. |
| R3-06 | Every page has a test where the owning office lacks the permission; the reviewer's break (Add lab ungated) now fails it. |
| Round 3 question 2 | The Overview page requests official changes only when the panel can show. |

What round 4 found, and what changed:

| Finding | Change |
|---|---|
| R4-01 | A department code in the path that is not 1–12 letters is a 404 with the platform envelope before it reaches the database, for `GET` and `PATCH`. It is the only string path parameter; status filters are checked against their allowed values. Tests added. |
| R4-02 | A test reads every office-only list as a principal holding every office designation while acting as a student, and as faculty; removing any list's role check fails it. |
| R4-03 | `assign` is split into `_locked_department`, `_check_dates_and_holder`, `_refuse_gap` and `_hand_over`; no function in the module's services is over 50 lines (round 5 found three test helpers that were; see R5-06). |
| R4-04 | The comment above `successorWindow` is one line. |
| Disclosure | The reviewer's probe left inventory item 5 ("a") in the working database; it is not part of the repository. |

What round 5 found, and what changed:

| Finding | Change |
|---|---|
| R5-01 | A tenure that starts inside the incumbent's and ends before it is refused (422 `would_cut_short`, saying to end it later or shorten the current tenure first), so the module never leaves the rest of a tenure without a holder. Two journey tests that recorded such a successor now record one that covers the rest of the term. |
| R5-02 | A test publishes slots for another programme in the same department and batch; the student never sees them. |
| R5-03 | A test revives an ended tenure that overlaps nothing and gets 409 `tenure_ended`, with the row unchanged. |
| R5-04 | Each of the five pages has a test where the row action's refusal reaches the screen as sent. |
| R5-05 | A timetable upload takes at most 500 slots; a larger one is 400 with a sentence, and saves nothing. |
| R5-06 | The three test helpers are split. Every function in the module, Python and TypeScript, tests included, is 50 lines or fewer; each page is split into its dialog, fields and table. |
| R5-07 | The traceability rows name `feedback/{id}/notes` and the profile record id. |
| R5-08 | §8 pastes the per-spec logs of runs on the final code, and §1 and §8 agree: no 403 and no 5xx. |
| Question 1 | Answered by R5-01: the incumbent's remaining time is kept; such a tenure is refused. |
| Question 2 | The central authority does not see official changes; BR-DEPT-011 and BR-DEPT-013 name only Dept_Admin and HOD, as approved in the blueprint. |

What round 6 found, and what changed:

| Finding | Change |
|---|---|
| R6-01 | A test sends every write endpoint twice at one write a minute and gets 429 on the repeat. |
| R6-02 | Tests show a deleted announcement is gone from the HOD's list and detail, and faculty never see a deactivated profile. |
| R6-03 | The two response shapes mark every field required (they are always sent), and `types.ts` marks optional exactly what the write schemas leave optional, `bio` included. A script compared every interface with its schema: no mismatch. |
| R6-04 | The endpoint table has `GET feedback/{id}`. |
| R6-05 | A test queues the same notice twice and finds one row. |
| Round 6 question 3 | Proposed and built: a failed send stores its error with every address replaced by `[address]`; tested. |

**After round 6: fix or waive.** Every round 6 finding is fixed above and none is waived. Student 2
approved this, and the answers below, in writing on 2026-11-23 18:05 IST (§11):

| Question | Answer |
|---|---|
| 1. May an HOD decide a stock request they made while acting as faculty? | Keep Q14 as approved: no self-decision guard; the request and the decision are both in the audit trail. |
| 2. Does the 50-line limit apply to a test file's `describe(...)` block? | No: it groups short tests and is not itself a function; every `it` and every function is 50 lines or fewer. |
| 3. Should `last_error` keep a recipient address? | No; built as above. |

The six approver questions from rounds 1, 2 and 3 were answered by Student 2 on 2026-11-23 (§11);
every answer keeps the current behaviour.

What review Q1 found (after the spec tests), and what changed:

| Finding | Change |
|---|---|
| RQ1-01 | §11 quotes Student 2's written approval of the change to Q2, with its date. |
| RQ1-02 | The migration header that matched the hygiene `grep` is gone with RQ1-03. |
| RQ1-03 | `instructor_user_id` and `dept_slot_instructor_idx` are folded into the single `0001_initial`; `makemigrations --check` is green and a fresh `migrate` works. |
| RQ1-04 | Every number in §1 to §3 was measured again after the last code change. |
| RQ1-05 | `instructor_user_id` is bounded to its column on upload and edit; a test sends a huge id to both and gets 400. |
| RQ1-06 | The `instructor_unknown` message tells the Dept_Admin to choose an active Faculty member of the department or leave the instructor empty. |
