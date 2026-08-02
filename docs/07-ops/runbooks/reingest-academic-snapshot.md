# Runbook — Re-ingest an Academic Snapshot

**Time:** ~1 min per 50 students. **Risk:** low — snapshots are immutable and ingest is idempotent.

Read [academic-snapshot-integration.md](../../04-placement/academic-snapshot-integration.md) before making a
judgement call here. The grade semantics are counter-intuitive (`F` earns 2.0 points and its credit; `S` earns
credit but no average; `X`/`CD` are excluded entirely) and a "wrong" CPI is usually correct.

```bash
cd /srv/fusion/platform/current
MANAGE="sudo -u fusion venv/bin/python manage.py"
ANN=812        # ERP ResultAnnouncement id
```

---

## When to use this

| Situation | Action |
|---|---|
| `SnapshotIngestRun.status = failed` | §2 |
| A declaration announced but no standings updated | §2 |
| `academics_snapshot_mismatch_total > 0` (nightly verify) | §4 — **investigate before re-ingesting** |
| A result was retracted and standings look wrong | §5 |
| Ingest queue backed up (`celery_queue_depth{ingest} > 500`) | §3 |
| A student says their CPI is wrong | §6 — usually not a bug |

---

## 1. Diagnose first

```bash
$MANAGE shell -c "
from modules.academics.models import ResultDeclaration, SnapshotIngestRun
d = ResultDeclaration.objects.get(erp_announcement_id=$ANN)
print(d.id, d.batch_label, d.semester, d.semester_type, 'seq', d.declared_seq)
print('declared', d.declared_at, 'ingested', d.ingested_at, 'retracted', d.retracted_at)
print('students', d.student_count, 'snapshots', d.snapshots.count())
for r in SnapshotIngestRun.objects.filter(declaration=d).order_by('-started_at')[:3]:
    print(r.status, r.chunks_done, '/', r.chunks_total, r.error[:300])
"
```

```bash
# Is the ERP-side endpoint healthy? (127.0.0.1 only — never exposed by nginx.)
curl -sS -X POST http://127.0.0.1:8000/api/examination/internal/academic-snapshot/ \
  -H "Authorization: Bearer $($MANAGE mint_service_token --scope academics:snapshot:read)" \
  -H 'Content-Type: application/json' \
  -d "{\"announcement_id\": $ANN, \"offset\": 0, \"limit\": 1}" | jq '.announcement, .total'
```

Common causes, in order of likelihood:

| Error | Cause | Fix |
|---|---|---|
| `connection refused` | legacy monolith down | start it; ingest retries automatically (8 attempts, backoff) |
| `401`/`403` | service token expired or scope missing | tokens are 5-minute; check `IAM_SERVICE_TOKEN_KEY_PATH` |
| `announcement not found` | deleted in the ERP | → §5, treat as a retraction |
| `announced: false` | un-announced after the event fired | correct — nothing to ingest |
| `semester_type: null` | a pre-migration-`0003` legacy row | **cannot be ingested.** See the note in §7. |
| `roll_no not resolvable` | no `directory_userref` for that student | run the directory reconcile first |
| `soft_time_limit` exceeded | chunk too large or ERP slow | leave `ACADEMICS_INGEST_CHUNK_SIZE` at 50; do not raise it |

---

## 2. Re-ingest

Safe to run repeatedly. `ResultSnapshot` is inserted with `ignore_conflicts=True`, and `UPDATE`/`DELETE` are
revoked at the database level — so a re-run cannot alter an existing snapshot.

```bash
$MANAGE ingest_declaration --announcement-id $ANN
```

Resume from a specific chunk if a long run failed partway:

```bash
$MANAGE ingest_declaration --announcement-id $ANN --offset 150
```

Watch it:

```bash
journalctl -u 'fusion-platform-worker@ingest' -f | grep -E "$ANN|ingest"
```

---

## 3. Queue backed up

```bash
redis-cli -p 6380 llen ingest
systemctl status 'fusion-platform-worker@ingest'
```

The `ingest` worker runs at **concurrency 1, prefetch 1, deliberately** — a 300-student declaration is roughly
1,500 ERP queries, and serializing it keeps the ERP's connection pool comfortable when two batches are declared
minutes apart.

**Do not raise the concurrency to drain the queue faster.** That is how a declaration turns into an ERP
slowdown during the exam-results period, which affects every academic user.

If it is genuinely stuck:

```bash
sudo systemctl restart 'fusion-platform-worker@ingest'      # acks_late → in-flight work is redelivered
```

If ingest must be stopped entirely while something else is fixed:

```bash
sudo sed -i 's/^ACADEMICS_INGEST_ENABLED=1/ACADEMICS_INGEST_ENABLED=0/' /etc/fusion/platform.env
sudo systemctl restart fusion-platform 'fusion-platform-worker@ingest'
```

Standings simply stay at the last declaration. Eligibility keeps working on the previous data — fail-safe, not
fail-open.

