# Gymkhana: quality report

Every number below comes from a run made on 2026-11-22 after the last code change. "Not run"
means not run, with the reason; nothing here is inferred.

## 1. `make check` and `make check-client`

```
$ make check            # exit 0
Contracts: 5 kept, 0 broken.          (incl. "Layering inside gymkhana KEPT")
no cross-module foreign keys
all contract getters are plural
nav items and client routes agree
permission manifest matches the registries
openapi schema matches the code
$ .venv/bin/python -m pytest -q       # the suite make check runs
698 passed, 27 subtests passed in 15.07s

$ make check-client     # exit 0
 Test Files  14 passed (14)
      Tests  82 passed (82)
✓ built in 3.64s

$ make e2e              # exit 0, IAM on 8001 and make dev on 8002
  25 passed (26.2s)
```

The module's largest chunk is `MyClubsPage` at 3.75 kB gzip; all six pages, `routes` and
`hooks` together are under 20 kB gzip, inside the 150 kB budget.

## 2. Coverage (Step 5.14)

```
$ pytest modules/gymkhana --cov=modules/gymkhana --cov-branch --cov-fail-under=90
modules/gymkhana/api/views.py   …    1  …   1  99%
TOTAL                          1621  1 240  1  99%
Required test coverage of 90% reached. Total coverage: 99.89%

$ pytest modules/gymkhana --cov=modules/gymkhana/domain --cov-branch --cov-fail-under=95
TOTAL                           145  0  52  0 100%
Required test coverage of 95% reached. Total coverage: 100.00%
```

The one uncovered line is `OpenPollListView`'s `swagger_fake_view` guard, which only schema
generation reaches (and `make schema-check` exercises it). No `# pragma: no cover` is used.

## 3. Test counts

| File | Tests | Concern |
|---|---|---|
| test_domain.py | 31 | every branch of every pure rule |
| test_state_machine.py | 54 | every illegal move and wrong actor, enumerated from the table |
| test_journeys.py | 43 | each use case through HTTP, with its alternate and exception flows |
| test_privilege_escalation.py | 79 | both gates on all 22 endpoints, 401, role switch, CSRF, 429, 400 filters |
| test_scoping_isolation.py | 10 | one club's or councillor's rows never reach another |
| test_concurrency.py | 6 | real threads on a barrier: booking, application, vote, approvals, names |
| test_query_budgets.py | 10 | same query count with 2 and 22 clubs, ≤ 8 per list |
| test_notifications.py | 13 | the drain runs once, twice in a row, twice at once |
| test_schedule.py | 3 | beat entry merged, task registered and routed |
| test_contracts.py | 4 | `get_club_affiliations`, `students_in_cohorts` |
| test_commands.py | 9 | venue seeding, readiness, manual drain |
| test_service_edges.py | 8 | refusals reachable only below the API |
| test_client_route_guards.py | 3 | every route guarded by its nav item's permission |
| **Total** | **273** | |

Journey tests by the use case their name starts with (main flows that span two use cases
are named for both): UC-GYM-001 5, UC-GYM-001+011 1, UC-GYM-002 4, UC-GYM-003 3,
UC-GYM-004 4, UC-GYM-004+005 1, UC-GYM-005 3, UC-GYM-006 2, UC-GYM-006+007 1,
UC-GYM-007 4, UC-GYM-008 3, UC-GYM-009 2, UC-GYM-010 1, UC-GYM-010+012 1, UC-GYM-011 2,
UC-GYM-012 1. The remaining 5 journey tests cover listing, My Clubs and the people picker. Every one of the 77 live ids is cited by at least one test
(`grep -rn '<ID>' modules/gymkhana/tests`, test names normalised).

## 4. Five rules broken on purpose (Step 5.15)

Each file was copied to the scratchpad, broken, the module suite run, and the copy restored.

