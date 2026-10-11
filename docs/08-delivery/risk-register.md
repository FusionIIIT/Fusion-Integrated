---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
review-cadence: monthly, and at every phase gate
---

# Risk Register

Each risk has an **owner**, a **likelihood**, an **impact**, a **mitigation**, and a **trigger** — the observable
signal that tells you it is happening. A risk with no trigger is a worry, not a managed risk.

Likelihood / impact: **H**igh · **M**edium · **L**ow.

---

## Open decisions blocking a phase

### R-H1 — Only one holder per designation, institute-wide · **blocks Phase 4**

| | |
|---|---|
| **Owner** | iam-lead + the academic office |
| **L / I** | **H / H** |
| **Risk** | `globals_holdsdesignation` has `unique_together ('working','designation')` — so only **one person institute-wide** can hold a given designation. Two placement coordinators cannot both be projected into the ERP. The projection either fails with `IntegrityError` or silently drops holders. |
| **Trigger** | A second holder is assigned to any projectable role. |
| **Mitigation** | Default **option B**: project only the `is_primary` holder (guaranteed unique by a partial index), and record the rest in `IntentionalProjectionGap` so drift reporting stays meaningful. |
| **Decision needed** | **A** — drop the legacy constraint (full fidelity; one migration on a live table + an audit of code assuming uniqueness; +1 week). **B** — primary-only, allowlist the rest *(default)*. **C** — never project multi-holder roles. |
| **Consequence of B** | A secondary or scoped role holder sees that role **only at `/app/`**; their legacy sidebar will not show it. Fails closed, so it is a fidelity gap and not a privilege escalation. |
| **Status** | **Open. Needs a written answer before Phase 4 begins.** |

The offices must be told before Phase 4 ships, or a known limitation arrives as a bug report during a placement
season.

### R-D2 — No `declared_at` on `ResultAnnouncement`

| | |
|---|---|
| **Owner** | platform-lead + the academic office |
| **L / I** | M / M |
| **Risk** | `created_at` is when the admin created the *not-yet-announced placeholder*; flipping `announced` writes no timestamp. We capture `declared_at` in the outbox event instead — so a declaration made while the platform is down loses its true timestamp. |
| **Trigger** | Ingest lands with `declared_at` equal to the ingest time rather than the declaration time. |
| **Mitigation** | Add `declared_at` + `declared_by` to `ResultAnnouncement` — a small additive legacy migration. Until then, an outbox gap is visible as a suspiciously late `declared_at`. |
| **Status** | Open. Not blocking; worth doing in Phase 5a. |

### R-D3 — Placement policy knobs unset

| | |
|---|---|
| **Owner** | placement office |
| **L / I** | M / H |
| **Risk** | `max_offers_allowed`, `pool_after_offer`, `dream_threshold_lpa`, `min_cpi_to_register` are **institute policy**, not engineering defaults. Discovering mid-season that `tier_upgrade_only` refuses a ₹30 LPA offer that `dream_only` would allow is a policy surprise, not a bug. |
| **Trigger** | Phase 5e approaching with no signed-off policy. |
| **Mitigation** | Walk the decision table in [offer-and-tier-policy.md](../04-placement/offer-and-tier-policy.md) with the office **before** 5e. Every refusal persists its `policy_decision`, so appeals are answerable either way. |
| **Status** | Open. Needed before 5e. |

---

### R-M1 — The migration graph cannot build a database from scratch · **found during Phase 0**

| | |
|---|---|
| **Owner** | platform-lead + central_mess owner |
| **L / I** | **H (already realized) / H** |
| **Risk** | `applications/central_mess/migrations/0001_initial.py` contains **two** `CreateModel(name='Payments', ...)` operations (lines 153 and 207). The second fails with `ProgrammingError: relation "central_mess_payments" already exists`. A from-scratch `migrate` therefore cannot complete. |
| **How it surfaced** | Trying to build a test database for the Phase 0 characterization suite. |
| **Why nobody noticed** | Production and development databases were built incrementally years ago, or restored from a dump. Nothing has replayed the graph from empty since the defect landed — and with no test suite and no CI, nothing ever tried. |
| **Real consequence** | A new environment cannot be stood up from source, and **disaster recovery by replaying migrations is impossible** — only a dump restore works. That is a meaningful gap in [restore-from-backup.md](../07-ops/runbooks/restore-from-backup.md)'s assumptions. |
| **Mitigation (now)** | `Fusion/settings/test.py` builds the test schema directly from models (`MIGRATION_MODULES` disabled), so the characterization suite runs and gates CI without touching a deprecated app. This is a **workaround, not a fix** — it deliberately stops exercising migrations. |
| **Fix needed** | Delete the duplicate `CreateModel`. One-line change, and safe: the migration is already recorded as applied everywhere, so editing it cannot re-run it. Blocked only on `central_mess` being a deprecated app that this programme is scoped not to touch — it needs an owner's sign-off. |
| **Trigger** | Any attempt to create a fresh database, or a CI job that migrates rather than syncing from models. |
| **Status** | **Open — needs a decision.** Recommend fixing it despite the app being deprecated; the blast radius is a fresh-build-only code path. |

