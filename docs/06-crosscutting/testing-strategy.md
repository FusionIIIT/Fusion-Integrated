---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Testing Strategy

The starting point matters here. **The existing estate has effectively no tests**: all 31
`applications/*/tests.py` in the monolith are the three-line Django stub (218 lines total), there is no
`pytest`, `pytest-django`, `factory-boy` or `coverage` in `requirements.txt`, neither React client has a test
runner, and CI is a welcome-bot.

So there is no safety net to lean on during the auth migration. That single fact shapes this strategy: the
**characterization suite** and the **empty-diff gate** are load-bearing, not optional extras.

---

## Layers

| Layer | Tools | Coverage | Speed |
|---|---|---|---|
| **Domain** (`domain/**`) | pytest + hypothesis | **90%** | ms — no database |
| Services / selectors | pytest-django + factory-boy + freezegun | 85% | fast |
| API | DRF `APIClient` + schemathesis | 80% | fast |
| Events | contract tests on **both** producer and consumer | **100% of topics** | fast |
| **Legacy compatibility** | characterization tests | **must never fail** | fast |
| Frontend units | vitest + RTL + MSW | 70% packages / 60% shell | fast |
| E2E | Playwright | the 6 critical journeys | slow |
| Visual | Playwright screenshots | shell layout, 3 breakpoints | slow |
| Mutation | `mutmut` on `domain/rules/` only | ≥ 80% killed | very slow, nightly |

Overall gate: `--cov-fail-under=75`, ratcheting upward. A phase cannot close below it.

**Domain at 90% is achievable because `domain/` cannot import Django** — enforced by `import-linter`. The
offer-acceptance policy is a pure function of `(policy, state, offer)`, so its twelve branches are twelve
millisecond tests instead of twelve fixture-heavy integration tests. That constraint is what makes the target
realistic rather than aspirational.

---

## Factories are the only way to create data

```python
# modules/placement/tests/factories.py
class JobPostingFactory(DjangoModelFactory):
    class Meta:
        model = JobPosting
    company        = factory.SubFactory(CompanyFactory)
    placement_year = factory.SubFactory(PlacementYearFactory)
    title          = factory.Sequence(lambda n: f"Role {n}")
    kind           = PostingKind.FTE
    ctc_lpa        = Decimal("12.00")
    status         = PostingStatus.DRAFT

    class Params:
        published = factory.Trait(
            status=PostingStatus.PUBLISHED,
            eligibility_rule_locked_at=factory.LazyFunction(timezone.now),
            published_at=factory.LazyFunction(timezone.now),
        )
```

No fixture JSON, no `setUp` that builds objects by hand. Traits express states (`published=True`), so a test
reads as intent rather than as setup.

**Time is always injected.** `freezegun` for anything touching `respond_by`, `valid_to`, `declared_at` or an
idle timeout. A test that depends on wall-clock time fails at midnight, once, and gets marked flaky.

---

## Tests run as the real application role

```python
# pytest.ini
DJANGO_SETTINGS_MODULE = config.settings.test
```

`config/settings/test.py` connects as **`platform_app`**, not as a superuser.

This is the detail that makes [ADR-0012](../01-architecture/adr/0012-postgres-roles-and-least-privilege.md)
real rather than decorative. Running tests as superuser would mean a missing grant is invisible until
production, and the following tests could not exist:

```python
def test_snapshot_is_immutable():
    snap = ResultSnapshotFactory()
    with pytest.raises(InternalError):          # InsufficientPrivilege
        ResultSnapshot.objects.filter(pk=snap.pk).update(cpi=Decimal("10.00"))

def test_platform_cannot_write_erp():
    with pytest.raises(InternalError):
        ErpStudentShadow.objects.using("erp").filter(pk=1).update(cpi=9.9)
```

A separate `CREATEDB` role is used for `--create-db`, documented in
[environments.md](../07-ops/environments.md).

---

## Domain tests

Pure, fast, exhaustive. Property-based where the state space is worth exploring.

```python
@pytest.mark.parametrize("policy,held,incoming,expected", DECISION_TABLE)
def test_can_accept_decision_table(policy, held, incoming, expected):
    assert can_accept(policy, held, incoming).reason == expected

@given(st.sampled_from(list(ApplicationStatus)), st.sampled_from(list(ApplicationStatus)))
def test_transition_legality_matches_the_table(frm, to):
    legal = any(t.frm == frm and t.to == to for t in TRANSITIONS)
    assert is_legal(frm, to) is legal

@given(st.sampled_from(list(ApplicationStatus)))
def test_terminal_states_have_no_outgoing_transitions(status):
    if status in TERMINAL:
        assert not [t for t in TRANSITIONS if t.frm == status]
```

