# FTS Operations & Observability Guide

**Module**: File Tracking System (`fts`)  
**Directory**: `modules/fts/`

---

## 1. Celery Background Tasks & Schedules

FTS registers periodic background schedules in `modules/fts/schedule.py` integrated into `config/celery.py`:

| Task Name | Schedule | Queue | Purpose |
|---|---|---|---|
| `modules.fts.tasks.dispatch_fts_notifications` | Every 5 minutes (`*/5 * * * *`) | `fts` | Dispatches pending movement alerts and emails to file recipients. |
| `modules.fts.tasks.verify_fts_audit_integrity` | Nightly at 02:30 IST (`30 2 * * *`) | `fts` | Validates hash/sequence continuity of all movement records across active files. |

### Routing
Registered in `config/celery.py`:
```python
FTS_ROUTES = {
    "modules.fts.tasks.*": {"queue": "fts"},
}
```

---

## 2. Management Commands

### 2.1 Demo Seeding: `seed_fts_demo`
Seeds realistic institute file tracking scenarios across synthetic users:
```bash
python manage.py seed_fts_demo
```
Creates:
- Pre-circulation drafts (e.g., Equipment purchase request).
- Active circulated files with multi-step forwarding history.
- Historical audit events and movement comments.

### 2.2 Operational Health Check: `fts_scheduled_work_status`
Reports operational health, backlog, lag, and audit integrity:
```bash
python manage.py fts_scheduled_work_status
```
Example Output:
```
  notifications pending: 0
  oldest pending lag:    0s
  audit integrity valid: True
  FTS scheduled work looks healthy
```

---

## 3. Query Budgets & Performance

FTS query paths are bounded to avoid N+1 query degradation:
1. **Inbox & Outbox listings**: Single SQL query with selective indexing (`current_holder_user_id`, `status`). Budget: `<= 4 queries`.
2. **File Detail with History**: Eager loading with `prefetch_related("comments", "attachments")`. Budget: `<= 5 queries`.
3. **Contracts Plural Lookups**: Batch lookups using `pk__in=file_ids` and dictionary comprehension. Budget: `<= 2 queries` regardless of sequence size.

---

## 4. Runbook & Troubleshooting

### Scenario: High Notification Lag
- **Symptom**: `fts_scheduled_work_status` reports `notifications pending > 100` or `oldest pending lag > 10m`.
- **Resolution**:
  1. Verify Celery worker is running: `celery -A config worker -l info -Q fts,celery`.
  2. Inspect Redis broker health: `docker exec -it redis-broker redis-cli ping`.
  3. Manually trigger notification dispatch via Django shell:
     ```python
     from modules.fts.tasks import dispatch_fts_notifications

     dispatch_fts_notifications.delay()
```

### Scenario: Audit Continuity Mismatch
- **Symptom**: `verify_fts_audit_integrity` flags sequence discontinuity.
- **Resolution**:
  1. Inspect `modules_fts_filemovement` for sequence gaps:
     ```sql
     SELECT file_id, sequence, movement_type, created_at 
     FROM modules_fts_filemovement 
     WHERE file_id = :id ORDER BY sequence ASC;
     ```
  2. Cross-reference `modules_fts_fileauditlog` to check actor action timestamps.