### R-M2 — Cross-app raw-SQL migrations with undeclared dependencies · **fixed in Phase 0**

| | |
|---|---|
| **Owner** | platform-lead · **L/I: M / M** |
| **Risk** | `programme_curriculum/0026_add_database_indexes.py` ran raw SQL against `course_registration` — a table owned by `academic_procedures` — without declaring a dependency on that app. The graph was free to order it before the table existed. |
| **Mitigation** | Dependency on `('academic_procedures', '0013_auto_20250423_1401')` added. A project-wide scan (see below) confirmed this was the only instance. |
| **Prevention** | Any migration touching a table it does not own **must** declare a dependency on the owning app. `globals/0008` follows this for `online_cms_student_grades`. Worth adding to CI as a check that walks raw-SQL migrations, resolves referenced tables to owning apps, and asserts a declared dependency. |
| **Status** | Fixed. Prevention check not yet automated. |

### R-M3 — Cache and session hardening blocked on a dependency approval

| | |
|---|---|
| **Owner** | project leads · **L/I: H / M** |
| **Risk** | The per-request Postgres session write (`SESSION_SAVE_EVERY_REQUEST` + database backend) cannot be removed without a shared cache. Django 3.1 has **no built-in Redis backend** (added in 4.0), so this needs `django-redis` in `requirements.txt` — which `CONTRIBUTING.md` reserves to the project leads. |
| **Why not just switch anyway** | `SESSION_SAVE_EVERY_REQUEST` must stay `True`, or `SESSION_COOKIE_AGE` stops being a sliding idle timeout and active users get logged out mid-work. And switching to a **LocMem** cache backend with multiple gunicorn workers would drop sessions at random — worse than the write. |
| **Mitigation** | `common.py` stages the wiring inert: it switches `CACHES` to Redis and `SESSION_ENGINE` to the cache backend **only** when `REDIS_URL` is set *and* `django_redis` imports. Until both hold, behaviour is byte-identical to before. Check `fusion.W004` reports the outstanding cost as `Info` (not `Warning`, so it cannot fail CI for something a PR author cannot action). |
| **Trigger** | `fusion.W004` appearing in `check --deploy` output. |
| **Status** | **Open — needs a one-line approval**: add `django-redis` to `requirements.txt`. |

---

## Technical risks

### R1 — No test suite exists in either live system

| | |
|---|---|
| **Owner** | platform-lead · **L/I: H / H** |
| **Risk** | All 31 legacy `tests.py` are 3-line stubs; no `pytest` in `requirements.txt`; neither React client has a test runner; CI is a welcome-bot. **The auth migration has no safety net to inherit.** |
| **Trigger** | Any change to `globals/api/views.py` or the settings. |
| **Mitigation** | The characterization suite in **Phase 0**, plus the Phase 2 **7-day empty-diff gate**. With no legacy tests to trust, a production diff is the strongest evidence available. |

### R2 — Legacy production runs `DEBUG = True`

| | |
|---|---|
| **Owner** | iam-lead · **L/I: H / H** |
| **Risk** | `production.py:3`. Any unhandled 500 renders a traceback page including `request.META` — which, once we issue a `Path=/` cookie, contains a working credential. |
| **Trigger** | Any 500 in production. |
| **Mitigation** | **Phase 0 blocking prerequisite.** No cookie is issued until `check --deploy` exits clean. |

### R3 — H2: production columns no migration knows about

| | |
|---|---|
| **Owner** | iam-lead · **L/I: H / M** |
| **Risk** | The console's `api/views/schema.py:12-52` applies raw `ALTER TABLE` to the ERP. Production has `globals_designation.{basic,category,dept_if_not_basic_id}` and `globals_moduleaccess.inventory_management` that `applications/globals/migrations/` does not. Three definitions of `ModuleAccess` disagree (legacy model 20 booleans, console shadow 21, production 22). **`makemigrations` on the monolith would generate migrations that drop production columns.** |
| **Trigger** | The `legacy_column_parity` CI check fails, or a projection write hits an unknown column. |
| **Mitigation** | The projector builds its shadow model from `information_schema` **at startup**; a CI check compares `legacy_column_name` against live columns; Phase 2 reconciles the drift into real migrations. |

