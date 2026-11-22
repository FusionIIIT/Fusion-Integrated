# Department: quality report

Branch `module/department`, cut from `main` at `5595be6`. Every number below came from a run made
after the last code change. Spec: `06-DEPT` v1.2.

## 1. Gates

`make check`, exit 0:

```text
System check identified no issues (0 silenced).
No changes detected
All checks passed!
Contracts: 5 kept, 0 broken.   (includes "Layering inside department KEPT")
no cross-module foreign keys
all contract getters are plural
nav items and client routes agree
permission manifest matches the registries
openapi schema matches the code
791 passed, 27 subtests passed          (whole repository, .venv/bin/python -m pytest)
```

`make check-client`, exit 0: `tsc --noEmit` (app and e2e) clean; `Test Files 15 passed (15)`,
`Tests 85 passed (85)`; `✓ built in 1.45s`. The largest department chunk is `InventoryPage`
at 1.76 kB gzip; every department chunk is under 2 kB gzip.

`make e2e` (IAM on 8001, `make dev` on 8002): `20 passed (11.7s)`. All 12 department specs and
the 8 existing specs pass.

Deploy check, with the production settings exactly as Step 7.7 gives them:
`System check identified no issues (2 silenced).`

`python ops/docs/department_reference.py`: `wrote docs/10-department/department-reference.md (121 ids)`.
`git status --porcelain` shows no change to it afterwards.

## 2. Coverage

```text
pytest modules/department --cov=modules/department --cov-branch --cov-fail-under=90
TOTAL  1701 stmts  26 miss  256 branches  20 partial  98%   Total coverage: 97.65%

pytest modules/department --cov=modules/department/domain --cov-branch --cov-fail-under=95
TOTAL   214 stmts   0 miss   78 branches   0 partial  100%  Total coverage: 100.00%
```

`pyproject.toml` excludes `tests/` and `migrations/` from coverage, and neither appears in the report.

## 3. Tests

366 department backend tests:

| File | Tests | What it covers |
|---|---|---|
| `test_domain.py` | 79 | Every rule branch, with no database. Every illegal transition is generated from the tables. |
| `test_journeys.py` | 33 | Every live UC through HTTP only (below). |
| `test_privilege_escalation.py` | 195 | For each of the 39 endpoints: module grant without the permission is 403; permission without the module grant is 403; no session is 401; a plain staff user gets nothing; a student is refused office endpoints. Also the role switch, per-office verbs, central-only assignment, designation without tenure, CSRF, and that permission codes match the registry. |
| `test_scoping_isolation.py` | 6 | Another department's rows are absent from lists and 404 by id. Feedback is confidential. A status filter cannot widen scope. Students never see alumni or inactive profiles. |
| `test_edge_cases.py` | 21 | 400 for bad filters, 409 for conflicts, 422 for rule refusals, 429 throttling, the ledger's immutability, and every adversarial question below. |
| `test_concurrency.py` | 6 | Real threads on a `Barrier`, with `transaction=True`: issue race, double issue, double decision, overlapping tenures, transitions twice, delivery twice. |
| `test_query_budgets.py` | 12 | The same query count with 2 rows and with 20, for all 11 list endpoints, plus prefetched notes. |
| `test_schedule.py` | 12 | Beat entries merged and routed; each task twice in a row; readiness, seeding and command output; the headship contract. |
| `test_client_route_guards.py` | 2 | Every client route is guarded with its own nav item's permission. |

Client: 47 department vitest tests. Each of the 8 pages tests loading, empty, a 500 error, a
missing control, and its main action with the server's refusal. There are also 3 hook tests.

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

## 4. Five rules broken on purpose

Each file was copied outside the repository, broken, and run against the whole module, then copied
back. The suite was green again afterwards (`363 passed`).

| Rule broken | Change | Caught by |
|---|---|---|
| Scoping (BR-DEPT-018) | HOD queryset stops excluding `new` feedback | `test_uc_dept_014_hod_oversight_note_and_closure`, `test_feedback_is_visible_only_to_its_submitter_and_the_handling_office` |
| Permission gate (BR-DEPT-006) | `StockRequestDecideView.perms` emptied | `test_module_grant_without_the_permission_is_403[post-stock-requests/1/decide-…]`, `test_student_role_reaches_none_of_the_office_endpoints[…decide…]` |
| Limit check (BR-DEPT-015) | `requested > available + 1000` | `test_uc_dept_004_alternate_insufficient_stock_is_not_advanced`, `test_br_dept_015_refusals[6-5-insufficient_stock]` |
| State transition (BR-DEPT-007) | Table gains `pending_hod → issued` | `test_a_pending_request_cannot_be_issued_before_the_hod_decides`, `test_cw_dept_01_stock_lifecycle_table` |
| Uniqueness (BR-DEPT-022) | `overlapping()` returns nothing | `test_uc_dept_020_alternate_cardinality_violation_is_blocked`, `test_two_overlapping_tenures_recorded_at_once_leave_one`, `test_ended_tenure_cannot_be_changed_and_extension_cannot_overlap` |

## 5. Adversarial pass

