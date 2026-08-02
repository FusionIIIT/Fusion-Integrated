---
owner: placement-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Application State Machine

An application's status changes **only** through this table. `services/applications.transition()` is the
only writer, and it validates against `domain/state_machine.py` before writing.

The table is declarative rather than a set of `if` branches, so an illegal transition is **impossible to
express** rather than merely rejected — and the table renders directly into the diagram below.

---

## States

| State | Meaning | Terminal |
|---|---|---|
| `DRAFT` | Started, not submitted. Invisible to the coordinator. | |
| `SUBMITTED` | In the queue. Eligibility was satisfied and frozen at this moment. | |
| `UNDER_REVIEW` | A coordinator has picked it up. | |
| `SHORTLISTED` | Cleared screening; will be put into rounds. | |
| `IN_PROCESS` | Participating in at least one round. | |
| `SELECTED` | Cleared all rounds. Awaiting an offer. | |
| `OFFER_ISSUED` | An offer exists and the clock is running. | |
| `REJECTED` | Not proceeding. | ✔ |
| `WITHDRAWN` | The student pulled out. | ✔ |
| `AUTO_WITHDRAWN` | Withdrawn by the system because they were placed elsewhere. | ✔ |
| `OFFER_ACCEPTED` | Accepted. | ✔ |
| `OFFER_DECLINED` | Declined. | ✔ |
| `OFFER_EXPIRED` | The response deadline passed with no answer. | ✔ |

`AUTO_WITHDRAWN` is deliberately distinct from `WITHDRAWN`. Statistics and any conversation about a
student's conduct need to distinguish "they chose to leave" from "policy removed them" — collapsing the two
makes a student look flaky when they were placed.

---

## Diagram

```
                          ┌──────────────────────────────────► WITHDRAWN
                          │  (student, from any non-terminal)
                          │
  DRAFT ──submit──► SUBMITTED ──review──► UNDER_REVIEW ──┬──shortlist──► SHORTLISTED
    │                                                     └──reject─────► REJECTED ◄────┐
    └──abandon──► (deleted)                                                             │
                                                                                        │
  SHORTLISTED ──schedule──► IN_PROCESS ──all rounds passed──► SELECTED                  │
                                 │                                                      │
                                 └──round failed / absent────────────────────────────────┘
                                                                                        │
  SELECTED ──issue offer──► OFFER_ISSUED ──┬──accept───► OFFER_ACCEPTED                 │
                                            ├──decline──► OFFER_DECLINED                │
                                            ├──lapse────► OFFER_EXPIRED                 │
                                            └──revoke───► REJECTED ─────────────────────┘

  any non-terminal ──placed elsewhere (per pool_after_offer)──► AUTO_WITHDRAWN
  any non-terminal ──posting cancelled──► AUTO_WITHDRAWN
```

Mermaid source: [`_diagrams/application-state-machine.mmd`](../_diagrams/application-state-machine.mmd).

---

## Transition table

`domain/state_machine.py`. `actor` is `student`, `coordinator` or `system`.

