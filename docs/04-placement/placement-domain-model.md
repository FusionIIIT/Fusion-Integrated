---
owner: placement-lead
status: authoritative
last-reviewed: 2026-08-01
note: >
  Designed from first principles. The deprecated applications/placement_cell app (25 models) is NOT
  the basis for this — see NG2 in vision-and-scope.md. Where a legacy idea is worth keeping it is
  called out explicitly.
---

# Placement Domain Model

All entities, fields, constraints and indexes for `modules/placement`.

Companions: [application-state-machine.md](application-state-machine.md) ·
[job-posting-lifecycle.md](job-posting-lifecycle.md) ·
[eligibility-rules-spec.md](eligibility-rules-spec.md) ·
[offer-and-tier-policy.md](offer-and-tier-policy.md) ·
[academic-snapshot-integration.md](academic-snapshot-integration.md).

---

## Shape

```
PlacementYear 1──1 PlacementPolicy
      │
      ├──* PlacementRegistration ─── user_id (no FK — crosses to IAM)
      │
      └──* JobPosting *──1 Company *──1 CompanyTier
               │
               ├──* EligibilityEvaluation ─── user_id
               ├──* Application *──1 Document(resume)
               │        └──* ApplicationTransition          (append-only)
               │        └──* RoundParticipation *──1 SelectionRound
               └──* SelectionRound
               └──* Offer ──► PlacementRecord
```

Every `user_id` is a **plain integer**, never a foreign key — it references IAM's `erp_user_id` across a
boundary ([ADR-0013](../01-architecture/adr/0013-no-cross-module-foreign-keys.md)). Reads go through
`directory.contracts.get_users(ids)` and `academics.contracts.get_standings(ids)`.

---

## Configuration

### `PlacementYear`

```python
class PlacementYear(TimeStampedModel):
    code      = models.CharField(max_length=12, unique=True)      # "2026-27"
    label     = models.CharField(max_length=60)
    starts_on = models.DateField()
    ends_on   = models.DateField()
    status    = models.CharField(max_length=10, choices=YearStatus.choices,
                                default=YearStatus.DRAFT)         # draft|active|closed
    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(ends_on__gt=F("starts_on")), name="year_window_valid"),
            models.UniqueConstraint(fields=["status"], condition=Q(status="active"),
                                    name="year_only_one_active"),
        ]
```

`year_only_one_active` is the important one: exactly one active year, enforced by a partial unique index.
Two active years would make "am I already placed?" ambiguous, and that question drives the entire offer
policy.

### `PlacementPolicy`

One row per year. The knobs are institute policy, not engineering
([offer-and-tier-policy.md](offer-and-tier-policy.md)).

```python
class PlacementPolicy(TimeStampedModel):
    placement_year          = models.OneToOneField(PlacementYear, on_delete=models.CASCADE,
                                                   related_name="policy")
    max_offers_allowed      = models.PositiveSmallIntegerField(default=1)
    pool_after_offer        = models.CharField(max_length=20, choices=PoolAfterOffer.choices,
                                               default=PoolAfterOffer.BLOCKED)
    dream_threshold_lpa     = MoneyField(null=True, blank=True)
    upgrade_tier_rank_delta = models.PositiveSmallIntegerField(default=1)
    min_cpi_to_register     = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    allow_backlog_registration = models.BooleanField(default=True)
    offer_response_days     = models.PositiveSmallIntegerField(default=7)
    class Meta:
        constraints = [models.CheckConstraint(
            check=~Q(pool_after_offer="dream_only") | Q(dream_threshold_lpa__isnull=False),
            name="policy_dream_needs_threshold")]
```

`policy_dream_needs_threshold` prevents the configuration that would make `can_accept` undecidable — a
`dream_only` policy with no threshold set.

### `CompanyTier`

```python
class CompanyTier(TimeStampedModel):
    code        = models.CharField(max_length=12, unique=True)     # "T1"
    label       = models.CharField(max_length=40)
    rank        = models.PositiveSmallIntegerField(unique=True)    # 1 = best
    min_ctc_lpa = MoneyField(null=True, blank=True)                # advisory only
```

**Lower rank = better company.** Stated here because the tier-upgrade rule reads `offer.tier_rank <
current.tier_rank`, which is only obvious once you know the direction.

---

## Companies

