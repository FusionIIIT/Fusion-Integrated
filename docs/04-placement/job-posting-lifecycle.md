---
owner: placement-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Job Posting Lifecycle

A posting's status machine, its approval flow, and the rule-locking that happens on publish.

---

## States

| State | Visible to students | Editable | Meaning |
|---|---|---|---|
| `draft` | no | fully | Being written. May be deleted outright. |
| `pending_approval` | no | no | Submitted for approval. |
| `published` | **yes** | metadata only | Live. **Eligibility rule is frozen.** |
| `applications_closed` | yes (read-only) | no | Window passed; rounds continue. |
| `in_progress` | yes | no | Rounds under way. |
| `completed` | yes | no | Offers issued and resolved. |
| `cancelled` | yes, with a banner | no | Withdrawn. Applications auto-withdrawn. |

```
draft ──submit──► pending_approval ──approve──► published ──window closes──► applications_closed
  │                     │                          │                              │
  │                     └──reject──► draft         │                              │
  │                                                ▼                              ▼
  └──delete──► (gone)                        in_progress ◄──────schedule rounds───┘
                                                   │
                                                   └──all offers resolved──► completed

  draft · pending_approval · published · applications_closed · in_progress ──cancel──► cancelled
```

Mermaid: [`_diagrams/job-posting-lifecycle.mmd`](../_diagrams/job-posting-lifecycle.mmd).

---

## Transition table

| # | From | To | Permission | Guards | Effects |
|---|---|---|---|---|---|
| 1 | `draft` | `pending_approval` | `job_posting.update` | `rule_valid`, `has_window`, `company_active` | notify approvers |
| 2 | `pending_approval` | `draft` | `job_posting.approve` | `has_reason` | notify author |
| 3 | `pending_approval` | `published` | `job_posting.publish` ⚠️ | `rule_valid`, `has_window`, `company_active`, `year_active` | **stamp `eligibility_rule_locked_at`**; set `published_at`; emit `posting.published`; precompute eligibility |
| 4 | `published` | `applications_closed` | system, or `job_posting.update` | `window_passed` or manual | emit `posting.closed` |
| 5 | `applications_closed` | `in_progress` | `round.manage` | `round_exists` | — |
| 6 | `published` | `in_progress` | `round.manage` | `round_exists` | closes the window early |
| 7 | `in_progress` | `completed` | `round.update` | `no_pending_offers` | emit stats refresh |
| 8 | any non-terminal | `cancelled` | `job_posting.delete` ⚠️ | `has_reason` | applications → `AUTO_WITHDRAWN`; pending offers revoked; notify everyone |
| 9 | `draft` | *deleted* | `job_posting.delete` | `no_applications` | hard delete — only ever possible from `draft` |

`draft` is the only state a posting can be deleted from, and only with no applications. Everything else is
**cancelled**, which preserves the audit trail — `Application` uses `PROTECT` on its posting for exactly this
reason.

### Guards

| Guard | Checks |
|---|---|
| `rule_valid` | `eligibility_rule` parses and every field is in the vocabulary ([eligibility-rules-spec.md](eligibility-rules-spec.md)) |
| `has_window` | both `application_opens_at` and `application_closes_at` set, and close > open |
| `company_active` | `company.status == active` — a blacklisted company cannot be published |
| `year_active` | `placement_year.status == active` |
| `window_passed` | `now >= application_closes_at` |
| `round_exists` | at least one `SelectionRound` |
| `no_pending_offers` | no offer in `issued` |
| `no_applications` | zero applications |
| `has_reason` | non-empty reason |

---

## Approval flow

Two-step by default: a coordinator drafts, an officer publishes. The separation exists because publishing is
the irreversible act — it makes the posting visible to hundreds of students and freezes the eligibility rule.

| Role | May |
|---|---|
| `placement_coordinator` | create, edit, submit for approval |
| `placement_officer` | everything above, plus **approve and publish** (⚠️ `job_posting.publish`) |

A single-role institute can grant `job_posting.publish` to coordinators, and transition 1→3 becomes one
action. That is a grant decision, not a code change.

---

## Publishing

