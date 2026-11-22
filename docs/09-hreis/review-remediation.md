# Independent review remediation

Round 1 reviewed committed checkout `e93cc164218353145556f591d672d5f1c78c8ef5`
in a separate clone. It returned **not yet**, with scores below. Automated
passing gates did not supply the required formal approvals or complete test categories.

| Dimension | R1 score |
|---|---:|
| Spec fidelity | 3 |
| Architecture | 1 |
| Code quality | 7 |
| Security | 4 |
| Backend tests | 0 |
| End-to-end behaviour | 1 |
| Frontend | 3 |
| Operability and docs | 2 |
| Hygiene | 9 |

The full unedited report is preserved separately at
`D:\HR(EIS)\lab 9\evidence\independent-review-r1.txt`.
SHA-256: `70B6CBACB20AD4677E5C1C7E9A48CB81E43BC565AE3AC8BBBE512F47BB43EAF3`.
The entries below describe candidate changes; they are not a replacement review score.

| Finding | Candidate disposition / evidence |
|---|---|
| R1-01 | **OPEN.** Required written Student 2 approvals and institutional rulings have not been supplied. Owner-directed continuation is documented as a deviation. |
| R1-02 | **OPEN.** Protected shared authentication/browser-harness changes remain visible in the branch diff. The owner authorized technical fixes; that does not remove the rubric's protected-file restriction or create a platform-baseline exception. |
| R1-03 | Employee-record/period database uniqueness, owner-row locking, structured conflict and real-thread/direct-SQL regressions. |
| R1-04 | Policy integer bounds at serializer and service; explicit identifier/revision bounds and reference-length validation before storage. |
| R1-05 | Independent Create and Edit permission checks; HTTP-boundary tests for update-only and read-only actors. |
| R1-06 | **PARTIAL / OPEN.** 188 directly cited live IDs; actual directory-contract identity-refresh/current-grant regression for BR-HR-028 and HR-AFR-092. Five IDs remain uncited and six broader external/source obligations unresolved. |
| R1-07 | Both claim families can record processing with unavailable external status, then append a later report. HTTP and browser alternatives use null external fields. |
| R1-08 | Notification read/audit writes moved to a transactional service; recipient scope and repeated-read semantics retained. |
| R1-09 | Platform PrincipalScopedThrottle reused; hreis_write registered in platform rate settings. |
| R1-10 | All 26 endpoint operations separately tested without the module grant and without the operation permission. |
| R1-11 | All seven list endpoints have populated 2/20-row constant-count assertions and maximum budgets. |
| R1-12 | Both real Celery entrypoints tested twice sequentially and twice concurrently; actual merged beat schedule and task routes asserted. |
| R1-13 | All builder actor factories validate their supplied permission codes against the real registry. Misspelled session and service actors fail immediately. |
| R1-14 | All twelve registered designations, all 21 live use cases and keyboard-only leave submission; timestamped browser observations are matched to actual runserver lines in browser-walkthrough.md. |
| R1-15 | Every protected deep link is opened by a module-granted synthetic employee with its permissions removed; controls remain absent. Original IAM permissions are restored and the test session refreshed. |
| R1-16 | HTTP journeys include policy/record/credit/audit maintenance, both Accountant alternatives and observable event-triggered reminder/deadline/read outcomes. |
| R1-17 | Page tests use actual module hooks and QueryClient with only the shared HTTP boundary substituted. Loading/empty/error states, hidden controls, writes, invalidation and server refusal messages are exercised. |
| R1-18 | Wire fields, enums and optionality are generated from actual OpenAPI. Cursor pages have results/next/previous and no fabricated count property. Drift fails a backend test. |
| R1-19 | Blueprint reconciled to actual entities, services, endpoints, route permissions, provisional mapping and unresolved decisions. |
| R1-20 | hreis-reference.md includes 193 live-ID source links. Generation fails unresolved files/symbols and stale committed output. Open external requirements are labeled as boundaries. |
| R1-21 | Extended source docstrings/comments shortened; standalone fixture suppression states its initialization reason on the same line. |
| R1-22 | Policy validation, request evidence, approval routes, financial processing, appraisal archive and notification handoff split into focused helpers while preserving atomic public services. |
| R1-23 | Business refusals now direct the user to correct fields, refresh the scoped view or contact HR. |
| R1-24 | Hooks added for notification read, own balances, record detail and compliance detail. |
| R1-25 | Unmerged module consolidated to one initial migration, retaining every immutable trigger and new constraint. Prior chain and database backup preserved outside Git; rollback/reapply uses disposable databases. |
| R1-26 | Every operation has synthetic response examples and request examples where applicable; schema-level regression checks all 26 operations. |
| R1-27 | Authorship wording removed from historical quality-report checkpoints; independent status remains factual. |

The protected-file and approval findings are not waived. No external finance
service, file-storage provider, signature or undefined LTC return transition is invented.
Fresh committed-clone review results belong in the latest quality-report checkpoint.

## R2 exploratory probe closure — Student 1 technical patch (2026-11-22)

The follow-up review's four concrete probe defects were fixed and covered by
`modules/hreis/tests/test_review_probe_regressions.py`:

| R2 probe | Code change and verified behavior |
|---|---|
| Reuse of an expired family/version | `services/policies.py` refuses a duplicate immutable family/version under the serialized family lock, returning a controlled HTTP 409 rather than a database HTTP 500 |
| Unbounded reminder-hours value | `services/policies.py` refuses unrepresentable policy delays; `services/notifications.py` compares elapsed seconds so even a legacy bad value cannot overflow the scheduler |
| Inactive IAM appraisal reviewer | `services/appraisals.py` refuses an inactive directory user; existing reviewer test fixtures now represent active users explicitly |
| Reminder leaking across acting roles | `selectors/scoping.py` restricts request-linked notices to the owner or current assigned role. A Registrar with notification-only permission may view its generic assigned reminder without gaining access to the underlying private form; acting as staff cannot view that other employee's reminder. `mark_notification_read` row-locks only the notification table to avoid nullable-join PostgreSQL errors |

The isolated browser runner's root-created evidence directory now permits its
synthetic IAM fixture user to write and restore the temporary permission snapshot.
Its test script remains Unix-LF and its cleanup successfully revoked the temporary
IAM service token and dropped the disposable database.

**Latest verification:** `make check` passed (all repository pytest, architecture,
lint, migrations, manifest and OpenAPI gates); `make check-client` passed (67/67
Vitest, TypeScript and production build); combined module coverage **92.25%**
(minimum 90%) and domain coverage **95.79%** (minimum 95%); real Chromium **58/58**
including 49 HR-EIS and 9 shared cases; production-settings deployment check
passed with zero unsilenced issues. The original independent R1 verdict is not
retroactively changed, and no new formal independent 10/10 verdict is claimed.

Student 2 approval, shared-file exception rulings, external provider integration,
institutional policy values and the source's unspecified LTC-return outcome remain
separate pending decisions. None has been signed or faked.
