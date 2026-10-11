---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# System Architecture

## Level 1 — context

```
                      ┌────────────────────────────────────────────┐
   students ──────────┤                                            │
   faculty  ──────────┤   fusion.iiitdmj.ac.in   (single nginx)    │
   staff    ──────────┤                                            │
   operators ─────────┤   /app/  → new unified shell               │
                      │   /      → legacy academic monolith        │
                      │   /sysadmin/ → console (until Phase 7)     │
                      └───────────────┬────────────────────────────┘
                                      │
                    ┌─────────────────┼──────────────────┐
                    ▼                 ▼                  ▼
              fusion-iam       fusion-platform     legacy monolith
                    │                 │                  │
                    ▼                 ▼                  ▼
           fusion_system_db    fusion_nonacad      fusion_newui_prod
             (schema iam)                          (auth_user + 424 models)

   External: SMTP relay (institute) · ClamAV (local daemon) · Sentry (self-host or SaaS)
```

There are **four** deployables in total, three of which are new to this programme, and one existing
system (the monolith) that we do not restructure.

## Level 2 — containers

| Container | Tech | Port / socket | Owns | Reads |
|---|---|---|---|---|
| **`apps/shell`** | React 18 + TS + Vite, static files | nginx `/app/` | nothing | all three APIs |
| **`fusion-iam`** | Django 5.2 + DRF, gunicorn | `unix:/run/fusion/iam.sock` | `fusion_system_db` schema `iam` | — |
| **`fusion-platform`** | Django 5.2 + DRF, gunicorn, modular monolith | `unix:/run/fusion/platform.sock` | `fusion_nonacad` | ERP (**read-only role**), IAM (HTTP) |
| **legacy monolith** | Django 3.1.5, unchanged | `127.0.0.1:8000` | `fusion_newui_prod` | validates IAM JWTs |
| **sysadmin console** | Django 5.1, existing | `127.0.0.1:8001` | `fusion_system_db` schema `public` | ERP. Absorbed in Phase 7. |
| **Celery workers** | one set per Django service | — | — | — |
| **Redis ×2** | cache instance + broker instance | `6379` / `6380` | — | — |
| **PgBouncer** | transaction pooling | `6432` | — | — |
| **PostgreSQL 16** | one cluster, several databases | `5432` | — | — |

### Why two Redis instances

The cache instance runs `maxmemory-policy allkeys-lru`; the broker instance runs `noeviction`. An
LRU-evicting broker **silently drops queued Celery tasks** under memory pressure. That is the class of
bug that loses a placement season's offer notifications and leaves no trace. → [ADR-0006](adr/0006-outbox-plus-celery-for-integration-events.md)

## Databases and who owns what

```
PostgreSQL 16 cluster
├── fusion_system_db
│   ├── schema iam      ← fusion-iam OWNS.       Migrations: fusion-iam only.
│   └── schema public   ← sysadmin console owns. Migrations: console only.
├── fusion_nonacad      ← fusion-platform OWNS.  Migrations: platform only.
└── fusion_newui_prod   ← legacy monolith OWNS.  Migrations: monolith only.
    (fusionlab in dev)     platform connects with a READ-ONLY role.
                           the IAM projector connects with a narrow write role.
```

**One writer per table, always.** The full table is in
[data-ownership-and-sync.md](data-ownership-and-sync.md).

Two Django projects cannot share one `public.django_migrations` without their histories colliding,
which is why IAM gets its own schema rather than sharing `public` with the console. Set via
`options: {'-c search_path=iam,public'}` on the connection. → [ADR-0002](adr/0002-separate-iam-service-and-database.md)

### Postgres roles (least privilege)

| Role | Grants |
|---|---|
| `iam_app` | full DML on `iam.*` |
| `platform_app` | full DML on `fusion_nonacad` public schema, **except** `REVOKE UPDATE, DELETE ON academics_resultsnapshot` — snapshot immutability is enforced by the database, not by discipline |
| `platform_erp_ro` | `SELECT` only, on a named allowlist of ERP tables |
| `iam_erp_projector` | `SELECT, INSERT, UPDATE, DELETE` on exactly `globals_designation`, `globals_holdsdesignation`, `globals_moduleaccess`; `SELECT` on `auth_user`, `globals_extrainfo`; **nothing else** |

→ [ADR-0012](adr/0012-postgres-roles-and-least-privilege.md)

## Request paths

### A shell page load

```
GET /app/                     → nginx serves shell/index.html + hashed assets
GET /app/api/iam/v1/me        → fusion-iam
                                 verifies fusion_at cookie (RS256, local, no DB hit)
                                 loads principal + roles + permissions (Redis, key includes pv)
                                 builds navigation (Redis, key includes pv)
                                 → {user, roles, active_role, permissions, permission_version,
                                    modules, navigation, external_links, idle_timeout_seconds}
shell renders <AppShellLayout navGroups={session.navigation}/>   ← zero client-side filtering
shell registers routes only for session.modules                  ← ungranted ⇒ no route exists
```

### A platform API call

```
GET /app/api/platform/v1/placement/postings?cursor=…
  nginx → unix:/run/fusion/platform.sock
    IamJWTAuthentication      verify RS256 against cached JWKS → request.principal
    HasPermission             "placement.job_posting.view", deny-by-default
    ModuleGrantPermission     "placement_cell" ∈ token.mod claim
    selector                  select_related/prefetch_related, cursor pagination
    → {results: [...], next: "cursor…"}   + X-Request-ID echoed
```

No per-request call into IAM. The access token carries `rol`, `mod` and `pv`; it lives 10 minutes,
which bounds how stale an authorization decision can be. → [ADR-0003](adr/0003-rs256-jwt-access-plus-opaque-refresh.md)

### A legacy monolith call during transition

