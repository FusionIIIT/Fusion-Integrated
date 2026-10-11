---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
enforced-by: >
  Contract tests assert that every topic listed here has a pydantic model in
  packages/fusion_contracts, and that every model in fusion_contracts appears here.
  A topic that exists in code but not in this document fails CI.
---

# Event Catalog

Every integration event in the system. Adding a topic means adding a row here, a pydantic model in
`packages/fusion_contracts`, and a contract test on both the producer and every consumer.

---

## Mechanics

**Transport is the transactional outbox, not a broker.** A write and its event commit in one database
transaction, so an event can never be lost, and never fires for a rolled-back write.

```python
# producer — inside the service function's transaction
with transaction.atomic():
    offer.status = "accepted"
    offer.save(update_fields=["status", "decided_at"])
    PlacementRecord.objects.create(...)
    emit("placement.offer.accepted", payload, dedupe_key=f"offer.accepted:{offer.id}")
```

```python
# consumer — idempotent by construction
@shared_task(acks_late=True, autoretry_for=(OperationalError,), retry_backoff=True,
             retry_jitter=True, max_retries=8)
def on_offer_accepted(event_id: int) -> None:
    event = OutboxEvent.objects.get(pk=event_id)
    _, created = InboxEvent.objects.get_or_create(dedupe_key=event.dedupe_key,
                                                 consumer="notifications")
    if not created:
        return                      # already handled — redelivery is a no-op
    ...
```

A `publish_outbox` beat task runs every 5 seconds, claims pending rows with
`SELECT ... FOR UPDATE SKIP LOCKED`, and dispatches one Celery task per consumer.

### Envelope

Every payload is wrapped identically:

```json
{
  "topic": "placement.offer.accepted",
  "version": 1,
  "event_id": "018f...",              // UUIDv7 — sortable, so it doubles as a sequence hint
  "occurred_at": "2026-08-01T10:04:22.117Z",
  "producer": "fusion-platform@a1b2c3d",
  "actor_user_id": 1234,              // null for system-originated events
  "request_id": "9f2c...",            // ties the event to the HTTP request that caused it
  "dedupe_key": "offer.accepted:8812",
  "data": { ... }                     // topic-specific, schema in fusion_contracts
}
```

### Guarantees

| Property | Guarantee |
|---|---|
| Delivery | **At least once.** Every consumer must be idempotent. There is no exactly-once. |
| Ordering | **Per aggregate only**, via task routing on the aggregate key. No global order. Consumers that care about order must be written to tolerate arrival out of order (see the `declared_seq` guard in `academics.result.declared`). |
| Durability | Committed with the write. Broker loss delays but never drops — rows stay in `outbox_event` until consumed. |
| Retention | `outbox_event` 30 days after `consumed_at`, then purged. `inbox_event` 30 days. |
| Latency | < 10 s typical, alert at `outbox_lag > 300 s`. |
| Schema evolution | **Additive fields are safe.** Removing or re-typing a field is a new `version`, and both versions must be handled for one release. |

### Versioning

`version` is per topic, in the envelope, not in the topic name. A consumer that sees an unknown version
raises rather than guessing — fail loud, never fail silent.

---

## Topics

### IAM — `iam.*`

Producer: `fusion-iam`.