| Rule broken | How | Caught by (failing count) |
|---|---|---|
| Scoping filter, BR-GYM-010 | `led_clubs` dropped its `user_id` filter | 13, e.g. `test_uc_gym_002_club_head_books_a_session…`, `test_uc_gym_008_club_head_replaces_both_leaders` |
| Permission gate, UC-GYM-002 | `SessionCreateView` lost `HasPermission` | 1, `test_module_grant_without_the_permission_is_403[post-sessions-…]` |
| Limit check, BR-GYM-017 | `amount < 0` became `amount < -1000` | 2, `test_br_gym_017_amount_is_zero_or_more`, `test_uc_gym_009_exception_flow…` |
| State transition, BR-GYM-004 | added `confirmed → confirmed` | 3, `test_uc_gym_011_exception_flow…`, `test_br_gym_004_approving_at_once_confirms_once`, `test_br_gym_004_and_011_confirmed_is_terminal` |
| Venue exclusivity under concurrency, BR-GYM-006 | removed the venue-day `select_for_update` | 1, `test_br_gym_006_overlapping_bookings_at_once_yield_one`, in 3 runs out of 3 |

The fifth was **not** caught at first. The test raced the day's first booking, which the
venue-day row's unique insert happens to serialize. The test now books an earlier slot first,
so only the lock can hold. After restoring: `273 passed`, and the concurrency file passed 3
runs out of 3.

## 5. Adversarial pass (Step 5.11)

| Question | Found | Done |
|---|---|---|
| Can an approver approve their own record? | A Club Head could approve their own application to the club they lead | Refused with `self_approval` (H2); the other leader approves. Tested |
| Can a thing appear in its own approval queue? | Same case; it appears, but cannot be approved by its owner | As above |
| Can a balance go negative? | No balance exists; a budget amount can't be negative | `check_amount` + `gym_budget_amount_non_negative` |
| Can something be back-dated without limit? | Bookings, poll expiry, report dates | Bookings: today to +365 days (H4). Polls: expiry not in the past. Reports: event not in the future (H5) |
| Is a required third party unavailable? | The event's councillor may no longer be faculty | Event refused with `councillor_invalid`, telling them to ask Student Admin |
| Acting on an out-of-scope id directly? | Every Club Head write resolves its club through `led_clubs` | 404 for foreign clubs, reports, polls. Tested per write |
| Can a closed record still change? | Confirmed club/membership; expired poll | No edge out of `confirmed`; an expired poll answers 409 `poll_closed` |
| Does the same request twice take effect twice? | Application, vote, booking, approval | DB uniques plus row locks; threaded tests for each |
| Can a body field override server-owned state? | `status`, `user_id` sent on apply | Ignored; tested |
| Is the poll a secret ballot to the club? | Leaders see counts only; the audit trail omits the choice | Tested (`test_poll_counts_reach_only_the_creating_clubs_leaders`) |

## 6. Security self-audit (Step 7.7)

| Item | Result |
|---|---|
| Both gates on every view | Yes, all 22 endpoints, each gate tested separately; no `AllowAny`, no auth override |
| Serializers list fields; server fields read-only | Yes; no `__all__`/`exclude`; output serializers are entirely read-only |
| Reads start from `scoping.py`; ids in bodies checked | Yes: `club_id` through `led_clubs`/`clubs_for`; people ids through the directory |
| No raw SQL / eval / pickle / subprocess | grep clean |
| File uploads | None: documents are Drive links through `core/files/drive.py` (R1) |
| `throttle_scope` on every write | Yes (`gymkhana_write`, `gymkhana_vote`); 429 tested |
| Logs carry ids only | Two log lines, both ids and counts |
| No stack trace in errors | Tested |
| Cookie write without CSRF → 403 | Tested |
| Client: no `dangerouslySetInnerHTML`, no `localStorage`, all calls via `lib/http.ts` | grep clean |
| New dependencies | None |
| Deploy check, production settings | `System check identified no issues (2 silenced).` (the 2 predate this module) |

## 7. Fresh install (Step 7.8)

Run on the throwaway `fusion_integrated_fresh` with `createdb`/`dropdb` (no Docker on this
machine), `DB_NAME` on every line.

