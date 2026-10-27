# Assignment 6B ELM review and improvement record

Prepared on 27 October 2026 using Codex. This is a factual retrospective of code review, repairs and executed checks, not a verbatim conversation or a local-model experiment.

## Baseline and preservation

Phase 2 starts from the original PR #70 branch `module/elm-assignment6`, commit `86d869dc6b2948ab33da03cfa8f9182e4b17e27b`. That commit remains unchanged and is also retained locally as `archive/elm-phase1-20261027`. Improvements are on `module/elm-assignment6b`, with `main` as the intended PR target. The original implementation has not been replaced by another pair's code.

Both the baseline and this improvement session used Codex. No local-model trial is claimed. This differs from the assignment's expected local-model provenance and requires appropriate disclosure to the instructor.

## Review inputs and method

Reviewed the locally supplied PS v1.4, FR v1.5, UC/BR v1.4, WF v1.6 and traceability v1.5 package, including all 32 coherent requirement summaries. Inspected the Django models, rules, services, selectors, authorization, API serializers, React screens and Fusion registration. Added focused regression tests before repairing the initial reproduced defects, then expanded boundary and integration coverage.

The initial runnable regression set produced **10 failures and 28 passes**. An earlier attempt could not initialize the SQLite test database because of an unrelated historical placement index migration. The opt-in SQLite test settings synchronize placement's current models while still applying ELM's actual migrations. PostgreSQL CI settings remain unchanged.

## Problems and changes

| Problem | Change and verification |
| --- | --- |
| Existing employee hierarchy edits failed DRF uniqueness validation | Aligned serializer validation with the existing service upsert; API edit regression passes. |
| Configuration-only administrators could not load employee choices | Corrected endpoint permission composition; retained module and capability checks. Record-maintenance users may also load the picker. |
| My Leave filtered ownership after pagination | Added server-side `scope=mine` filtering before pagination and connected the client to it. |
| Absolute cursor links produced malformed API requests | Normalize pagination links to the ELM namespace on the configured HTTP client; preserve cursor query strings; added navigation to tasks, ledger and notifications. |
| An approved extension continued blocking dates released by early resumption | Original leave's effective interval now represents approved extensions; only pending extension rows independently reserve dates. |
| Resumption used a historical authority after hierarchy changes | Resolve resumption's reviewer from current configured hierarchy. |
| Closed account years accepted subsequent ledger writes | Reject new postings against processed accounts while retaining replay-safe existing event keys. |
| Offline higher-sanction leave could name the Unit Head as final authority | Require the configured final authority, rather than any intermediate route member. |
| Partial policy changes raised a missing-key exception | Merge submitted values with existing/default policy, validate thresholds and preserve omitted settings. |
| Incomplete responsibility-escalation configuration could be saved | Require an escalation assignee and designation for reassignment. |
| Invalid domain-level half-day tokens silently consumed half a day | Explicitly validate full/first/second portions. |
| Inactive directory identities could be accepted as employees | Expose active status in the directory DTO and reject inactive identities in ELM. |
| A zero directory cache TTL could still treat an equal-timestamp row as fresh | Make zero TTL explicitly bypass the freshness cache; added deterministic directory regressions. |
| Director configuration could use the ordinary hierarchy | Enforce the Director-specific self-sanction route. |
| Administrative forms could overwrite current settings and category routes | Hydrate saved policy/hierarchy and preserve existing per-category routes and escalation settings when only employee metadata changes. |
| Offline entry and reference correction had no dedicated frontend | Added permission-scoped Leave Records page, sanction-evidence entry, reference correction, record/history display and pagination. |
| Reference evidence could be cleared through a direct service call | Reject blank reference corrections; preserve sanction and balance separation. |
| Generated code failed repository lint checks | Corrected imports, formatting and flagged expressions; whole-repository Ruff check passes. |

## Specification coverage reviewed

The table identifies focused evidence, not exhaustive certification of every atomic requirement.