The exhaustive 13×13 legality matrix is what makes the transition table *the* specification rather than
documentation of it.

Deny-wins resolution is property-tested over generated role graphs — the ordering-independence claim in
[rbac-model.md](../02-iam/rbac-model.md) needs to hold for **every** graph, not the three we thought of.

---

## Service tests

Concurrency tests run against **real Postgres**, never sqlite. sqlite serializes everything, which would make
these vacuous:

```python
@pytest.mark.django_db(transaction=True)
def test_two_concurrent_accepts_yield_one_placement():
    student, a, b = _setup_two_offers()
    with ThreadPoolExecutor(2) as ex:
        results = [f for f in as_completed([ex.submit(accept, a.id), ex.submit(accept, b.id)])]
    outcomes = [_outcome(f) for f in results]
    assert outcomes.count("ok") == 1
    assert PlacementRecord.objects.filter(user_id=student, is_active=True).count() == 1

@pytest.mark.django_db(transaction=True)
def test_unique_index_backstops_a_bypassed_service():
    """Even if the service layer is circumvented, the DB holds."""
    rec = PlacementRecordFactory()
    with pytest.raises(IntegrityError):
        PlacementRecord.objects.create(user_id=rec.user_id, placement_year=rec.placement_year, ...)
```

Also asserted per service: the audit row exists, the outbox row exists **and** is absent when the transaction
rolls back:

```python
def test_no_outbox_row_when_the_transaction_rolls_back():
    with pytest.raises(BoomError):
        service_that_emits_then_raises()
    assert OutboxEvent.objects.count() == 0
```

---

## API tests

Every endpoint tests the happy path **and** 401, 403/404, 409, 422, 429. The 404-not-403 rule needs an explicit
test per ownership-scoped endpoint, because getting it wrong is invisible until someone enumerates ids:

```python
def test_foreign_application_is_404_not_403(client, other_students_application):
    assert client.get(f"/api/v1/placement/applications/{other_students_application.id}").status_code == 404
```

`schemathesis` fuzzes the **committed** OpenAPI schema against a live test server. It reliably finds the
endpoints that 500 on an empty string, a negative integer, or a 10,000-character field — the cases nobody
writes by hand.

