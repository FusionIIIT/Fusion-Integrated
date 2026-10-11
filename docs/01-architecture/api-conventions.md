---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
enforced-by: >
  drf-spectacular schema generation + `git diff --exit-code openapi/` in CI, schemathesis
  fuzzing against the committed schema, and a shared DRF settings block in core/api/.
---

# API Conventions

One way to do each thing. Deviating needs a comment explaining why, and a reviewer who agrees.

---

## 1. URLs

```
https://fusion.iiitdmj.ac.in/app/api/iam/v1/…          fusion-iam
https://fusion.iiitdmj.ac.in/app/api/platform/v1/…     fusion-platform
https://fusion.iiitdmj.ac.in/app/api/sysops/v1/…       sysadmin console (Phase 7)
```

Inside the platform, the module owns its prefix:

```
/app/api/platform/v1/placement/postings
/app/api/platform/v1/placement/postings/{id}/rounds
/app/api/platform/v1/hr/employees
/app/api/platform/v1/academics/standings/{user_id}
```

Rules:

- **`snake_case` in paths and in JSON.** Not camelCase. The generated TypeScript client handles the
  boundary; hand-converting is how fields get mistyped.
- **Plural collection nouns**, singular for a specific member: `/postings`, `/postings/{id}`.
- **No verbs in paths** except for a genuine non-CRUD action, which is a `POST` to a sub-resource:
  `POST /applications/{id}/withdraw`, `POST /offers/{id}/accept`. Actions are not `PATCH` with a magic
  `status` field — an explicit endpoint gets its own permission, its own audit row and its own tests.
- **No trailing slash.** `APPEND_SLASH = False`. The legacy monolith is inconsistent about this and it
  causes real 404s; we pick one.
- **Never expose a database id in a path when a natural key exists.** `/postings/{id}` is fine (ids are
  opaque); `/companies/{slug}` is better where a slug exists.

### Versioning

`v1` is in the path, per service. It changes only for a **breaking** change: removing a field,
re-typing a field, changing a status code, or tightening validation. Adding an optional request field
or a response field is **not** breaking and does not bump the version.

When `v2` arrives, `v1` keeps working for at least one full release cycle, and the deprecation is
announced through a `Deprecation` and `Sunset` response header. → [ADR-0005](adr/0005-drf-over-django-ninja.md)

---

## 2. Response envelopes

### Success — the resource, unwrapped

```json
GET /app/api/platform/v1/placement/postings/8812
{
  "id": 8812,
  "title": "SDE-1",
  "company": {"id": 41, "name": "Acme", "slug": "acme", "tier": {"code": "T1", "rank": 1}},
  "ctc_lpa": "18.00",
  "seats": 4,
  "status": "published",
  "application_closes_at": "2026-08-14T18:30:00Z",
  "created_at": "2026-08-01T09:00:00Z",
  "updated_at": "2026-08-01T09:12:00Z"
}
```

No `{"data": ...}` wrapper on single resources. No `{"success": true}` — HTTP status carries that.

> The legacy monolith returns `{"success": true, "message": "...", ...}` from
> `POST /api/auth/login/`. That exact shape is frozen by a characterization test for as long as
> `Fusion-client` exists — see
> [legacy-compatibility-and-erp-projection.md](../02-iam/legacy-compatibility-and-erp-projection.md).
> New endpoints do not copy it.

### Lists — cursor pagination, always

```json
GET /app/api/platform/v1/placement/postings?limit=25
{
  "results": [ ... ],
  "next": "cD0yMDI2LTA4LTAxKzA5JTNBMDA...",
  "previous": null
}
```