```python
def publish(*, posting_id: int, principal) -> JobPosting:
    with transaction.atomic():
        p = (JobPosting.objects.select_for_update()
             .select_related("company", "placement_year").get(pk=posting_id))
        resolve_transition(p.status, PostingStatus.PUBLISHED)
        require_permission(principal, "placement_cell.job_posting.publish")
        run_guards((rule_valid, has_window, company_active, year_active), posting=p)

        p.status = PostingStatus.PUBLISHED
        p.eligibility_rule_locked_at = timezone.now()      # ← the freeze
        p.published_at = timezone.now()
        p.save(update_fields=["status", "eligibility_rule_locked_at", "published_at", "updated_at"])

        emit("placement.posting.published",
             {"posting_id": p.id, "company_id": p.company_id, "title": p.title,
              "application_closes_at": p.application_closes_at.isoformat(),
              "eligibility_rule_hash": sha256_of(p.eligibility_rule)},
             dedupe_key=f"posting.published:{p.id}")
    precompute_eligibility.delay(posting_id=p.id)           # after commit
    return p
```

Three things happen exactly once, atomically:

1. **The eligibility rule is frozen.** Enforced additionally by the database constraint
   `posting_published_has_locked_rule`, so it holds even if this service is bypassed.
2. `eligibility_rule_hash` goes into the event, so we can later prove which rule text a cohort was evaluated
   against.
3. Eligibility is precomputed for every registered student, which turns the students' posting list into one
   indexed read instead of N evaluations at page load.

### After publish: what may still change

| Field | Editable | Why |
|---|---|---|
| `eligibility_rule` | **never** | Fairness. A change means cancel and re-post. |
| `application_closes_at` | **extend only** | Extending helps students; shortening would strand applications in progress |
| `seats`, `role_summary`, `location`, `venue` | yes | Informational |
| `ctc_lpa` | yes, **audited** | It happens (a corrected figure), but it affects the dream-offer test, so every change writes an `audit_event` |
| `company`, `kind`, `placement_year` | **never** | Identity of the posting |

`ctc_lpa` is the subtle one. It feeds `is_dream` at offer-issue time, so changing it after publication changes
who may accept a second offer. Editing is allowed because corrections are real, but it is audited and the UI
warns.

---

## Cancellation

```python
def cancel(*, posting_id: int, reason: str, principal) -> JobPosting:
    require_permission(principal, "placement_cell.job_posting.delete")
    if not reason.strip():
        raise GuardFailed("has_reason")
    with transaction.atomic():
        p = JobPosting.objects.select_for_update().get(pk=posting_id)
        p.status = PostingStatus.CANCELLED
        p.save(update_fields=["status", "updated_at"])
        for offer in p.offers.filter(status=OfferStatus.ISSUED):
            offers.revoke(offer_id=offer.id, reason=f"posting cancelled: {reason}",
                          principal=principal, skip_step_up=True)
        emit("placement.posting.cancelled", {"posting_id": p.id, "reason": reason})
    # applications → AUTO_WITHDRAWN via the event handler
```

An **accepted** offer is not revoked by cancellation. Once a student has accepted and holds a
`PlacementRecord`, that is a commitment between them and the company; withdrawing the posting does not undo
it. Cancelling a posting with accepted offers requires each one to be revoked deliberately first, and the UI
says so.

---

## Timing tasks

| Task | Schedule | Does |
|---|---|---|
| `close_expired_windows` | hourly | `published` + `window_passed` → `applications_closed` (4) |
| `open_scheduled_postings` | hourly | no-op for state; `application_opens_at` gates the submit guard |
| `remind_closing_soon` | daily | notifies eligible students who have not applied, 48 h before close |
| `expire_offers` | every 15 min | offer expiry ([offer-and-tier-policy.md](offer-and-tier-policy.md)) |

All idempotent — they select on current state, so a second run finds nothing.

`remind_closing_soon` reads the precomputed `EligibilityEvaluation` (partial index on `is_eligible`) rather
than evaluating at send time, and is `digestable`, so a student with twelve closing postings gets one email.

---

## Verification

- Exhaustive `(from, to)` legality matrix, as in
  [application-state-machine.md](application-state-machine.md).
- Publishing with an invalid rule fails; the posting stays in `pending_approval`.
- Publishing stamps `eligibility_rule_locked_at`; a published posting's rule cannot be edited (service raises
  **and** the constraint holds if the service is bypassed).
- `application_closes_at` can be extended, not shortened.
- Changing `ctc_lpa` after publish writes an `audit_event`.
- A blacklisted company's posting cannot be published.
- Cancelling auto-withdraws applications and revokes **issued** offers, but leaves **accepted** ones intact.
- Deleting is possible only from `draft` with zero applications.
- `close_expired_windows` twice → one transition per posting.
- Publishing a posting precomputes eligibility for every registered student, within the task's soft time
  limit, with a bounded query count.