### R4 — Ingest cost against the ERP

| | |
|---|---|
| **Owner** | platform-lead · **L/I: M / M** |
| **Risk** | `calculate_cpi_for_student` is several queries per student, so a 300-student declaration is ~1,500 ERP queries — during the exam-results period, when the ERP is busiest. |
| **Trigger** | ERP p95 rises during ingest; `celery_queue_depth{ingest} > 500`. |
| **Mitigation** | 50-student chunks, 2 s apart, `ingest` queue at **concurrency 1**, off-peak, load-tested in 5a (scenario L3 runs ingest *while* peak student traffic runs). `ACADEMICS_INGEST_ENABLED` kills it instantly. |
| **Note** | **Do not raise the concurrency to drain a backlog.** That converts our problem into an academic-wide slowdown. |

### R5 — CPI lag is a feature, and will be reported as a bug

| | |
|---|---|
| **Owner** | placement-lead · **L/I: H / L** |
| **Risk** | Placement shows a value minutes behind the ERP and semesters behind "provisional". Students will say their CPI is wrong. |
| **Trigger** | Support tickets about CPI. |
| **Mitigation** | Every CPI renders `8.10 · Sem 5 (Odd) · declared 28 Jul 2026`; a bare number in the UI is a bug. Documented in the placement office SOP and in [reingest-academic-snapshot.md](../07-ops/runbooks/reingest-academic-snapshot.md) §6, which tabulates the six common complaints against their actual causes. |

### R6 — A result is retracted after applications exist

| | |
|---|---|
| **Owner** | placement-lead · **L/I: M / H** |
| **Risk** | A student who applied and interviewed becomes retroactively ineligible. |
| **Trigger** | `academics.result.retracted`; unresolved `ReviewFlag`s. |
| **Mitigation** | Standing recomputes from the highest non-retracted declaration; affected applications are **flagged for a coordinator, never auto-rejected**. `cpi_at_apply` and `eligibility_snapshot` frozen on the application show what was true at submission. |

### R7 — Everything on one VM

| | |
|---|---|
| **Owner** | ops · **L/I: M / H** |
| **Risk** | No HA, no failover. A disk or host failure is a total outage. |
| **Trigger** | Disk > 85%; any hardware alert. |
| **Mitigation** | Postgres on its own disk · WAL archiving · off-box nightly backups · `MemoryMax` and worker recycling so one bad request cannot take the box down · **a restore performed for real in Phase 1, with measured timings**. |
| **Accepted** | Yes — cost and operational capacity for a team with no SRE function. Stated in [vision-and-scope.md](../00-overview/vision-and-scope.md). |

### R8 — Redis broker misconfigured as `allkeys-lru`

| | |
|---|---|
| **Owner** | ops · **L/I: L / H** |
| **Risk** | An LRU-evicting broker **silently drops queued Celery tasks**. No error, no trace. Lost offer notifications and lost projections with nothing to investigate. |
| **Trigger** | A startup assertion refuses to boot; or tasks vanish with `outbox_pending_rows` stuck. |
| **Mitigation** | Two Redis instances, broker `noeviction`, asserted at startup via `CONFIG GET maxmemory-policy`. The outbox makes every event replayable regardless. |

### R9 — Client single-flight refresh breaks → mass logout

| | |
|---|---|
| **Owner** | frontend-lead · **L/I: M / H** |
| **Risk** | Parallel 401s each fire a refresh; nine present the same not-yet-rotated token; reuse detection revokes the family; everyone is logged out. A self-inflicted outage. |
| **Trigger** | `iam_refresh_reuse_detected_total` spikes. |
| **Mitigation** | Single-flight refresh in `packages/api-client`, with a test asserting ten parallel requests produce **one** refresh. **Response is to roll back the frontend — never to disable reuse detection.** |

### R10 — PgBouncer + persistent connections

| | |
|---|---|
| **Owner** | ops · **L/I: L / H** |
| **Risk** | Transaction pooling with `CONN_MAX_AGE > 0` or server-side cursors lets one request inherit another's session state — a **silent data-correctness failure**, not an error. |
| **Trigger** | A startup assertion refuses to boot. |
| **Mitigation** | `CONN_MAX_AGE=0` and `DISABLE_SERVER_SIDE_CURSORS=True`, asserted at startup while `PGBOUNCER=1`. |

