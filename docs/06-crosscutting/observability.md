---
owner: ops
status: authoritative
last-reviewed: 2026-08-01
---

# Observability

The design goal is narrow and practical: **a user reads an id off an error toast, and support finds the exact
request in one grep.** Everything else follows from that.

Six alerts, not sixty. An alert nobody acts on trains everyone to ignore the channel.

---

## Logging

structlog → JSON on stdout → journald (→ Loki, optionally, later). No log files, no rotation to manage.

Every line carries:

```json
{"ts":"2026-08-01T10:04:22.117Z","level":"info","event":"http.request",
 "request_id":"9f2c1b4e-7a3d-4c1e-9f8a-2b6d5e0c1a77",
 "session_id":"018f4c2a-8a01-7d20-b3c4-9e2f1a0b7d55",
 "user_id":1234,"active_role":"placement_coordinator",
 "service":"fusion-platform","release":"a1b2c3d",
 "method":"GET","path":"/api/v1/placement/postings","status":200,
 "duration_ms":42,"db_queries":4,"db_time_ms":11,"module":"placement"}
```

`db_queries` and `db_time_ms` are on **every** request line. That single pair is what turns "the postings page
feels slow" into "it issues 340 queries" without adding instrumentation first.

### Request IDs

`RequestIDMiddleware` (`core/observability/middleware.py`):

1. Accepts nginx's `$request_id` via `X-Request-ID`, else generates a UUIDv7.
2. Stores it in a `contextvar`, so every log line in the request — including Celery tasks it spawns — carries it.
3. Echoes it in the `X-Request-ID` response header.
4. Puts it in the **error envelope**, so it is visible on screen.

```
User sees:  "Something went wrong.  Reference: 9f2c1b4e"
Support runs: journalctl -u fusion-platform | grep 9f2c1b4e
```

That is the whole point of the field, and it is why the frontend's `ErrorState` always renders it.

### Redaction

The structlog processor recursively redacts `{password, token, otp, secret, authorization, cookie, phone,
address, date_of_birth, category, aadhaar}` and anything declared `SensitivePIIField`. **Request and response
bodies are never logged.**

### Levels

| Level | For |
|---|---|
| `debug` | dev only |
| `info` | one line per request; state transitions; task start/finish |
| `warning` | throttled, lockout, guard failure, retry, projection drift |
| `error` | unhandled 5xx, task failure after retries, integration failure |
| `critical` | signing key unreadable, database unreachable, broker misconfigured |

A 403 or 422 is **`info`**, not `error` — the system worked correctly. Logging expected refusals as errors is
how an error dashboard becomes noise.

### Domain events worth logging explicitly

`auth.login` (with `outcome`) · `auth.refresh.reuse_detected` · `rbac.role.assigned` ·
`projection.drift_detected` · `academics.declaration.ingested` · `academics.snapshot.mismatch` ·
`placement.offer.accepted` · `placement.export.pii` · `outbox.published` · `task.failed`.

---

## Metrics

`django-prometheus` on a **localhost-only** port, scraped by a small Prometheus on the VM, with Grafana.

### Golden signals, per service

`http_requests_total{method,path_template,status}` ·
`http_request_duration_seconds{path_template}` (histogram) ·
`http_requests_in_flight` · `db_query_duration_seconds` · `db_connections_in_use`.

`path_template` — not the raw path — otherwise every id becomes its own cardinality explosion.

### Domain metrics

| Metric | Watching for |
|---|---|
| `iam_login_total{outcome}` | credential stuffing; a broken login path |
| `iam_refresh_reuse_detected_total` | should be ~0. **A spike almost always means the client's single-flight refresh broke**, not an attack |
| `iam_lockout_total` | brute force |
| `iam_stepup_required_total{granted}` | dangerous-permission friction |
| `reconcile_drift_total` | IAM↔ERP projection divergence |
| `outbox_pending_rows{topic}` | consumer lag or a stuck publisher |
| `outbox_lag_seconds{topic}` | the primary event-pipeline health signal |
| `event_consumed_total{topic,consumer,outcome}` | failing handlers |
| `celery_queue_depth{queue}` | worker saturation |
| `celery_task_duration_seconds{task}` | slow tasks |
| `academics_ingest_lag_seconds` | declaration → standing latency |
| `academics_snapshot_mismatch_total` | **legacy CPI semantics changed under us** |
| `placement_applications_submitted_total` | deadline-day load shape |
| `eligibility_eval_duration_seconds` | the rule engine |
| `placement_export_pii_total{user}` | the weekly privileged review |

`academics_snapshot_mismatch_total` is the quiet but important one. It is the only signal that would catch
someone "fixing" `grade_conversion["F"]` in the legacy monolith and silently changing every CPI we hold.

---

## Tracing

`sentry-sdk[django,celery,redis]`, `traces_sample_rate=0.1`, `profiles_sample_rate=0.1`,
`send_default_pii=False` with a `before_send` scrubber, `release=<git-sha>`, per-service DSNs.

Sentry is the error tracker; Prometheus is the metrics store. No separate tracing backend — at two services and
one VM, distributed tracing would cost more to run than it would explain.