Query budgets per list endpoint, constant in row count
([performance-and-capacity.md](performance-and-capacity.md#n1-prevention)).

---

## Event contract tests

Both sides, for every topic. A topic in code but not in
[event-catalog.md](../01-architecture/event-catalog.md) fails CI, and vice versa.

```python
def test_producer_payload_validates(): OfferAcceptedV1.model_validate(emitted_payload)
def test_consumer_accepts_the_schema(): on_offer_accepted(build_event(OfferAcceptedV1(...)))

def test_replay_is_a_noop():
    """At-least-once delivery is the contract. Every consumer must be idempotent."""
    handler(event); before = snapshot_state()
    handler(event); assert snapshot_state() == before

def test_out_of_order_declaration_does_not_regress_standing():
    ingest(sem5_declaration); ingest(sem3_declaration)
    assert StudentAcademicStanding.objects.get(user_id=u).semester == 5
```

The last one is the test that proves the `declared_seq` guard in
[academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md#5-the-advance-rule--one-atomic-statement)
actually works.

---

## Legacy characterization tests — the safety net

`Fusion/FusionIIIT/applications/globals/tests/test_auth_contract.py`, written in **Phase 0, before anything
else**. This is the only thing standing between the auth migration and a broken `Fusion-client`.

```python
LOGIN_KEYS = {"success", "message", "token", "designations"}

def test_login_response_key_set_is_frozen(client, student):
    r = client.post("/api/auth/login/", {...})
    assert set(r.json()) == LOGIN_KEYS      # EXTRA keys fail too — the client uses Object.keys

def test_designations_puts_user_type_first_for_students(...): ...
def test_me_accessible_modules_is_role_to_module_to_bool(...): ...
def test_iam_me_matches_legacy_me(staging):          # the Phase 3 gate
    assert iam_payload == legacy_payload
```

**These must never fail.** A failure blocks any release. Extra keys are as breaking as missing ones, because
the client iterates.

The other half of the net is not a test but a **gate**: `iam_diff_module_access --days 7` must report zero
discrepancies across all ~3,277 users for seven consecutive days before Phase 3 begins
([auth-migration-runbook.md](../02-iam/auth-migration-runbook.md)). With no legacy test suite to trust, a
production diff is the strongest evidence available.

Spot-checks that **must** be in the sample, because they are the known crash cases in the legacy middleware: a
user with 3+ designations · a user with **zero** `HoldsDesignation` rows (`designation[0]` → `IndexError`) · a
user whose designation has no `ModuleAccess` row (`access_rights` → `UnboundLocalError`).

---

## Frontend

```tsx
renderWithProviders(<ComplaintQueuePage />, { permissions: ["complaints.complaint.view"] });
```

`packages/testing` supplies Mantine + TanStack Query + `MemoryRouter` + a mock `AuthProvider`.

**MSW handlers are generated from the OpenAPI examples**, so a mock cannot drift from the real API. That is the
failure mode that makes frontend tests worthless: green tests against a mock that no longer resembles the
server. It is also why `@extend_schema` examples are mandatory on the backend.

Asserted per page: loading, empty and error are **three distinct** rendered outputs; `ErrorState` renders the
`request_id`; a permission-gated control is absent without the permission.

---

## E2E — six journeys

Playwright against a `docker compose` stack (postgres + 2× redis + iam + platform + shell preview).

1. Login → the sidebar shows **exactly** the granted modules.
2. Role switch → the sidebar changes; cached data is cleared.
3. Student applies → appears in "my applications".
4. Coordinator shortlists → the student sees the status change.
5. **Offer acceptance blocks the second accept** — two contexts, one student.
6. Deep-link an ungranted module → `<Forbidden/>`, URL preserved, not a blank screen.

Six, not sixty. E2E is slow and flaky by nature; everything else belongs in vitest.

### Visual regression

`expect(page).toHaveScreenshot()` at `375`, `768`, `1440`, with baselines captured from the **live
`/sysadmin/` client**. This is how the design-system extraction is *proved* pixel-identical rather than asserted
([design-system.md](../05-frontend/design-system.md)).

**Run only inside a pinned Docker image.** Host font rendering differs between macOS and Linux, and
regenerating baselines from a laptop is exactly how these tests become noise everyone ignores.

---

## Mutation testing

`mutmut` on `domain/rules/` only — the eligibility engine and the offer policy. ≥ 80% of mutants killed.

Restricted to those two directories deliberately: they are pure, small, and the place where a plausible-looking
test can pass while the logic is wrong. Running mutation testing over the whole codebase would take hours and
teach us little.

Nightly, not per-PR.

---

## CI gates

```
ruff check · ruff format --check
mypy                       (strict on core/ and */domain/, lenient elsewhere)
bandit -r -ll
lint-imports               (the boundary contracts)
no_cross_module_fk.py
pytest -n auto --cov --cov-fail-under=75
makemigrations --check --dry-run
check --deploy --fail-level WARNING
django-migration-linter
spectacular --validate && git diff --exit-code openapi/
export_permission_catalog && git diff --exit-code docs/02-iam/permission-catalog.md
module_registry_parity · nav_route_parity · nav_icon_parity · nav_permission_parity
legacy_column_parity       (hazard H2)
grep guards                (Student.cpi · Spi · raw() outside core/db/sql/)
```

Frontend: `turbo lint typecheck test build` → coverage gate → `size-limit` → Playwright (PR: chromium;
nightly: all browsers + visual).

---

## What we do not test

| Not tested | Why |
|---|---|
| Django, DRF, Mantine internals | Not ours |
| Generated `orval` hooks | Generated from a validated schema |
| The legacy monolith's business logic | Out of scope. We pin its **auth contract** and nothing else. |
| Getters and trivial serializers | Coverage theatre |
| Every permutation of every filter | One representative test per filter type |

## Anti-patterns

| Don't | Because |
|---|---|
| `sqlite` for concurrency tests | it serializes, making the test vacuous |
| Tests as superuser | a missing Postgres grant becomes invisible |
| `time.sleep()` | flake; use `freezegun` or a callback |
| Fixture JSON | drifts from the models; use factories |
| Asserting on `error.message` | it is human-facing; assert on `error.code` |
| A test that passes at 50 rows and fails at 500 | that is the N+1 the budget exists to catch |
| Regenerating visual baselines locally | font differences make them meaningless |
| `@pytest.mark.skip` without an issue link | it never comes back |
