---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
criticality: >
  Read this fully before touching anything CPI-shaped. Every claim about legacy behaviour was verified
  by reading the code at the cited path:line on 2026-08-01. The grade semantics in §1 are
  counter-intuitive and are the single most likely source of a wrong number reaching a student.
---

# Academic Snapshot Integration

**The rule: Placement never computes CPI, SPI or credit arithmetic. It reads an immutable snapshot of the
ERP's own computation, taken at the moment of declaration.**

Decision and rationale: [ADR-0008](../01-architecture/adr/0008-declared-academic-snapshot-for-cpi.md).
Sequence diagram: [`_diagrams/academic-ingest-sequence.mmd`](../_diagrams/academic-ingest-sequence.mmd).

---

## 1. What the ERP actually does

### There is no stored CPI

| Field | Reality |
|---|---|
| `academic_information.Student.cpi` | `FloatField(default=0)`. **Permanently `0.0`.** Its only writers set it to zero at student creation: `programme_curriculum/signals.py:117`, `programme_curriculum/api/views_student_management.py:5013`, `academic_information/views.py:1388`. |
| `academic_information.Spi` | **Zero writers.** No `Spi.objects.create` and no `Spi(...)` constructor call exists anywhere in the codebase. The table is empty. |

The deprecated placement module filters candidates with `cpi__gte=...` against that dead column
(`applications/placement_cell/views.py:3693`) and exports it (`:5441`). `gymkhana/views.py:749,911` reads it
too. **They have all been reading zero for their entire existence.** A CI grep fails the build if anything
in the new platform references either field.

CPI is recomputed **on every request** by `calculate_cpi_for_student`
(`applications/examination/api/views.py:134`) from `online_cms.Student_grades`.

### The grade semantics — counter-intuitive, and load-bearing

From `grade_conversion` (`examination/api/views.py:47-56`) and the accumulation loop (`:190-202`):

| Grade | Factor | Earns credit (`total_unit`) | In the CPI average (`total_credits`) |
|---|---|---|---|
| `O`, `A+` | 1.0 | ✔ | ✔ |
| `A` … `D` | 0.9 … 0.3 | ✔ | ✔ |
| **`F`** | **0.2** | **✔** | **✔** |
| `S` | 0.0 | **✔** | ✘ |
| `X`, `CD`, `I`, `AU` | *absent from the dict* → `-1` | ✘ | ✘ |

The mechanism, in the ERP's own code:

```python
grade_factor = grade_conversion.get((best_record.grade or '').strip(), -1)
if grade_factor >= 0:            # X / CD absent → -1 → excluded from EVERYTHING
    if grade_factor != 0:        # S is 0.0 → credit only, no points, no denominator
        total_points  += Decimal(str(grade_factor)) * credit
        total_credits += credit
    total_unit += credit
```

Three things to internalize:

1. **`F` is not zero.** It contributes 2.0 grade points *and* its credit to the denominator. Any system that
   assumes `F = 0` will disagree with every Fusion transcript.
2. **`S` earns credit but is excluded from the average** — correct pass/fail semantics.
3. **`X` and `CD` are excluded entirely** — no credit, no points, and they do not even appear in
   `total_unit`. Note `CD` *is* in `ALLOWED_GRADES` (`:63`) but missing from `grade_conversion`, so it falls
   through the `-1` path.

### Two different credit totals

`calculate_cpi_for_student` returns `(cpi, total_unit, total_points * 10)`:

- **`total_unit`** — credits earned, **including** `S`-graded courses.
- **`total_credits`** (internal to the function) — the CPI denominator, **excluding** `S` and `X`.

These are different numbers. Conflating them produces a wrong CPI, so the snapshot stores both:
`earned_credits` and `cpi_denominator_credits`.

### Dedup and replacement

- **Dedup by `Course.code`**, keeping the attempt with the highest `grade_conversion` factor
  (`:171-179`). This collapses backlogs, improvement retakes, duplicate rows, and different
  `Course.version` rows sharing a code. `Student_grades` has **no unique constraint at all**, which is why
  dedup is necessary rather than defensive.
- **`course_replacement` chains** (`:156-186`) mean a swayam or replacement course supersedes the elective it
  replaced; every reachable `old_code` is added to `superseded_codes` and skipped.

### Not filtered on `verified`

`Student_grades.verified` is **never consulted**. An unverified, freshly-uploaded grade counts toward the
ERP's CPI immediately. This is precisely why Placement needs the *declaration* gate rather than just reading
the CPI function.

### SPI differs from CPI