| Topic | Payload `data` | Consumers | Notes |
|---|---|---|---|
| `iam.user.created` | `user_id, erp_user_id, username, email, display_name, kind` | ERP projector, `directory` | The ERP `auth_user` projection is **synchronous** at creation (see [data-ownership](data-ownership-and-sync.md#the-one-deliberate-exception)); this event covers the rest. |
| `iam.user.updated` | `user_id, changed: {field: [old, new]}` | ERP projector, `directory` | `changed` carries only the fields that moved |
| `iam.user.status_changed` | `user_id, from_status, to_status, reason` | ERP projector, `directory`, `placement` | `suspended`/`archived` ⇒ platform flags in-flight work; **never auto-rejects** |
| `iam.role.assigned` | `user_id, role_code, scope_type, scope_id, kind, is_primary, valid_from, valid_to` | ERP projector, `notifications` | Routed by `user_id` so two changes for one person cannot interleave |
| `iam.role.revoked` | `user_id, role_code, scope_type, scope_id, reason` | ERP projector, `notifications`, `placement` | |
| `iam.role.permissions_changed` | `role_code, added[], removed[], permission_version` | cache warmers | Bumps `pv`, which invalidates every derived cache by key |
| `iam.module.granted` / `.revoked` | `role_code, module_code` | ERP projector | Projects into `globals_moduleaccess` |
| `iam.session.role_switched` | `user_id, session_id, from_role, to_role` | ERP projector | Projects `ExtraInfo.last_selected_role` — subject to hazard **H3** (20-char column) |
| `iam.session.revoked` | `user_id, session_id, reason` | — | Redis denylist is written synchronously; this event is for audit only |
| `iam.credential.changed` | `user_id, kind` (`password` \| `mfa`) | `notifications` | Payload carries **no** secret material, ever |

### Academics — `academics.*`

Producers: the **legacy monolith** (`examination` app) for the first two; `fusion-platform`
(`modules/academics`) for the rest.

| Topic | Producer | Payload `data` | Consumers |
|---|---|---|---|
| `academics.result.declared` | legacy | `announcement_id, batch_id, semester, semester_type, per_student_selection, declared_at` | platform `academics` ingest |
| `academics.result.retracted` | legacy | `announcement_id, retracted_at, reason` | platform `academics` ingest |
| `academics.declaration.ingested` | platform | `declaration_id, student_count, chunks, duration_ms` | observability only |
| `academics.standing.changed` | platform | `user_id, standing_version, cpi, semester, semester_type, declared_seq, declared_at, previous_cpi` | `placement` |

Legacy production detail — the only new table in the monolith:

```python
class ExamOutboxEvent(models.Model):
    topic       = models.CharField(max_length=80)
    payload     = models.JSONField()
    dedupe_key  = models.CharField(max_length=160, unique=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        indexes = [models.Index(fields=["consumed_at", "id"], name="examoutbox_pending_idx")]
```

Written inside the existing `transaction.atomic()` in the announce/publish path
(`applications/examination/api/views.py:3235-3260` and `3411-3456`). The platform polls it over the
read-only ERP connection and marks rows consumed through a single narrow RPC.

> **`academics.result.declared` may arrive out of order** — for instance Sem 5 before a late Sem 3
> correction. This is safe: the ingest upsert's `WHERE EXCLUDED.declared_seq > current.declared_seq`
> clause makes an older declaration a no-op against standing, while still recording its snapshot.
> There is a test for exactly this. → [academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md)

### Placement — `placement.*`

Producer: `fusion-platform` (`modules/placement`).

| Topic | Payload `data` | Consumers |
|---|---|---|
| `placement.year.opened` / `.closed` | `placement_year_id, code` | `notifications` |
| `placement.registration.created` | `placement_year_id, user_id` | `notifications` |
| `placement.registration.status_changed` | `placement_year_id, user_id, from, to, reason` | `notifications` — covers debarment |
| `placement.posting.published` | `posting_id, company_id, title, application_closes_at, eligibility_rule_hash` | `notifications` (**digestable**), eligibility precompute |
| `placement.posting.closed` | `posting_id, application_count` | `notifications` |
| `placement.posting.cancelled` | `posting_id, reason` | `notifications`, applications → `AUTO_WITHDRAWN` |
| `placement.application.submitted` | `posting_id, application_id, user_id, cpi_at_apply, standing_version_at_apply` | `notifications`, stats debounce |
| `placement.application.status_changed` | `application_id, user_id, from, to, actor_user_id, reason` | `notifications` |
| `placement.round.scheduled` | `round_id, posting_id, seq, kind, starts_at, participant_count` | `notifications` |
| `placement.round.result_recorded` | `round_id, passed[], failed[], absent[]` | `notifications` |
| `placement.offer.issued` | `offer_id, posting_id, user_id, ctc_lpa, tier_rank, is_dream, respond_by` | `notifications`, stats debounce |
| `placement.offer.accepted` | `offer_id, user_id, placement_record_id, superseded_offer_id, policy_decision` | `notifications`, stats debounce, auto-withdraw |
| `placement.offer.declined` / `.expired` | `offer_id, user_id` | `notifications` |
| `placement.offer.revoked` | `offer_id, user_id, reason, actor_user_id` | `notifications`, stats debounce — **`is_dangerous`, requires step-up auth** |
| `placement.stats.refreshed` | `placement_year_id, dimensions[], computed_at` | observability only |

### HR / Leave — `hr.*`, `leave.*`

Phase 6. Placeholders so the naming is settled now:
`hr.employee.created`, `hr.employment.changed`, `hr.employment.ended`,
`leave.request.submitted`, `leave.request.decided`, `leave.balance.adjusted`.

### Notifications — `notification.*`

Producer: `fusion-platform` (`modules/notifications`). Terminal — nothing consumes these; they exist
for observability and for the digest builder.

`notification.queued`, `notification.sent`, `notification.failed`, `notification.suppressed`.

---

## Fan-out reference

| Topic | Consumers |
|---|---|
| `iam.role.assigned` | ERP projector · notifications |
| `iam.user.status_changed` | ERP projector · directory · placement |
| `academics.standing.changed` | placement (eligibility invalidation + review flags) |
| `placement.offer.accepted` | notifications · stats (debounced 60 s) · auto-withdraw |
| `placement.posting.published` | notifications (digestable) · eligibility precompute |

---

## Consumer obligations

Every consumer **MUST**:

1. Check `inbox_event.dedupe_key` before acting. At-least-once delivery is the contract.
2. Tolerate out-of-order arrival within its aggregate, or guard against it explicitly (as the
   `declared_seq` upsert does).
3. Validate `data` against its `fusion_contracts` model and **raise** on an unknown `version`.
4. Be safe to replay from any point. Replaying the last 24 hours of events must not corrupt state.
5. Never call another module's internals — only `contracts.py`.
6. Never block on a synchronous HTTP call to a third party without a timeout and a retry budget.

Every consumer **MUST NOT**:

1. Assume it is the only consumer.
2. Assume the producer's transaction is still open (it is not — the event fires post-commit).
3. Mutate the event.
4. Emit a new event that its own handler consumes, directly or transitively. There is a CI check for
   cycles in the producer/consumer graph.

---

## Notification rules are data, not code

Event → notification mapping lives in tables, not in `if` chains:

```
NotificationTemplate(code UNIQUE, channel enum{in_app,email}, subject, body_md, variables jsonb)
NotificationRule(event_topic, audience_selector jsonb, template FK, is_active, digestable bool)
NotificationOutbox(recipient_user_id, channel, template FK, context jsonb,
                   status enum{queued,sent,failed,suppressed}, attempts,
                   sent_at, error, dedupe_key UNIQUE)
```

`digestable = True` rules batch into a daily digest, and each recipient is capped at 20 emails per
day with the overflow forced into the digest. Without this, publishing 30 postings on deadline day
sends every student 30 emails.

---

## Observability

Per-topic metrics: `outbox_pending_rows{topic}`, `outbox_lag_seconds{topic}`,
`event_consumed_total{topic,consumer,outcome}`, `event_handler_duration_seconds{topic,consumer}`.

Alerts: `outbox_lag_seconds > 300` (any topic) · `celery_queue_depth{queue="ingest"} > 500` ·
`event_consumed_total{outcome="failed"}` rate > 1% over 10 minutes.

Every event log line carries `event_id`, `topic`, `dedupe_key` and the originating `request_id`, so a
user-visible action can be traced end to end from one id read off an error toast.

---

## Adding a topic — checklist

- [ ] Row added to the relevant table in this document
- [ ] Pydantic model in `packages/fusion_contracts/<domain>.py`, `version = 1`
- [ ] Producer emits inside the write's transaction, with a deterministic `dedupe_key`
- [ ] Every consumer registered, idempotent, and listed in the fan-out table above
- [ ] Contract test on producer **and** each consumer
- [ ] Replay test: deliver twice, assert no state change on the second
- [ ] If ordering matters: an out-of-order delivery test
- [ ] Notification rule row, if it should notify anyone
- [ ] No cycle introduced (CI checks the graph)