| # | From | To | Actor | Permission | Guards | Effects |
|---|---|---|---|---|---|---|
| 1 | `DRAFT` | `SUBMITTED` | student | `application.create` | `window_open`, `is_registered`, `not_debarred`, **`is_eligible`**, `has_resume` | freeze `cpi_at_apply` + `standing_version_at_apply` + `eligibility_snapshot`; set `applied_at`; emit `application.submitted` |
| 2 | `SUBMITTED` | `UNDER_REVIEW` | coordinator | `application.review` | — | emit `status_changed` |
| 3 | `SUBMITTED` | `REJECTED` | coordinator | `application.review` | `has_reason` | notify student |
| 4 | `UNDER_REVIEW` | `SHORTLISTED` | coordinator | `application.review` | — | notify student |
| 5 | `UNDER_REVIEW` | `REJECTED` | coordinator | `application.review` | `has_reason` | notify student |
| 6 | `SHORTLISTED` | `IN_PROCESS` | coordinator | `round.manage` | `round_exists` | create `RoundParticipation`; notify student |
| 7 | `SHORTLISTED` | `REJECTED` | coordinator | `application.review` | `has_reason` | notify student |
| 8 | `IN_PROCESS` | `SELECTED` | coordinator | `round.update` | `all_rounds_passed` | notify student |
| 9 | `IN_PROCESS` | `REJECTED` | coordinator | `round.update` | `a_round_failed_or_absent` | notify student |
| 10 | `SELECTED` | `OFFER_ISSUED` | coordinator | `offer.issue` ⚠️ | `no_pending_offer_for_posting`, `respond_by_in_future` | create `Offer`; notify student |
| 11 | `OFFER_ISSUED` | `OFFER_ACCEPTED` | student | `offer.approve` | **`can_accept(policy, state, offer)`** | create `PlacementRecord`; supersede prior; auto-withdraw others; bump counters; emit `offer.accepted` |
| 12 | `OFFER_ISSUED` | `OFFER_DECLINED` | student | `offer.approve` | — | emit `offer.declined` |
| 13 | `OFFER_ISSUED` | `OFFER_EXPIRED` | system | — | `respond_by_passed` | emit `offer.expired` |
| 14 | `OFFER_ISSUED` | `REJECTED` | coordinator | `offer.revoke` ⚠️ | `has_reason`, step-up auth | `Offer → revoked`; notify student; audit |
| 15 | any non-terminal | `WITHDRAWN` | student | `application.delete` | `not_offer_accepted` | emit `status_changed` |
| 16 | any non-terminal | `AUTO_WITHDRAWN` | system | — | `placed_elsewhere` **and** `policy.pool_after_offer == blocked` | notify student, stating why |
| 17 | any non-terminal | `AUTO_WITHDRAWN` | system | — | `posting_cancelled` | notify student |

Transitions 3, 5, 7, 9 and 14 all land on `REJECTED` from different origins with different guards. Modelling
them as distinct rows rather than one wildcard keeps the guard requirements explicit — a rejection at review
needs a reason, a rejection from a failed round needs the round outcome.

### Guards

Pure predicates in `domain/state_machine.py`. No Django import, so each is a fast unit test.

| Guard | Checks |
|---|---|
| `window_open` | `application_opens_at <= now < application_closes_at` |
| `is_registered` | a `PlacementRegistration` exists for the posting's year |
| `not_debarred` | `registration.status == registered` |
| `is_eligible` | a **fresh** `EligibilityEvaluation` (matching `inputs_version`) says eligible |
| `has_resume` | an active `resume` document with `scan_status == clean` |
| `all_rounds_passed` | every `RoundParticipation` for the application is `passed` |
| `a_round_failed_or_absent` | at least one is `failed` or `absent` |
| `no_pending_offer_for_posting` | no `issued` offer already exists for this `(posting, user)` |
| `respond_by_in_future` | the deadline is in the future at issue time |
| `respond_by_passed` | the deadline has passed |
| `not_offer_accepted` | prevents withdrawing after acceptance — use revoke instead |
| `placed_elsewhere` | an active `PlacementRecord` exists for the year |
| `can_accept` | the full policy decision — [offer-and-tier-policy.md](offer-and-tier-policy.md) |
| `has_reason` | a non-empty reason string |

---

## The service

```python
def transition(*, application_id: int, to_status: str, principal,
               reason: str = "", **ctx) -> Application:
    with transaction.atomic():
        app = (Application.objects.select_for_update()
               .select_related("posting__placement_year__policy")
               .get(pk=application_id))

        t = resolve_transition(app.status, to_status)          # raises InvalidTransition (→ 409)
        require_permission(principal, t.permission)            # raises Forbidden (→ 403)
        run_guards(t.guards, app=app, principal=principal, reason=reason, **ctx)  # → 422

        frm, app.status = app.status, to_status
        apply_field_effects(app, t, principal, **ctx)
        app.save(update_fields=t.touched_fields + ["updated_at"])

        ApplicationTransition.objects.create(
            application=app, from_status=frm, to_status=to_status,
            actor_user_id=principal.erp_user_id if principal else None, reason=reason)

        emit("placement.application.status_changed",
             {"application_id": app.id, "user_id": app.user_id, "posting_id": app.posting_id,
              "from": frm, "to": to_status,
              "actor_user_id": principal.erp_user_id if principal else None, "reason": reason},
             dedupe_key=f"app.status:{app.id}:{frm}->{to_status}:{app.updated_at.timestamp()}")
    return app
```

