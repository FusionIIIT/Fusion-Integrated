# Gymkhana quality report

Every number below comes from a run on 24 November 2026, after the last backend change. It replaces an
earlier report whose claims did not hold.

Status: Student 2's written approval and review are **pending** (items 10, 11 and 12).

## 1. Gates

`make check`:

```text
No changes detected
All checks passed!
Contracts: 5 kept, 0 broken.
no cross-module foreign keys
all contract getters are plural
nav items and client routes agree
permission manifest matches the registries
openapi schema matches the code
make check exit 0
```

`make check-client`, its three commands run one after the other:

```text
tsc --noEmit && tsc --noEmit -p e2e      (no output)
Test Files  14 passed (14)
     Tests  96 passed (96)
built in 3.98s
```

The largest Gymkhana chunk is `ClubManagementPage`: 6.89 kB gzip, against a limit of 150 kB.

Deployment check, with the command in Step 7.7:

```text
System check identified no issues (2 silenced).
```

## 2. Coverage

Measured without the spec tests.

```text
--cov=modules/gymkhana --cov-branch --cov-fail-under=90
TOTAL                  1519     21    224     10    98%
Required test coverage of 90% reached. Total coverage: 98.22%
642 passed in 58.53s

--cov=modules/gymkhana/domain --cov-branch --cov-fail-under=95
TOTAL                   127      1     48      1    99%
Required test coverage of 95% reached. Total coverage: 98.86%
```

## 3. Tests

| File in `modules/gymkhana/tests/` | Tests |
|---|---|
| `test_access.py` | 40 |
| `test_api.py` | 8 |
| `test_client_route_guards.py` | 2 |
| `test_concurrency.py` | 7 |
| `test_contracts.py` | 2 |
| `test_directory_lookups.py` | 8 |
| `test_domain.py` | 10 |
| `test_journeys.py` | 38 |
| `test_models.py` | 5 |
| `test_notifications.py` | 12 |
| `test_query_budgets.py` | 6 |
| `test_schedule.py` | 5 |
| `test_scoping_isolation.py` | 9 |
| `test_selectors.py` | 8 |
| `test_services.py` | 8 |
| `test_uploads.py` | 17 |
| `test_validation_rules.py` | 18 |
| `stress/test_stress_polls_and_voting.py` | 85 |
| `stress/test_stress_rbac_scoping.py` | 59 |
| `stress/test_stress_validation_and_fuzzing.py` | 100 |
| `stress/test_stress_venue_bookings.py` | 195 |
| **Total** | **642** |

Every live CFR, AFR, UC, BR and BW id is cited by at least one of these tests.

Journeys in `test_journeys.py`, by use case:

| Use case | Tests beginning |
|---|---|
| UC-GYM-001, UC-GYM-011 | `test_uc_gym_001_011_`, `test_uc_gym_001_`, `test_uc_gym_011_` |
| UC-GYM-002, UC-GYM-003 | `test_uc_gym_002_`, `test_uc_gym_003_`, `test_uc_gym_002_003_` |
| UC-GYM-004, UC-GYM-005 | `test_uc_gym_004_005_`, `test_uc_gym_004_`, `test_uc_gym_005_` |
| UC-GYM-006, UC-GYM-007 | `test_uc_gym_006_007_`, `test_uc_gym_006_`, `test_uc_gym_007_` |
| UC-GYM-008 | `test_uc_gym_008_` |
| UC-GYM-009 | `test_uc_gym_009_` |
| UC-GYM-010, UC-GYM-012 | `test_uc_gym_010_012_`, `test_uc_gym_010_` |

## 4. Rules broken on purpose

Each file was copied out, broken, tested and copied back.

| Rule | What was broken | Caught by |
|---|---|---|
| BR-GYM-013 | The target-group filter on polls removed | `test_br_gym_013_a_poll_reaches_only_its_own_batch_and_branch` |
| Acting-role permission gate | The gate always answers yes | `test_acting_as_student_admin_the_student_permissions_do_not_count` |
| BR-GYM-006 | The venue lock removed | `test_br_gym_006_one_slot_is_booked_once_across_sessions_and_events[True]` |
| BR-GYM-011 | A confirmed membership may be approved again | `test_uc_gym_005_an_approved_application_is_not_changed_again` |
| BR-GYM-015 | The already-voted check removed | `test_uc_gym_006_007_a_targeted_student_votes_once` |