```
Applying gymkhana.0001_initial... OK  |  Unapplying gymkhana.0001_initial... OK  |  Applying gymkhana.0001_initial... OK
gymkhana: registered but NOT active — 1 prerequisite(s) unmet:
    No Gymkhana venue list is in effect. Run `manage.py seed_gymkhana_venues --venue "<name>" ...` …
CommandError: gymkhana is not ready: 1 prerequisite(s) unmet.        (readiness exit=1)
$ seed_gymkhana_venues --venue "LHTC 101" --venue "Open Air Theatre"
Venue list 1 takes effect 2026-11-22 19:42: LHTC 101, Open Air Theatre
$ seed_modules → registered gymkhana (active)   |   gymkhana_readiness → gymkhana is ready. (exit=0)
accesscontrol_module: gymkhana|active
```

IAM seeded from the regenerated manifest, and one account granted its role:

```
$ seed_iam_permissions --manifest …/registry/permissions.json
  gymkhana: 18 mapping(s)
21 added, 0 revoked; 67 total
$ assign_role --user stf00063 --designation "Student Admin"
Granted 'Student Admin' on stf00063
  'Student Admin' was new, so it was added to the ERP's designations
```

Then `DB_NAME=fusion_integrated_fresh make dev`, and the first user action over HTTP: sign in
through the IAM as `stf00063`, list clubs, create one and confirm it.

```
POST auth/login -> 200
GET me -> active_role: Student Admin | gymkhana granted: True
GET gymkhana/clubs -> 200            {"results": []}
POST gymkhana/clubs/create -> 201    id 1, status open, leaders and councillor by name
POST gymkhana/clubs/1/approve -> 200 status confirmed
```

`runserver` log for those requests:

```
[22/Nov/2026 20:08:44] "POST /api/v1/auth/login HTTP/1.1" 200 91
[22/Nov/2026 20:08:44] "GET /api/v1/me HTTP/1.1" 200 648
[22/Nov/2026 20:08:44] "GET /api/v1/gymkhana/clubs HTTP/1.1" 200 42
[22/Nov/2026 20:08:44] "POST /api/v1/gymkhana/clubs/create HTTP/1.1" 201 451
[22/Nov/2026 20:08:44] "POST /api/v1/gymkhana/clubs/1/approve HTTP/1.1" 200 486
```

The server was then stopped and the database dropped (`dropdb … fusion_integrated_fresh`;
`pg_database` count for it afterwards: 0).

## 8. Browser walkthrough (Step 6.9)

Automated in a real browser (Chromium, Playwright) against the real IAM and `make dev`:
`make e2e` → **25 passed**, 15 of them Gymkhana's. The spec fails on any uncaught page
error, console error or 5xx, so "passed" also means none of those happened.

Walked by hand on 2026-11-22 by the person running this session, following a 10-step
checklist (Student Admin creates and confirms a club; a student applies, hits a guarded URL,
sees the schedule and votes; the Club Head approves, books, is refused an overlapping event,
creates a poll, reads results, submits a budget request and a report; the councillor reviews;
another faculty member sees nothing; one application done by keyboard alone). Reported
result: **all 10 steps ok, no console errors.**

| Role | Dump account | Use case | Spec | Automated | By hand |
|---|---|---|---|---|---|
| Student Admin | stf00063 | UC-GYM-001, UC-GYM-011 | e2e/gymkhana/journeys.spec.ts | passed | ok |
| Student (applicant, voter) | stu00004 | UC-GYM-004, UC-GYM-007 | journeys.spec.ts | passed | ok |
| Club Head | stu00002 | UC-GYM-005, 002, 003, 006, 008, 009, 010 | journeys.spec.ts | passed | ok |
| Club Faculty Councillor | fac00001 | UC-GYM-012 | journeys.spec.ts | passed | ok |
| Plain student | stu00001 | guarded pages | guarded-pages.spec.ts | passed | ok |
| Faculty | fac00001 | guarded pages | guarded-pages.spec.ts | passed | ok |
| Keyboard-only flow | stu00004 | UC-GYM-004 | — | — | ok |

### Server log for each row

Captured from `make dev` on 2026-11-22 by replaying each row's requests over HTTP as that
row's account (the hand walkthrough itself was not logged). Every line is real `runserver`
output; 409 and 403 are the refusals the row checks for. No 5xx in any row.

