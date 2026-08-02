---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
note: >
  Load-test results are committed into this file per phase. A phase cannot close without them —
  see definition-of-done.md.
---

# Performance & Capacity

The system serves ~3,300 users at one institute. The engineering goal is **headroom and no cliffs**, not raw
throughput ([ADR-0011](../01-architecture/adr/0011-no-multi-tenancy.md)).

Worth stating what we are improving on. The legacy monolith has: **no `CACHES` setting at all** (so its two
`cache`-importing views hit a per-process local-memory cache), a **non-functional Celery** (broker commented
out, settings module misnamed), **one** `db_index=True` across 424 models, database-backed sessions with
`SESSION_SAVE_EVERY_REQUEST = True` (a write per request), and no `CONN_MAX_AGE` (a new connection per
request). Fixing those is most of the win, and most of it happens in Phase 0.

---

## Budgets

| Surface | p50 | p95 | Notes |
|---|---|---|---|
| `GET /me` | 40 ms | 120 ms | warm cache; on the login critical path |
| Login | 150 ms | 400 ms | Argon2 is ~100 ms of it, deliberately |
| List endpoint (25 rows) | 60 ms | 250 ms | |
| Detail endpoint | 40 ms | 150 ms | |
| Write (state transition) | 80 ms | 300 ms | includes the outbox insert |
| Public stats page | 60 ms | **200 ms** | snapshot reads only |
| Shell first contentful paint | — | 1.5 s | cold, 3G Fast |
| Module chunk load | — | 400 ms | |

Frontend budgets, enforced by `size-limit` in CI: **shell entry ≤ 220 kB gz**, **each module chunk ≤ 150 kB
gz**. Neither existing client code-splits at all, so this is a genuine improvement rather than a regression
guard.

Alert threshold: p95 > 1.5 s for 5 minutes ([observability.md](observability.md)).

---

## Indexes

**Policy:** declared explicitly in `Meta.indexes` with a name and a reason. `db_index=True` only on a lone
foreign-key-like column where no composite is needed.

Named indexes matter operationally: Django's generated names change between versions, which makes a
hand-written migration or an emergency `DROP INDEX` riskier than it should be.

Rules:

1. Every foreign key is indexed (Django does this).
2. Every **list endpoint** gets a composite index matching its actual `WHERE` + `ORDER BY`.
3. Every allowlisted **sort field** is backed by an index — asserted by the query-budget test.
4. **Partial indexes** wherever the interesting rows are a small fraction: pending offers, eligible
   evaluations, active documents, live sessions.
5. Review `pg_stat_statements` top-20 monthly. It is a calendar item, not an aspiration.

Representative partial indexes and what they serve:

| Index | Query |
|---|---|
| `offer_user_accepted_idx` `WHERE status='accepted'` | the hot path in `can_accept` |
| `offer_pending_expiry_idx` `WHERE status='issued'` | the 15-minute expiry sweep, which otherwise scans every offer ever issued |
| `evaluation_eligible_idx` `WHERE is_eligible` | "who is eligible for this posting?" |
| `session_live_expiry_idx` `WHERE revoked_at IS NULL` | the session purge |
| `outbox_pending_idx` `WHERE consumed_at IS NULL` | `publish_outbox` — keeps dispatch cost independent of table size |

### One index on the legacy ERP — Phase 0, done

Shipped as `applications/globals/migrations/0008_hot_path_indexes.py`:

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS ocms_grades_roll_sem_idx
  ON online_cms_student_grades (roll_no, semester);
```

The exact filter `calculate_cpi_for_student` uses (`examination/api/views.py:139,153`). Measured on the
development dump, ~104k rows:

```
before:  Seq Scan on online_cms_student_grades
after:   Bitmap Heap Scan
           -> Bitmap Index Scan on ocms_grades_roll_sem_idx