The first attempt at BR-GYM-006 was not caught: on a day with no bookings, inserting the day's row
already queues them. The test now also covers a day that has its row.

## 5. Adversarial pass

| Question | Found | Now |
|---|---|---|
| Can an approver approve their own record? | Yes, a club head who applied to their own club | Refused: `test_br_gym_010_nobody_approves_their_own_application` |
| Can something appear in its own approval queue? | The head's own application is listed | It cannot be approved by them |
| Can a balance go negative? | No: budget amounts are zero or more | `test_uc_gym_009_an_invalid_request_is_not_stored` |
| Can something be back-dated without limit? | A past booking date is accepted; no rule forbids it | Open question in the blueprint |
| Can a report be dated in the future? | Yes | Refused: `test_uc_gym_010_an_event_may_be_reported_from_the_moment_it_occurs` |
| Can a required third party be unavailable? | The directory contract does not say whether an account is active | Known gap |
| Can someone act outside their scope by sending an id? | Student Admin could read every club's event reports | `test_scoping_isolation.py` |
| Can a closed record still be changed? | No | Repeat approvals and expired votes are refused in `test_journeys.py` |
| Can the same request take effect twice? | Two bookings could take one slot | `test_concurrency.py`, eight threads each |
| Does a held role count when not acting as it? | Yes | `test_acting_as_student_an_admin_cannot_approve_a_club` |
| Can the people search be used to list everyone? | It needs three characters and a role that assigns people | `test_a_people_search_is_never_an_enumeration` |

## 6. Security self-audit

| Item | Result |
|---|---|
| Both gates on every view | `GymkhanaView` sets the module grant and the acting permission; `test_access.py` drives every path |
| Explicit serializer fields | No `__all__` or `exclude`; server-owned fields are not accepted as input |
| Scoping on reads and on ids in the body | `selectors/scoping.py`; `test_scoping_isolation.py` |
| No raw SQL, `eval`, `pickle` or similar | None |
| Uploads | Size, type and active content are checked, stored privately under a generated name, and served only as scoped attachments. `core/files` offers no byte validation today, so the checks are in the module and use its `sanitise_filename`. Bytes are not matched to the extension: open question |
| Throttle on every write | `gymkhana_write`; `test_writes_are_throttled_and_reads_are_not` |
| Logs carry ids only | Yes |
| Errors carry no trace, SQL or path | Yes, through the platform's handler |
| Cookie write without `X-CSRF-Token` | 403: `test_a_write_by_cookie_needs_the_csrf_header` |
| Client | No `dangerouslySetInnerHTML`, no token in storage, every call through `lib/http.ts` |
| Dependencies | None added |
| Deployment check | Passes (item 1) |

## 7. Fresh install

On a throwaway database, dropped afterwards.

```text
## migrate zero
  Unapplying gymkhana.0001_initial... OK
## seed_modules
  registered placement_cell (active)
  registered gymkhana (active)
2 module(s) registered
## readiness
Gymkhana is ready.
## first user action: create then confirm a club
login 200
confirm 200
confirm without CSRF 403
[24/Nov/2026 01:02:53] "POST /api/v1/auth/login HTTP/1.1" 200 91
[24/Nov/2026 01:02:53] "POST /api/v1/gymkhana/clubs/ HTTP/1.1" 201 372
[24/Nov/2026 01:02:53] "POST /api/v1/gymkhana/clubs/1/confirm/ HTTP/1.1" 200 377
[24/Nov/2026 01:02:53] "POST /api/v1/gymkhana/clubs/1/confirm/ HTTP/1.1" 403 222
```

The first action was sent over HTTP, not through a browser. The module has no policy to seed. The single
migration gives the same schema, line for line, as the two it replaced.

## 8. Browser walkthrough

Run by Playwright in installed Chrome, through a temporary configuration that has been deleted: the
bundled Chromium was not installed. The whole suite, Placement's specs included: `28 passed (1.2m)`.
A walkthrough by a person is still to be done (Step 10 of the guide).

