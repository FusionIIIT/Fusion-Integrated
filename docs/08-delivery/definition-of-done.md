---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Definition of Done

Three levels: a **pull request**, a **module**, a **phase**. Each is a gate, not a guideline — "done" means the
checklist passed, not that the work feels finished.

---

## A pull request

- [ ] CI green — every gate in [testing-strategy.md](../06-crosscutting/testing-strategy.md#ci-gates)
- [ ] New reads go through a selector; new writes through a service; `api/` touches neither model directly
- [ ] `domain/` has no Django import
- [ ] No cross-module FK; no import of another module's internals
- [ ] Ownership/scope filtering in the selector, so a foreign id yields **404** not 403
- [ ] Explicit `permission_classes` on every new endpoint
- [ ] Indexes named, in `Meta.indexes`, matching the actual query's `WHERE` + `ORDER BY`
- [ ] New tables added to `ops/db/roles.sql`
- [ ] `makemigrations --check` clean; `django-migration-linter` clean; no destructive migration shipped with the
      code that stops using the column
- [ ] OpenAPI committed and diff-clean; every endpoint has an `@extend_schema` example
- [ ] Query-count budget test on any new list endpoint, **constant in row count**
- [ ] Error paths tested: 401, 403/404, 409, 422, 429
- [ ] Any new event is in [event-catalog.md](../01-architecture/event-catalog.md) with a pydantic model and a
      replay test
- [ ] Docs updated in the **same** PR if behaviour changed
- [ ] No secret, no PII in a log line, no `except Exception: pass`

**Reviewer's five questions:** Is the boundary in the right place? Can a user see someone else's data? What
happens on the second click? What happens if this event arrives twice? Does the failure message tell the user
what to do?

---

## A module

Everything above, plus:

- [ ] `domain/` at **90%** coverage; services and selectors 85%; API 80%
- [ ] `contracts.py` exists, is read-only, and **plural by signature**
- [ ] `permissions.py` and `registry.py` seeded; permission catalog regenerated and diff-clean
- [ ] Frontend `manifest.code` === `registry_module.code`; all four parity checks pass
- [ ] Every table has an explicit `empty` state; every page an `ErrorState` path
- [ ] `size-limit`: module chunk ≤ 150 kB gz
- [ ] `axe-core` clean; keyboard-navigable
- [ ] One Playwright happy path
- [ ] A load test if the module has a predictable peak (a deadline, a declaration)
- [ ] `registry_module.status` flipped to `active` in the **final** commit

---

## Phase 0 — Docs + legacy hardening

**Documentation**

- [ ] Every file listed in [README.md](../README.md) exists and is non-placeholder
- [ ] `docs/README.md` gives a reading order per role
- [ ] Mermaid diagrams render in CI; internal links resolve (`markdown-link-check`)
- [ ] 13 ADRs written, each with Context / Decision / Consequences / Alternatives
- [ ] **A developer who has never seen the repo follows `module-authoring-guide.md` and scaffolds a module
      unaided.** Test this on a real person; if they ask a question, the guide has a gap.

**Legacy hardening**

- [ ] `cd Fusion/FusionIIIT && python manage.py check --deploy --fail-level WARNING` exits **0**
- [ ] A forced 500 in production renders **no traceback page**
- [ ] No secret in the repo (`gitleaks` clean); rotated OAuth + DB credentials
- [ ] `CACHES` → Redis; sessions in cache; `SESSION_SAVE_EVERY_REQUEST` gone
- [ ] Three `CREATE INDEX CONCURRENTLY` applied
- [ ] `ExtraInfo.last_selected_role` widened to 64
- [ ] `pytest applications/globals/tests/test_auth_contract.py` green, wired into CI
- [ ] Login p95 before/after recorded in
      [performance-and-capacity.md](../06-crosscutting/performance-and-capacity.md)
- [ ] Production functionally unchanged — verified by a manual pass over the five live academic apps

---

## Phase 1 — Skeletons

- [ ] `docker compose up` → postgres, 2× redis, iam, platform all healthy
- [ ] `/healthz` and `/readyz` correct on both services; `/healthz` still 200 with the DB stopped
- [ ] Startup assertions fire: an integration test boots each service against a correctly **and** an
      incorrectly configured role, expecting a clean start and a hard failure
- [ ] CI green on both repos, every gate wired (not stubbed)
- [ ] `pnpm turbo lint typecheck test build` green
- [ ] **Playwright visual baselines match the live `/sysadmin/` layout at 375/768/1440**, captured inside the
      pinned Docker image
- [ ] `ops/db/roles.sql` applied; tests run as `platform_app`, and the immutability tests pass — proving grants
      are actually in force
- [ ] **A backup restored for real on a scratch host, with measured timings written into
      [restore-from-backup.md](../07-ops/runbooks/restore-from-backup.md) §7**

---

## Phase 2 — IAM shadow mode

- [ ] ~3,277 users imported; **password hashes copied verbatim**, no resets
- [ ] An imported PBKDF2 hash logs in and is Argon2id afterwards
- [ ] Designations, holds and module access mapped; H2 column drift reconciled into real migrations
- [ ] **`iam_diff_module_access --days 7` reports zero discrepancies for 7 consecutive days**
- [ ] The sample includes: 3+ designations · **zero** `HoldsDesignation` rows · a designation with no
      `ModuleAccess` row · a name over 20 chars · an officiating holder
- [ ] Nothing depends on IAM; stopping it changes nothing observable

---

## Phase 3 — Dual auth

- [ ] Deployed in order: validators → shell → `IAM_JWT_AUTH_ENABLED` → `IAM_LOGIN_ENABLED`
- [ ] `test_iam_me_matches_legacy_me` passes against staging
- [ ] Pilot users: log in at `/app/` · sidebar shows exactly the granted modules · deep-link into legacy works ·
      role switch propagates within 30 s · logout kills both · two tabs with different roles do not interfere ·
      30-minute idle logout
- [ ] `document.cookie` exposes `fusion_csrf` only — **not** `fusion_at` or `fusion_rt`
- [ ] `fusion_rt` absent from a non-refresh request's headers
- [ ] Ten parallel requests on an expired token → **exactly one** refresh call
- [ ] Legacy DRF tokens still work
- [ ] `iam_refresh_reuse_detected_total` ≈ 0 over 48 h
- [ ] **Rollback rehearsed**: flag off → restart → users continue with no re-login

---

## Phase 4 — IAM becomes the writer

- [ ] **The H1 decision is written down and approved by the academic office**
- [ ] `reconcile_erp_projection --mode=report` → 0 drift for 7 consecutive days *before* `enforce`
- [ ] A role change in the shell appears in legacy `/api/auth/me` within 30 s
- [ ] Projecting a second holder produces an `IntentionalProjectionGap`, **not** an `IntegrityError`
- [ ] The console's write endpoints return `410 Gone`; its UI points at the shell
- [ ] The projector role cannot write `academic_information_student` (raises `InsufficientPrivilege`)
- [ ] `IAM_IS_ROLE_WRITER=off` pauses cleanly — no data loss, no event loss
- [ ] The placement and academic offices have been told about the H1 sidebar limitation

---

## Phase 5 — Placement

### 5a — the correctness gate

- [ ] For **200 students** of a declared batch, `ResultSnapshot.{cpi, spi, earned_credits}` **exactly equals**
      `POST /examination/api/check_result/`
- [ ] The sample includes: an **`S`** grade · an **`X`** or `CD` · an **`F`** · a backlog retake · a
      `course_replacement`/swayam substitution · a **Summer** semester
- [ ] `(4, "Summer Semester")` beats `(4, "Even Semester")` via `declared_seq`
- [ ] Replay: same event twice → snapshots unchanged, `standing_version` unchanged
- [ ] Out-of-order: Sem 5 then Sem 3 → standing stays on Sem 5
- [ ] `UPDATE academics_resultsnapshot` raises `InsufficientPrivilege`
- [ ] A student excluded from a `per_student_selection` allow-list gets **no** snapshot
- [ ] `announced = False` and `semester_type IS NULL` announcements are not ingested
- [ ] Retraction falls back to the previous non-retracted declaration; in-flight applications are **flagged, not
      rejected**
- [ ] Load: a 300-student declaration keeps the ERP's p95 within 20% of baseline

### 5b–5f

- [ ] **5b** staff publish; students see nothing; a published posting's rule cannot be edited (service **and**
      DB constraint)