`calculate_spi_for_student` (`:93-125`) does **no dedup and no replacement handling**. A duplicate
`Student_grades` row double-counts in SPI but not in CPI. We store both values as the ERP produces them and
do not attempt to reconcile them.

---

## 2. What "declared" means

The declaration fact is `examination.ResultAnnouncement`:

```python
class ResultAnnouncement(models.Model):
    batch                 = models.ForeignKey(Batch, on_delete=models.CASCADE)
    semester              = models.PositiveIntegerField()
    semester_type         = models.CharField(max_length=20, choices=..., null=True, blank=True)
    announced             = models.BooleanField(default=False)
    per_student_selection = models.BooleanField(default=False)
    created_at            = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = [("batch", "semester", "semester_type")]
```

plus an optional per-student allow-list (`PublishedResultStudent`), gated by:

```python
# examination/api/views.py:3324 — note it does NOT check `announced`
def _is_result_published_for(ann, roll_number):
    if not getattr(ann, "per_student_selection", False):
        return True                       # whole-batch (legacy) publish
    return ann.published_students.filter(roll_no=roll_number).exists()
```

So the full condition is **`ann.announced AND _is_result_published_for(ann, roll_no)`** — two parts, ANDed by
hand at every ERP call site (`:2996`, `:3695`). Forgetting the first half leaks unpublished results.

### Five traps

| Trap | Detail | Our handling |
|---|---|---|
| **No `declared_at`** | `created_at` is when the admin created the *not-yet-announced placeholder*, typically well before declaration. Flipping `announced` writes no timestamp. | We capture `declared_at` in the outbox event at the moment of the flip. |
| **Summer under even numbers** | Summer semesters are stored with an **even** `semester` and labelled `Summer {semester // 2}` (`:3462-3472`). So `(4, "Summer Semester")` = "Summer 2" and `(4, "Even Semester")` = "Semester 4" — different declarations that sort identically by `semester`. | `declared_seq` |
| **Nullable `semester_type`** | On Postgres, `UNIQUE(batch, semester, semester_type)` does not dedupe NULLs, so pre-migration-`0003` rows can be duplicated **and never match** a `semester_type=<value>` lookup. Those students see "Results not announced yet" forever. | A data-quality report lists NULL-type announcements; they are not ingested. |
| **`UpdateAnnouncementAPI` ignores `per_student_selection`** | `:3253` flips `announced` without touching it, so re-announcing after a per-student publish silently reuses the **stale allow-list**. | We read the allow-list at pull time, never cache it. |
| **`PublishedResultStudent.roll_no` is an unvalidated CharField** | Validated against batch membership at write time (`:3435-3439`), but nothing prevents drift if a student later changes batch. | Unresolvable roll numbers are reported, not silently dropped. |

### Admin endpoints ignore declaration entirely

`generate_transcript`, `generate_gradesheet_data`, `grade_validation` and `generate_result` **do not check
`ResultAnnouncement` at all**. They would happily serve undeclared results. `GenerateStudentResultPDFAPI`
additionally has a live `ImportError` on its server-computed path (`:3728` imports `grade_conversion` from
`academic_information.models`, where it does not exist), so only its client-supplied-data branch works — and
that branch has no declaration gate and trusts client-supplied CPI verbatim.

This is why we do not reuse any of them, and instead add one purpose-built endpoint that reuses the gate.

---

## 3. The two legacy changes

The **only** changes this programme makes to the monolith's behaviour. Both additive.

### 3a. An outbox row inside the existing transaction

```python
# applications/examination/models.py
class ExamOutboxEvent(models.Model):
    topic       = models.CharField(max_length=80)
    payload     = models.JSONField()
    dedupe_key  = models.CharField(max_length=160, unique=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        indexes = [models.Index(fields=["consumed_at", "id"], name="examoutbox_pending_idx")]
```

Written inside the `transaction.atomic()` blocks that already exist in `UpdateAnnouncementAPI`
(`:3245-3255`) and `PublishResultSelectedAPI` (`:3441-3449`):

```python
ExamOutboxEvent.objects.update_or_create(
    dedupe_key=f"result.declared:{ann.id}:{int(now.timestamp())}",
    defaults={"topic": "academics.result.declared",
              "payload": {"announcement_id": ann.id, "batch_id": ann.batch_id,
                          "semester": ann.semester, "semester_type": ann.semester_type,
                          "per_student_selection": ann.per_student_selection,
                          "declared_at": now.isoformat()}})
```

Setting `announced = False`, or deleting an announcement, emits `academics.result.retracted` the same way.

