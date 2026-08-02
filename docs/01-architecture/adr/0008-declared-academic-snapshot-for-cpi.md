# ADR-0008 — Snapshot the ERP's own declared CPI; never recompute it

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0007](0007-read-only-erp-access-via-acl.md), [0006](0006-outbox-plus-celery-for-integration-events.md)
- **Detail:** [academic-snapshot-integration.md](../../04-placement/academic-snapshot-integration.md)

## Context

Placement eligibility turns on CPI. The requirement is explicit: **when a result is declared, the CPI of
the latest declared semester is what Placement sees** — never a provisional value.

Investigation of the ERP produced three findings that determine the design.

**1. There is no stored CPI.** `academic_information.Student.cpi` is a `FloatField(default=0)` whose only
writers set it to `0.0` at student creation (`programme_curriculum/signals.py:117`,
`programme_curriculum/api/views_student_management.py:5013`, `academic_information/views.py:1388`).
`academic_information.Spi` has **zero writers**. CPI is recomputed on **every request** by
`calculate_cpi_for_student` (`applications/examination/api/views.py:134`) from `online_cms.Student_grades`.

**2. That computation has subtle, load-bearing semantics.** From `grade_conversion`
(`examination/api/views.py:47-56`) and the loop at lines 190–202:

| Grade | Factor | Earns credit | In the CPI average |
|---|---|---|---|
| `O`, `A+` | 1.0 | yes | yes |
| `A`…`D` | 0.9…0.3 | yes | yes |
| **`F`** | **0.2** | **yes** | **yes** |
| `S` | 0.0 | **yes** | **no** (inner `!= 0` guard) |
| `X`, `CD` | *absent from the dict* → `-1` | **no** | **no** |

Plus: dedup by `Course.code` keeping the best-graded attempt (collapsing backlogs and retakes);
`course_replacement` chains so a swayam course supersedes the elective it replaced; two different credit
totals returned (`total_unit` includes `S`-graded credits, `total_credits` excludes `S` and `X`); and
**no filter on `Student_grades.verified`**, so unverified grades count immediately.

**3. Declaration is a separate, two-part fact.** `examination.ResultAnnouncement(batch, semester,
semester_type, announced, per_student_selection)` plus an optional `PublishedResultStudent` allow-list,
gated by `_is_result_published_for` (`views.py:3324`) — which notably does **not** itself check
`announced`; every ERP call site ANDs it by hand. And there is **no `declared_at` field**: `created_at` is
when the admin created the not-yet-announced placeholder.

So a CPI can exist for a semester nobody declared, and the only correct CPI is one computed by that
function for a student covered by an announced declaration.

## Decision

**Placement never computes CPI, SPI or credit arithmetic. Anywhere.**

`modules/academics` pulls the ERP's own computed values at declaration time and stores them as an
immutable snapshot.

Two — and only two — additions to the legacy monolith:

1. **`examination.ExamOutboxEvent`** plus one `get_or_create` inside the *existing*
   `transaction.atomic()` in the announce/publish path (`views.py:3235-3260`, `3411-3456`), emitting
   `academics.result.declared` with a real `declared_at`. Retraction emits `academics.result.retracted`.

2. **`POST /api/examination/internal/academic-snapshot/`** — service-token auth, bound to `127.0.0.1`,
   never exposed by nginx, throttled, paginated. It **reuses `_is_result_published_for` verbatim** so
   per-student gating is honoured exactly, then calls `calculate_spi_for_student` and
   `calculate_cpi_for_student` and returns both credit totals separately, plus
   `computed_by: "erp:calculate_cpi_for_student@<git-sha>"`.

Platform side:

```
ResultDeclaration           one row per (batch, semester, semester_type), with declared_seq
ResultSnapshot              IMMUTABLE — UPDATE/DELETE revoked in Postgres for platform_app
StudentAcademicStanding     one row per student: the latest DECLARED values
SnapshotIngestRun           observability for a chunked pull
```

`declared_seq = semester * 10 + {Odd: 0, Even: 1, Summer: 2}` reproduces the ERP's own
`semester_type_order` ordering (`views.py:98-106`) and separates `Summer N` from `Semester N`, which
`semester` alone cannot.

The advance rule is **one atomic upsert** whose `WHERE` clause is the entire guarantee:

```sql
ON CONFLICT (user_id) DO UPDATE SET ..., standing_version = standing_version + 1
WHERE  EXCLUDED.declared_seq >  studentacademicstanding.declared_seq
   OR (EXCLUDED.declared_seq = studentacademicstanding.declared_seq
       AND EXCLUDED.declared_at > studentacademicstanding.declared_at);
```

An older or provisional declaration can never overwrite a newer declared one; a re-declaration of the same
semester (a correction) does win; out-of-order delivery is harmless. No read-modify-write, so no race.

**Every CPI rendered in Placement carries its provenance:** `8.10 · Sem 5 (Odd) · declared 28 Jul 2026`.

## Consequences

**Good**

- Exactly one CPI implementation exists in the institute. Placement cannot disagree with a transcript.
- The snapshot is the audit trail behind every eligibility decision — "what did we decide on, and why" is
  answerable months later, which matters for appeals.
- Undeclared and provisional results are structurally invisible to Placement, not filtered out by a
  condition someone might forget.
- Legacy changes are minimal and additive: one table, one line in an existing transaction, one new
  read-only endpoint. No existing behaviour changes.
- Immutability is a Postgres grant, not a convention.

**Bad, and accepted**

- **The displayed CPI lags the ERP** — by minutes after a declaration, and by semesters behind
  "provisional". This is a *feature*, and the mitigation is honesty: provenance on screen, and a line in
  the placement office SOP. Without it, this generates a support queue.
- Ingest is expensive: `calculate_cpi_for_student` is several queries per student, so a 300-student
  declaration is roughly 1,500 ERP queries. Mitigated by 50-student chunks with a 2-second gap on the
  `ingest` queue at concurrency 1, run off-peak, and load-tested before Phase 5a ships.
- We depend on legacy internals (`calculate_cpi_for_student`, `_is_result_published_for`). Mitigated by
  `computed_by` recording the ERP git SHA, and by a **nightly 2% re-pull that asserts byte-equality** with
  the stored snapshot — the guard against a legacy change silently altering CPI semantics.
- Retraction needs an explicit path: recompute standing from the highest non-retracted declaration, then
  flag affected in-flight applications for coordinator review. **Never auto-reject** — a retraction is an
  administrative event and a human decides.
- We inherit the ERP's `verified`-agnosticism. A grade edited after declaration changes the *ERP's* CPI but
  not our snapshot, which is the correct behaviour for an audit record and is exactly why the nightly
  reconciliation samples rather than asserts blanket equality.

## Alternatives considered

**Reimplement CPI in the platform.** Rejected as the highest-risk option available. Reproducing the
`S`/`X`/`CD` handling, `F = 2.0`, best-attempt dedup by course code and `course_replacement` chains — and
then keeping that in step with an actively-developed ERP — would inevitably produce two disagreeing CPIs.
Codified as [NG5](../../00-overview/vision-and-scope.md#non-goals).

**Read `Student.cpi`.** Rejected: permanently `0.0`. This is not hypothetical — the deprecated placement
module does exactly this at `placement_cell/views.py:3693`.

**Call `calculate_cpi_for_student` live on every eligibility check.** Rejected: several queries per student
per check, no audit trail, and eligibility results that change silently between page loads. It would also
make a posting list page a load test against the ERP.

**Have the ERP write CPI into a table we read.** Rejected: that is a change to legacy write behaviour with
no owner, and it re-creates the `Student.cpi` problem — a denormalized column that quietly goes stale.

**Use the existing admin endpoints (`generate_transcript`, `grade_validation`).** Rejected: they **ignore
`ResultAnnouncement` entirely** and would serve undeclared results. `GenerateStudentResultPDFAPI` also has
a live `ImportError` on its server-computed path (`views.py:3728` imports `grade_conversion` from
`academic_information.models`, where it does not exist). A purpose-built internal endpoint that reuses the
publication gate is both safer and simpler.

## Verification (the Phase 5a gate)

- For 200 students of a declared batch, `ResultSnapshot.{cpi, spi, earned_credits}` **exactly equals**
  `POST /examination/api/check_result/`. Includes an `S`-credit case, an `X`-exclusion case, an
  `F`-carrying transcript, and a student with a `course_replacement` substitution.
- `StudentAcademicStanding` prefers `Summer 2` over `Semester 4` correctly via `declared_seq`.
- Replaying the same declaration event twice leaves snapshots unchanged and does not bump
  `standing_version`.
- Delivering Sem 5 then Sem 3 leaves standing on Sem 5.
- A write to `academics_resultsnapshot` raises `InsufficientPrivilege`.
