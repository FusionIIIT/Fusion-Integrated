# Runbook — Rollback

**Time:** ~60 s. **Risk:** low for code, **high if a migration must be reversed** — read §3 before touching one.

```bash
SVC=platform
```

---

## 1. Decide fast

Roll back **now** if: error rate is up, p95 is over budget, users report breakage, or a new `CRITICAL` log line
appeared. Rolling back is cheap; debugging in production is not.

Do **not** roll back if the problem is data rather than code — a rollback will not fix bad data, and may make
it harder to reason about. Escalate instead.

---

## 2. Code rollback

```bash
ls -la /srv/fusion/$SVC/           # note where `current` points
ls -1t /srv/fusion/$SVC/releases/  # newest first

sudo -u fusion /srv/fusion/ops/deploy/rollback.sh "$SVC"
```

Or by hand:

```bash
PREV=/srv/fusion/$SVC/releases/<previous-sha>
sudo -u fusion ln -sfn "$PREV" /srv/fusion/$SVC/current
sudo systemctl reload "fusion-$SVC"
sudo systemctl restart "fusion-$SVC-worker@*" "fusion-$SVC-beat"
sudo -u fusion /srv/fusion/ops/deploy/smoke.sh "$SVC"
```

Frontend: swap `/srv/fusion/shell/current`. No restart needed.

---

## 3. Migrations — the part that needs care

**Code rollback does not undo a migration.**

This is why the deploy rule is **expand → migrate → contract across two releases**: the previous release must
still work against the new schema. If that rule was followed, a code rollback is safe and you are done.

```bash
# What ran in this release?
sudo -u fusion /srv/fusion/$SVC/venv/bin/python manage.py showmigrations --plan | tail -20
```

| Migration type | Safe to leave applied? | Action |
|---|---|---|
| `AddField` (nullable / with default) | **yes** | leave it. The old code ignores the column. |
| `AddIndex` (`CONCURRENTLY`) | **yes** | leave it |
| `CreateModel` | **yes** | leave it |
| `AlterField` widening (e.g. `varchar(20)` → `varchar(64)`) | **yes** | leave it |
| `RemoveField` / `DeleteModel` | **no — data is gone** | → §4 |
| `AlterField` narrowing or re-typing | **no** | → §4 |
| `RenameField` | **no** | → §4 |

**Django migrations are not reliably reversible, and `migrate <app> <prev>` can lose data.** Do not run it
reflexively.

If a reverse is genuinely required and the migration is declared reversible:

```bash
# STOP. This can destroy data. Take a dump first, and escalate.
pg_dump -Fc fusion_nonacad > /var/backups/pre-reverse-$(date +%s).dump
sudo -u fusion manage.py migrate <app> <previous_migration_number>
```

`django-migration-linter` blocks unsafe operations in CI, so reaching this section usually means the two-release
rule was skipped. Note that in the incident write-up.

---

## 4. Data was lost or corrupted

Stop. Do not improvise. → [restore-from-backup.md](restore-from-backup.md), and escalate to the platform lead.

---

## 5. Feature-flag rollback — usually the better option

Many changes can be neutralized without touching code:

```bash
sudo sed -i 's/^IAM_JWT_AUTH_ENABLED=1/IAM_JWT_AUTH_ENABLED=0/' /etc/fusion/legacy.env
sudo systemctl restart fusion
```

| Flag | Effect when off |
|---|---|
| `IAM_JWT_AUTH_ENABLED` | legacy/console stop accepting IAM cookies; existing DRF tokens still work — **nobody has to log in again** |
| `IAM_LOGIN_ENABLED` | `/app/login` redirects to the legacy login |
| `IAM_IS_ROLE_WRITER` | the projector pauses; events queue in `outbox_event`, nothing is lost |
| `ACADEMICS_INGEST_ENABLED` | declaration ingest stops; standings stay at the last declaration |

**Prefer a flag flip to a code rollback** when one exists. It is faster, narrower, and reversible in both
directions.

---

## 6. Verify

```bash
sudo -u fusion /srv/fusion/ops/deploy/smoke.sh "$SVC"
curl -s -o /dev/null -w '%{http_code}\n' https://fusion.iiitdmj.ac.in/api/auth/me   # legacy alive → 401
```

- [ ] Error rate back to baseline
- [ ] p95 within budget
- [ ] `outbox_lag_seconds` < 60 and falling
- [ ] `celery_queue_depth` draining
- [ ] A manual login at `/app/` works and the sidebar renders

---

## 7. Afterwards

- Write it up **the same day**: what shipped, what broke, what the signal was, how long detection took.
- Add the test that would have caught it. This is the deliverable — not the write-up.
- If a migration made rollback hard, note which rule was skipped.
- If the smoke test passed but the deploy was bad, the smoke test needs a new assertion.

---

## Quarterly drill

Roll back staging to the previous release and back again. Time it. If the drill finds a gap in this document,
that gap would have been found during a real incident instead.