```python
class Company(TimeStampedModel):
    name       = models.CharField(max_length=160)
    slug       = models.SlugField(max_length=80, unique=True)
    website    = models.URLField(blank=True)
    sector     = models.CharField(max_length=60, blank=True)
    hq_city    = models.CharField(max_length=80, blank=True)
    tier       = models.ForeignKey(CompanyTier, null=True, blank=True, on_delete=models.SET_NULL)
    status     = models.CharField(max_length=12, choices=CompanyStatus.choices,
                                 default=CompanyStatus.PROSPECT)   # prospect|active|blacklisted
    notes      = models.TextField(blank=True)                      # internal, never exposed to students
    class Meta:
        indexes = [models.Index(fields=["status", "name"], name="company_status_name_idx")]

class CompanyContact(TimeStampedModel):
    company     = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="contacts")
    name        = models.CharField(max_length=120)
    designation = PIIField(max_length=80, blank=True)
    email       = PIIField(max_length=254, blank=True)
    phone       = SensitivePIIField(max_length=20, blank=True)
    is_primary  = models.BooleanField(default=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["company"], condition=Q(is_primary=True),
                                               name="contact_one_primary_per_company")]
```

Contact fields use the PII field classes from `core/db/fields.py`, so the structlog redactor and the
export-audit check pick them up automatically. `Company.notes` is internal and excluded from every
student-facing serializer.

---

## Registration

```python
class PlacementRegistration(TimeStampedModel):
    placement_year          = models.ForeignKey(PlacementYear, on_delete=models.CASCADE,
                                                related_name="registrations")
    user_id                 = models.IntegerField(db_index=True)
    status                  = models.CharField(max_length=12, choices=RegistrationStatus.choices,
                                               default=RegistrationStatus.REGISTERED)
    offer_count             = models.PositiveSmallIntegerField(default=0)
    best_accepted_tier_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    debarred_reason         = models.CharField(max_length=200, blank=True)
    registered_at           = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["placement_year", "user_id"],
                                               name="registration_unique_per_year")]
        indexes = [models.Index(fields=["placement_year", "status"],
                                name="registration_year_status_idx")]
```

`RegistrationStatus` = `registered` · `debarred` · `opted_out`.

**This row is the per-student mutex for offer acceptance.** `services/offers.accept()` opens its transaction
with `select_for_update()` on it, so two browser tabs accepting two offers serialize and the second sees the
first's state. `offer_count` and `best_accepted_tier_rank` are denormalized counters maintained inside that
same transaction — deliberately, because the policy check needs them under the lock.

---

## Postings

```python
class JobPosting(TimeStampedModel):
    company        = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="postings")
    placement_year = models.ForeignKey(PlacementYear, on_delete=models.PROTECT, related_name="postings")
    title          = models.CharField(max_length=160)
    kind           = models.CharField(max_length=12, choices=PostingKind.choices)  # internship|fte|ppo
    role_summary   = models.TextField(max_length=8000, blank=True)                 # markdown
    location       = models.CharField(max_length=120, blank=True)
    ctc_lpa        = MoneyField(null=True, blank=True)
    stipend_pm     = MoneyField(null=True, blank=True)
    bond_months    = models.PositiveSmallIntegerField(null=True, blank=True)
    seats          = models.PositiveSmallIntegerField(null=True, blank=True)       # null = unspecified

    eligibility_rule           = models.JSONField(default=dict)
    eligibility_rule_locked_at = models.DateTimeField(null=True, blank=True)

    status                = models.CharField(max_length=20, choices=PostingStatus.choices,
                                             default=PostingStatus.DRAFT)
    application_opens_at  = models.DateTimeField(null=True, blank=True)
    application_closes_at = models.DateTimeField(null=True, blank=True)
    published_at          = models.DateTimeField(null=True, blank=True)
    created_by_user_id    = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(application_closes_at__isnull=True)
                      | Q(application_opens_at__isnull=True)
                      | Q(application_closes_at__gt=F("application_opens_at")),
                name="posting_window_valid"),
            models.CheckConstraint(
                check=~Q(status="published") | Q(eligibility_rule_locked_at__isnull=False),
                name="posting_published_has_locked_rule"),
        ]
        indexes = [
            models.Index(fields=["placement_year", "status", "application_closes_at"],
                         name="posting_year_status_close_idx"),
            models.Index(fields=["company", "placement_year"], name="posting_company_year_idx"),
            models.Index(fields=["status", "-published_at"], name="posting_status_published_idx"),
        ]
```