**Student Admin · stf00063 · UC-GYM-001, UC-GYM-011**

```
[22/Nov/2026 20:31:09] "POST /api/v1/auth/login HTTP/1.1" 200 91
[22/Nov/2026 20:31:09] "GET /api/v1/me HTTP/1.1" 200 648
[22/Nov/2026 20:31:09] "GET /api/v1/gymkhana/clubs HTTP/1.1" 200 4397
[22/Nov/2026 20:31:09] "POST /api/v1/gymkhana/clubs/create HTTP/1.1" 201 441
[22/Nov/2026 20:31:09] "POST /api/v1/gymkhana/clubs/10/approve HTTP/1.1" 200 476
```

**Student (applicant) · stu00004 · UC-GYM-004**

```
[22/Nov/2026 20:31:11] "POST /api/v1/auth/login HTTP/1.1" 200 91
[22/Nov/2026 20:31:11] "GET /api/v1/me HTTP/1.1" 200 2092
[22/Nov/2026 20:31:11] "GET /api/v1/gymkhana/clubs HTTP/1.1" 200 4909
[22/Nov/2026 20:31:11] "POST /api/v1/gymkhana/memberships/apply HTTP/1.1" 201 227
```

**Club Head · stu00002 · UC-GYM-005, 002, 003, 006, 009, 010**

```
[22/Nov/2026 20:31:12] "POST /api/v1/auth/login HTTP/1.1" 200 91
[22/Nov/2026 20:31:12] "GET /api/v1/me HTTP/1.1" 200 2092
[22/Nov/2026 20:31:12] "GET /api/v1/gymkhana/me/clubs HTTP/1.1" 200 3893
[22/Nov/2026 20:31:12] "GET /api/v1/gymkhana/memberships?club=10&status=open HTTP/1.1" 200 294
[22/Nov/2026 20:31:12] "POST /api/v1/gymkhana/memberships/approve HTTP/1.1" 200 71
[22/Nov/2026 20:31:12] "GET /api/v1/gymkhana/venues HTTP/1.1" 200 42
[22/Nov/2026 20:31:12] "POST /api/v1/gymkhana/sessions HTTP/1.1" 201 302
[22/Nov/2026 20:31:12] "POST /api/v1/gymkhana/events HTTP/1.1" 409 207
[22/Nov/2026 20:31:13] "POST /api/v1/gymkhana/polls/create HTTP/1.1" 201 256
[22/Nov/2026 20:31:13] "POST /api/v1/gymkhana/budget-requests/create HTTP/1.1" 201 279
[22/Nov/2026 20:31:13] "POST /api/v1/gymkhana/event-reports/create HTTP/1.1" 201 347
```

Same Club Head, a successful event booking and a successful leadership change (UC-GYM-003,
UC-GYM-008), replayed the same way:

```
[22/Nov/2026 20:51:47] "POST /api/v1/auth/login HTTP/1.1" 200 91
[22/Nov/2026 20:51:47] "GET /api/v1/me HTTP/1.1" 200 2092
[22/Nov/2026 20:51:47] "GET /api/v1/gymkhana/me/clubs HTTP/1.1" 200 3893
[22/Nov/2026 20:51:47] "POST /api/v1/gymkhana/events HTTP/1.1" 201 374
[22/Nov/2026 20:51:47] "POST /api/v1/gymkhana/clubs/10/leadership HTTP/1.1" 200 42
```

**Student (voter) and Club Head (results) · stu00004, stu00002 · UC-GYM-007**

```
[22/Nov/2026 20:31:14] "GET /api/v1/gymkhana/bookings HTTP/1.1" 200 1834
[22/Nov/2026 20:31:14] "GET /api/v1/gymkhana/polls HTTP/1.1" 200 1705
[22/Nov/2026 20:31:14] "POST /api/v1/gymkhana/polls/6/votes HTTP/1.1" 201 16
[22/Nov/2026 20:31:14] "GET /api/v1/gymkhana/polls/managed?club=10 HTTP/1.1" 200 365
```