Every Sentry event carries `request_id`, `user_id` (an id, never a name or email), `active_role`, `module` and
`release`, so a Sentry issue and a log line join on `request_id`.

---

## Health checks

| Endpoint | Checks | Used by |
|---|---|---|
| `/healthz` | the process is alive. **No dependencies.** | systemd, uptime monitor |
| `/readyz` | database + Redis + JWKS reachable | deploy smoke test, load-balancer readiness |

`/healthz` deliberately checks nothing external. A liveness probe that fails when Postgres blips restarts a
healthy process during an incident and turns a database problem into an outage.

---

## The six alerts

Deliberately few. Each is actionable, has a runbook, and pages a human.

| Alert | Condition | Means | Runbook |
|---|---|---|---|
| **Event pipeline stalled** | `outbox_lag_seconds > 300` (any topic, 5 min) | Broker down, worker dead, or a handler crash-looping. Nothing is lost — the outbox is durable — but roles and notifications are not propagating. | [incident-auth-outage.md](../07-ops/runbooks/incident-auth-outage.md) |
| **Ingest backlog** | `celery_queue_depth{queue="ingest"} > 500` | Declaration ingest is not draining; standings are stale and eligibility decisions are on old data. | [reingest-academic-snapshot.md](../07-ops/runbooks/reingest-academic-snapshot.md) |
| **Auth failing** | login 5xx rate > 1% over 5 min | Signing key, JWKS, or database. Users cannot log in. | [incident-auth-outage.md](../07-ops/runbooks/incident-auth-outage.md) |
| **Latency regression** | p95 > 1.5 s for 5 min (any service) | A missing index, an N+1 that escaped CI, or database pressure. | [performance-and-capacity.md](performance-and-capacity.md) |
| **Disk** | > 85% on the Postgres volume | The one failure that corrupts rather than degrades. | [restore-from-backup.md](../07-ops/runbooks/restore-from-backup.md) |
| **Projection drift** | `reconcile_drift_total > 0` | IAM and the legacy `globals_*` tables disagree — someone hand-edited, or the projector is broken. | [legacy-compatibility-and-erp-projection.md](../02-iam/legacy-compatibility-and-erp-projection.md) |

### Warn-only (dashboard, no page)

`iam_refresh_reuse_detected_total > 0` · `academics_snapshot_mismatch_total > 0` ·
`event_consumed_total{outcome="failed"}` rate > 1% · a PII export outside working hours ·
`iam_lockout_total` spike.

`reconcile_drift_total > 0` is a page rather than a warning specifically because intentional gaps (H1
multi-holder roles) are **allowlisted**, so the steady state is exactly zero and any non-zero value is a real
problem. That property is what makes the alert worth having at all.

---

## Dashboards

**Service health** — request rate, error rate, p50/p95/p99, in-flight, database connections, per service.

**Event pipeline** — `outbox_pending_rows` and `outbox_lag_seconds` per topic, queue depths, task duration,
failure rate. The single most useful page during an incident, because almost every cross-boundary symptom
shows up here first.

**Auth** — logins by outcome, lockouts, refresh reuse, step-up rate, active sessions.

**Academic integration** — declarations ingested, ingest duration, standings updated, snapshot mismatches,
retraction count.

**Placement (seasonal)** — applications submitted per hour, offers issued and accepted, eligibility evaluation
duration, export count. Watched live on deadline days.

---

## Retention

| | Retention |
|---|---|
| journald logs | 30 days, capped at 4 GB |
| Prometheus | 90 days |
| Sentry | per plan, typically 90 days |
| `audit_event` | **3 years**, then archived, never deleted |
| `identity_login_attempt` | 90 days |
| `outbox_event` / `inbox_event` | 30 days after consumption |

The audit table is the one with a legal-ish shape, and it is append-only at the database level
(`UPDATE`/`DELETE` revoked for `iam_app`).

---

## What we deliberately do not do

| Not doing | Why |
|---|---|
| A full ELK / OpenTelemetry collector stack | journald + Prometheus + Sentry answers the questions we actually have, on hardware we actually own |
| Distributed tracing across services | Two services, one VM. `request_id` correlation is sufficient. |
| Log every request body | A PII leak waiting to happen, and no question needs it |
| Alert on every anomaly | Six actionable alerts beat sixty ignored ones |
| Synthetic monitoring beyond `/healthz` | Revisit if uptime becomes a stated commitment |

---

## Verification

- Every response carries `X-Request-ID`; it matches the envelope's `request_id` and appears in the log line.
- A deliberately-triggered 500 produces a Sentry event whose `request_id` joins to the log line.
- The redaction processor strips every listed key, including nested — property-tested.
- No log line ever contains a request body — asserted by a test that posts a password and greps the output.
- `db_queries` and `db_time_ms` are present on every request line.
- `/healthz` still returns 200 with the database stopped; `/readyz` returns 503.
- Each of the six alerts fires against a synthetic condition in staging, and its runbook resolves it.
- `path_template`, not the raw path, is the metric label — asserted by a cardinality test.