```
GET /api/auth/me   (Fusion-client, unchanged response shape)
  DEFAULT_AUTHENTICATION_CLASSES = [
      IamJWTAuthentication,      ← new, first, behind IAM_JWT_AUTH_ENABLED
      TokenAuthentication,       ← existing, still works
      SessionAuthentication,
  ]
```

Existing DRF tokens keep working for the entire transition, so a rollback needs no re-login.

## Synchronous vs asynchronous

Synchronous HTTP **only** where freshness is load-bearing:

- shell → IAM `/me` (the session must be current)
- platform → IAM, to resolve a principal not yet in `directory.UserRef`
- platform → legacy `POST /api/examination/internal/academic-snapshot/` (the CPI pull)

Everything else is **transactional outbox → Celery**. The write and its event commit in one
transaction, so an event can neither be lost nor fired for a rolled-back write. Consumers record a
`dedupe_key` in `inbox_event` before acting, so redelivery is a no-op.

```
service function
  ┌─ transaction.atomic() ────────────────────────┐
  │  write domain rows                            │
  │  OutboxEvent.objects.create(topic, payload,   │
  │                             dedupe_key)       │
  └───────────────────────────────────────────────┘
        │  committed
        ▼
  publish_outbox beat task (every 5s) → Celery task per topic
        │
        ▼
  consumer: InboxEvent.get_or_create(dedupe_key) → already there? return
                                                 → else handle, mark consumed
```

Full topic list, payloads, ordering and idempotency guarantees:
[event-catalog.md](event-catalog.md).

## The academic integration, at container level

```
legacy monolith (examination app)
  ├─ ResultAnnouncement.announced flips True
  │    └─ inside the SAME transaction: ExamOutboxEvent("academics.result.declared")
  └─ POST /api/examination/internal/academic-snapshot/   ← new, 127.0.0.1 only,
       reuses _is_result_published_for + calculate_cpi_for_student verbatim
                    │
                    ▼  pulled in 50-student chunks, 2s apart, ingest queue concurrency 1
        fusion-platform  modules/academics
          ResultDeclaration → ResultSnapshot (immutable) → StudentAcademicStanding (upsert)
                    │
                    ▼  academics.standing.changed
        modules/placement  invalidates EligibilityEvaluation by inputs_version
```

These are the **only two changes** this programme makes to legacy behaviour: one outbox row inside an
existing transaction, and one new read-only internal endpoint. Detail:
[academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md).

## Inside `fusion-platform`

A modular monolith. One deployable, hard internal boundaries.

```
config/            settings (base/dev/staging/prod), urls, celery, wsgi
core/              shared kernel — db, api, events, files, rules
modules/
  directory/       UserRef projection from IAM
  academics/       read-only ACL over the ERP + declaration snapshots
  placement/       ┐
  hr/              ├ bounded contexts
  leave/           ┘
```

Every module has the same five layers — `domain/` (pure Python, no Django), `models.py`,
`selectors/`, `services/`, `api/` — plus `contracts.py`, which is its **only** public surface to other
modules. Enforced by `import-linter` in CI, not by convention.
[platform-structure.md](../03-platform/platform-structure.md) has the contracts verbatim.

**No foreign key crosses a module boundary.** Cross-module references are plain id columns; a CI
script walks every `ForeignKey` target and fails on any cross-module edge. This is what keeps the
option of extracting a module into its own service cheap. → [ADR-0013](adr/0013-no-cross-module-foreign-keys.md)

## Failure modes

| If this dies | Effect | Recovery |
|---|---|---|
| `fusion-iam` | No new logins, no role switches. **Existing sessions keep working** for up to 10 minutes (access tokens validate locally against cached JWKS) and legacy DRF tokens keep working indefinitely. | `systemctl restart fusion-iam`; [incident-auth-outage.md](../07-ops/runbooks/incident-auth-outage.md) |
| `fusion-platform` | Non-academic modules 502. Academic monolith and login unaffected. | restart |
| legacy monolith | Academic modules down. Shell login and non-academic modules unaffected — **this is a new property**; today it is a single point of failure. | restart |
| Redis (cache) | Everything degrades to database reads; throttle counters reset. Not fatal. | restart; `allkeys-lru` means data loss here is by design |
| Redis (broker) | Events queue in `outbox_event` and drain when it returns. **Nothing is lost** — that is the point of the outbox. `outbox_lag > 300s` alerts. | restart, then watch `outbox_pending_rows` fall |
| PostgreSQL | Total outage. | [restore-from-backup.md](../07-ops/runbooks/restore-from-backup.md) — a runbook that has been executed for real |
| ERP snapshot endpoint | Ingest retries with exponential backoff up to 8 times, then the run is marked `failed` and alerts. Standing simply stays at the previous declaration. | [reingest-academic-snapshot.md](../07-ops/runbooks/reingest-academic-snapshot.md) |

**The single real single-point-of-failure is the VM itself.** Mitigation is honest rather than
architectural: Postgres on its own disk, WAL archiving, nightly off-box backups, and a restore
runbook executed in Phase 1 — not a Phase 8 aspiration. → risk R7 in
[risk-register.md](../08-delivery/risk-register.md).

## What this architecture deliberately does not have

No service mesh, no API gateway beyond nginx, no Kubernetes, no message broker beyond
Postgres + Redis + Celery, no CQRS, no event sourcing, no multi-region, no tenancy. Each of those
solves a problem we do not have, and each would need to be operated by the same small team.

## Diagrams

Mermaid sources in [`../_diagrams/`](../_diagrams/): `c4-context.mmd`, `c4-container.mmd`,
`request-path-shell.mmd`, `academic-ingest-sequence.mmd`, `auth-token-lifecycle.mmd`. Rendered by CI;
never commit a rendered image.