**Club Faculty Councillor · fac00001 · UC-GYM-012**

```
[22/Nov/2026 20:31:15] "POST /api/v1/auth/login HTTP/1.1" 200 91
[22/Nov/2026 20:31:15] "GET /api/v1/me HTTP/1.1" 200 581
[22/Nov/2026 20:31:15] "GET /api/v1/gymkhana/event-reports HTTP/1.1" 200 2354
[22/Nov/2026 20:31:16] "GET /api/v1/gymkhana/event-reports/6 HTTP/1.1" 200 372
```

**Plain student · stu00001 · guarded: Student Admin actions refused**

```
[22/Nov/2026 20:31:17] "POST /api/v1/auth/login HTTP/1.1" 200 91
[22/Nov/2026 20:31:17] "GET /api/v1/me HTTP/1.1" 200 2092
[22/Nov/2026 20:31:17] "GET /api/v1/gymkhana/clubs HTTP/1.1" 200 4874
[22/Nov/2026 20:31:17] "POST /api/v1/gymkhana/clubs/create HTTP/1.1" 403 166
[22/Nov/2026 20:31:17] "POST /api/v1/gymkhana/clubs/10/approve HTTP/1.1" 403 166
```

**Faculty · fac00001 · guarded: student pages refused**

```
[22/Nov/2026 20:31:18] "GET /api/v1/gymkhana/clubs HTTP/1.1" 403 166
[22/Nov/2026 20:31:18] "POST /api/v1/gymkhana/sessions HTTP/1.1" 403 166
```

**Keyboard-only flow · stu00004 · UC-GYM-004 (the requests it makes)**

```
[22/Nov/2026 20:31:20] "GET /api/v1/gymkhana/clubs HTTP/1.1" 200 4916
[22/Nov/2026 20:31:20] "POST /api/v1/gymkhana/memberships/apply HTTP/1.1" 201 226
```

Defects the E2E run found, each fixed with a test that fails without the fix:

- People showed as raw user ids ("4093 / 5974"). The API now returns names from one batched
  directory call (`selectors/people.py`), and the client shows them.
- The person picker searched again with the chosen person's label, got no match, and lost the
  choice. The server log proved the IAM search was correct: `q=stu00003` returned one
  student every time, and no `/people` request was throttled (zero 429s).
- Re-picking the current leader deselected them (`allowDeselect` now off).

The role-switch defect found during this run is outside the module; see section 10.

## 9. Scheduled task run by hand

```
$ gymkhana_deliver_notifications          (one row queued for a recipient with no address)
expanded=0 sent=0 failed=1 deferred=0
$ gymkhana_deliver_notifications
expanded=0 sent=0 failed=0 deferred=1
row: manual-check-1 | pending | attempts=1 | No email address on record for this recipient.
```

The second run deferred the row under backoff instead of re-sending it. A real delivery to a
dump account needs the IAM running, and is part of the walkthrough not yet run.

## 10. Known gaps accepted

| Spec id | Gap | Reason | Approval |
|---|---|---|---|
| UC-GYM-002/003 (H7) | No booking cancellation | Not in the baseline | Student 2, 2026-11-22 (blueprint quote) |
| H1 | Real post holding `Student Admin` unknown | Academic office's decision | Student 2, 2026-11-22 |

### Known platform issue (shared code, not this module)

**Role switch replies with the previous role.** `fusion_auth/views.py::MeView.patch` changes
the role at the IAM, then answers with `self.get(request)`, whose principal was resolved
before the change. The switch does take effect; the reply is one step behind, so the role
picker shows the role just left until the next `GET /me` (a reload fixes it). Reproduced over
HTTP on 2026-11-22: `PATCH` to `student` replied `ug_student`, and a `GET` straight after said
`student`; switching back behaved the same way in reverse. It affects every module, Placement
included. Per the session owner's instruction (2026-11-22), `fusion_auth/views.py` is not
changed here; it is for the platform's owner. Gymkhana does not depend on it: its server reads
permissions and club data only. The E2E accounts avoid it because each account's stored role
already equals the role its spec acts as, so no switch is needed.