**Cursor, not offset.** Offset pagination on a table receiving concurrent inserts silently skips and
duplicates rows, and `COUNT(*)` on a large table is a sequential scan. There is therefore **no `count`
field** by default. Where a total is genuinely needed (a coordinator's "142 applications" badge) it is a
separate, cached, explicitly-requested `?with_count=true` — and it is approximate above 10,000.

`limit` defaults to 25, maximum 100. A request above the maximum is clamped, not rejected.

### Errors — one envelope, everywhere

```json
HTTP/1.1 422 Unprocessable Entity
{
  "error": {
    "code": "validation_error",
    "message": "The submitted data was not valid.",
    "details": [
      {"field": "ctc_lpa", "code": "min_value", "message": "Must be greater than 0."},
      {"field": "seats",   "code": "required", "message": "This field is required."}
    ],
    "request_id": "9f2c1b4e-7a3d-4c1e-9f8a-2b6d5e0c1a77"
  }
}
```

Produced by a single handler in `core/api/exceptions.py`. **No view builds an error response by
hand.**

- `code` is a stable machine string. The client switches on it; it never parses `message`.
- `message` is human-readable, safe to display, and **never** contains internal detail — no SQL, no
  stack, no table names.
- `details` is present only for field-level validation.
- `request_id` is always present and matches the `X-Request-ID` response header, so a user can read it
  off an error toast and support can grep for it.

### Status codes

| Code | Used for |
|---|---|
| 200 | successful read, or an action that changed nothing observable |
| 201 | resource created — `Location` header **required** |
| 202 | accepted for asynchronous processing — body carries a poll URL |
| 204 | successful delete |
| 400 | malformed request (bad JSON, bad cursor) |
| 401 | no valid credentials, or the access token expired — **the client's cue to refresh** |
| 403 | authenticated but not permitted. Never used for "not found but you also lack access" (see below) |
| 404 | does not exist, **or exists but is outside your visibility** |
| 409 | state conflict — an illegal state-machine transition, a uniqueness collision |
| 410 | endpoint permanently retired (the console's write endpoints, from Phase 4) |
| 422 | well-formed but semantically invalid — validation, or a business rule refusal |
| 429 | throttled — `Retry-After` header **required** |
| 5xx | our fault. `message` is generic; the detail is in the logs under `request_id`. |

**403 vs 404.** If a user may not know a resource exists, return **404**. Returning 403 leaks
existence and turns any id column into an enumeration oracle. Ownership is enforced by *filtering the
queryset*, not by fetching and then checking — so 404 falls out naturally.

**409 vs 422.** 409 is "the world is in the wrong state" (accepting an already-accepted offer). 422 is
"your input is wrong" (a CTC of −5). A business-rule refusal that depends on policy rather than state —
"you already hold an offer and the policy is `blocked`" — is 422, with the `policy_decision` in
`details`.

---

## 3. Filtering, sorting, sparse fields

```
GET /placement/postings?status=published&company=acme&closes_after=2026-08-10&sort=-ctc_lpa
```

- Filters are explicit `django-filter` `FilterSet` fields. **No generic `?filter[...]` passthrough** —
  an unbounded filter surface is an unbounded index requirement and a denial-of-service vector.
- An unknown query parameter is a **422**, not silently ignored. Silent ignoring is how a typo becomes
  "the filter didn't work in production".
- Sorting: `?sort=field` / `?sort=-field`, from a per-endpoint allowlist. Every allowlisted sort must
  be backed by an index — asserted by the query-budget test.
- Sparse fieldsets: `?fields=id,title,ctc_lpa`. Optional, and only on endpoints where a heavy
  serializer measurably hurts.
- Dates are **ISO 8601 with an explicit offset**, UTC on the wire. `USE_TZ = True`, and no endpoint
  ever accepts a naive datetime.
- Money is a **string-serialized decimal** (`"18.00"`), never a float. `ctc_lpa` is
  `numeric(6,2)`.

---

## 4. Writes

### Idempotency

Every `POST` that creates a resource **MUST** accept an `Idempotency-Key` header, and the shell always
sends one (a UUIDv7 per user gesture).

```
POST /app/api/platform/v1/placement/applications
Idempotency-Key: 018f4c2a-...
```

Stored in `core_idempotency_record(key, principal_id, endpoint, request_hash, response_status,
response_body, created_at)` with a 24-hour TTL. A replay with the same key **and** the same request
hash returns the stored response. A replay with the same key and a *different* body is a **409** — that
is a client bug, not a retry.

This is what makes a double-click, a flaky network, or an impatient user pressing "Apply" twice safe.

### Partial updates

`PATCH` with only the changed fields. `PUT` is not used — full-replacement semantics on a model with
server-managed fields is a footgun.

Optimistic concurrency where concurrent edits are realistic: the client sends
`If-Match: "<updated_at epoch>"`, and a mismatch is **412 Precondition Failed**.

### Bulk operations

Explicit, bounded, and never a loop of single requests from the client:

```json
POST /placement/postings/{id}/applications/bulk-shortlist
{"application_ids": [11, 12, 13], "reason": "cleared aptitude"}

→ 200 {"succeeded": [11, 12], "failed": [{"id": 13, "code": "invalid_transition",
                                          "message": "Application is already REJECTED."}]}
```

Bulk endpoints are **partially successful by design** and always report per-item outcomes. Maximum
500 items; above that it is a 422 pointing at an async job endpoint. Each item's state transition is
validated individually — a bulk action cannot bypass the state machine.

---

## 5. Authentication & authorization at the HTTP edge

```python
# core/api/defaults.py — the shared DRF block
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["fusion_auth.IamJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES":     ["fusion_auth.IsAuthenticatedPrincipal"],
    "DEFAULT_PAGINATION_CLASS":       "core.api.pagination.CursorPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES":       ["core.api.throttling.ScopedUserThrottle"],
    "DEFAULT_THROTTLE_RATES":         {"anon": "30/min", "user": "600/min", "write": "120/min", ...},
    "EXCEPTION_HANDLER":              "core.api.exceptions.handler",
    "DEFAULT_SCHEMA_CLASS":           "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS":       "rest_framework.versioning.URLPathVersioning",
}
```

**Deny by default.** Every view declares its permission explicitly:

```python
class OfferIssueView(APIView):
    permission_classes = [HasPermission("placement.offer.issue"),
                          HasModuleGrant("placement_cell")]
```

- `HasModuleGrant` reads the token's `mod` claim — no database hit.
- `HasPermission` reads the cached permission set keyed by `pv` — no database hit on a warm cache.
- Object-level ownership is enforced by **filtering the queryset in the selector**, never by fetching
  and post-checking. A student's `get_queryset` returns only their own applications, so an id from
  another student is a 404 without a special case.
- Cookies carry the credential; CSRF is a double-submit `X-CSRF-Token` header on every unsafe method.
  → [ADR-0004](adr/0004-cookie-auth-and-csrf-strategy.md)

**Client-side permission checks are UX only.** `can("placement.offer.revoke")` hides a button. Every
one has a server counterpart, and a review that finds a client-only check rejects the PR.

### Throttling

Redis-backed, so counters are shared across gunicorn workers — an in-memory throttle with 5 workers is
a 5× throttle.

| Scope | Limit |
|---|---|
| `login` | 5/min per IP **and** 10/hour per username |
| `password_reset_send` | 3/hour per username, 10/hour per IP |
| `mfa_verify` | 5 per 5 min per user |
| `refresh` | 60/hour per session |
| `anon` | 30/min |
| `user` (read) | 600/min |
| `write` | 120/min |
| `apply` (placement) | 30/hour per user |
| `export` | 5/hour per user |
| `upload` | 20/hour per user |

429 responses always carry `Retry-After`.

---

## 6. Serializers

- **Read and write serializers are separate classes.** A single serializer doing both grows
  `read_only_fields` lists nobody can reason about, and eventually writes a field it should not.
- Nested reads are shallow — one level, with an explicit `select_related`. Deeper nesting means the
  client wants a different endpoint.
- **No `fields = "__all__"`.** Ever. It is how a `password_hash` or an internal note reaches a client
  the day someone adds a column.
- Computed fields are `SerializerMethodField` **only** if they need no extra query. If they do, the
  selector annotates them.
- Enums serialize as their string value plus a display label where the UI needs one:
  `{"status": "under_review", "status_display": "Under review"}`.

---

## 7. OpenAPI

`drf-spectacular` generates it; the schema is **committed**; CI runs:

```bash
python manage.py spectacular --file openapi/platform.v1.yaml --validate --fail-on-warn
git diff --exit-code openapi/
```

So the schema can never drift from the code, and the generated TypeScript client is always accurate.
Every view **MUST** carry `@extend_schema` with a summary, tagged by module, with at least one response
example — those examples become the MSW mocks in frontend tests, which is what stops frontend mocks
from drifting from reality.

`schemathesis` fuzzes the committed schema in CI against a live test server, which reliably finds the
endpoints that 500 on an empty string or a negative integer.

---

## 8. Long-running work

Anything that can exceed ~2 seconds returns **202** and a job:

```json
POST /placement/reports/placement-summary
→ 202 {"job_id": "018f...", "status": "queued",
       "poll_url": "/app/api/platform/v1/jobs/018f..."}

GET /app/api/platform/v1/jobs/018f...
→ 200 {"job_id": "018f...", "status": "succeeded",
       "result_url": "/app/api/platform/v1/downloads/018f...",
       "expires_at": "2026-08-02T10:00:00Z"}
```

Statuses: `queued` → `running` → `succeeded` | `failed` | `expired`. Files are served through
`X-Accel-Redirect` with `Content-Disposition: attachment`, from a UUID key, and download links expire.
Reports and exports are **never** generated synchronously — a coordinator exporting 3,000 rows must
not hold a gunicorn worker.

---

## 9. Headers

**Request:** `Authorization` is not used by the shell (cookies) but is accepted for service-to-service
calls · `X-CSRF-Token` on every unsafe method · `X-Request-ID` optional (generated if absent) ·
`Idempotency-Key` on creating POSTs · `If-Match` for optimistic concurrency.

**Response:** `X-Request-ID` always · `Location` on 201 · `Retry-After` on 429 and 503 · `ETag` and
`Last-Modified` on cacheable GETs · `Deprecation` and `Sunset` on retiring endpoints · plus the
security header block from [security-baseline.md](../06-crosscutting/security-baseline.md).

---

## 10. Checklist for a new endpoint

- [ ] Path is `snake_case`, plural, no trailing slash, no verb (or an explicit action sub-resource)
- [ ] Explicit `permission_classes` — never relying on the default alone for anything sensitive
- [ ] Queryset filtered by ownership/scope in the selector, so a foreign id yields 404
- [ ] Separate read/write serializers; no `fields = "__all__"`
- [ ] Cursor pagination on any list
- [ ] `django-filter` `FilterSet` with an allowlist; unknown params → 422
- [ ] Every sort field backed by an index
- [ ] `Idempotency-Key` accepted, if it creates
- [ ] Throttle scope chosen deliberately
- [ ] `@extend_schema` with a summary, tag and a response example
- [ ] `django_assert_max_num_queries` test with an explicit budget
- [ ] Error paths tested: 401, 403/404, 409, 422, 429
- [ ] `nplusone` clean in the test run
- [ ] Audit row written if the action is `is_dangerous`