```

That function runs several queries per student, so a 300-student declaration is ~1,500 of them — this is
what makes the academic snapshot pull affordable.

> **Correction — two proposed indexes were retired after measurement.** This is the worked example of
> the index policy above: *verify against real data, do not reason from the query text alone.*
>
> | Proposed | Why it was dropped |
> |---|---|
> | `globals_moduleaccess (lower(designation))` | Two errors. Django compiles `__iexact` to `UPPER(designation::text)` — note the cast — so `lower(...)` could never match. And the table is **101 rows in one 8 KB page**; Postgres declines the index even spelled correctly (reachable only with `enable_seqscan=off`). The earlier claim of "one sequential scan per designation per login" was alarmist: it is a single page read. The real cost is the N+1 query *pattern* in `auth_view`, which no index fixes. |
> | `globals_holdsdesignation (working_id)` | Redundant. `working_id` is the leading column of the composite index backing `unique_together ('working','designation')`; the planner already uses it (Index Only Scan). A second single-column index would add write cost and never be read. |

`CONCURRENTLY` takes no exclusive lock, so this is safe on a live production table, and the statement is
`IF NOT EXISTS` so it is idempotent — which matters because the development database is refreshed from a
production dump daily and migrations are re-applied each time.

---

## N+1 prevention

Three layers, because one is never enough:

1. **`nplusone` with `NPLUSONE_RAISE=True` in dev *and* test.** A lazy relation load fails the build.
2. **A `django_assert_max_num_queries` budget on every list endpoint**, with an explicit number in the test.
   The number is the specification.
3. **`contracts.py` is plural by signature.** There is no `get_user(id)` to call in a loop, because it does not
   exist ([ADR-0013](../01-architecture/adr/0013-no-cross-module-foreign-keys.md)).

```python
def test_posting_list_query_budget(client, django_assert_max_num_queries):
    PostingFactory.create_batch(50)
    with django_assert_max_num_queries(6):
        client.get("/api/v1/placement/postings?limit=25")
