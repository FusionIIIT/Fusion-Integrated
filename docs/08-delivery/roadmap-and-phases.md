---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
note: >
  Durations are estimates for a small team. The GATES are not estimates — a phase does not close until its
  gate holds, regardless of the calendar.
---

# Roadmap & Phases

Nine phases. Each is independently shippable, gated, and reversible. **Nothing after Phase 0 touches production
without a documented rollback.**

Exit criteria per phase: [definition-of-done.md](definition-of-done.md). Risks:
[risk-register.md](risk-register.md).

---

## Overview

| # | Phase | Est. | Gate | Touches prod? |
|---|---|---|---|---|
| 0 | Docs + legacy hardening | 2–3 wk | `check --deploy` clean; contract tests green | ✔ (settings + indexes only) |
| 1 | Skeletons | 2 wk | CI green; visual baselines match `/sysadmin/`; **a restore performed for real** | ✘ |
| 2 | IAM in shadow mode | 3 wk | **7 consecutive days of empty module-access diffs** | deployed, nothing depends on it |
| 3 | Dual auth ⚠️ | 2 wk | pilot works; `/api/auth/me` byte-identical | ✔ behind flags |
| 4 | IAM becomes the writer | 2 wk | role change visible in legacy < 30 s; 0 drift for 7 days | ✔ behind a flag |
| 5 | Placement vertical slice | 5–6 wk | six sub-gates, 5a is the correctness gate | ✔ behind module grants |
| 6 | HR + Leave | 4–5 wk | same module recipe | ✔ behind module grants |
| 7 | Absorb the sysadmin console | 3 wk | `/sysadmin/` and `/app/sysops/` both work for one cycle | ✔ |
| 8 | Academic absorption | — | **plan only, out of scope now** | ✘ |

Phase 3 is the risky one. It is entirely feature-flagged, and **existing DRF tokens keep working throughout**, so
a rollback needs no re-login.

---

## Phase 0 — Docs + legacy hardening *(2–3 weeks)*

**Documentation:** this whole set — `docs/00` through `docs/08`, including the 13 ADRs. Written before code, so
the design is arguable while it is still cheap to change.

**Legacy hardening**, in parallel. Independently valuable, and a **hard prerequisite** for cookie auth:

| Item | Why |
|---|---|
| `DEBUG = False` in `production.py` | **The blocker.** A 500 renders `request.META` including the auth cookie. |
| Secrets, `ALLOWED_HOSTS`, CORS to env | committed `SECRET_KEY`, DB password (in 4 files), OAuth secret |
| `CACHES` → Redis; `SESSION_ENGINE` → cache; drop `SESSION_SAVE_EVERY_REQUEST` | removes a DB write per request |
| Three `CREATE INDEX CONCURRENTLY` | fixes a sequential scan **per designation per login** |
| Widen `ExtraInfo.last_selected_role` 20 → 64 | hazard H3 |
| `applications/globals/tests/test_auth_contract.py` | the **only** safety net for the migration |

**Gate:** `manage.py check --deploy --fail-level WARNING` exits 0 · characterization suite green in CI · login
p95 recorded before and after · production functionally unchanged.

**Rollback:** `git revert` + `systemctl restart fusion`.

> Why this is first: there is **no test suite anywhere** in the live systems (all 31 `tests.py` are 3-line
> stubs) and CI is a welcome-bot. The characterization suite and the Phase 2 diff gate are the entire safety net
> for everything that follows.

---

## Phase 1 — Skeletons *(2 weeks)*

`Fusion-Integrated`: both service skeletons, `core/`, `packages/`, `docker-compose`, `/healthz` + `/readyz`,
OpenAPI emitting, `ops/db/roles.sql`, CI green with every gate wired.

`fusion-frontend`: monorepo, `packages/ui` **extracted verbatim** from the sysadmin client, shell rendering the
layout from a hardcoded nav.

**Gate:** CI green on both · **Playwright visual baselines match the live `/sysadmin/` layout pixel-for-pixel**
(this is how the extraction is proved, not asserted) · **a backup restored for real on a scratch host, with the
elapsed time written into
[restore-from-backup.md](../07-ops/runbooks/restore-from-backup.md)**.