`posting_published_has_locked_rule` is enforced by the database rather than only by the service, because
publishing without freezing the eligibility rule would let a rule change after students have applied —
which is the unfairness this whole design is guarding against
([eligibility-rules-spec.md](eligibility-rules-spec.md)).

FSM and approval flow: [job-posting-lifecycle.md](job-posting-lifecycle.md).

---

## Eligibility

```python
class EligibilityEvaluation(models.Model):
    posting        = models.ForeignKey(JobPosting, on_delete=models.CASCADE,
                                       related_name="evaluations")
    user_id        = models.IntegerField(db_index=True)
    is_eligible    = models.BooleanField()
    failed_rules   = models.JSONField(default=list)
    inputs_version = models.BigIntegerField()      # standing_version + registration mtime
    evaluated_at   = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["posting", "user_id"],
                                               name="evaluation_unique")]
        indexes = [models.Index(fields=["posting"], condition=Q(is_eligible=True),
                                name="evaluation_eligible_idx")]
```

A **cache with an audit trail**, not a source of truth. `inputs_version` means a standing change invalidates
it for free — no explicit invalidation call, so no forgotten one.

`failed_rules` stores per-rule outcomes so the student sees *"CPI 6.8 < 7.0 required"* rather than "not
eligible", which is the difference between a useful screen and a helpdesk ticket.

---

## Applications

```python
class Application(TimeStampedModel):
    posting     = models.ForeignKey(JobPosting, on_delete=models.PROTECT, related_name="applications")
    user_id     = models.IntegerField(db_index=True)
    status      = models.CharField(max_length=20, choices=ApplicationStatus.choices,
                                  default=ApplicationStatus.DRAFT)

    # Frozen at submission — what the decision was actually made on.
    cpi_at_apply                 = models.DecimalField(max_digits=4, decimal_places=2, null=True)
    standing_version_at_apply    = models.BigIntegerField(null=True)
    eligibility_snapshot         = models.JSONField(default=dict)

    resume          = models.ForeignKey("placement.Document", null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name="applications")
    cover_note      = models.TextField(max_length=4000, blank=True)
    applied_at      = models.DateTimeField(null=True, blank=True)
    withdrawn_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["posting", "user_id"], name="application_unique"),
            models.CheckConstraint(check=~Q(status="submitted") | Q(applied_at__isnull=False),
                                   name="application_submitted_has_timestamp"),
        ]
        indexes = [
            models.Index(fields=["posting", "status"], name="application_posting_status_idx"),
            models.Index(fields=["user_id", "status"], name="application_user_status_idx"),
            models.Index(fields=["status", "-applied_at"], name="application_status_applied_idx"),
        ]

class ApplicationTransition(models.Model):
    """Append-only. Every status change, forever."""
    application   = models.ForeignKey(Application, on_delete=models.CASCADE,
                                      related_name="transitions")
    from_status   = models.CharField(max_length=20)
    to_status     = models.CharField(max_length=20)
    actor_user_id = models.IntegerField(null=True)     # null = system (auto-withdraw, expiry)
    reason        = models.CharField(max_length=300, blank=True)
    at            = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["application", "at"], name="transition_app_at_idx")]
```

The three frozen fields — `cpi_at_apply`, `standing_version_at_apply`, `eligibility_snapshot` — record what
was true when the student applied. When a result is later retracted and the CPI moves, this is what answers
*"was this application legitimate at the time?"* without reconstructing history.

`Application` uses `PROTECT` on its posting: a posting with applications is **cancelled**, never deleted.

---

## Rounds

```python
class SelectionRound(TimeStampedModel):
    posting   = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name="rounds")
    seq       = models.PositiveSmallIntegerField()
    name      = models.CharField(max_length=80)
    kind      = models.CharField(max_length=12, choices=RoundKind.choices)   # test|gd|tech|hr|other
    mode      = models.CharField(max_length=10, choices=RoundMode.choices)   # online|campus|offsite
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at   = models.DateTimeField(null=True, blank=True)
    venue     = models.CharField(max_length=160, blank=True)
    capacity  = models.PositiveSmallIntegerField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["posting", "seq"], name="round_unique_seq")]
        ordering = ["posting", "seq"]

class RoundParticipation(TimeStampedModel):
    round       = models.ForeignKey(SelectionRound, on_delete=models.CASCADE,
                                    related_name="participations")
    application = models.ForeignKey(Application, on_delete=models.CASCADE,
                                    related_name="participations")
    outcome     = models.CharField(max_length=12, choices=RoundOutcome.choices,
                                   default=RoundOutcome.PENDING)
    score       = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    remarks     = models.CharField(max_length=300, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["round", "application"],
                                               name="participation_unique")]
        indexes = [models.Index(fields=["application"], name="participation_app_idx")]
```

