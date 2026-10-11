---
owner: placement-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Placement Reports & Statistics

**Statistics are materialized, never computed on request.** The public dashboard reads only
`PlacementStatsSnapshot`, so a viral share of the placement page cannot touch the transactional tables during
a live drive.

---

## Snapshot dimensions

One row per `(placement_year, dimension, dimension_value)`.

| Dimension | Values | Audience |
|---|---|---|
| `overall` | `""` | public |
| `discipline` | `CSE`, `ECE`, `ME`, … | public |
| `batch` | `2023`, `2024`, … | public |
| `programme` | `B.Tech`, `M.Tech`, … | public |
| `tier` | `T1`, `T2`, … | internal |
| `company` | company slug | internal |
| `sector` | `IT`, `Core`, `Finance`, … | public |

Measures: `registered`, `placed`, `offers`, `median_ctc`, `mean_ctc`, `max_ctc`, `computed_at`.

**Never in a snapshot:** any student identifier, and any cell where `placed < 5`. A single-student cell in a
small discipline is personally identifying — "the one placed student in Design 2023" plus a public median is
that student's salary. Suppressed cells report `placed` and nothing else.

---

## Refresh policy

| Trigger | Timing |
|---|---|
| Beat, during an active year | every 15 min |
| `placement.offer.accepted` / `.revoked` | debounced 60 s |
| `placement.posting.published` | debounced 60 s (affects `registered` denominators) |
| Manual | `manage.py refresh_placement_stats --year 2026-27` |

The 60-second debounce matters on offer day, when twenty acceptances arrive in a minute. Without it, twenty
full recomputes queue up behind each other.

```python
@shared_task(queue="reports", soft_time_limit=300)
def refresh_placement_stats(placement_year_id: int) -> None:
    """One aggregate query per dimension. Medians in SQL, never in Python."""
```

Medians use a single Postgres aggregate rather than pulling rows into Python:

```sql
SELECT d.value AS dimension_value,
       count(DISTINCT r.user_id)                                     AS placed,
       count(o.id)                                                   AS offers,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY r.ctc_lpa)         AS median_ctc,
       avg(r.ctc_lpa)                                                AS mean_ctc,
       max(r.ctc_lpa)                                                AS max_ctc
FROM placement_placementrecord r ...
WHERE r.placement_year_id = %s AND r.is_active
GROUP BY d.value;
```

`percentile_cont` comes from `core/db/functions.py`. Pulling 800 records into Python to sort them would work
today and stop working at scale — and it is the kind of thing nobody revisits.

Writes are a single upsert per dimension row, so a reader never sees a half-refreshed dashboard.

---

## What "placed" means

Stated explicitly, because every institute counts differently and the number ends up in public material:

- **Placed** = holds an **active** `PlacementRecord` for the year. Superseded records are not counted;
  revoked ones are not counted.
- **Registered** = `PlacementRegistration.status == registered`. Debarred and opted-out students are excluded
  from **both** numerator and denominator, which is the honest treatment — a student who opted out was never
  seeking placement.
- **Offers** counts every `accepted` offer, so a student who upgraded contributes 2 offers and 1 placement.
  This is why `offers >= placed` always, and the dashboard labels them distinctly.
- **Placement percentage** = `placed / registered`, rendered with the denominator visible
  (`142 / 310 = 45.8%`) so the basis is never ambiguous.

A note on the dashboard states these definitions verbatim. A percentage without its definition invites the
reader to assume the most flattering one.

---

## Reports

| Report | Permission | Contents | PII |
|---|---|---|---|
| Placement summary | `statistics.view` | the snapshot table, all public dimensions | no |
| Company-wise | `report.export` | offers, acceptances, median CTC per company | no |
| Discipline-wise | `report.export` | placed/registered/median per discipline × programme | no |
| Drive report | `application.view` | one posting: funnel counts by status, round outcomes | no |
| **Student-wise placement list** | **`export.pii`** ⚠️ | roll no, name, company, CTC, declared CPI at apply | **yes** |
| **Applicant list for a posting** | **`export.pii`** ⚠️ | roll no, name, CPI, eligibility outcome | **yes** |
| Unplaced students | **`export.pii`** ⚠️ | roll no, name, applications count | **yes** |

