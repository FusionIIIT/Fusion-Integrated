---
owner: placement-lead
status: authoritative
last-reviewed: 2026-08-01
note: >
  The policy knobs are institute policy, not engineering. They must be set by the placement office
  before a placement year opens. The engineering commitment is that whatever is set is applied
  consistently, atomically, and with a persisted justification for every decision.
---

# Offer & Tier Policy

Whether a student may accept an offer is decided by one pure function. Every decision — allow or deny — is
persisted on the offer, so an appeal is answered from data rather than from memory.

---

## Policy knobs

`PlacementPolicy`, one row per `PlacementYear`.

| Knob | Type | Default | Meaning |
|---|---|---|---|
| `max_offers_allowed` | int | `1` | How many accepted offers a student may hold simultaneously |
| `pool_after_offer` | enum | `blocked` | What happens once they hold `max_offers_allowed` |
| `dream_threshold_lpa` | money | null | The CTC at or above which an offer is a "dream offer" |
| `upgrade_tier_rank_delta` | int | `1` | How many tiers a single upgrade may jump |
| `min_cpi_to_register` | decimal | `0` | Declared-CPI floor to register for the year |
| `allow_backlog_registration` | bool | `true` | Whether students with active backlogs may register |
| `offer_response_days` | int | `7` | Default response window |

### `pool_after_offer`

| Value | Once placed, a student… |
|---|---|
| `blocked` | may accept nothing further. Their other applications are auto-withdrawn. |
| `dream_only` | may accept **one** further offer, only if it is a dream offer and they do not already hold one. |
| `tier_upgrade_only` | may accept a further offer only from a strictly better tier, within `upgrade_tier_rank_delta`. |
| `unrestricted` | may accept any number up to `max_offers_allowed`. |

`policy_dream_needs_threshold` in the database prevents the undecidable configuration: `dream_only` with no
threshold set.

**Tier ranks: lower is better.** Rank 1 is the top tier. The upgrade rule therefore reads
`offer.tier_rank < current_best.tier_rank`.

---

## The decision function

`domain/rules/offer_policy.py` — pure, no Django, no database.

```python
def can_accept(policy: PolicyView, state: StudentOfferState, offer: OfferView) -> Decision:
    if state.is_debarred:
        return Decision.deny("debarred")
    if offer.status != "issued":
        return Decision.deny("offer_not_pending", actual=offer.status)
    if offer.respond_by < state.now:
        return Decision.deny("offer_expired", required=offer.respond_by, actual=state.now)
    if not state.accepted:
        return Decision.allow("first_offer")

    if len(state.accepted) < policy.max_offers_allowed:
        return Decision.allow("within_offer_quota",
                              required=policy.max_offers_allowed, actual=len(state.accepted))

    match policy.pool_after_offer:
        case "blocked":
            return Decision.deny("already_placed", detail=state.best.company_name)

        case "dream_only":
            if offer.ctc_lpa is None or policy.dream_threshold is None:
                return Decision.deny("dream_threshold_unset")
            if offer.ctc_lpa < policy.dream_threshold:
                return Decision.deny("below_dream_threshold",
                                     required=policy.dream_threshold, actual=offer.ctc_lpa)
            if any(o.is_dream for o in state.accepted):
                return Decision.deny("dream_offer_already_held")
            return Decision.allow("dream_upgrade", supersedes=state.best.offer_id)

        case "tier_upgrade_only":
            if offer.tier_rank is None or state.best.tier_rank is None:
                return Decision.deny("tier_unknown")
            if offer.tier_rank >= state.best.tier_rank:            # lower rank = better
                return Decision.deny("not_a_tier_upgrade",
                                     required=state.best.tier_rank - 1, actual=offer.tier_rank)
            if state.best.tier_rank - offer.tier_rank > policy.upgrade_tier_rank_delta:
                return Decision.deny("tier_jump_too_large",
                                     required=policy.upgrade_tier_rank_delta,
                                     actual=state.best.tier_rank - offer.tier_rank)
            return Decision.allow("tier_upgrade", supersedes=state.best.offer_id)

        case "unrestricted":
            return Decision.allow("unrestricted")

    return Decision.deny("policy_unrecognised")      # fail closed on an unknown enum value
```

