---
owner: iam-lead
status: authoritative
last-reviewed: 2026-08-01
criticality: >
  This is the highest-risk edge in the system. It touches live production data for ~3,277 users
  through an untested legacy codebase. Read it fully before changing anything in the projector.
---

# Legacy Compatibility & ERP Projection

Two obligations, both non-negotiable:

1. **The existing `Fusion-client` must keep working, byte-for-byte.** Its response contracts are frozen.
2. **The legacy monolith's own authorization must keep working**, which means the `globals_*` tables must
   stay populated correctly — so IAM projects into them, one way.

---

## Part 1 — Frozen response contracts

`Fusion-client` (73k LOC, no tests, no types) parses these three responses. Their shapes are frozen for as
long as it exists, and pinned by a characterization test suite written in **Phase 0**, before anything
else happens:
`Fusion/FusionIIIT/applications/globals/tests/test_auth_contract.py`.

### `POST /api/auth/login/`

```json
{"success": true, "message": "User logged in successfully",
 "token": "<40-char DRF key>", "designations": ["student", "placement_coordinator"]}
```

The `designations` array is built at `globals/api/views.py:39-64`, which prepends
`ExtraInfo.user_type` for students and then appends each `HoldsDesignation` whose designation differs from
it. That ordering quirk is load-bearing: the client uses `designations[0]` as the default role.

**IAM must reproduce it exactly**, including the ordering rule.

### `GET /api/auth/me`

Exact key set, verified against `globals/api/views.py:106-112` and pinned by
`ME_RESPONSE_KEYS` in the characterization suite:

```json
{"designation_info": ["student", "placement_coordinator"],
 "name": "Asha_Verma",
 "roll_no": "22bcs001",
 "accessible_modules": {"placement_coordinator": {"placement_cell": true, "examinations": false}},
 "last_selected_role": "student"}
```

Note there is **no `username` key** — the username is returned as `roll_no`, and the display name is
`first_name + "_" + last_name` (an underscore, not a space). Both are load-bearing for the client.

`accessible_modules` is `{designation_name: {module_column_name: bool}}`, built at
`globals/api/views.py:79-114` from `ModuleAccess.objects.filter(designation__iexact=...)` — one query per
designation, against an unindexed column.

**The keys are `globals_moduleaccess` column names.** `registry_module.legacy_column_name` exists precisely
to reproduce them.

### `PATCH /api/update-role/`

Writes `ExtraInfo.last_selected_role`, `max_length=20`. Hazard **H3**.

### The characterization suite

```python
LOGIN_KEYS = {"success", "message", "token", "designations"}
ME_KEYS    = {"username", "designation_info", "accessible_modules", "last_selected_role", ...}

def test_login_response_key_set_is_frozen(client, student):
    r = client.post("/api/auth/login/", {"username": ..., "password": ...})
    assert set(r.json()) == LOGIN_KEYS          # extra keys are as breaking as missing ones

def test_me_accessible_modules_shape(client, student_token):
    body = client.get("/api/auth/me", HTTP_AUTHORIZATION=f"Token {student_token}").json()
    assert set(body) == ME_KEYS
    for role, modules in body["accessible_modules"].items():
        assert all(isinstance(v, bool) for v in modules.values())

def test_designations_puts_user_type_first_for_students(...): ...
def test_iam_me_matches_legacy_me(...): ...   # the Phase 3 gate, run against staging
```

Extra keys fail too. The client uses `Object.keys` in places, and a new key changes iteration.

---

## Part 2 — The projection

```
IAM (authoritative)                    ERP (projection target)
rbac_role                        ───►  globals_designation
rbac_user_role                   ───►  globals_holdsdesignation
registry_role_module_grant       ───►  globals_moduleaccess
identity_user                    ───►  auth_user, globals_extrainfo
identity_session.active_role     ───►  globals_extrainfo.last_selected_role
```

**Strictly one-way.** ERP → IAM never happens. A hand-edit to `globals_holdsdesignation` is reported as
drift and, from Phase 4, overwritten. This is why the console's write endpoints
(`Fusion_System_Administrator/Backend/backend/api/views/roles.py:57,110,185`) return `410 Gone` from
Phase 4.

