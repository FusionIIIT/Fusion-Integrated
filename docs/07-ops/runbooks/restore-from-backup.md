# Runbook — Restore from Backup

**Risk: the highest of any procedure here.** Escalate before starting. Two people, one driving, one reading
this document aloud.

> **Phase 1 deliverable:** this must be **executed for real on a scratch host**, and the measured elapsed time
> written into §7 below. An untested restore procedure is not a backup strategy.

```bash
BACKUP_DIR=/var/backups/fusion
TARGET_TIME='2026-08-01 09:30:00+05:30'      # for PITR
```

---

## 1. Decide what you are actually doing

| Situation | Procedure | Blast radius |
|---|---|---|
| One table's rows wrong | §4 — single-table restore into a scratch schema, then copy rows | small |
| One database corrupt | §5 — full database restore | that database |
| Cluster lost / disk failure | §6 — PITR from base backup + WAL | everything |
| Accidental `DELETE`/`UPDATE`, recent | §6 PITR to just before it | everything |
| A bad migration | → [rollback.md](rollback.md) §3 first | — |

**Do not restore a whole cluster to fix one table.** §4 exists for that.

---

## 2. Stop writes first

```bash
sudo systemctl stop fusion-platform fusion-iam
sudo systemctl stop 'fusion-platform-worker@*' 'fusion-iam-worker@*' fusion-platform-beat
```

Leave the **legacy monolith running** unless the ERP itself is the problem — academic services are independent
of ours, and there is no reason to extend the outage.

```bash
# Confirm nothing is writing.
psql -c "SELECT datname, count(*) FROM pg_stat_activity
         WHERE state='active' AND datname LIKE 'fusion%' GROUP BY 1;"
```

---

## 3. Take a snapshot of the current (broken) state

**Do this before anything else.** You may need it, and after a restore it is gone forever.

```bash
mkdir -p "$BACKUP_DIR/pre-restore-$(date +%s)" && cd "$_"
pg_dump -Fc fusion_nonacad   > nonacad.dump
pg_dump -Fc fusion_system_db > system.dump
```

---

## 4. Single table (preferred where possible)

```bash
DB=fusion_nonacad
TABLE=placement_application

createdb scratch_restore
pg_restore -d scratch_restore -t "$TABLE" "$BACKUP_DIR/latest/$DB.dump"

psql scratch_restore -c "SELECT count(*) FROM $TABLE;"      # sanity-check first
```

Then copy only what you need, inside a transaction:

```sql
BEGIN;
INSERT INTO placement_application
SELECT * FROM scratch_restore.public.placement_application s
WHERE s.id NOT IN (SELECT id FROM placement_application);
-- verify counts, THEN commit
COMMIT;
```

```bash
dropdb scratch_restore
```

**Never `TRUNCATE` and reload** a table that others reference. Cross-boundary references are unconstrained
integers ([ADR-0013](../../01-architecture/adr/0013-no-cross-module-foreign-keys.md)), so the database will not
stop you from orphaning them.

---

## 5. Full database restore

**Destroys the current contents of that database.** §3 first.

```bash
DB=fusion_nonacad

sudo -u postgres psql -c "ALTER DATABASE $DB RENAME TO ${DB}_broken_$(date +%s);"
sudo -u postgres createdb -O platform_migrator "$DB"
pg_restore -d "$DB" -j 4 "$BACKUP_DIR/latest/$DB.dump"
psql -f /srv/fusion/platform/current/ops/db/roles.sql      # grants are not in the dump
```

Renaming rather than dropping means the broken database is still there if the restore turns out worse.

---

## 6. Point-in-time recovery (whole cluster)

**Everything is affected, including the ERP.** Escalate first. This is the procedure for disk failure or a
destructive statement you need to rewind past.

```bash
sudo systemctl stop postgresql
sudo mv /var/lib/postgresql/16/main /var/lib/postgresql/16/main.broken

sudo -u postgres tar -xzf "$BACKUP_DIR/base/latest.tar.gz" -C /var/lib/postgresql/16/

sudo -u postgres tee /var/lib/postgresql/16/main/recovery.signal >/dev/null <<'EOF'
EOF
sudo -u postgres tee -a /var/lib/postgresql/16/main/postgresql.auto.conf >/dev/null <<EOF
restore_command = 'cp $BACKUP_DIR/wal/%f %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_action = 'promote'
EOF

sudo systemctl start postgresql
sudo -u postgres tail -f /var/log/postgresql/postgresql-16-main.log   # watch for "recovery complete"
```

