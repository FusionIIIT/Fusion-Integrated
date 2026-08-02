---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Shared Kernel Reference

`core/` is the code every module may depend on. It is deliberately small, because a shared kernel is the
one place in a modular monolith where coupling is legitimate — and therefore the place where accidental
coupling hides.

`core/` **may not import `modules`**. Enforced by the `core-is-a-leaf` contract in `.importlinter`. If
something in `core` needs to know about a module, it belongs in that module.

---

## The admission test

A thing belongs in `core/` only if **all three** hold:

1. **Three or more modules need it.** Two is not enough — duplicate it and wait. The third occurrence tells
   you the real shape; the second only tells you two things looked similar.
2. **It has no domain semantics.** `paginate()` qualifies. `calculate_eligibility()` does not, even if three
   modules would use it — that is a module with a bad name.
3. **A change to it would be reviewed by an owner of each affected module.** If you would not want that
   review, it is not shared infrastructure; it is something you are hoping nobody notices.

**Removal is as important as admission.** If a `core/` module ends up used by one module, move it there. A
quarterly grep for single-consumer kernel code is a maintenance task, not a nice-to-have.

> The failure mode this guards against is visible in the legacy codebase: `helpers/decorators.py` contains
> `critical_section` (broken — `@wraps` used bare) and `designation_filter` (a `pass` stub). Shared
> utilities nobody owns rot quietly, and everybody assumes somebody else depends on them.

---

## Inventory

### `core/db/`

| Module | Contents | Notes |
|---|---|---|
| `fields.py` | `PIIField`, `SensitivePIIField`, `EncryptedField`, `MoneyField` | **PII classification is structural, not a comment.** `SensitivePIIField` marks DOB, phone, address, category, gender, medical. The structlog redactor and the export-audit check both read this classification, so marking a field is what makes it protected. `MoneyField` is `Decimal(12,2)` and refuses float assignment. |
| `mixins.py` | `TimeStampedModel`, `SoftDeleteModel`, `AuditedModel` | `SoftDeleteModel` is for anything referenced across a boundary — a hard delete would leave dangling ids, since cross-boundary refs are unconstrained integers ([ADR-0013](../01-architecture/adr/0013-no-cross-module-foreign-keys.md)). |
| `functions.py` | `Uuid7()`, `JsonbPath()`, `PercentileCont()` | Postgres expressions Django lacks. `PercentileCont` is how placement medians are computed in one aggregate rather than in Python. |
| `introspection.py` | `introspect_columns(table)` | Builds a shadow model from `information_schema`. This is the mechanical guard against hazard **H2** — the legacy `globals_moduleaccess` has columns added by raw DDL that no migration knows about. |
| `routers.py` | `ErpReadOnlyRouter` | Routes `erpshadow` models to the `erp` alias, `allow_migrate = False` always. Defence in depth; the actual control is the `platform_erp_ro` Postgres role. |
| `sql/` | The **only** place `raw()` is permitted | Parameterized, one file per query, each with a docstring saying why the ORM cannot express it. CI greps for `raw()`/`extra()`/`RawSQL` outside this directory. |

### `core/api/`

| Module | Contents | Notes |
|---|---|---|
| `defaults.py` | the shared `REST_FRAMEWORK` block | A new module inherits correct pagination, throttling, error handling and deny-by-default permissions **whether or not its author thought about it**. This is the highest-value file in `core/`. |
| `pagination.py` | `CursorPagination` | Cursor, not offset — offset pagination on a concurrently-written table silently skips and duplicates rows. No `count` by default; `COUNT(*)` is a sequential scan. |
| `exceptions.py` | `handler()` | Maps domain errors → the one error envelope. **No view builds an error response by hand.** Also where `request_id` is injected, so a user can read an id off a toast and support can grep it. |
| `filters.py` | `StrictFilterSet` | An unknown query parameter is a **422**, not silently ignored. Silent ignoring is how a typo becomes "the filter didn't work in production". |
| `throttling.py` | `ScopedUserThrottle` | Redis-backed, so counters are shared across gunicorn workers. An in-memory throttle with 5 workers is a 5× throttle. |
| `idempotency.py` | `@idempotent` | Backs `Idempotency-Key`. Same key + same body → the stored response; same key + different body → **409**. Makes a double-click safe. |
| `hydrate.py` | `attach(rows, mapping, attr)` | Attaches a `contracts` mapping to serializer context. Exists because `select_related` cannot cross a module boundary, and hand-rolling this per module is how N+1s reappear. |
| `schema.py` | drf-spectacular hooks | Enum naming, the error-envelope component, module tagging. |

### `core/events/`

| Module | Contents |
|---|---|
| `outbox.py` | `OutboxEvent`, `emit()`. Writes **inside** the caller's transaction — the whole point ([ADR-0006](../01-architecture/adr/0006-outbox-plus-celery-for-integration-events.md)). |
| `inbox.py` | `InboxEvent`, `@idempotent_consumer`. Records `dedupe_key` before acting, so redelivery is a no-op. |
| `publisher.py` | `publish_outbox` beat task. `SELECT ... FOR UPDATE SKIP LOCKED`, so multiple publishers are safe. |
| `registry.py` | `subscribe(topic, handler)`. Also enforces the **no-cycles** rule in the producer/consumer graph. |