### 3b. One internal read endpoint

```python
@api_view(["POST"])
@authentication_classes([IamServiceTokenAuthentication])   # aud=fusion-legacy
@permission_classes([HasScope("academics:snapshot:read")])
@throttle_classes([SnapshotThrottle])                      # 30/min
def academic_snapshot(request):
    """Declared SPI/CPI for the students an announcement publishes to.
    Body: {"announcement_id": int, "offset": int, "limit": int <= 100}
    """
```

- Bound to `127.0.0.1`; **never** exposed by nginx.
- **Reuses `_is_result_published_for` verbatim**, so per-student gating is honoured exactly rather than
  reimplemented. Also checks `ann.announced` explicitly.
- Returns `computed_by: "erp:calculate_cpi_for_student@<git-sha>"` so a snapshot records which ERP revision
  produced it.

```json
{"announcement": {"id": 812, "batch_id": 44, "batch_label": "B.Tech - CSE 2023",
                  "semester": 5, "semester_type": "Odd Semester", "announced": true,
                  "declared_at": "2026-07-28T11:04:00Z"},
 "total": 118, "offset": 0, "limit": 50,
 "students": [
   {"roll_no": "22BCS001", "erp_user_id": 1234,
    "spi": "8.40", "cpi": "8.10",
    "earned_credits": "96.0",              /* total_unit — INCLUDES S-graded credits */
    "cpi_denominator_credits": "92.0",     /* EXCLUDES S and X */
    "active_backlogs": 0, "total_backlogs": 1,
    "courses": [{"code": "CS3001", "credit": 4, "grade": "A"}]}],
 "computed_by": "erp:calculate_cpi_for_student@a1b2c3d"}
```

---

## 4. Platform models

```python
class ResultDeclaration(models.Model):
    erp_announcement_id = models.IntegerField(unique=True)
    batch_erp_id        = models.IntegerField(db_index=True)
    batch_label         = models.CharField(max_length=120)      # denormalized for display
    semester            = models.PositiveSmallIntegerField()
    semester_type       = models.CharField(max_length=20)
    declared_seq        = models.PositiveIntegerField(db_index=True)
    declared_at         = models.DateTimeField()
    ingested_at         = models.DateTimeField(null=True, blank=True)
    retracted_at        = models.DateTimeField(null=True, blank=True)
    student_count       = models.PositiveIntegerField(default=0)
    payload_hash        = models.CharField(max_length=64)
    source_revision     = models.CharField(max_length=64)       # the ERP git sha

class ResultSnapshot(models.Model):
    """IMMUTABLE. UPDATE and DELETE are REVOKED for platform_app in Postgres."""
    declaration             = models.ForeignKey(ResultDeclaration, on_delete=models.PROTECT,
                                                related_name="snapshots")
    user_id                 = models.IntegerField(db_index=True)
    roll_no                 = models.CharField(max_length=20)
    spi                     = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    cpi                     = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    earned_credits          = models.DecimalField(max_digits=6, decimal_places=2)
    cpi_denominator_credits = models.DecimalField(max_digits=6, decimal_places=2)
    active_backlogs         = models.PositiveSmallIntegerField(default=0)
    total_backlogs          = models.PositiveSmallIntegerField(default=0)
    courses                 = models.JSONField()
    computed_by             = models.CharField(max_length=120)
    created_at              = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["declaration", "user_id"],
                                               name="snapshot_unique_per_declaration")]
        indexes = [models.Index(fields=["user_id", "declaration"], name="snapshot_user_decl_idx")]

class StudentAcademicStanding(models.Model):
    """One row per student: the LATEST DECLARED values. The only thing eligibility reads."""
    user_id             = models.IntegerField(primary_key=True)
    roll_no             = models.CharField(max_length=20, db_index=True)
    current_declaration = models.ForeignKey(ResultDeclaration, on_delete=models.PROTECT)
    declared_seq        = models.PositiveIntegerField(db_index=True)
    semester            = models.PositiveSmallIntegerField()
    semester_type       = models.CharField(max_length=20)
    cpi                 = models.DecimalField(max_digits=4, decimal_places=2)
    spi_latest          = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    earned_credits      = models.DecimalField(max_digits=6, decimal_places=2)
    active_backlogs     = models.PositiveSmallIntegerField(default=0)
    total_backlogs      = models.PositiveSmallIntegerField(default=0)
    declared_at         = models.DateTimeField()
    standing_version    = models.BigIntegerField(default=1)
    updated_at          = models.DateTimeField(auto_now=True)

class SnapshotIngestRun(models.Model):
    declaration = models.ForeignKey(ResultDeclaration, on_delete=models.CASCADE)
    status      = models.CharField(max_length=12)   # running|succeeded|failed|partial
    chunks_total = models.PositiveSmallIntegerField(default=0)
    chunks_done  = models.PositiveSmallIntegerField(default=0)
    started_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    error       = models.TextField(blank=True)
```