Mechanics — outbox, ordering, idempotency, pausability — are in
[data-ownership-and-sync.md](../01-architecture/data-ownership-and-sync.md#2-projection-mechanics-iam--erp).
The projector uses the `iam_erp_projector` Postgres role, which can write exactly three tables
([ADR-0012](../01-architecture/adr/0012-postgres-roles-and-least-privilege.md)).

### Column mapping

| IAM | ERP | Notes |
|---|---|---|
| `rbac_role.legacy_designation_name` | `globals_designation.name` | unique, `max_length=50`; ours capped at 20 for H3 |
| `rbac_role.name` | `globals_designation.full_name` | |
| `rbac_role.kind` | `globals_designation.type` | `academic`/`administrative` only; `functional` and `system` map to `administrative` |
| — | `globals_designation.basic`, `.category`, `.dept_if_not_basic_id` | **exist in production via raw DDL, not in any migration.** Written as `NULL`/default. Hazard **H2** |
| `rbac_user_role` holder | `globals_holdsdesignation.working` | the column legacy code should use for permissions |
| `rbac_user_role` permanent holder | `globals_holdsdesignation.user` | equals `working` unless officiating |
| `registry_module.legacy_column_name` | `globals_moduleaccess.<column>` | `NULL` ⇒ not projected |
| `identity_user.username` | `auth_user.username` | |
| `identity_user.status` | `auth_user.is_active` | `active` → `True`; `suspended`/`archived` → `False` |

---

## Part 3 — The three hazards

### H1 — only one holder per designation, institute-wide

```python
# applications/globals/models.py:166
unique_together = [['user', 'designation'], ['working', 'designation']]
```

Two placement coordinators cannot both be projected. The second insert raises `IntegrityError`.

**Default handling (option B):** project only the `is_primary` holder. IAM's
`userrole_one_primary_per_scope` partial unique index guarantees exactly one primary per `(role, scope)`,
so the choice is deterministic rather than "whichever the projector saw first".

Secondary holders are recorded in an explicit allowlist table so the reconciler reports zero drift in the
steady state — a non-empty report must always mean a real problem:

```python
class IntentionalProjectionGap(models.Model):
    user_role  = models.OneToOneField("rbac.UserRole", on_delete=models.CASCADE)
    reason     = models.CharField(max_length=64)   # h1_multi_holder | h1_scoped | delegated
    noted_at   = models.DateTimeField(auto_now_add=True)
```

**Projection predicate:**

```python
def is_projectable(assignment) -> bool:
    return (assignment.role.legacy_projectable
            and assignment.scope_type is None            # scoped roles cannot be represented
            and assignment.kind in ("permanent", "officiating")
            and assignment.is_primary
            and (assignment.valid_to is None or assignment.valid_to > now()))
```

**Consequence for users, stated plainly:** a secondary or scoped role holder sees that role only at
`/app/`. Their legacy sidebar will not show it. Acceptable because all new module work is in the shell —
but the placement office must be told, because it will otherwise be reported as a bug.

**This needs an institutional decision before Phase 4.** Options A (drop the legacy constraint — full
fidelity, one migration on a live table plus an audit of code assuming uniqueness) and C (never project
multi-holder roles) are in
[data-ownership-and-sync.md](../01-architecture/data-ownership-and-sync.md#h1--the-blocker). Tracked as
**R-H1** in [risk-register.md](../08-delivery/risk-register.md).

### H2 — production columns no migration knows about

`Fusion_System_Administrator/Backend/backend/api/views/schema.py:12-52` applies raw `ALTER TABLE`
statements to the ERP. Production therefore has:

- `globals_designation.basic` (bool), `.category` (varchar 20), `.dept_if_not_basic_id` (FK)
- `globals_moduleaccess.inventory_management` (bool)

None appear in `applications/globals/migrations/`, which stops at `0006_auto_20260304_0836`. Three
definitions of `ModuleAccess` disagree: the legacy model (20 booleans), the console's shadow model (21 —
has `inventory_management`, lacks `database`), and production (22).

**`manage.py makemigrations` on the monolith would generate migrations that drop production columns.**

Handling:

1. The projector builds its shadow model **at startup from `information_schema`**, so it always matches
   the live table rather than a stale Python class:

```python
def build_module_access_model():
    cols = introspect_columns("globals_moduleaccess")     # live, per boot
    bool_cols = [c for c in cols if c.data_type == "boolean"]
    return type("ModuleAccessShadow", (models.Model,), {
        "__module__": __name__,
        "designation": models.CharField(max_length=155),
        **{c.name: models.BooleanField(default=False) for c in bool_cols},
        "Meta": type("Meta", (), {"managed": False, "db_table": "globals_moduleaccess",
                                  "app_label": "erpshadow"}),
    })
```

2. A CI check asserts every non-null `registry_module.legacy_column_name` exists in the live column list
   and, conversely, reports live boolean columns with no corresponding module — so a column added by raw
   DDL surfaces as a build failure rather than a silent write of the wrong field.

3. **Phase 2 reconciles the drift into real monolith migrations** (`--fake`-aligned `AddField`s matching
   production exactly), so `makemigrations` stops wanting to drop columns. This is a prerequisite for
   anyone ever safely running `makemigrations` on the monolith again.

### H3 — `last_selected_role` is 20 characters

`ExtraInfo.last_selected_role` is `max_length=20`; `Designation.name` is 50 and
`ModuleAccess.designation` is 155. A role name longer than 20 characters cannot round-trip through
`PATCH /api/update-role/` — it is silently truncated by MySQL-style behaviour or raises on Postgres.

Handling: Phase 0 widens the column to 64. Until then, `rbac_role.legacy_designation_name` is
`max_length=20` and **validated at role creation** rather than truncated at projection time — the error
belongs where the name is chosen, not deep inside a Celery task.

---

## Part 4 — The reconciler

```
manage.py reconcile_erp_projection [--mode report|enforce] [--user <id>]
```

For every user, recompute the expected `globals_*` state and diff it against actual.

| Drift | `report` | `enforce` (Phase 4+) |
|---|---|---|
| Missing `globals_designation` row | log | create |
| Missing/extra `globals_holdsdesignation` row | log | create / delete |
| Wrong `globals_moduleaccess` boolean | log | correct |
| Extra designation not in IAM | log | delete + `audit_event` |
| Row matching an `IntentionalProjectionGap` | **not counted as drift** | ignored |
| Dangling `erp_user_id` (IAM points at a missing `auth_user`) | log + alert | **never auto-fix** — needs a human |

Nightly, plus on demand. Alert: `reconcile_drift_total > 0`. Because intentional gaps are allowlisted, the
steady state is exactly zero and any non-zero value is a real problem — which is the property that makes
the alert worth having.

**Phase 2's exit gate** uses a narrower job:

```
manage.py iam_diff_module_access --days 7
```

It recomputes IAM's `accessible_modules` payload for every user and diffs it against the live legacy
`/api/auth/me` output. **Seven consecutive days of empty diffs** is the gate to Phase 3. Spot-checks that
must be in the sample: a user with three designations; a user with **zero** `HoldsDesignation` rows (the
legacy middleware's `designation[0]` `IndexError` case); and a user whose designation has no
`ModuleAccess` row (the `access_rights` `UnboundLocalError` case).

---

## Part 5 — Making the legacy monolith accept IAM tokens

One new file, one settings change. No existing behaviour altered.

```python
# applications/globals/api/iam_auth.py
class IamJWTAuthentication(BaseAuthentication):
    """Validate an IAM RS256 token. Returns the ERP User so all existing code is unchanged."""
    def authenticate(self, request):
        if not getattr(settings, "IAM_JWT_AUTH_ENABLED", False):
            return None
        raw = request.COOKIES.get("fusion_at") or _bearer(request)
        if not raw:
            return None
        claims = _verify(raw)                       # cached JWKS, no call into IAM
        if _sid_revoked(claims["sid"]):
            raise AuthenticationFailed("Session revoked.")
        try:
            user = User.objects.get(pk=claims["erp_uid"])
        except User.DoesNotExist:
            raise AuthenticationFailed("Unknown user.")
        request.iam_claims = claims                 # rol / mod available if a view wants them
        return (user, None)
```

```python
# settings/production.py
REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "applications.globals.api.iam_auth.IamJWTAuthentication",   # first
    "rest_framework.authentication.TokenAuthentication",        # still works
    "rest_framework.authentication.SessionAuthentication",
]
```

Returning the ERP `User` object means every existing decorator, permission class and view — including
`applications/globals/access.py` and the three inconsistent enforcement paths — keeps working untouched.

### `Fusion-client` changes: two lines

`src/helper/validateauth.jsx` and `src/pages/login.jsx` gain `withCredentials: true`. Nothing else.

**Fallback** if even that is undesirable during the pilot: IAM also creates a legacy
`authtoken_token` row at login and returns it in the login response, so the old client continues working
with zero changes. Costs one extra write per login and is removed once the cookie path is proven.

---

## Part 6 — Prerequisites that are not optional

Before IAM issues a `Path=/` cookie the legacy production settings **must** be fixed:

| Item | Location | Why it blocks |
|---|---|---|
| `DEBUG = True` | `Fusion/settings/production.py:3` | **Any unhandled 500 renders `request.META`, including the auth cookie.** This is the blocker. |
| Hardcoded `SECRET_KEY` | `development.py:5` | Session and signing compromise |
| Hardcoded DB password | `development.py`, `production.py`, `docker-compose.yml`, `README.md:272` | Credential exposure |
| `CORS_ORIGIN_ALLOW_ALL = True` | `common.py:285` | Any origin can drive the authenticated API |
| `NAME = 'fusionlab'` in production | `production.py:14-22` | Production actually runs `fusion_newui_prod` |

All Phase 0. Verified by `manage.py check --deploy --fail-level WARNING` exiting clean.

Also in Phase 0, **one** `CREATE INDEX CONCURRENTLY` — zero risk, measured benefit
(`applications/globals/migrations/0008_hot_path_indexes.py`):

```sql
CREATE INDEX CONCURRENTLY IF NOT EXISTS ocms_grades_roll_sem_idx
  ON online_cms_student_grades (roll_no, semester);
```

That is the exact filter `calculate_cpi_for_student` uses. Verified on the development dump
(~104k rows): `Seq Scan` → `Bitmap Index Scan on ocms_grades_roll_sem_idx`.

> **Correction.** An earlier draft of this document specified three indexes. `EXPLAIN` against real data
> retired two of them:
>
> * `globals_moduleaccess (lower(designation))` — wrong expression *and* pointless. Django compiles
>   `__iexact` to `UPPER(designation::text)`, not `lower(...)`, so it would never have matched. And the
>   table is **101 rows in a single 8 KB page**: Postgres refuses the index even when it is spelled
>   correctly (reachable only with `enable_seqscan=off`). The claim that this caused "one sequential scan
>   per designation per login" was alarmist — it is a one-page read. The real cost on that path is the
>   N+1 query *pattern* in `auth_view`, which an index cannot fix.
> * `globals_holdsdesignation (working_id)` — redundant. `working_id` is already the leading column of the
>   composite index backing `unique_together ('working','designation')`, and the planner uses it for a
>   `working_id`-only lookup (verified: Index Only Scan).

---

## Verification

- Characterization suite green in CI, always. A failure blocks any release.
- `iam_diff_module_access --days 7` reports zero discrepancies across all users — the Phase 2 gate.
- A role assigned in the shell appears in the legacy `/api/auth/me` within 30 seconds.
- `reconcile_erp_projection --mode report` reports zero drift for 7 consecutive days before `enforce` is
  enabled.
- Projecting a second holder of a role produces an `IntentionalProjectionGap`, **not** an `IntegrityError`.
- The projector role cannot write `academic_information_student` (raises `InsufficientPrivilege`).
- Shadow-model introspection detects a column added by raw DDL, in a test that adds one.
- `IAM_JWT_AUTH_ENABLED=off` leaves legacy authentication byte-identical to today.
- A pilot user logs in at `/app/`, deep-links to `/dashboard` in the legacy app, and is recognized.
- `IAM_IS_ROLE_WRITER=off` pauses the projector with no data loss and no event loss.