`RoundOutcome` = `pending` · `attended` · `absent` · `passed` · `failed`.

`attended` and `absent` are attendance; `passed` and `failed` are results. They are separate values on one
field rather than two fields because a student can be `absent` without a result, and `passed` implies
attendance — two nullable booleans would allow the meaningless `absent + passed`.

---

## Offers

```python
class Offer(TimeStampedModel):
    posting   = models.ForeignKey(JobPosting, on_delete=models.PROTECT, related_name="offers")
    user_id   = models.IntegerField(db_index=True)
    ctc_lpa   = MoneyField()
    tier_rank = models.PositiveSmallIntegerField(null=True, blank=True)   # COPIED at issue
    is_dream  = models.BooleanField(default=False)                        # COMPUTED at issue
    letter    = models.ForeignKey("placement.Document", null=True, blank=True,
                                  on_delete=models.SET_NULL)
    status    = models.CharField(max_length=12, choices=OfferStatus.choices,
                                 default=OfferStatus.ISSUED)
    respond_by      = models.DateTimeField()
    policy_decision = models.JSONField(default=dict)
    issued_by_user_id = models.IntegerField()
    decided_at      = models.DateTimeField(null=True, blank=True)
    revoked_reason  = models.CharField(max_length=200, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "status"], name="offer_user_status_idx"),
            models.Index(fields=["user_id"], condition=Q(status="accepted"),
                         name="offer_user_accepted_idx"),
            models.Index(fields=["status", "respond_by"], condition=Q(status="issued"),
                         name="offer_pending_expiry_idx"),
        ]
```

`OfferStatus` = `issued` · `accepted` · `declined` · `revoked` · `superseded` · `expired`.

**`tier_rank` and `is_dream` are copied/computed at issue time, not looked up later.** If a company is
re-tiered mid-season, past offers keep the tier they were issued under — otherwise a re-tiering would
retroactively change whether a student's acceptance was permitted, and an appeal would be unanswerable.

`policy_decision` persists the `Decision` object from every acceptance attempt, so an appeal is answered from
data. `offer_pending_expiry_idx` is what makes the expiry sweep cheap.

```python
class PlacementRecord(TimeStampedModel):
    """The canonical 'this student is placed' fact."""
    user_id        = models.IntegerField(db_index=True)
    placement_year = models.ForeignKey(PlacementYear, on_delete=models.PROTECT,
                                        related_name="records")
    offer          = models.OneToOneField(Offer, on_delete=models.PROTECT, related_name="record")
    company        = models.ForeignKey(Company, on_delete=models.PROTECT)
    ctc_lpa        = MoneyField()
    is_active      = models.BooleanField(default=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_id", "placement_year"],
                                    condition=Q(is_active=True),
                                    name="record_one_active_per_year"),
        ]
        indexes = [models.Index(fields=["placement_year", "company"], name="record_year_company_idx")]
```

**`record_one_active_per_year` is the database-level backstop** for the whole offer policy. Even if the
service layer is bypassed — a management command, a data fix, a bug — a student cannot hold two active
placement records for one year. The `select_for_update` on the registration row is the primary control;
this is the one that holds when the primary is circumvented.

---

## Documents

```python
class Document(TimeStampedModel):
    owner_user_id = models.IntegerField(db_index=True)
    kind          = models.CharField(max_length=16, choices=DocumentKind.choices)
    file          = models.FileField(upload_to=uuid_key_path)   # UUID key, never the user's filename
    original_name = models.CharField(max_length=160)
    sha256        = models.CharField(max_length=64, db_index=True)
    size_bytes    = models.PositiveIntegerField()
    scan_status   = models.CharField(max_length=12, default="pending")   # pending|clean|infected
    is_active     = models.BooleanField(default=True)
    class Meta:
        indexes = [models.Index(fields=["owner_user_id", "kind"], condition=Q(is_active=True),
                                name="document_owner_kind_idx")]
```