| Requirements | Focused evidence |
| --- | --- |
| CFR-EL-001 | API and service authorization, ownership, active role, module grant and inactive identity tests. Live IAM remains unverified. |
| CFR-EL-002–003 | Application input validation, eligibility, dates, station details, balances and overlap checks. |
| CFR-EL-004–009 | Half-day CL, RH cap, COL evidence, staff EL/COL carry-forward, faculty VL provider gating and fractional VL conversion. Vacation provider tests use a stub. |
| CFR-EL-010 | Continuous weekend/holiday counting and separate yearly charges. |
| CFR-EL-011–012 | Invalid substitutes, decline/replacement/accept gate and withdrawal. |
| CFR-EL-013–015 | Unit Head decisions, higher-sanction progression, optional Establishment processing and Director self-sanction. |
| CFR-EL-016–018 | Decision/task notifications, immutable submitted details and immediate withdrawal at every non-Director pending stage. |
| CFR-EL-019–021 | Cancellation boundaries/refund, incremental extension, rejected/withdrawn extension preservation and normal/early/late resumption. |
| CFR-EL-022–023 | Own history, cursor normalization, balances/ledger and protected application export. |
| CFR-EL-024–025 | Configuration upsert, saved-setting preservation and published-calendar replacement semantics. |
| CFR-EL-026–027 | Offline synchronization without an approval task, final authority validation, evidence and narrow reference correction. |
| CFR-EL-028 | Staff carry-forward, faculty fractional conversion, annual lapse, replay prevention and exception reporting. |
| CFR-EL-029–032 | Threshold validation, assignment notification, pending-only reminder/escalation and replay prevention. |

## Executed verification

| Check | Final recorded result |
| --- | --- |
| Full backend suite using opt-in SQLite settings | **444 passed**, including 62 ELM tests and two new directory regressions |
| Full frontend Vitest suite | **48 passed**, including 13 new ELM tests |
| Production frontend build | Passed; existing shared bundle exceeds Vite's 500 kB advisory threshold |
| Whole-repository Ruff | All checks passed |
| Django system checks | Zero issues |
| Model/migration drift | No changes detected |
| Module import boundaries | Five contracts kept, zero broken |
| Cross-module foreign keys | None |
| Plural contract getters | Passed |
| Navigation/client route parity | Passed |
| Permission manifest parity | Passed after regeneration |
| Strict OpenAPI generation and committed schema comparison | Passed and matched |

Reproduce backend verification with:

```powershell
.\.venv\Scripts\python.exe -m pytest --ds=config.settings.test_sqlite
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe manage.py check --settings=config.settings.test_sqlite
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.settings.test_sqlite
.\.venv\Scripts\lint-imports.exe
.\.venv\Scripts\python.exe ops/checks/no_cross_module_fk.py
.\.venv\Scripts\python.exe ops/checks/contracts_are_plural.py
.\.venv\Scripts\python.exe ops/checks/nav_matches_routes.py
.\.venv\Scripts\python.exe manage.py permission_manifest --check
.\.venv\Scripts\python.exe manage.py spectacular --fail-on-warn --file openapi-check.yaml
```

Run `npm test`, `npm run typecheck` and `npm run build` from `client/`. Standard PostgreSQL verification remains `python -m pytest --ds=config.settings.test` with the supplied database configured.

## Remaining deployment gates

- PostgreSQL and live IAM were unavailable locally. SQLite tests do not verify PostgreSQL migration history, row locks, concurrent decisions or database-specific behavior.
- A local HTTP smoke attempt was blocked by the execution environment's socket permissions. Authenticated API tests exercised the Django request stack with stubbed IAM; a browser-to-live-IAM deployment was not demonstrated.
- Real Academic Calendar vacation periods and an attendance outbox consumer are external dependencies. Their deployed delivery has not been verified; VL fails closed without its provider.
- Functional tests are focused rather than an exhaustive proof of all 128 atomic requirements, every hierarchy change, every role combination or every concurrent schedule.
- Re-publish the generated IAM manifest and assign appropriate designations for the new Leave Records navigation item.

This is a tested improvement over the preserved baseline, not a certification of production readiness. No PR was opened during preparation of this review draft.