---

## 4. A verification mismatch

The nightly `verify_snapshots` re-pulls a 2% sample and asserts **byte-equality** with what we stored. A
mismatch means the ERP and our snapshot disagree about a **past** declaration.

```bash
$MANAGE verify_snapshots --declaration $ANN --full --report /tmp/mismatch.json
jq '.mismatches[] | {roll_no, field, stored, recomputed}' /tmp/mismatch.json
```

**Do not re-ingest yet.** Work out which of these it is:

| Pattern | Meaning | Action |
|---|---|---|
| A few students, CPI changed slightly | grades edited in the ERP after declaration | **expected.** The snapshot is the audit record of what we decided on. Leave it. |
| **Every** student, CPI shifted systematically | **legacy CPI semantics changed** — e.g. someone "fixed" `grade_conversion["F"]` from 0.2 to 0.0 | **Stop. Escalate.** Every eligibility decision downstream is affected. |
| `earned_credits` differs but `cpi` matches | `S`/`X` handling changed | escalate |
| Mismatch only for `course_replacement` students | replacement-chain logic changed | escalate |

The second row is the reason this check exists. It is the only signal that would catch a change to the ERP's
grade table, and it must not be silently re-ingested away.

Once the cause is understood and the *current* ERP computation is the one we want:

```bash
$MANAGE ingest_declaration --announcement-id $ANN --force-new-declaration
```

`--force-new-declaration` records a **new** declaration row with a later `declared_at`, so the guarded upsert
accepts it and the old snapshot is preserved as history. It never mutates a snapshot.

---

## 5. Retraction

```bash
$MANAGE handle_retraction --announcement-id $ANN --reason "clerical correction"
```

This sets `retracted_at`, then for each affected student recomputes standing from their highest
**non-retracted** declaration — unconditionally, since we are deliberately moving backwards.

```bash
$MANAGE shell -c "
from modules.placement.models import ReviewFlag
print(ReviewFlag.objects.filter(kind='now_ineligible', resolved_at=None).count(), 'flags for review')
"
```

**Applications are flagged, never auto-rejected.** A retraction may be a clerical correction, and a student who
has already attended three rounds deserves a human decision. Tell the placement office that flags are waiting.

If no non-retracted declaration remains, the standing row is removed and the student becomes ineligible
everywhere — fail-closed, and correct.

---

## 6. "My CPI is wrong"

Usually it is not. Check in this order:

```bash
ROLL=22bcs001
$MANAGE shell -c "
from modules.academics.models import StudentAcademicStanding, ResultSnapshot
s = StudentAcademicStanding.objects.filter(roll_no='$ROLL').first()
print('standing:', s.cpi, 'Sem', s.semester, s.semester_type, 'declared', s.declared_at) if s else print('NO STANDING')
for snap in ResultSnapshot.objects.filter(roll_no='$ROLL').select_related('declaration').order_by('-declaration__declared_seq')[:5]:
    print(snap.declaration.declared_seq, snap.cpi, snap.earned_credits, snap.computed_by,
          'retracted' if snap.declaration.retracted_at else '')
"
```

| The student says | Likely reality |
|---|---|
| "It's lower than my transcript" | Their latest semester is **not declared**. We only ever show declared values — by design. |
| "I passed but credits didn't increase" | Grade `X` or `CD` — excluded from credits **and** units entirely. |
| "My `S` course didn't help my CPI" | Correct. `S` earns credit but is excluded from the average. |
| "My `F` shouldn't count" | It does — factor 0.2, so 2.0 points **and** its credit. This is the ERP's rule and we adopt it verbatim. |
| "I cleared a backlog, nothing changed" | Dedup keeps the **best** attempt per course code; the retake only helps if it beat the original. |
| "Nothing shows at all" | No declared standing → ineligible everywhere. Not "CPI 0.0". |

The UI always renders `8.10 · Sem 5 (Odd) · declared 28 Jul 2026` for exactly this reason. If a screen shows a
bare number, that is a frontend bug worth fixing — it is the cheapest defence against this queue.

---

## 7. Notes

- Snapshots are **immutable at the database level** (`UPDATE`/`DELETE` revoked for `platform_app`). Everything
  here either inserts or records a new declaration.
- Ingest is idempotent: replaying a declaration inserts nothing and does not bump `standing_version`.
- Out-of-order delivery is harmless — the upsert's
  `WHERE EXCLUDED.declared_seq > current.declared_seq` clause makes an older declaration a no-op against
  standing while still recording its snapshot.
- **Announcements with `semester_type IS NULL`** (pre-migration-`0003` legacy rows) cannot be ingested: on
  Postgres the unique constraint does not dedupe NULLs, and a typed lookup never matches them. They appear in
  the data-quality report and need an ERP-side fix by the academic office. Affected students see "results not
  announced" indefinitely.
- We **never** write to the ERP. If a procedure seems to need that, stop and escalate.