Non-PII reports are generated from snapshots and are cheap. PII reports read transactional tables.

### PII export controls

Every PII export:

1. Requires the `export.pii` permission — `is_dangerous`, so MFA plus **step-up re-auth within 5 minutes**.
2. Writes an `audit_event` recording the **exact filter used and the row count returned**, not just "an export
   happened".
3. Is throttled to 5 per hour per user.
4. Is asynchronous (202 + job + expiring download link), never a synchronous response.
5. Carries a footer with the requester, timestamp and `request_id`, so a leaked spreadsheet is traceable.
6. Applies **CSV formula-injection escaping** — any cell beginning `= + - @ \t \r` is prefixed with `'`.
   Without this, a student-supplied field can execute in Excel on the recipient's machine.

> The audit row records the filter because "who exported PII" is a much weaker question than "who exported
> *which* PII". A year later, only the second is answerable from the first.

---

## Generation

All reports return **202 + a job**, per
[api-conventions.md](../01-architecture/api-conventions.md#8-long-running-work):

```
POST /placement/reports/student-wise        → 202 {job_id, poll_url}
GET  /jobs/{job_id}                         → {status, result_url, expires_at}
GET  /downloads/{token}                     → X-Accel-Redirect, Content-Disposition: attachment
```

Never synchronous. A coordinator exporting 3,000 rows must not hold a gunicorn worker for 40 seconds — that
is one of five workers gone during the busiest hour of the season.

Formats: `xlsx` (default, `openpyxl`, streamed), `csv`, `pdf` for the summary. Download links expire after
24 hours and are single-purpose, UUID-keyed, and authorization-checked on every fetch — the token is a lookup
key, not a bearer credential.

---

## Dashboards

### Public — `/placement/stats`

Snapshot reads only. Cached with an `ETag` derived from `max(computed_at)`, so repeat views are 304s.
p95 target **< 200 ms**.

Shows: overall placed/registered with the denominator visible, median and highest CTC, discipline breakdown,
sector mix, `computed_at` stated on the page.

Charts follow the shared visualization conventions and the `#15ABFF` brand accent from `packages/ui`. Suppressed
cells (`placed < 5`) render as "—" with a footnote, never as a zero.

### Coordinator — `/placement/dashboard`

Live transactional reads, but bounded: counts come from indexed aggregates over `application_posting_status_idx`,
and the funnel is one grouped query per posting rather than one per status.

Shows: open postings closing this week, applications awaiting review, rounds scheduled today, offers pending
response with their deadlines, and **unresolved `ReviewFlag`s** — the queue created when a student's declared
standing changed under an in-flight application
([academic-snapshot-integration.md](academic-snapshot-integration.md#7-retraction)).

### Student — `/placement/mine`

Their applications with current status, eligible postings they have not applied to, offers awaiting response
with a countdown, and their declared CPI **with provenance**:

```
8.10 · Sem 5 (Odd) · declared 28 Jul 2026
```

Never a bare number. This is the single cheapest defence against the "my CPI is wrong" support queue.

---

## Verification

- Public dashboard issues **zero** queries against `placement_application` or `placement_offer` — asserted
  with `django_assert_num_queries` naming the tables.
- p95 < 200 ms for `/placement/stats` under 200 concurrent readers (k6).
- Median from `percentile_cont` matches a Python-computed median on a fixture of 101 records, odd and even
  counts both tested.
- A dimension cell with `placed < 5` suppresses its CTC measures.
- `placed` excludes superseded and revoked records; a student who upgraded counts as 1 placement, 2 offers.
- Debarred and opted-out students are excluded from both numerator and denominator.
- Twenty acceptances within one minute trigger **one** stats refresh, not twenty.
- A PII export writes an `audit_event` containing the filter **and** the row count.
- A PII export without step-up auth returns 403 `step_up_required`.
- A CSV cell beginning `=` is escaped in the output file.
- A download token belonging to another user returns **404**, not 403.
- An expired download token returns 410.
