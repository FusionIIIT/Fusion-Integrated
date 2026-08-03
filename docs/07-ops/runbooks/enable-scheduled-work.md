# Runbook — enabling scheduled work (Celery beat)

Until beat runs, three things simply do not happen:

| Task | Every | What stops without it |
|---|---|---|
| `placement.deliver_notifications` | 60 s | Nothing is ever emailed. The outbox grows. |
| `placement.expire_overdue_offers` | 5 min | **An unanswered offer never expires**, so the student stays blocked from the pool with no way out but a database edit. |
| `placement.rebuild_active_stats` | 15 min | The statistics page serves stale snapshots. |

The second is the reason this is not optional.

---

## Before you enable anything

### 1. Count what is queued — do this first

Turning on the drain sends **every pending row at once**. On a database that has
been seeded, restored from a dump, or used for testing, those rows may name real
students.

```
$MANAGE send_notifications --status
```

If `pending` is larger than you can account for, stop and look at who they are
addressed to:

```
$MANAGE shell -c "
from modules.placement.models import NotificationOutbox as O
for r in O.objects.filter(status='pending')[:40]:
    print(r.topic, r.recipient_email or r.recipient_user_id)
"
```

Suppress anything that should not go out **before** starting the worker:

```
$MANAGE shell -c "
from modules.placement.models import NotificationOutbox as O
O.objects.filter(status='pending', topic='posting.published').update(
    status='suppressed', last_error='Backlog from seeding; not sent.')
"
```

`suppressed` is the right state, not deleted — the row is why the decision was
made, and PC-BR-021 keeps that history.

### 2. Confirm the mail backend is the one you mean

```
$MANAGE shell -c "from django.conf import settings; print(settings.EMAIL_BACKEND)"
```

`console.EmailBackend` sends nothing. On a host that is meant to be sending,
that is a misconfiguration; on a staging host it is the point.

### 3. Confirm no other host is already running beat

Two schedulers double every tick. The outbox claim makes a duplicate *send*
harmless, but nothing makes a duplicate *scheduler* harmless.

```
# on every application host
systemctl is-enabled fusion-platform-beat 2>/dev/null || echo "not enabled here"
```

Exactly one must answer `enabled`.

---

## Enable

Workers first. Beat only dispatches; with no worker the messages queue and then
expire silently, which looks identical to beat not running.

```
cp ops/systemd/fusion-platform-worker@.service /etc/systemd/system/
cp ops/systemd/fusion-platform-beat.service     /etc/systemd/system/
systemctl daemon-reload

systemctl enable --now fusion-platform-worker@default
systemctl enable --now fusion-platform-worker@notifications
systemctl enable --now fusion-platform-worker@reports

# ONE host only.
systemctl enable --now fusion-platform-beat
```

---

## Verify

Within about ninety seconds:

```
journalctl -u fusion-platform-beat -n 20 --no-pager
#   Scheduler: Sending due task placement.deliver-notifications

journalctl -u fusion-platform-worker@notifications -n 20 --no-pager
#   Task placement.deliver_notifications[...] succeeded
```

Then confirm work actually moved, not just that tasks ran:

```
$MANAGE send_notifications --status      # pending should be falling
```

And that the queues are being drained rather than filling:

```
redis-cli -p 6380 llen notifications     # should sit near 0
redis-cli -p 6380 llen default
redis-cli -p 6380 llen reports
```

A queue that only grows means beat is dispatching to a queue no worker is
consuming. Check the `--queues` argument against
`modules/<module>/schedule.py`'s `TASK_ROUTES`.

---

## Rollback

```
systemctl disable --now fusion-platform-beat
```

Nothing is lost. Beat holds no work of its own — it only dispatches, and the
tasks are idempotent. Workers may stay running; with no beat they simply have
nothing to do, and anything already queued still gets processed.

To stop delivery specifically while leaving the rest scheduled, point the mail
backend at the console and reload — the outbox keeps accumulating and drains
when you put it back.

---

## Known gotchas

- **Beat's schedule file** lives at `/var/lib/fusion/celerybeat-schedule` and is
  its only state. Deleting it makes every entry fire once on the next start.
  That is safe — the tasks are idempotent — but it is a burst.
- **`redis-broker` must be `noeviction`.** An LRU broker silently drops queued
  tasks under memory pressure, which presents as work quietly not happening.
  See `docker-compose.yml`, where the same rule is written down.
- **A 15-minute crontab entry uses `CELERY_TIMEZONE`**, which is pinned to
  `TIME_ZONE` (Asia/Kolkata). A host in UTC still fires correctly.
- **`--max-tasks-per-child=500`** recycles workers, so slow memory growth never
  needs investigating.