```python
@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str                       # a stable machine code
    required: Any | None = None
    actual: Any | None = None
    detail: str | None = None
    supersedes: int | None = None     # the offer id being upgraded away from
```

Persisted verbatim to `Offer.policy_decision`. Every acceptance **and** every refused attempt carries a
machine-readable justification with the numbers involved, which is what makes an appeal answerable months
later.

The trailing `deny("policy_unrecognised")` is unreachable today. It is there so that adding an enum value
without updating this function denies rather than falls through — fail closed.

---

## Decision table

`max_offers_allowed = 1`, dream threshold ₹20 LPA, `upgrade_tier_rank_delta = 1`.

| Held | Incoming offer | `blocked` | `dream_only` | `tier_upgrade_only` | `unrestricted` |
|---|---|---|---|---|---|
| nothing | anything | ✅ `first_offer` | ✅ | ✅ | ✅ |
| T3, ₹8 LPA | T3, ₹9 LPA | ❌ `already_placed` | ❌ `below_dream_threshold` | ❌ `not_a_tier_upgrade` | ✅ |
| T3, ₹8 LPA | T2, ₹12 LPA | ❌ | ❌ `below_dream_threshold` | ✅ `tier_upgrade` | ✅ |
| T3, ₹8 LPA | T1, ₹30 LPA | ❌ | ✅ `dream_upgrade` | ❌ `tier_jump_too_large` (2 > 1) | ✅ |
| T1, ₹25 LPA (dream) | T1, ₹28 LPA | ❌ | ❌ `dream_offer_already_held` | ❌ `not_a_tier_upgrade` | ✅ |
| anything | expired | ❌ `offer_expired` | ❌ | ❌ | ❌ |
| anything, debarred | anything | ❌ `debarred` | ❌ | ❌ | ❌ |

The third row is the interesting one and worth showing the placement office before they choose a policy: a
₹30 LPA T1 offer is accepted under `dream_only` but **refused** under `tier_upgrade_only`, because it jumps
two tiers. That is a real policy difference, not a bug, and it is exactly the kind of thing that must be
decided deliberately rather than discovered in week three of a season.

---

## Acceptance — one transaction

```python
def accept(*, offer_id: int, principal) -> PlacementRecord:
    with transaction.atomic():
        offer = Offer.objects.select_related("posting__placement_year__policy",
                                             "posting__company").get(pk=offer_id)
        if offer.user_id != principal.erp_user_id:
            raise Forbidden

        # THE per-student mutex. Two tabs accepting two offers serialize here.
        reg = (PlacementRegistration.objects.select_for_update()
               .get(placement_year=offer.posting.placement_year, user_id=offer.user_id))

        state    = build_student_offer_state(reg)
        decision = can_accept(PolicyView.of(reg.placement_year.policy), state, OfferView.of(offer))
        offer.policy_decision = asdict(decision)
        if not decision.allowed:
            offer.save(update_fields=["policy_decision"])       # record the refusal too
            raise OfferNotAcceptable(decision)                  # → 422 with the decision in details

        offer.status = OfferStatus.ACCEPTED
        offer.decided_at = timezone.now()
        offer.save(update_fields=["status", "decided_at", "policy_decision"])

        if decision.supersedes:
            prior = Offer.objects.select_for_update().get(pk=decision.supersedes)
            prior.status = OfferStatus.SUPERSEDED
            prior.save(update_fields=["status"])
            PlacementRecord.objects.filter(offer=prior, is_active=True).update(is_active=False)

        record = PlacementRecord.objects.create(
            user_id=offer.user_id, placement_year=offer.posting.placement_year,
            offer=offer, company=offer.posting.company, ctc_lpa=offer.ctc_lpa)

        applications.transition(application_id=offer.application_id,
                                to_status=ApplicationStatus.OFFER_ACCEPTED, principal=principal)

        if reg.placement_year.policy.pool_after_offer == PoolAfterOffer.BLOCKED:
            auto_withdraw_other_applications(reg, reason="auto_withdrawn_placed")

        reg.offer_count = len(state.accepted) + 1
        reg.best_accepted_tier_rank = _min_rank(state, offer)
        reg.save(update_fields=["offer_count", "best_accepted_tier_rank"])

        emit("placement.offer.accepted",
             {"offer_id": offer.id, "user_id": offer.user_id, "placement_record_id": record.id,
              "superseded_offer_id": decision.supersedes, "policy_decision": asdict(decision)},
             dedupe_key=f"offer.accepted:{offer.id}")
    return record
```