Nothing deployed to production.

> The restore drill is a Phase 1 deliverable rather than a Phase 8 aspiration deliberately. Everything on one VM
> is the largest accepted risk in the design ([risk-register.md](risk-register.md) R7), and an untested restore
> is not a mitigation.

---

## Phase 2 — IAM in shadow mode *(3 weeks)*

Build all IAM tables. Import ~3,277 users with **password hashes copied verbatim** (`algo=pbkdf2_sha256`,
upgraded to Argon2id on each user's next login — nobody resets a password). Map
`Designation → rbac_role`, `HoldsDesignation → rbac_user_role`,
`ModuleAccess → registry_module + grants`.

Reconcile the **H2 column drift** into real monolith migrations, so `makemigrations` stops wanting to drop
production columns added by raw DDL.

Deploy `fusion-iam` with **nothing depending on it**.

**Gate:** `iam_diff_module_access --days 7` reports **zero discrepancies for 7 consecutive days**, across all
users. Not "mostly empty".

The sample must include: a user with 3+ designations · a user with **zero** `HoldsDesignation` rows (the legacy
middleware's `designation[0]` → `IndexError` case) · a user whose designation has no `ModuleAccess` row (the
`access_rights` → `UnboundLocalError` case) · a designation name over 20 characters · an officiating holder.

**Rollback:** `systemctl stop fusion-iam`. Nothing else is affected.

---

## Phase 3 — Dual auth *(2 weeks)* ⚠️

**Order matters — validators before issuer:**

```
1. Deploy IamJWTAuthentication to legacy + sysadmin, flags OFF     (no behaviour change)
2. Deploy the shell at /app/, IAM_LOGIN_ENABLED off                (login → legacy)
3. Turn ON IAM_JWT_AUTH_ENABLED in legacy + sysadmin               (they accept both)
4. Turn ON IAM_LOGIN_ENABLED for the pilot group only              (IAM starts issuing)
```

Never reverse 3 and 4. Issuing tokens nothing can validate has no clean rollback point.

Pilot: placement staff (~5) + one batch (~60). Small enough to phone everyone.

**Gate:** pilot users log in at `/app/`, deep-link into the legacy app, and `test_iam_me_matches_legacy_me`
passes against staging · `iam_refresh_reuse_detected_total` ≈ 0 (non-zero means the client's single-flight
refresh is broken, not an attack).

**Rollback:** unset `IAM_JWT_AUTH_ENABLED` + restart, ~30 s. Existing DRF tokens were never invalidated, so
**nobody has to log in again**.

---

## Phase 4 — IAM becomes the writer *(2 weeks)*

**Blocked on the H1 decision** — see [risk-register.md](risk-register.md) R-H1. Do not start without a written
answer from the academic office on multi-holder designations.

Role and module administration moves into the shell. The console's `update_user_roles`,
`modify_moduleaccess` and `add_designation` return `410 Gone`. IAM's projector becomes the **sole** writer of
`globals_designation`, `globals_holdsdesignation`, `globals_moduleaccess`. Reconciler → `enforce`.

**Gate:** a role change in the shell appears in legacy `/api/auth/me` within 30 s ·
`reconcile_erp_projection --mode=report` shows **0 drift for 7 consecutive days** before `enforce` is enabled.

**Rollback:** `IAM_IS_ROLE_WRITER=off`. The projector pauses; events queue in `outbox_event` and drain on
re-enable — idempotent, nothing lost. Re-enable the console's write endpoints.

**Comms:** the placement and academic offices must be told that secondary and scoped role holders **will not
appear in the legacy sidebar** (H1). Without that note, a known limitation arrives as a bug report during a
placement season.

---

## Phase 5 — Placement vertical slice *(5–6 weeks)*

Six sub-phases, each shippable. Every one deploys behind the module grant — **a module granted to nobody is
invisible and unroutable**, so partial features are safe in production.

| Sub | Contents | Gate |
|---|---|---|
| **5a** | `modules/academics` ACL · `ResultDeclaration` / `ResultSnapshot` / `StudentAcademicStanding` · chunked ingest · the two legacy changes (outbox row + internal snapshot endpoint) | **Declared CPI exactly equals `POST /examination/api/check_result/` for a 200-student sample**, including an `S`, an `X`/`CD`, an **`F`**, a backlog retake, a `course_replacement`, and a Summer semester. Plus: replay is a no-op, out-of-order delivery does not regress standing, and a write to `academics_resultsnapshot` raises `InsufficientPrivilege`. |
| **5b** | Company · tier · `PlacementYear` · `PlacementPolicy` · posting CRUD + FSM + publish | Staff create and publish; **students see nothing** |
| **5c** | Eligibility engine · registration · student browse + apply · application FSM to `SUBMITTED` | An ineligible student sees a **precise per-rule failure list** ("CPI 6.80 — 7.00 required"), and a student with **no declared standing** is ineligible rather than treated as CPI 0.0 |
| **5d** | Rounds · shortlisting · participation · bulk actions | A coordinator runs a full drive end to end; bulk actions are partially successful with per-item outcomes |
| **5e** | Offers · `can_accept` policy · `PlacementRecord` · auto-withdraw | **A second concurrent accept is denied** — Playwright *and* a real-threads DB concurrency test; the partial unique index backstops a bypassed service |
| **5f** | Statistics snapshots · exports · dashboards | Public stats serves **from snapshots only** (zero queries against transactional tables), p95 < 200 ms; PII export writes an audit row with the filter **and** row count |

5a is the phase whose gate cannot be negotiated. Everything downstream depends on the declared-CPI contract
being exactly right ([academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md)).

---

## Phase 6 — HR + Leave *(4–5 weeks)*

Same eight-step module recipe. Parallelizable after 5c, since the platform patterns are then settled.

Leave consumes `hr.contracts.get_employments(user_ids)`. Neither reads the other's tables.

**Fresh domain design** — the deprecated `establishment` (19 models), `hr2` (12) and `leave` (14) apps are not
ported ([NG2](../00-overview/vision-and-scope.md#non-goals)).

---

## Phase 7 — Absorb the sysadmin console *(3 weeks)*

Its pages move into the shell as the `sysops` module; its backend moves to `services/sysops/`. Operators stop
being a separate account pool — they become IAM users with the `sysops` role.

`/sysadmin/` keeps serving for **one full release cycle**, then redirects to `/app/sysops/`.

**Rollback:** the old mount is still there for a cycle.

---

## Phase 8 — Academic absorption

**Out of scope for this programme.** ~199k lines of Django templates across the five live academic apps. Planned
here only so the shape is known: absorb module by module behind the same module-grant mechanism, with
`Fusion-client` linked from the sidebar until each module moves.

---

## Two waits that must not be compressed

```
Phase 4 stable for 30 days
  └─► LEGACY_LOGIN_ENABLED=0        # /api/auth/login/ returns 410
        └─► stable for a further 30 days
              └─► scramble auth_user.password to '!'
```

Scrambling the password column is the **only irreversible step in the entire migration**. Until it happens, a
full rollback to legacy authentication is available at any moment. Before it: a verified backup, restored and
checked on a scratch host, retained indefinitely.

---

## Critical path

```
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 7
                            │                        │
                            └──► Phase 5 ────────────┴──► Phase 6
                                 (5a is the correctness gate)
```

Phase 5 can start once IAM authenticates the shell (end of Phase 3). It does **not** wait for Phase 4 — placement
does not depend on the ERP role projection.

**H1 blocks Phase 4 only.** Everything else proceeds while that decision is pending, which is why it is raised in
Phase 0 rather than discovered in Phase 4.

---

## What could reasonably change

| Trigger | Change |
|---|---|
| The Phase 2 diff never reaches zero | Do not proceed. Investigate — a persistent diff means the legacy semantics are not yet understood. |
| H1 option A chosen (drop the legacy constraint) | Phase 4 gains a migration on a live table plus an audit of code assuming uniqueness; +1 week |
| 5a's CPI comparison disagrees | **Stop.** Investigate before building anything on top. This gate exists precisely to be respected. |
| A placement season starts mid-Phase 5 | Freeze at the last completed sub-phase. A half-built drive tool during a live season is worse than none. |
| The team grows | Phase 6 parallelizes cleanly; Phases 2–4 do not — they are sequential by nature. |