### R11 — Two frontends live simultaneously (Phases 3–7)

| | |
|---|---|
| **Owner** | frontend-lead · **L/I: M / M** |
| **Risk** | Session confusion between `/app/` and the legacy SPA; mismatched idle timeouts (5 min vs 30 min) log a user out of one while they work in the other. |
| **Trigger** | Reports of being logged out while active. |
| **Mitigation** | Legacy accepts the JWT cookie after a **two-line** change; idle timeout unified at 30 min; fallback of IAM also minting a legacy DRF token so the old client works untouched. |

### R12 — Team new to monorepos and strict TypeScript

| | |
|---|---|
| **Owner** | frontend-lead · **L/I: M / M** |
| **Risk** | Onboarding drag; a workaround culture around pnpm's symlinks and Turborepo caching. |
| **Trigger** | PRs disabling type checks or adding a fifth package. |
| **Mitigation** | Four packages, one app, **resist a fifth** · a `Makefile` of named tasks · a `CONTRIBUTING.md` walkthrough · CI never uses a local Turbo cache. |

### R13 — Visual baselines flake across operating systems

| | |
|---|---|
| **Owner** | frontend-lead · **L/I: M / L** |
| **Risk** | Font rendering differs between macOS and Linux; baselines regenerated from a laptop make the suite noise everyone ignores — and the design-extraction proof evaporates. |
| **Trigger** | Visual specs failing on unrelated PRs. |
| **Mitigation** | Run visual specs **only** inside a pinned Docker image; never regenerate baselines locally. |

### R14 — Scope creep into porting the 26 deprecated apps

| | |
|---|---|
| **Owner** | platform-lead · **L/I: H / H** |
| **Risk** | ~60k LOC and ~290 models of deprecated code. Any "just port this one module" request threatens the schedule, and ports the bugs — the old placement module filters on `Student.cpi`, a column that is permanently `0.0`. |
| **Trigger** | A request framed as "it already exists, just move it". |
| **Mitigation** | Written non-goal ([NG2](../00-overview/vision-and-scope.md#non-goals)). Any port goes through a new-module design doc first. **This is the risk most likely to be realized**, because the request always sounds reasonable. |

### R15 — DRF token rotation on login breaks concurrent devices

| | |
|---|---|
| **Owner** | iam-lead · **L/I: L / L** |
| **Risk** | Legacy `AuthUserSerializer.get_auth_token` **deletes and recreates** the token on every login, so logging in on a phone logs out the laptop. Existing behaviour, but it will be reported as a new bug once `/app/` exists. |
| **Trigger** | Reports of being logged out after logging in elsewhere. |
| **Mitigation** | IAM supports multiple concurrent sessions correctly. Pilot comms should mention it; the behaviour disappears when legacy login retires. |

### R16 — A placement season starts mid-Phase 5

| | |
|---|---|
| **Owner** | placement-lead · **L/I: M / H** |
| **Risk** | A half-built drive tool during a live season is worse than none. |
| **Trigger** | The season calendar overlapping the 5b–5f estimate. |
| **Mitigation** | Freeze at the last **completed** sub-phase. Module grants make an unfinished module invisible and unroutable, so freezing is safe rather than a scramble. |

### R17 — `semester_type IS NULL` legacy announcements

| | |
|---|---|
| **Owner** | platform-lead + the academic office · **L/I: M / L** |
| **Risk** | Pre-migration-`0003` rows have `semester_type = NULL`. On Postgres the unique constraint does not dedupe NULLs, and a typed lookup never matches them — so those students see "results not announced" **indefinitely**, both in the legacy app and here. |
| **Trigger** | The data-quality report lists NULL-type announcements. |
| **Mitigation** | Reported, not ingested. Needs an ERP-side fix by the academic office. Pre-existing, and this is the first time anyone will have noticed. |

---

## Retired

*(Nothing yet. Risks move here with the date and the reason, rather than being deleted — a retired risk is
evidence that the mitigation worked.)*

---

## Review

Monthly, and at every phase gate. For each risk: has the trigger fired? Is the mitigation actually in place, or
just written down? Has the likelihood changed?

**The three to watch hardest:** **R-H1** (blocks Phase 4 and needs a decision from outside engineering) ·
**R14** (the most likely to be realized, because the request always sounds reasonable) · **R1** (everything else
depends on the safety net existing before it is needed).
