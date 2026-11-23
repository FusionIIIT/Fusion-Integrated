# Spec-test triage: MMS A9

## PostgreSQL environment diagnosis and correction

The project configuration is correct for the local database: `.env` sets `DB_HOST=127.0.0.1`
and `DB_PORT=5432`, matching `config/settings/base.py` defaults. Inside the test sandbox, TCP
connection attempts to localhost returned `PermissionError`; outside it, both `127.0.0.1:5432`
and `localhost:5432` accepted connections. The system `postgresql.service` unit is absent, but
the configured listener is reachable. A Django-configured `SELECT 1` returned `1`, confirming
credentials and the application database connection. All four test runs then created their
PostgreSQL test databases successfully, with zero setup errors.

**Minimal correction:** execute the test process outside the network-restricted sandbox. No
project or production database settings, credentials, or service configuration were changed.

## Recorded independent suite results (2026-11-24, Asia/Kolkata)

Each suite was run once after PostgreSQL connectivity was restored. Counts are from the run's
JUnit XML; coverage rates are from its coverage XML. `Passed` is the test-item total minus
failures, errors, and skips.

| Suite | Tests | Passed | Failed | Errors | Skipped | Line % | Branch % | Pytest exit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FR | 117 | 98 | 3 | 0 | 16 | 75.0 | 46.9 | 1 |
| UC | 128 | 113 | 2 | 0 | 13 | 78.1 | 57.3 | 1 |
| BR | 84 | 65 | 6 | 0 | 13 | 72.9 | 48.6 | 1 |
| WF | 24 | 14 | 0 | 0 | 10 | 66.2 | 36.0 | 0 |
| **Total** | **353** | **290** | **11** | **0** | **52** | — | — | — |

These are the captured results before the final triage clarification below. The broad suites
were not rerun; these counts remain historical and are not a claim that the final spec-test
snapshot passes.

Commands used `.venv/bin/pytest modules/mms/tests/spec/<strategy> --tb=short -q` with
JUnit XML, `--cov=modules/mms --cov-branch`, and XML/terminal coverage output. JUnit and
coverage outputs were captured under `/tmp/mms-a9-<strategy>-*` for the four runs.

The earlier “285 passed” and old coverage figures did not match these captured runs and have
been replaced. Ruff's last targeted result remains `.venv/bin/ruff check modules/mms/tests/spec`:
exit 0, `All checks passed!`.

## Oracle and failure reconciliation

### Invalid oracles corrected

- `TC-FR-001` is blocked by AFR-MMS-001's broad scope statement; it does not assert a student
  status `cycle` field.
- `TC-FR-052` exercises the Warden feedback view under AFR-MMS-046, not Warden access to
  individual bills.
- `TC-FR-110` remains blocked under AFR-MMS-095; it no longer tests Warden `billing_summary`.
- Menu deletion is allowed. The BR and UC tests update an existing 21-entry menu to 20 entries
  and expect the deletion to persist. The BR notification negative control is an unauthorized
  Student update attempt. The UC invalid-menu case uses unsupported meal value `brunch`, not a
  valid deletion.

### Pre-fix Student 1 implementation finding: role reassignment

Before Student 1 commit `99536a7`, these executed tests failed on a 409 while exercising the
specified reassignment success path:

- `TC-BR-005` and `TC-BR-006`: expected replacement Caretaker/Warden assignment; got 409.
- `TC-BR-009` and `TC-BR-010`: expected the mid-cycle replacement effective at the recorded
  time; got 409.
- `TC-UC-002`: expected the mid-cycle Caretaker reassignment and request handoff; got 409.

The frozen text is explicit:

- AFR-MMS-097: “A mid-cycle Caretaker or Warden reassignment shall take effect immediately in
  MMS from the recorded reassignment time.”
- BR-MMS-003: “MMS shall enforce exactly one active Mess Caretaker at a time.”
- MMS-UC-001 Main Success Scenario, step 5: “For a mid-cycle reassignment, MMS makes the change
  immediately effective from the recorded reassignment time and transfers pending
  Caretaker-owned request visibility/actionability to the newly assigned Caretaker.”
- MMS-UC-001 Alternative Flow A1: “If the requested assignment would violate the
  exactly-one-active-role constraint for its effective period, MMS prevents the conflicting
  assignment.”

A valid reassignment must take effect at its recorded time while preserving the one-active-role
constraint. The specifications do not prescribe an internal retirement/deactivation mechanism.
A1 permits refusal of a genuinely conflicting assignment; it does not cancel the explicit
mid-cycle reassignment success scenario. `TC-BR-011` also gets 403 when the newly assigned
Caretaker attempts to view a pending request, but its test does not assert the preceding role
POST succeeded, so treat that result as downstream of the reassignment blocker, not separate
evidence about request visibility.

### Post-fix verification (2026-11-24)

Student 1 commit `99536a7` retires the overlapping incumbent at the requested effective time,
preserves its historical row, and makes the replacement active. The incoming Caretaker's
pending-request visibility/actionability is covered by the implementation regression test.

- `.venv/bin/lint-imports`: exit 0; 244 files analyzed; all five contracts kept, zero broken.
  The BR, FR, and UC spec tests now seed directory fixtures through IAM and
  `modules.directory.contracts`; they no longer import `modules.directory.models`.