### `core/files/`

| Module | Contents |
|---|---|
| `validators.py` | Extension allowlist ∩ magic-byte sniff (`python-magic`) ∩ size cap ∩ filename sanitized to `[A-Za-z0-9._-]`. **All four**, because each alone is bypassable. |
| `storage.py` | UUID-keyed storage, never the user's filename. Serves via `X-Accel-Redirect` with `Content-Disposition: attachment` and `nosniff`. |
| `scanning.py` | ClamAV in a Celery task, gating download; `pikepdf` sanitize pass stripping embedded JavaScript from PDFs. |

### `core/rules/`

| Module | Contents |
|---|---|
| `ast.py` | The rule AST as a pydantic discriminated union. Shared because eligibility (placement), entitlement (leave) and approval routing (HR) are the same evaluation problem over different vocabularies. |
| `engine.py` | `evaluate(rule, facts) -> Outcome`. **Fail-closed**: unknown field, missing fact or an error ⇒ `False` with an explicit reason, never true-by-default. Returns per-rule outcomes so a user sees *"CPI 6.8 < 7.0 required"* rather than "not eligible". |

The **field vocabulary** is supplied by the calling module, not by `core`. That is what keeps this
domain-free and passes admission test #2.

### `core/observability/`

| Module | Contents |
|---|---|
| `logging.py` | structlog → JSON on stdout. The PII redaction processor reads `core/db/fields` classifications and recursively redacts `{password, token, otp, secret, authorization, cookie, phone, address, date_of_birth, category, aadhaar}`. |
| `middleware.py` | `RequestIDMiddleware` — accepts nginx's `$request_id`, else generates a UUIDv7, stores it in a contextvar, echoes it in the response header **and** the error envelope. |
| `metrics.py` | django-prometheus registry plus the domain counters listed in [observability.md](../06-crosscutting/observability.md). |

---

## What is deliberately *not* in `core/`

| Not here | Where instead | Why |
|---|---|---|
| Any notion of a user | `modules/directory` | It has domain semantics, and `core` may not import modules |
| Academic concepts | `modules/academics` | The whole point of the ACL ([ADR-0007](../01-architecture/adr/0007-read-only-erp-access-via-acl.md)) |
| Notification sending | `modules/notifications` | Templates and audience rules are domain data |
| Approval-workflow engine | the module that needs it | Tempting, and wrong — HR, leave and placement approvals differ in ways a generic engine would paper over. Revisit when there are three real implementations to generalize from, not before. |
| Authentication | `packages/fusion_auth` | Shared with `services/iam` too, so it lives above `core` |
| Event **schemas** | `packages/fusion_contracts` | Shared across services; `core/events` is the transport, `fusion_contracts` is the vocabulary |
| `BaseService` / `BaseSelector` classes | nowhere | Inheritance-based scaffolding creates coupling without removing duplication. Services are plain functions. |

The approval-engine row is the one to keep re-reading. It is the single most common suggestion for a shared
kernel, and premature generalization there is how a kernel becomes a framework nobody can change.

---

## `packages/` — above `core/`

Shared across **both** Django projects (`services/iam` and `services/platform`), so they cannot live in
either one's `core`.

| Package | Contents | Consumers |
|---|---|---|
| `fusion_common` | structlog config, request-id contextvar, the error-envelope shape, pagination cursors | both services |
| `fusion_contracts` | pydantic models for **every** event topic, versioned | both services + contract tests |
| `fusion_auth` | `IamJWTAuthentication`, `HasPermission`, `HasModuleGrant`, `RequiresStepUp`, `Principal`, JWKS cache | both services, **and** the legacy monolith |

`fusion_auth` is also installed into the legacy monolith — that is how one new authentication class makes it
accept IAM tokens with no other change
([legacy-compatibility-and-erp-projection.md](../02-iam/legacy-compatibility-and-erp-projection.md#part-5--making-the-legacy-monolith-accept-iam-tokens)).
It therefore must stay compatible with **Django 3.1.5 / Python 3.8**, which is a real constraint: no
`match`, no `X | Y` annotations at runtime, no `StrEnum`. A tox target checks it.

---

## Changing `core/`

Kernel changes have the largest blast radius in the repository.

1. Get review from an owner of each affected module.
2. Additive changes only, where possible. A signature change means updating every caller in the same PR —
   `mypy` and `import-linter` will find them.
3. Deprecate before removing: keep the old name for one release with a `DeprecationWarning`, and CI treats
   the warning as an error in tests so callers are actually forced to move.
4. `core/` has its own tests at **90%** coverage. A bug here is a bug in every module.
5. Adding a dependency to `core/` adds it to every service. Justify it in the PR description.

## Quarterly review

- Is anything in `core/` used by fewer than three modules? → move it into the module that uses it.
- Has anything acquired domain semantics? → move it out.
- Is any module duplicating logic that now genuinely belongs here? → promote it, with the admission test.
- Is anything in `core/` untested or unused? → delete it. `helpers/decorators.py` in the legacy monolith is
  the cautionary example.