## 11. Approvals

> "I approve the Gymkhana blueprint (docs/18-gymkhana/gymkhana-blueprint.md) including R1–R10,
> R9 (directory contracts change) and H1–H9 defaults. — Saroj Aman, 22 Nov 2026"
> (written, WhatsApp, 2026-11-22). Covers the blueprint, R1–R10, the `modules/directory/contracts.py`
> change and H1–H9.

Shared-file changes made under Step 4.0's pre-approval: `config/settings/base.py`,
`config/urls.py`, `config/celery.py`, `.importlinter`, `client/src/app/registry.ts`,
`client/e2e/accounts.ts` (four entries), `ops/docs/gymkhana_reference.py`, and the regenerated
`openapi/fusion-integrated.v1.yaml`, `registry/permissions.json` and
`docs/02-iam/permission-catalog.generated.md`.

Approver answers to round 2's questions, agreed by Student 2 and Student 1 on 2026-11-22:

- Q1: poll expiry has no upper limit; the spec sets none, so none is invented.
- Q2: the `~/.claude` files in the home directory are tool-managed caches, not instruction
  files; no `CLAUDE.md` exists.

Departures from the blueprint, confirmed by Student 2:

> "I confirm departures 1–3. — Saroj Aman, 22 Nov 2026" (written, WhatsApp, 2026-11-22)

1. **People picker** uses the IAM's `search_users` through `get_client()`, the way Placement's
   `services/facts.py` does, instead of `directory.search`. `directory.search` reads only the
   local projection, which on this fixture holds almost no students.
2. **"Active" is not checked** for leaders, councillors or the student in charge.
   `directory.get_users` carries no `is_active` field, so only kind is checked. Adding it is
   another change to `modules/directory`, which has not been approved.
3. **Poll target groups** are checked for shape only (batch year 2000–2100, branch ≤ 40
   characters), not against the IAM's list of batches.

## 12. Review scorecards

Round 1, reviewing commit `e52b101`:

| Spec | Arch | Code | Security | Backend tests | E2E | Frontend | Ops | Hygiene |
|---|---|---|---|---|---|---|---|---|
| 10 | 10 | 10 | 10 | 10 | 7 (R1-01, major) | 10 | 10 | 9 (R1-02, minor) |

Verdict: not yet, 2 open findings. The review ran in auto mode, and it skipped its hands-on
probes after it was asked to be quick.

Findings and what was done:

- R1-01 (dimension 6, major): walkthrough rows had no server log lines. Each row in section 8
  now carries the real `runserver` lines for its requests.
- R1-02 (dimension 9, minor): two header lines matched the AI-name grep. Reworded in
  `modules/gymkhana/migrations/0001_initial.py` and in the reference generator (and so in
  `gymkhana-reference.md`); the grep now prints nothing.

Every gate re-run afterwards: `make check` exit 0 (698 passed), `make check-client` exit 0
(82 passed), coverage 99.89% and 100%, reference 77 ids, deploy check clean.

Round 2, reviewing commit `8f68bb2`:

| Spec | Arch | Code | Security | Backend tests | E2E | Frontend | Ops | Hygiene |
|---|---|---|---|---|---|---|---|---|
| 10 | 10 | 7 (R2-02..04) | 10 | 10 | 7 (R2-01) | 10 | 9 (R2-05) | 10 |

Verdict: not yet, 5 findings. Fixes:

- R2-01: the Club Head row in section 8 now has a 201 event booking and a 200 leadership change.
- R2-02: a report outside one's scope (or missing) answers 404 `report_not_found`, "No such
  event report among the clubs you lead or review. Open one from the report list instead."
  Tested.
- R2-03: a bad batch year now says "Enter a year from 2000 to 2100, such as 2023." Tested.
- R2-04: `_book` is 29 lines, split into `_check_slot`, `_event_faculty` and `_reserve`, still
  one transaction.
- R2-05: the blueprint's endpoint table now names `clubs/create`, `memberships/apply`,
  `polls/create`, `budget-requests/create` and `event-reports/create`, matching `api/urls.py`.