```

Budgets are **constant in row count**. A test that passes at 50 rows and fails at 500 has a linear query
count, which is the bug.

Cross-module reads cost exactly two extra queries regardless of row count:

```python
apps      = list(Application.objects.filter(...).select_related("posting", "resume"))
users     = directory.get_users([a.user_id for a in apps])       # 1
standings = academics.get_standings([a.user_id for a in apps])   # 1
```

---

## Caching

Three layers, distinct purposes.

**1. Per-request memoization** (`contextvar`) for the principal and its permission set. A view checking three
permissions performs one lookup.

**2. Redis, version-in-key, never deleted.**

```
iam:perms:<role>:<pv>
iam:nav:<user_id>:<role>:<pv>
iam:jwks:<kid>
placement:stats:<year>:<dim>:<val>:<computed_at>
placement:eligibility:<posting>:<user>:<inputs_version>
```

The version in the key **removes the invalidation bug class entirely**. Nothing is ever deleted; a version bump
simply misses the old key, and the stale entry expires on its own TTL. In an authorization path this is a
correctness property, not a performance trick — a stale permission cache grants a revoked permission.

**3. HTTP `ETag` / `Last-Modified`** via `ConditionalGetMiddleware` on GET lists, so a repeat view is a cheap
304. The public stats page derives its `ETag` from `max(computed_at)`.

---

## Celery

Queues: `default` · `notifications` · `reports` · `ingest` · `iam`.

Every task: `acks_late=True` · `reject_on_worker_lost=True` · `autoretry_for` + `retry_backoff` +
`retry_jitter` · `soft_time_limit` **and** `time_limit` · `ignore_result=True` unless needed · **ids only in
arguments**, never ORM objects · idempotent via `inbox_event.dedupe_key`.

| Queue | Concurrency | Prefetch | Why |
|---|---|---|---|
| `default` | 4 | 4 | short tasks |
| `notifications` | 4 | 4 | I/O bound on SMTP |
| `reports` | 2 | **1** | long, memory-heavy; prefetch 1 stops one worker hoarding a queue |
| `ingest` | **1** | **1** | deliberately serial — see below |
| `iam` | 2 | 4 | projection, ordered per user |

**`ingest` at concurrency 1 is a capacity decision, not a default.** `calculate_cpi_for_student` is several
queries per student, so a 300-student declaration is roughly 1,500 ERP queries. Running it serially, 50
students per chunk with a 2-second gap, keeps the ERP's connection pool comfortable even if two batches are
declared minutes apart.

Beat schedules live in `django-celery-beat` (database-backed), so a schedule changes without a deploy.

---

## Connection pooling

PgBouncer, `pool_mode=transaction`, `default_pool_size=25`, `max_client_conn=500`.

```python
CONN_MAX_AGE = 0                        # MANDATORY
DISABLE_SERVER_SIDE_CURSORS = True      # MANDATORY
```

**Not tuning.** Transaction pooling hands a different backend connection to each transaction. Persistent
connections or server-side cursors let one request inherit another's session state — a silent
data-correctness failure, not an error. A startup assertion refuses to boot if either is wrong while
`PGBOUNCER=1`.

Sizing: 2 services × 5 gunicorn workers × 4 threads = 40 potential concurrent transactions, plus ~13 Celery
workers. A pool of 25 with 500 client slots is comfortable, and Postgres `max_connections` stays at 100.

---

## Read replicas — a seam, not a deployment

Not deployed now. The seam exists so it can be turned on without a rewrite:

```python
@use_replica
def public_placement_stats(year_id): ...
```

An explicit decorator on chosen selectors — analytics, public stats, exports. **Never blanket-route reads.**
Blanket routing produces read-your-writes bugs the week after launch: a coordinator shortlists, the list
refetches from a lagging replica, and their change appears to have vanished.

---

## Postgres

`shared_buffers` 25% of RAM · `effective_cache_size` 75% · `work_mem` 16 MB ·
`maintenance_work_mem` 512 MB · `random_page_cost` 1.1 (SSD) · `pg_stat_statements` enabled ·
`log_min_duration_statement = 500ms` · `statement_timeout = 30s` (app role) ·
`idle_in_transaction_session_timeout = 60s`.

`statement_timeout` matters: it converts a pathological query into an error with a `request_id` instead of a
held connection that starves the pool.

Autovacuum tuned more aggressively on the churn tables (`outbox_event`, `identity_login_attempt`,
`identity_session`).

---

## Redis

Two instances, and the distinction is load-bearing:

| Instance | Port | `maxmemory-policy` | Consequence of getting it wrong |
|---|---|---|---|
| cache | 6379 | `allkeys-lru` | eviction is fine — that is what a cache is |
| broker | 6380 | **`noeviction`** | **an LRU broker silently drops queued tasks.** No error, no trace. |

A startup assertion reads `CONFIG GET maxmemory-policy` on the broker and refuses to start if it is not
`noeviction`.

---

## Load testing

`k6`, before each phase ships. Results committed to this file.

### Scenarios

| # | Scenario | Assertion |
|---|---|---|
| L1 | **Deadline spike** — 200 concurrent students on posting-list + apply for 5 min | p95 < 800 ms, **zero 5xx**, no duplicate applications |
| L2 | **Login storm** — 100 logins in 60 s | p95 < 400 ms; throttles engage correctly, not spuriously |
| L3 | **Declaration ingest** — a 300-student batch declared while L1 runs | ERP p95 within 20% of baseline; ingest completes; `outbox_lag` stays < 60 s |
| L4 | **Public stats** — 200 concurrent readers | p95 < 200 ms; **zero queries** against `placement_application` or `placement_offer` |
| L5 | **Offer day** — 50 concurrent acceptances, some contending on the same student | exactly one acceptance per student; no `IntegrityError` surfaced to a user |
| L6 | **Bulk shortlist** — 500 applications in one request | completes within the write budget; per-item outcomes returned |

L3 is the one that would be skipped and should not be. Ingest and peak student traffic will coincide in a real
season, and the interaction is the risk — not either load alone.

### Committed results

| Phase | Date | Scenario | Result | Notes |
|---|---|---|---|---|
| 0 | *pending* | legacy login p95, before/after Redis sessions + the three indexes | — | the Phase 0 baseline |
| 1 | *pending* | L2 | — | |
| 5a | *pending* | L3 | — | the gate for the academic ingest |
| 5c | *pending* | L1 | — | |
| 5e | *pending* | L5 | — | |
| 5f | *pending* | L4 | — | |

---

## Capacity, current sizing

| Resource | Now | Headroom |
|---|---|---|
| Users | ~3,300 | 10× before any structural change |
| Peak concurrent | ~200 (deadline day) | 5× on current worker counts |
| `fusion_nonacad` | < 1 GB projected year 1 | years |
| ERP | existing | unchanged by us — we only read |
| gunicorn | 2 × (5 workers × 4 threads) | scale workers first, then the VM |
| Celery | ~13 workers across 5 queues | scale per queue independently |

**The binding constraint is the single VM, not the software** ([threat-model.md](threat-model.md) A3). Scaling
path, in order: raise gunicorn workers → move Postgres to its own host → add a read replica behind
`@use_replica` → split Celery onto a second host. None requires an application rewrite, which is the property
worth preserving.

---

## Verification

- `nplusone` clean in dev and test; a lazy load fails the build.
- Every list endpoint has a query budget, and it is constant in row count.
- Every allowlisted sort field has a backing index.
- Startup assertions: `CONN_MAX_AGE=0`, cursors disabled, broker `noeviction`, ERP role read-only.
- All six k6 scenarios pass their assertions; results committed above.
- The public stats page issues zero queries against transactional tables.
- Monthly `pg_stat_statements` review recorded here.
- The three ERP indexes exist; login p95 before/after recorded.