Five properties worth naming:

- **`select_for_update`** — two coordinators clicking "shortlist" at once serialize; the second sees the
  first's result and gets a 409 rather than double-writing.
- **The audit row is written in the same transaction**, so history can never diverge from state.
- **`emit()` inside the transaction** — the outbox pattern. An event cannot fire for a rolled-back
  transition ([ADR-0006](../01-architecture/adr/0006-outbox-plus-celery-for-integration-events.md)).
- **Domain errors, not HTTP errors.** `core/api/exceptions.py` maps `InvalidTransition` → 409,
  `GuardFailed` → 422, `Forbidden` → 403. The same service is callable from a task or a management command.
- **`update_fields`** from the transition definition, so a transition cannot accidentally persist an
  unrelated in-memory change.

---

## Bulk transitions

A coordinator shortlisting 40 applications is one request, and it is **partially successful by design**:

```json
POST /placement/postings/{id}/applications/bulk-transition
{"application_ids": [11, 12, 13], "to_status": "shortlisted", "reason": "cleared aptitude"}

→ 200 {"succeeded": [11, 12],
       "failed": [{"id": 13, "code": "invalid_transition",
                   "message": "Application is already REJECTED."}]}
```

Each item runs the **full** validation independently — a bulk action cannot bypass the state machine, and one
bad item does not roll back the good ones. Maximum 500 per request. This matters because the alternative,
all-or-nothing, means a coordinator with one stale row in their selection cannot proceed at all.

---

## Automatic transitions

| Task | Schedule | Does |
|---|---|---|
| `expire_offers` | every 15 min | `respond_by` passed → `OFFER_EXPIRED` (13) |
| `auto_withdraw_after_placement` | on `placement.offer.accepted` | applies (16) per `pool_after_offer` |
| `cancel_posting_applications` | on `placement.posting.cancelled` | applies (17) |
| `close_expired_windows` | hourly | posting → `applications_closed`; leaves applications alone |

All idempotent and re-runnable: they select on current state, so a second run finds nothing to do.

---

## Interaction with academic retraction

When `academics.standing.changed` arrives and a student would no longer be eligible for a posting they have
an in-flight application to:

1. Their `EligibilityEvaluation` invalidates automatically (`inputs_version` changed).
2. A `ReviewFlag(kind="now_ineligible")` is created for the coordinator.
3. **The application's status does not change.**

**No automatic rejection, ever.** A retraction may be a clerical correction, and a student who has already
attended three rounds deserves a human decision. `cpi_at_apply` and `eligibility_snapshot` on the
application are what let that human see what was true at submission.
[academic-snapshot-integration.md](academic-snapshot-integration.md#7-retraction)

---

## Verification

- **Exhaustive legality:** for every `(from, to)` pair in the 13×13 matrix, assert legal ⇔ present in
  `TRANSITIONS`. This is the test that makes the table the specification.
- **Terminal states have no outgoing transitions** — property test over all states.
- **Every guard has a failing test and a passing test.**
- **Concurrency:** two threads transitioning the same application — exactly one succeeds, the other gets
  409. Run against a real database, not `sqlite`.
- **Eligibility freshness:** submitting with a stale `EligibilityEvaluation` re-evaluates rather than
  trusting the cache.
- **`can_accept`:** two tabs accepting two offers — exactly one succeeds; the loser's response carries the
  persisted `policy_decision` reason.
- **Audit completeness:** every status change has a matching `ApplicationTransition` row. Asserted by a
  test that walks a full lifecycle and compares counts.
- **Idempotent automation:** running `expire_offers` twice produces one transition per offer.
- **Bulk partial success:** a mixed batch returns per-item outcomes and commits the valid ones.
- **Retraction:** a now-ineligible in-flight application gains a `ReviewFlag` and keeps its status.