- [ ] **5c** an ineligible student sees a per-rule failure list; **no declared standing ⇒ ineligible, not CPI
      0.0**; a provisional-but-not-declared result does not confer eligibility
- [ ] **5d** a full drive runs end to end; bulk actions are partially successful with per-item outcomes and
      cannot bypass the state machine
- [ ] **5e** two concurrent accepts → exactly one succeeds (Playwright **and** a real-threads DB test); a
      directly-inserted second active record raises `IntegrityError`; tier immutability holds; every attempt
      persists its `policy_decision`
- [ ] **5f** the public stats page issues **zero** queries against `placement_application`/`placement_offer`,
      p95 < 200 ms; a `placed < 5` cell suppresses CTC; a PII export writes an audit row with **the filter and
      the row count** and requires step-up
- [ ] All six k6 scenarios pass; results committed to
      [performance-and-capacity.md](../06-crosscutting/performance-and-capacity.md#committed-results)

---

## Phase 6 — HR + Leave

- [ ] Both modules meet the module DoD
- [ ] Leave reads HR only via `contracts`; no shared tables, no FK
- [ ] Approval chains audited; balance adjustments are `is_dangerous`

---

## Phase 7 — Absorb the sysadmin

- [ ] Every routed console page exists in the shell's `sysops` module (the three unrouted `ArchivingPages` are
      **not** carried over — they are dead code)
- [ ] Console operators migrated to IAM users with the `sysops` role; the separate account pool is gone
- [ ] `sysops.backup.restore`, `archive.manage`, `batch.import` all `is_dangerous` with step-up
- [ ] Both `/sysadmin/` and `/app/sysops/` work for one full release cycle before the redirect
- [ ] The console's existing `test_backup_restore.py` suite is carried over and still passes

---

## Not done

Some things read as done and are not:

| Looks done | Actually needs |
|---|---|
| "Tests pass" | tests that run as `platform_app`, with query budgets and error paths |
| "It works locally" | a `--frozen` install on a clean checkout |
| "Migration applied" | timed on staging, and the previous release still works against the new schema |
| "The endpoint is protected" | a test that a foreign id returns 404 |
| "The event fires" | a replay test and an out-of-order test |
| "Documented" | in the same PR, and a newcomer could follow it |
| "Rollback is possible" | rehearsed, at least on staging |
| "Backups exist" | a restore performed, and timed |
| "The alert is configured" | fired against a synthetic condition, and its runbook walked |
| "CPI displays correctly" | with its provenance — `8.10 · Sem 5 (Odd) · declared 28 Jul 2026` |