Note that a **refusal is persisted too**. When a student says "the system wouldn't let me accept", the answer
is in `policy_decision` with the exact numbers.

---

## Race safety — two independent layers

**Primary: `select_for_update` on `PlacementRegistration`.** That row is the per-student mutex. Two browser
tabs accepting two different offers serialize on it; the second transaction sees the first's committed state
and is denied by `can_accept`.

**Backstop: a partial unique index in the database.**

```sql
CREATE UNIQUE INDEX record_one_active_per_year
  ON placement_placementrecord (user_id, placement_year_id) WHERE is_active;
```

Even if the service layer is bypassed — a management command, a data fix, a future bug — a student cannot end
up with two active placement records for one year. The application-level lock is the control; this is what
holds when the control is circumvented, which over a system's lifetime it eventually is.

Both are tested: a concurrency test with two real threads against a real Postgres (not sqlite, which
serializes everything and would make the test vacuous), and a test that inserts a second record directly and
expects `IntegrityError`.

---

## Revocation

`placement.offer.revoke` is `is_dangerous`: MFA required, **step-up re-authentication within 5 minutes**, an
`audit_event` on every use, and inclusion in the weekly privileged-access report.

```python
def revoke(*, offer_id: int, reason: str, principal) -> Offer:
    require_step_up(principal, max_age_seconds=300)
    if not reason.strip():
        raise GuardFailed("has_reason")
    with transaction.atomic():
        offer = Offer.objects.select_for_update().get(pk=offer_id)
        was_accepted = offer.status == OfferStatus.ACCEPTED
        offer.status, offer.revoked_reason = OfferStatus.REVOKED, reason
        offer.save(update_fields=["status", "revoked_reason"])
        if was_accepted:
            PlacementRecord.objects.filter(offer=offer, is_active=True).update(is_active=False)
            _recompute_registration_counters(offer.user_id, offer.posting.placement_year_id)
        applications.transition(application_id=offer.application_id,
                                to_status=ApplicationStatus.REJECTED,
                                principal=principal, reason=f"offer revoked: {reason}")
        emit("placement.offer.revoked", {...})
```

Revoking an **accepted** offer deactivates the placement record and recomputes counters, which frees the
student to accept elsewhere. It does **not** restore their auto-withdrawn applications — those postings have
moved on, and silently resurrecting an application into a closed process would be worse than leaving it
withdrawn. The coordinator is told this explicitly in the confirmation dialog.

---

## Expiry

`respond_by = issued_at + policy.offer_response_days`, extendable by
`placement_cell.offer.update` (not dangerous — extending a deadline only ever helps the student).

`expire_offers` runs every 15 minutes over the partial index `offer_pending_expiry_idx`, so the sweep never
scans historical offers. Idempotent.

A reminder notification goes out 48 hours and 12 hours before the deadline.

---

## Verification

- **Every row of the decision table** is a test, for all four `pool_after_offer` values.
- `dream_only` with no threshold → `dream_threshold_unset`, never an exception.
- An unknown `pool_after_offer` value → `policy_unrecognised` (deny), not a fall-through.
- **Concurrency:** two threads, two offers, one student — exactly one succeeds; the loser's response carries
  the persisted `policy_decision`.
- **Backstop:** inserting a second active `PlacementRecord` directly raises `IntegrityError`.
- Superseding: the prior offer becomes `superseded`, its record `is_active=False`, and the student has
  exactly one active record throughout.
- Tier immutability: re-tiering a company does **not** change `tier_rank` on already-issued offers.
- Revoking an accepted offer frees the student to accept elsewhere, and does not resurrect auto-withdrawn
  applications.
- Revocation without step-up auth returns 403 `step_up_required`.
- Every acceptance attempt, allowed or denied, leaves a `policy_decision` on the offer.
- `expire_offers` twice produces one transition per offer.