| Question | Found | Done |
|---|---|---|
| Can an approver approve their own record? | Possible by design (Q14 approved: one HOD per department, so a guard would strand the request). | The decider is recorded on every decision. |
| Can a thing appear in its own approval queue? | Only the HOD's own Faculty request, by Q14. | As above. |
| Can a balance go negative? | Two approved requests could exceed stock at issuance. | `select_for_update` on the item, `CheckConstraint(current_quantity >= 0)`, 409 `stock_exhausted` (Q13); real-thread race test. |
| Can something be back-dated without limit? | A tenure could have started in the past. | 422 `backdated_tenure` past a 5-minute grace; an end date cannot move into the past. |
| Can a required third party be unavailable? | A department may have no HOD or Dept_Admin in effect (Q1, Q4). | Fails closed: no one acts in that role; readiness and the Roles page show it. |
| Can someone act on another department's row by id? | No. | Every write starts from `selectors/scoping.py`; 404 tests for every write endpoint. |
| Can a closed or rejected record still change? | No. | 409 for re-decide, re-issue, re-review, re-dispose; hidden or deleted announcements are frozen. |
| Does the same request twice take effect twice? | No. | Conditional state moves under row locks; concurrency tests for issue and decide. |
| Does an ordinary user work? (Step 5.2) | **Found a defect:** a real student acts as `ug_student` and a real faculty member as their rank (`Assistant Professor`), so the first build gave them no department. | The basic kind now decides Student or Faculty. Tests use the real IAM shape; checked against the live IAM as `stu00002`. |
| Does the role switch leak? | The IAM sends the union of every held role's permissions. | Rows follow the acting designation, so an HOD acting as faculty cannot reach the HOD queue (404); test added. |
| Can a profile leak sensitive data? | No such field is stored. | Tier test asserts none appears. |

## 6. Security self-audit

| Item | Result |
|---|---|
| Both gates on every view | Every view is a `DepartmentView`: `HasModuleGrant("department")` and then the method's permission. No `AllowAny`; no view overrides authentication (asserted by a test). |
| Explicit serializer fields | Every serializer lists its `fields`; every server-owned field is read-only. |
| Scope on every read and body id | Every list and detail read starts in `selectors/scoping.py`. Body ids (`item`, `department`) are resolved through scoping or a locked lookup, never used raw. |
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
check_department_readiness      -> Department module is ready.
run_department_tasks            -> Role transitions applied: 0. Notifications: sent=0 failed=0 reclaimed=0.
```

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

Synthetic `fusion-dev.dump` accounts, each automated by a Playwright spec that passed in the last
`make e2e`. The specs fail on any console error, uncaught error or 5xx.

| Role | Username | Use case | Result | Spec |
|---|---|---|---|---|
| Institute Admin (`acadadmin`) | stf00002 | UC-DEPT-020, UC-DEPT-022 | pass | `roles.spec.ts` |
| Faculty (`Assistant Professor`) | fac00002 | UC-DEPT-002, UC-DEPT-004, UC-DEPT-011, UC-DEPT-015 | pass | `announcements`, `stock`, `resources` |
| Student (`ug_student`) | stu00002 | UC-DEPT-001, UC-DEPT-007, UC-DEPT-018; guarded routes | pass | `announcements`, `feedback`, `resources`, `guarded-pages` |
| HOD (`HOD (CSE)`) | fac00049 | UC-DEPT-003, UC-DEPT-005, UC-DEPT-012, UC-DEPT-014 | pass | `announcements`, `stock`, `details`, `feedback` |
| Dept_Admin (`deptadmin_cse`) | stf00019 | UC-DEPT-006, UC-DEPT-008, UC-DEPT-009, UC-DEPT-010, UC-DEPT-016, UC-DEPT-017, UC-DEPT-019 | pass | `stock`, `feedback`, `resources`, `details` |

Representative `runserver` lines from the e2e runs:

```text
"POST /api/v1/department/role-assignments HTTP/1.1" 201
"POST /api/v1/department/announcements HTTP/1.1" 201
"POST /api/v1/department/stock-requests HTTP/1.1" 201
"POST /api/v1/department/feedback/2/review HTTP/1.1" 200
"POST /api/v1/department/feedback/2/dispose HTTP/1.1" 200
```

**Not run:** a by-hand walk of one flow using the keyboard alone, watching the browser console.
It needs a person at the keyboard. Open item for Student 1.

Two defects were found while making these specs pass, and both are fixed:
- The stock request's item picker could be cleared by clicking the selected item, after which
  "Submit request" did nothing. The picker can no longer be cleared, and the button explains why it
  is disabled.
- Dialogs showed an empty body while closing.

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
| AFR-DEPT-026 | Faculty see students at the basic tier, never detailed. | No course-roster endpoint on the IAM's `main` (Q2). Dependency: an IAM roster projection. | Q2, below |
| BR-DEPT-022 (SM), HOD-gated ids for SM | SM has no HOD. | `HOD (SM)` does not exist in `globals_designation` (Q4). | Q4, below |

## 11. Approvals

All from Student 2, Shubham Kulkarni (24BCS236), on WhatsApp, 2026-11-22 19:41 IST (shown as edited):

> "I approve the Department blueprint and Q1-Q14 as proposed, including the changes outside the module's folders. Shubham Kulkarni (24BCS236)"

This covers:
- the blueprint;
- every proposal in Q1 to Q14, including the gaps above;
- the changes outside the module's folders: registration lines in `config/settings/base.py`,
  `config/urls.py`, `config/celery.py`, `.importlinter` and `client/src/app/registry.ts`; the
  regenerated `openapi/fusion-integrated.v1.yaml`, `registry/permissions.json` and
  `docs/02-iam/permission-catalog.generated.md`; the new entries in `client/e2e/accounts.ts`;
  and `ops/docs/department_reference.py`.

No dependency was added.

## 12. Review rounds

None yet. Round 1 reviews the commit that adds this report.