---

## 7. Restore order — this matters

IAM holds `erp_user_id` values that reference the ERP's `auth_user`, with **no foreign key** to enforce it
([ADR-0002](../../01-architecture/adr/0002-separate-iam-service-and-database.md)). So:

```
1. fusion_newui_prod      the reference TARGET — first
2. fusion_system_db       IAM + console
3. fusion_nonacad         platform
4. manage.py reconcile_erp_projection --mode=enforce
5. manage.py verify_snapshots --full
```

Restoring IAM to an **earlier** point than the ERP is safe — every `erp_user_id` it holds still exists.
Restoring it **later** can leave IAM pointing at rows that do not exist yet. Hence the ordering, and hence the
reconciler running last.

The reconciler **reports** dangling `erp_user_id`s; it never invents users. Those need a human.

```bash
cd /srv/fusion/iam/current
sudo -u fusion venv/bin/python manage.py reconcile_erp_projection --mode=enforce
cd /srv/fusion/platform/current
sudo -u fusion venv/bin/python manage.py verify_snapshots --full
```

### Measured timings

Fill these in from the Phase 1 drill. Estimates are not useful during an incident.

| Step | Estimated | **Measured** | Date |
|---|---|---|---|
| `pg_restore fusion_nonacad` | ~5 min | *pending* | |
| `pg_restore fusion_system_db` | ~2 min | *pending* | |
| `pg_restore fusion_newui_prod` | ~15 min | *pending* | |
| PITR full cluster | ~40 min | *pending* | |
| `reconcile_erp_projection --enforce` | ~3 min | *pending* | |
| `verify_snapshots --full` | ~10 min | *pending* | |
| **Total, worst case** | **~75 min** | *pending* | |

---

## 8. Restart and verify

```bash
sudo systemctl start fusion-iam fusion-platform
sudo systemctl start 'fusion-platform-worker@*' 'fusion-iam-worker@*' fusion-platform-beat
sudo -u fusion /srv/fusion/ops/deploy/smoke.sh platform
sudo -u fusion /srv/fusion/ops/deploy/smoke.sh iam
```

- [ ] `/readyz` green on both services
- [ ] A real login at `/app/` works; the sidebar renders
- [ ] The legacy app responds (`/api/auth/me` → 401)
- [ ] `reconcile_erp_projection --mode=report` → **0 drift**
- [ ] `verify_snapshots --full` → **0 mismatches**
- [ ] Row counts on the key tables match expectation:

```sql
SELECT 'users',    count(*) FROM iam.identity_user
UNION ALL SELECT 'roles',        count(*) FROM iam.rbac_user_role
UNION ALL SELECT 'applications', count(*) FROM placement_application
UNION ALL SELECT 'offers',       count(*) FROM placement_offer
UNION ALL SELECT 'records',      count(*) FROM placement_placementrecord
UNION ALL SELECT 'snapshots',    count(*) FROM academics_resultsnapshot;
```

- [ ] `outbox_pending_rows` drains rather than growing
- [ ] Placement: exactly one **active** `PlacementRecord` per `(user, year)`:

```sql
SELECT user_id, placement_year_id, count(*) FROM placement_placementrecord
WHERE is_active GROUP BY 1,2 HAVING count(*) > 1;      -- must return zero rows
```

---

## 9. Afterwards

- **A restored backup contains full PII.** Any scratch host used is treated as production, and is wiped when
  done ([data-retention-and-privacy.md](../../06-crosscutting/data-retention-and-privacy.md)).
- Keep the broken database (`*_broken_<ts>`) for 7 days, then drop it.
- Record actual timings in §7. Those numbers are the point of the drill.
- Write up the data-loss window: what was lost between the backup and the incident, and who needs telling.
- If `verify_snapshots` found mismatches, → [reingest-academic-snapshot.md](reingest-academic-snapshot.md).

## Quarterly drill

Restore the previous night's backup onto a scratch host. Time every step. Update §7. If the drill takes longer
than the table says, the table was wrong — and it would have been wrong during a real incident.
