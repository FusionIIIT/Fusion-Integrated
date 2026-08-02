# ADR-0006 — Transactional outbox + Celery; no external broker

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0002](0002-separate-iam-service-and-database.md), [0008](0008-declared-academic-snapshot-for-cpi.md)

## Context

Several cross-boundary reactions must happen reliably:

- A role assignment in IAM must reach the legacy `globals_*` tables, or the user's legacy sidebar is
  wrong.
- A declared result in the ERP must trigger an academic snapshot pull, or Placement makes eligibility
  decisions on stale standing.
- An accepted offer must withdraw the student's other applications, refresh statistics and send
  notifications — reliably, and exactly once in effect.

The naive implementation is to fire a Celery task from the service function. That has a well-known
failure mode in both directions: dispatch before commit and the consumer can read state that does not
exist yet (or the transaction rolls back and the event fires for a write that never happened); dispatch
after commit and a crash in between loses the event silently.

Context on the existing estate: **Celery in the legacy monolith cannot boot.** The broker URL is
commented out (`common.py:82-83`) and `Fusion/celery.py` points at `Fusion.settings`, a module that does
not exist. Whatever we build must not assume any working async infrastructure to inherit.

## Decision

**Transactional outbox.** The event row is written **inside the same database transaction** as the domain
write:

```python
with transaction.atomic():
    offer.status = "accepted"
    offer.save(update_fields=["status", "decided_at"])
    PlacementRecord.objects.create(...)
    emit("placement.offer.accepted", payload,
         dedupe_key=f"offer.accepted:{offer.id}")   # → outbox_event, same transaction
```

A `publish_outbox` beat task runs every 5 seconds, claims pending rows with
`SELECT ... FOR UPDATE SKIP LOCKED`, and dispatches one Celery task per registered consumer.

**Consumers are idempotent by construction** — each records `dedupe_key` in `inbox_event` before acting,
so redelivery returns immediately.

**Celery over Redis**, with **two separate Redis instances**: cache (`allkeys-lru`) and broker
(`noeviction`). Queues: `default`, `notifications`, `reports`, `ingest`, `iam`. Every task sets
`acks_late=True`, `reject_on_worker_lost=True`, `autoretry_for`, `retry_backoff`, `retry_jitter`,
`soft_time_limit` and `time_limit`, takes **ids only** as arguments, and is safe to replay.

Beat schedules live in `django-celery-beat` (database-backed), so a schedule can change without a deploy.

**No RabbitMQ, no Kafka, no external event bus.**

## Consequences

**Good**

- **An event can never be lost, and never fires for a rolled-back write.** That is the entire point, and
  it is a database guarantee rather than a code convention.
- Broker downtime delays but does not drop. Rows accumulate in `outbox_event` and drain on recovery.
  `outbox_lag_seconds > 300` alerts.
- The outbox is a queryable audit log — "what happened, in what order, and was it consumed" is a `SELECT`.
- Replay is a first-class operation: reset `consumed_at` and the event re-fires. This is how the
  academic re-ingest runbook works.
- No new infrastructure to operate. Postgres and Redis are already required.
- The legacy monolith participates with **one new table and one `get_or_create` inside an existing
  transaction** — no Celery in the monolith at all, which is fortunate given it cannot boot Celery.

**Bad, and accepted**

- Up to ~5 seconds of dispatch latency from the beat interval. Irrelevant for every current consumer;
  anything needing lower latency (session revocation) is done synchronously instead.
- The outbox table grows. Purged 30 days after `consumed_at` by a beat task, with the pending-row count
  monitored.
- The beat scheduler is a single point of dispatch. Mitigated by `SKIP LOCKED` claiming (safe to run
  multiple publishers) and a `readyz` check on beat liveness.
- **At-least-once, not exactly-once.** Every consumer must be idempotent; there is no way around this and
  it is stated as a hard obligation in [event-catalog.md](../event-catalog.md#consumer-obligations).
- **No global ordering.** Only per-aggregate, via task routing on the aggregate key. Consumers that care
  must guard explicitly — as the academic ingest does with its `declared_seq` comparison.
- Redis as a broker can lose in-flight messages under some failure modes. This is precisely why the
  outbox exists: the message is a *dispatch hint*, and the durable record is the Postgres row. It is also
  why the broker instance runs `noeviction` — an LRU-evicting broker silently drops queued tasks, which
  is the kind of bug that loses a season's offer notifications with no trace.

## Alternatives considered

**Direct `task.delay()` from service functions.** Rejected: the dispatch-before/after-commit problem
above. It is what most Django codebases do and it is the source of "the notification didn't send and we
don't know why".

**`transaction.on_commit(lambda: task.delay(...))`.** Better — it solves the rollback case. Rejected as
insufficient: a process crash between commit and dispatch still loses the event, with no record that it
existed. The outbox row is what makes loss impossible.

**RabbitMQ.** Genuinely better as a broker: real acknowledgements, no eviction, dead-letter queues.
Rejected for now as another daemon to operate, monitor, back up and upgrade on a single VM with no SRE
function. The outbox makes broker durability much less critical, which is what buys us this simplicity.
Recorded as the documented upgrade path if broker reliability ever becomes the binding problem.

**Kafka / Redpanda.** Rejected outright: retention, partitioning and consumer groups solve problems of
scale and replay that we do not have, at an operational cost we cannot carry.

**Postgres `LISTEN`/`NOTIFY` instead of Celery.** Rejected: no retries, no visibility, no scheduling, and
notifications are dropped if nobody is listening. It would mean reimplementing Celery's useful parts.

**Debezium / logical-decoding CDC.** Rejected: heavyweight, and it would couple event semantics to
physical table shape rather than to explicit domain events.

## Verification

- Rollback test: a service function that raises after `emit()` leaves **no** outbox row.
- Replay test: every consumer handles the same `dedupe_key` twice with no state change on the second.
- Broker-outage test: stop the broker, perform writes, restart, assert all events consumed and
  `outbox_pending_rows` returns to zero.
- Out-of-order test: deliver `academics.result.declared` for Sem 5 then Sem 3, assert standing stays on
  Sem 5.