### `declared_seq`

```python
SEM_TYPE_RANK = {"Odd Semester": 0, "Even Semester": 1, "Summer Semester": 2}
declared_seq = semester * 10 + SEM_TYPE_RANK[semester_type]
```

This reproduces the ERP's own `semester_type_order` `Case/When` ordering (`:98-106`) and is what separates
`Summer 2` (`semester=4, Summer` → 42) from `Semester 4` (`semester=4, Even` → 41). Ordering by `semester`
alone cannot tell them apart, and getting it wrong means a student's standing silently regresses.

---

## 5. The advance rule — one atomic statement

```sql
INSERT INTO academics_studentacademicstanding
  (user_id, roll_no, current_declaration_id, declared_seq, semester, semester_type,
   cpi, spi_latest, earned_credits, active_backlogs, total_backlogs,
   declared_at, standing_version, updated_at)
VALUES (%s, ...)
ON CONFLICT (user_id) DO UPDATE SET
  current_declaration_id = EXCLUDED.current_declaration_id,
  declared_seq  = EXCLUDED.declared_seq,
  semester      = EXCLUDED.semester,
  semester_type = EXCLUDED.semester_type,
  cpi           = EXCLUDED.cpi,
  spi_latest    = EXCLUDED.spi_latest,
  earned_credits = EXCLUDED.earned_credits,
  active_backlogs = EXCLUDED.active_backlogs,
  total_backlogs  = EXCLUDED.total_backlogs,
  declared_at   = EXCLUDED.declared_at,
  standing_version = academics_studentacademicstanding.standing_version + 1,
  updated_at    = now()
WHERE  EXCLUDED.declared_seq >  academics_studentacademicstanding.declared_seq
   OR (EXCLUDED.declared_seq = academics_studentacademicstanding.declared_seq
       AND EXCLUDED.declared_at > academics_studentacademicstanding.declared_at);
```

**The `WHERE` on the `DO UPDATE` is the entire guarantee:**

- An **older** declaration can never overwrite a newer one — so out-of-order event delivery is harmless.
- A **re-declaration of the same semester** (a correction) *does* win, because `declared_at` is later.
- There is **no read-modify-write**, so there is no race between two concurrent ingest chunks.

`standing_version` increments on every real change, which is what invalidates cached eligibility for free.

---

## 6. Ingest

```python
@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True,
             autoretry_for=(RequestException,), retry_backoff=True, retry_jitter=True,
             max_retries=8, soft_time_limit=600, queue="ingest")
def ingest_declaration(self, announcement_id: int, offset: int = 0) -> None:
    # 1. upsert ResultDeclaration (compute declared_seq) + SnapshotIngestRun
    # 2. POST /internal/academic-snapshot/ {announcement_id, offset, limit: 50}
    # 3. resolve roll_no -> user_id via directory.UserRef (batched)
    # 4. bulk_create ResultSnapshot(ignore_conflicts=True)   ← immutability + idempotency
    # 5. run the ON CONFLICT upsert above for this chunk
    # 6. emit academics.standing.changed for each user_id that actually changed
    # 7. if offset + 50 < total: self.apply_async(kwargs={..., "offset": offset + 50}, countdown=2)
    # 8. else: mark the run succeeded; emit academics.declaration.ingested
```

**50 students per chunk, 2 seconds apart, `ingest` queue at concurrency 1.**
`calculate_cpi_for_student` is several queries per student, so a 300-student declaration is roughly 1,500 ERP
queries. Chunking keeps the ERP's connection pool comfortable; running it at concurrency 1 keeps it that way
when two batches are declared minutes apart. `ACADEMICS_INGEST_ENABLED` gates the whole path.

`ignore_conflicts=True` on the snapshot insert gives idempotency and immutability simultaneously: replaying a
chunk inserts nothing and changes nothing.

Unresolvable roll numbers (no `UserRef`) are collected into the run's `error` field and reported — never
silently skipped.

---

## 7. Retraction

`academics.result.retracted` → set `retracted_at`, then for each affected user recompute from the highest
**non-retracted** declaration:

```sql
SELECT s.* FROM academics_resultsnapshot s
JOIN academics_resultdeclaration d ON d.id = s.declaration_id
WHERE s.user_id = %s AND d.retracted_at IS NULL
ORDER BY d.declared_seq DESC, d.declared_at DESC
LIMIT 1;
```

Write that as the new standing — **unconditionally**, because we are deliberately moving backwards, so the
guard clause from §5 must not apply. Bump `standing_version`, emit `academics.standing.changed`.

If no non-retracted declaration remains, the standing row is deleted and the student has no declared
standing — which makes them ineligible everywhere, fail-closed.

**Placement's reaction:** eligibility evaluations invalidate automatically (`inputs_version` changed), and
for applications in `SUBMITTED` / `UNDER_REVIEW` / `SHORTLISTED` whose student became ineligible, a
`ReviewFlag` is created for the coordinator.

**Never auto-reject.** A retraction is an administrative event — possibly a clerical correction — and a human
must decide what happens to a student who has already interviewed.

---

## 8. Provenance on screen

Every CPI rendered in Placement shows where it came from:

```
8.10 · Sem 5 (Odd) · declared 28 Jul 2026
```

This is not decoration. The number is minutes behind the ERP and semesters behind "provisional", and without
provenance every difference becomes a support ticket. The placement office SOP says the same thing in
non-technical words.

The API always returns the provenance fields alongside the value; a serializer that returns a bare `cpi` is a
review rejection.

---

## 9. Reconciliation

```python
@shared_task(queue="ingest")
def verify_snapshots(sample_pct: int = 2) -> None:
    """Re-pull a random sample of the latest declaration and assert byte-equality."""
```

Nightly, 2% sample. Any mismatch pages. This is the guard against a legacy change silently altering CPI
semantics — for instance someone "fixing" `grade_conversion["F"]` to `0.0`. Without it, we would discover
that from a student complaint.

A mismatch is **not** self-healed. It means the ERP and our snapshot genuinely disagree about a past
declaration, which needs a human to decide whether to re-ingest.

Manual re-ingest: [reingest-academic-snapshot.md](../07-ops/runbooks/reingest-academic-snapshot.md).

---

## 10. Contract

```python
# modules/academics/contracts.py
def get_standings(user_ids: Sequence[int]) -> dict[int, StandingDTO]:
    """Latest DECLARED standing per user. Missing ⇒ absent from the mapping ⇒ ineligible."""

def get_standing_history(user_id: int) -> list[SnapshotDTO]:
    """Every non-retracted snapshot, newest first. For the transcript-style view."""
```

```python
@dataclass(frozen=True)
class StandingDTO:
    user_id: int
    cpi: Decimal
    earned_credits: Decimal
    active_backlogs: int
    semester: int
    semester_type: str          # provenance is part of the value
    declared_at: datetime
    standing_version: int
```

Provenance is in the DTO because a CPI without it is not a usable number. Placement never sees
`Student_grades`, `ResultAnnouncement` or `grade_conversion`.

---

## 11. Verification — the Phase 5a gate

**Correctness (blocking):**

- For 200 students of a declared batch, `ResultSnapshot.{cpi, spi, earned_credits}` **exactly equals**
  `POST /examination/api/check_result/`. The sample **must** include:
  - a student with an `S` grade (credit counted, average unaffected)
  - a student with an `X` or `CD` (excluded from credits *and* units)
  - a student with an `F` (2.0 points, credit counted)
  - a student with a backlog retake (dedup keeps the best attempt)
  - a student with a `course_replacement` / swayam substitution
  - a student with a Summer semester

**Ordering:**

- `(4, "Summer Semester")` beats `(4, "Even Semester")` via `declared_seq`.
- Deliver Sem 5 then Sem 3 → standing stays on Sem 5.
- Re-declare Sem 5 with a corrected grade → standing updates, `standing_version` increments.

**Idempotency & immutability:**

- Replay the same event twice → snapshots unchanged, `standing_version` unchanged.
- `UPDATE academics_resultsnapshot` raises `InsufficientPrivilege`.

**Gating:**

- A student excluded from a `per_student_selection` allow-list gets **no** snapshot.
- An announcement with `announced = False` is not ingested.
- An announcement with `semester_type IS NULL` is reported, not ingested.

**Retraction:**

- Retract the latest → standing falls back to the previous non-retracted declaration.
- Retract the only one → standing row removed; the student is ineligible everywhere.
- In-flight applications are **flagged**, not rejected.

**Load:**

- A 300-student declaration completes without the ERP's p95 exceeding its baseline by more than 20%.