- Focused PostgreSQL command:
  `.venv/bin/pytest -q 'modules/mms/tests/spec/br/test_br_cases.py::test_frozen_br_case[TC-BR-005]' 'modules/mms/tests/spec/br/test_br_cases.py::test_frozen_br_case[TC-BR-006]' 'modules/mms/tests/spec/br/test_br_cases.py::test_frozen_br_case[TC-BR-009]' 'modules/mms/tests/spec/br/test_br_cases.py::test_frozen_br_case[TC-BR-010]' 'modules/mms/tests/spec/uc/test_uc_cases.py::test_frozen_uc_case[TC-UC-002]'`
- Actual result: exit 0, five selected tests passed (`..... [100%]`), zero failures or setup
  errors. The previously confirmed reassignment failure is resolved for these five cases.

This was a targeted verification only; no full independent suite was rerun.

### Failures not routed as Student 1 defects

- `TC-BR-003` has a design source for unavailable employee identity, while its executable handler
  attempts a role reassignment. Its 409 is a test/design mapping error.
- `TC-FR-004`, `TC-FR-011`, and `TC-FR-012` fail in a shared role-reassignment handler, but their
  design sources are respectively AFR-MMS-002 (initial Caretaker assignment), AFR-MMS-098
  (pending-request handoff), and AFR-MMS-099 (employee identity boundary). Those handlers do not
  exercise their stated FR cases; their failures are not implementation evidence.
- In the recorded pre-cleanup suite, `TC-UC-078` got 409 because the approval path required a
  special-food charge. The frozen specification does not define the charge source/value or who
  supplies it. The canonical UC design marks this case blocked with a null expected result; do
  not invent a value or route this policy gap as a Student 1 code fix.

### Focused post-review verification (2026-11-24)

After marking `TC-UC-078` blocked, only the affected UC case and the current FR vacation-summary
case were checked:

- Command: `.venv/bin/python -m pytest -q 'modules/mms/tests/spec/uc/test_uc_cases.py::test_frozen_uc_case[TC-UC-078]' 'modules/mms/tests/spec/fr/test_fr_cases.py::test_frozen_fr_case[TC-FR-085]'`
- Result: one passed (`TC-FR-085`), one skipped (`TC-UC-078`, unresolved charge policy).

No broad suite was rerun.

### Student 1 cleanup commit and charge-policy disposition

Commit `39f2b62` disables special-food approval until authoritative policy exists and displays
that limitation in the UI. This is a fail-closed technical disposition, not an institution
policy decision. The charge source, value, and rule remain blocked.

The first focused run before cleanup failed because the regression test read
`response.json()["code"]`; the platform nests the code at `response.json()["error"]["code"]`.
Commit `39f2b62` corrects that test assertion. The focused regression test
`.venv/bin/python -m pytest -q modules/mms/tests/test_implementation_defects.py::test_special_food_approval_fails_closed_without_authoritative_charge_policy`
now passes (exit 0). Pytest emitted a database-teardown warning that the test database did not
exist; the test itself passed. No Student 1 files were changed in this review.

### Joint ISS-MMS-014 interpretation

Student 1 agrees with Student 2 that the active Mess Caretaker records Served/Cancelled updates,
following the primary actor and main success scenario in MMS-UC-021. This resolves the actor
interpretation only; it is not institution policy. Cancellation billing remains unresolved
under ISS-MMS-015.

The reserved BR/FR/UC cases were updated to use that interpretation. They do not add a charge
amount or assert billing after cancellation. The combined ten-case invocation
(`TC-BR-054`, `TC-FR-091`–`093`, `TC-FR-097`–`099`, `TC-FR-101`–`102`, and `TC-UC-086`)
failed because `TC-FR-097`'s notification fixture omitted the directory identity. Therefore this
was not a passing ten-case run, and no aggregate pass is claimed. The record confirms a focused
rerun of `TC-FR-097` passed after the fixture correction; no successful rerun of the full
ten-case selection is evidenced. No broader suite was rerun.

## Handoff

**Student 2 implementation finding:** the mid-cycle reassignment blocker is resolved by commit
`99536a7` and verified by the five focused BR/UC cases above. No actionable Student 1 fix for
that finding remains.

**Final review gates:** The ISS-MMS-014 actor interpretation is jointly resolved as described
above; ISS-MMS-015 cancellation billing remains unresolved. No authoritative special-food
charge source/value/rule has been supplied, so approval remains blocked.

The original Student 1 builder's tool/model/provider is unavailable and is not inferred. The
available record says the Student 1 finalization and Student 2 review used the same provider/model;
provider separation is therefore not established. The instructor ruling request for missing
original-provider and chronology/baseline/scorecard evidence is documented but has not been
transmitted. No waiver or instructor decision is claimed.

The concise instructor email is prepared, not sent, at
[`docs/16-mms/instructor-email-draft.md`](../instructor-email-draft.md).

The canonical design files under `docs/16-mms/spec-tests/` are untracked. Commit `148181b`
contains the original A9 designs with implementation, and no 10/10 baseline scorecard is
evidenced; design-first chronology cannot be recreated from current artifacts. No waiver is
recorded or relied upon.

**Final A9 verdict: Rejected pending external policy/instructor decisions and missing evidence.**
The reassignment and agreed fulfillment-actor interpretation are technically supported by the
recorded focused passing checks. The ten-case combined run failed; only the separately recorded
`TC-FR-097` rerun is claimed as passing from that group. The charge-policy and
assignment-evidence gates remain open. No broad-suite completion or approval is claimed here.