| Role | Account | Use case | Result | Spec in `client/e2e/gymkhana/` |
|---|---|---|---|---|
| Student Admin | `stu00002` | UC-GYM-001, UC-GYM-011 | Pass | `clubs.spec.ts` |
| Student, then club head | `stu00001`, `stu00003` | UC-GYM-004, UC-GYM-005 | Pass | `clubs.spec.ts` |
| Club head | `stu00003` | UC-GYM-008 | Pass | `clubs.spec.ts` |
| Club head | `stu00003` | UC-GYM-002, UC-GYM-003 | Pass | `activities.spec.ts` |
| Club head, then student | `stu00003`, `stu00001` | UC-GYM-006, UC-GYM-007 | Pass | `activities.spec.ts` |
| Club head | `stu00003` | UC-GYM-009, and once by keyboard alone | Pass | `activities.spec.ts` |
| Club head, then councillor | `stu00003`, `fac00001` | UC-GYM-010, UC-GYM-012 | Pass | `activities.spec.ts` |
| Plain student | `stu00001` | Five open pages open; two guarded pages are refused | Pass | `pages.spec.ts` |
| Faculty | `fac00001` | Four guarded pages are refused | Pass | `pages.spec.ts` |

Server log of that run; no 500 and no traceback:

```text
"POST /api/v1/gymkhana/clubs/ HTTP/1.1" 201 391
"POST /api/v1/gymkhana/clubs/29/confirm/ HTTP/1.1" 200 396
"POST /api/v1/gymkhana/bookings/session/ HTTP/1.1" 201 351
"POST /api/v1/gymkhana/bookings/event/ HTTP/1.1" 409 192
"POST /api/v1/gymkhana/bookings/event/ HTTP/1.1" 201 374
"POST /api/v1/gymkhana/polls/ HTTP/1.1" 201 417
"POST /api/v1/gymkhana/polls/5/vote/ HTTP/1.1" 200 416
"POST /api/v1/gymkhana/budgets/ HTTP/1.1" 201 273
"POST /api/v1/gymkhana/reports/ HTTP/1.1" 201 347
"POST /api/v1/gymkhana/memberships/apply/ HTTP/1.1" 201 261
"POST /api/v1/gymkhana/memberships/5/approve/ HTTP/1.1" 200 303
"POST /api/v1/gymkhana/clubs/36/leadership/ HTTP/1.1" 200 396
```

The 409 is the event that tries to take a booked slot. The run before this one failed UC-GYM-005: a
student saw a cached status for up to 30 seconds after a decision. Lists are now fetched again whenever
a page opens.

## 9. Scheduled tasks

Run by hand with `manage.py gymkhana_run_tasks`, with mail kept in memory.

| Task | What changed |
|---|---|
| `gymkhana.expire_polls` | `polls expired: 1`: the overdue poll went from `active` to `expired`. A second run expired 0 |
| `gymkhana.deliver_notifications` | `notifications sent: 500`, its batch limit, then 500 more on a second run |

## 10. Known gaps

Listed in the blueprint, Steps 3.8 and "Revision 2". **None has a recorded acceptance yet.**

| Spec id | Gap |
|---|---|
| BR-GYM-001, BR-GYM-002 | "Valid" checks the person's kind; the directory contract does not say whether an account is active |
| BR-GYM-013 | The poll audience is read from an endpoint that also returns CPI; only ids are kept |
| AFR-GYM-014 | The event poster is optional, pending the reading of FR-015 |
| BR-GYM-018, BR-GYM-019 | Files are stored under `PLACEMENT_UPLOAD_ROOT`, another module's setting |

## 11. Approvals

| Approval | Record |
|---|---|
| Blueprint | Pending. `gymkhana-blueprint-review-s2.md` is not signed by a person, and predates Revision 2 |
| Known gaps | Pending |
| Files outside the module: `config/settings/base.py`, `config/urls.py`, `config/celery.py`, `.importlinter`, `client/src/app/registry.ts`, `client/e2e/accounts.ts`, `ops/docs/gymkhana_reference.py` | Pending |
| Dependencies | None needed |

## 12. Review rounds

No reviewer output is on record. The scores in the earlier report have none
behind them and are not repeated here.

The spec tests were re-run on this code by Student 1 and await Student 2's confirmation: FR 39, UC 25,
BR 44 and WF 16 passed, none failed, none skipped. Seven of them were automated, and two fixtures
corrected, as `spec-tests/triage.md` records.