`DocumentKind` = `resume` · `offer_letter` · `certificate` · `other`.

Validation is extension allowlist ∩ magic-byte sniff ∩ size cap ∩ sanitized filename ∩ UUID storage key ∩
ClamAV scan gating download ∩ `pikepdf` sanitize pass — **all of them**, via `core/files/`
([security-baseline.md](../06-crosscutting/security-baseline.md)). `scan_status = "pending"` blocks download
until the scan completes.

`sha256` deduplicates storage and detects a resume re-uploaded unchanged.

---

## Statistics

```python
class PlacementStatsSnapshot(models.Model):
    placement_year  = models.ForeignKey(PlacementYear, on_delete=models.CASCADE)
    dimension       = models.CharField(max_length=20)   # overall|discipline|batch|tier|company
    dimension_value = models.CharField(max_length=80, blank=True)
    registered      = models.PositiveIntegerField(default=0)
    placed          = models.PositiveIntegerField(default=0)
    offers          = models.PositiveIntegerField(default=0)
    median_ctc      = MoneyField(null=True)
    mean_ctc        = MoneyField(null=True)
    max_ctc         = MoneyField(null=True)
    computed_at     = models.DateTimeField()
    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["placement_year", "dimension", "dimension_value"], name="stats_unique_dimension")]
```

**Materialized, never computed on request.** The public statistics page reads only snapshots, so a viral
share cannot touch the transactional tables.
Detail: [placement-reports-and-statistics.md](placement-reports-and-statistics.md).

---

## Review flags

```python
class ReviewFlag(TimeStampedModel):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="flags")
    kind        = models.CharField(max_length=32)     # standing_changed|now_ineligible|user_suspended
    detail      = models.JSONField(default=dict)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by_user_id = models.IntegerField(null=True, blank=True)
```

Created when a student's declared standing changes such that they would no longer be eligible for a posting
they have an in-flight application to, or when their account is suspended.

**Never auto-rejects.** A result retraction may be a clerical correction, and a student who has already
interviewed deserves a human decision.

---

## Index rationale

Every index above matches a real query's `WHERE` + `ORDER BY`. The ones worth explaining:

| Index | Query it serves |
|---|---|
| `posting_year_status_close_idx` | the student's posting list: active year, published, closing soon |
| `application_posting_status_idx` | the coordinator's applications-for-a-posting screen, filtered by status |
| `application_user_status_idx` | the student's "my applications" screen |
| `offer_user_accepted_idx` (partial) | the hot path in `can_accept` — "does this student hold an accepted offer?" |
| `offer_pending_expiry_idx` (partial) | the expiry sweep, which otherwise scans every offer ever issued |
| `evaluation_eligible_idx` (partial) | "who is eligible for this posting?" without scanning ineligible rows |
| `document_owner_kind_idx` (partial) | a student's active resume |
| `snapshot_user_decl_idx` | retraction fallback: the latest non-retracted snapshot per user |

Partial indexes appear wherever the interesting rows are a small fraction of the table — pending offers,
eligible evaluations, active documents. The legacy monolith has **one** `db_index=True` across 424 models,
which is why its login path performs a sequential scan per designation.

---

## What we deliberately did not carry over from the legacy module

| Legacy | Why not |
|---|---|
| 25 models mixing placement with a full student professional profile (`Project`, `Skill`, `Education`, `Experience`, `Publication`, `Patent`, `Interest`, `Achievement`, `Extracurricular`, …) | Two bounded contexts in one app. A professional profile is a separate module if it is wanted at all; `eis` already covers faculty. |
| `StudentRecord` / `StudentPlacement` / `PlacementRecord` — three overlapping models | One `PlacementRecord`, with a partial unique index that makes "placed" unambiguous |
| `PlacementStatus` as a free-text status field | An explicit state machine with an append-only transition log |
| Reading `Student.cpi` for eligibility | It is permanently `0.0`. Declared snapshots instead — [academic-snapshot-integration.md](academic-snapshot-integration.md) |
| `NotifyStudent` / `MessageOfficer` models | Notification rules as data, in `modules/notifications` |
| `ChairmanVisit`, `PlacementSchedule` | Not modelled until someone asks for them. `SelectionRound` covers scheduling. |
| No offer-acceptance policy at all | `can_accept` as a pure function with a persisted decision |
