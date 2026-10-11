---
owner: iam-lead
status: authoritative
last-reviewed: 2026-08-01
---

# IAM Domain Model

Every table in `fusion_system_db` schema `iam`, with its constraints, indexes and the reasoning behind
them. Django app labels: `identity`, `rbac`, `registry`, `auditing`.

Companion documents: [rbac-model.md](rbac-model.md) for resolution semantics,
[token-and-session-design.md](token-and-session-design.md) for the session tables in use,
[legacy-compatibility-and-erp-projection.md](legacy-compatibility-and-erp-projection.md) for the ERP
projection.

---

## Conventions

- **Primary keys.** `uuid7` for anything a client may see or reference across a boundary
  (`identity_user`, `identity_session`); `bigserial` for append-only internal tables (`audit_event`,
  `outbox_event`). UUIDv7 is time-sortable, so it indexes well and doubles as a creation-order hint.
- **`citext`** for `username` and `email`. Case-sensitive usernames are a support-ticket generator, and
  `LOWER()` comparisons cannot use a plain B-tree index.
- **Timestamps** are `timestamptz`, always. `USE_TZ = True`; no naive datetime is ever accepted.
- **Enums** are `CharField` with `choices` plus a `CheckConstraint`. Postgres native enums require a
  migration to add a value, which is friction with no payoff.
- **Soft delete** for anything referenced elsewhere: `identity_user.status = 'archived'`, never `DELETE`.
  Cross-boundary references are unconstrained integers
  ([ADR-0013](../01-architecture/adr/0013-no-cross-module-foreign-keys.md)), so a hard delete would create
  dangling ids.
- **No PII in any table an access token's claims are derived from.** Claims carry `sub` and `erp_uid`
  only.

---

## `identity` — who someone is

### `identity_user`

```python
class User(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid7)
    erp_user_id   = models.IntegerField(null=True, blank=True, unique=True)
    username      = CICharField(max_length=64, unique=True)
    email         = CIEmailField(max_length=254, db_index=True)
    display_name  = models.CharField(max_length=150)
    kind          = models.CharField(max_length=16, choices=UserKind.choices)
    status        = models.CharField(max_length=16, choices=UserStatus.choices,
                                    default=UserStatus.ACTIVE)
    is_superadmin = models.BooleanField(default=False)
    mfa_required  = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(kind__in=UserKind.values), name="user_kind_valid"),
            models.CheckConstraint(check=Q(status__in=UserStatus.values), name="user_status_valid"),
            models.CheckConstraint(
                check=Q(kind="service") | Q(erp_user_id__isnull=False),
                name="human_users_have_erp_id"),
        ]
        indexes = [
            models.Index(fields=["status"], name="user_status_idx"),
            models.Index(fields=["kind", "status"], name="user_kind_status_idx"),
            models.Index(fields=["erp_user_id"], name="user_erp_id_idx"),
        ]
```

`UserKind` = `student` · `faculty` · `staff` · `operator` · `service`.
`UserStatus` = `active` · `suspended` · `archived`.

**`erp_user_id` is the join to the ERP's `auth_user.id`** — a logical reference with a uniqueness
constraint and **no foreign key**, because it lives in a different database
([ADR-0002](../01-architecture/adr/0002-separate-iam-service-and-database.md)). It is nullable only so
`kind = service` principals can exist without an ERP row; the `human_users_have_erp_id` constraint enforces
that every other kind has one.

`is_superadmin` is a break-glass flag, not a role. It grants all permissions, bypasses grant checks, is
held by at most two accounts, and **every** request made under it writes an `audit_event`. A CI check
fails if more than two active users hold it.

`mfa_required` is set automatically when a user holds any role carrying an `is_dangerous` permission, and
can also be set manually. It is never unset automatically.

### `identity_credential`

```python
class Credential(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name="credential")
    algo          = models.CharField(max_length=32, default="argon2id")
    password_hash = models.CharField(max_length=255)
    must_change   = models.BooleanField(default=False)
    changed_at    = models.DateTimeField(auto_now=True)
    expires_at    = models.DateTimeField(null=True, blank=True)
```

`algo` exists so imported PBKDF2 hashes from the legacy `auth_user` can be verified as-is and
**transparently upgraded to Argon2id on the next successful login**. That is what makes the Phase 2
user import a copy rather than a password reset for 3,277 people.

`expires_at` is null by default — **no forced rotation** (NIST SP 800-63B). It exists for
deliberately time-boxed credentials such as a temporary operator account.

### `identity_password_history`

```python
class PasswordHistory(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_history")
    password_hash = models.CharField(max_length=255)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "-created_at"], name="pwhist_user_recent_idx")]
```

Last 5 retained, older rows trimmed on write. Prevents immediate reuse. Verifying a new password against
five Argon2id hashes costs ~250 ms, which is acceptable on a password-change path and is why history is 5
rather than 24.

### `identity_mfa_factor`

```python
class MfaFactor(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mfa_factors")
    kind         = models.CharField(max_length=16, choices=MfaKind.choices)   # totp | recovery
    secret_enc   = models.BinaryField()          # Fernet, key from env — never plaintext
    label        = models.CharField(max_length=64, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "kind", "label"], name="mfa_unique_per_label"),
        ]
```

`secret_enc` is Fernet-encrypted with a key from the environment, so a database dump alone does not yield
TOTP secrets. `confirmed_at` null means enrolment started but was never verified — such factors do not
count toward MFA satisfaction. Recovery codes are stored one row each, hashed, and marked used via
`last_used_at`.

### `identity_session`

```python
class Session(models.Model):
    id                  = models.UUIDField(primary_key=True, default=uuid7)
    user                = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    active_role         = models.ForeignKey("rbac.Role", null=True, blank=True,
                                            on_delete=models.SET_NULL)
    device_label        = models.CharField(max_length=120, blank=True)
    ip                  = models.GenericIPAddressField(null=True)
    user_agent          = models.CharField(max_length=400, blank=True)
    amr                 = models.JSONField(default=list)     # ["pwd"] or ["pwd","otp"]
    created_at          = models.DateTimeField(auto_now_add=True)
    last_seen_at        = models.DateTimeField(auto_now=True)
    absolute_expires_at = models.DateTimeField()
    revoked_at          = models.DateTimeField(null=True, blank=True)
    revoke_reason       = models.CharField(max_length=64, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"], name="session_user_recent_idx"),
            models.Index(fields=["absolute_expires_at"],
                         condition=Q(revoked_at__isnull=True), name="session_live_expiry_idx"),
        ]
```

The `session_live_expiry_idx` partial index is what makes the purge job cheap — it only ever scans live
sessions.

`active_role` on the **session**, not on the user, so the same person can be a student in one tab and a
coordinator in another without the two fighting. Note this differs deliberately from the legacy
`ExtraInfo.last_selected_role`, which is per-user; the projection writes the primary session's value.

`revoke_reason` values: `logout` · `admin` · `password_change` · `refresh_reuse` · `idle` · `absolute` ·
`status_change`.

### `identity_refresh_token`

```python
class RefreshToken(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid7)
    session         = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="refresh_tokens")
    token_hash      = models.CharField(max_length=64, unique=True)   # sha256 hex
    parent          = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name="children")
    issued_at       = models.DateTimeField(auto_now_add=True)
    expires_at      = models.DateTimeField()
    used_at         = models.DateTimeField(null=True, blank=True)
    reuse_detected  = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["session", "-issued_at"], name="rt_session_recent_idx"),
            models.Index(fields=["expires_at"], condition=Q(used_at__isnull=True),
                         name="rt_live_expiry_idx"),
        ]
```

**Only the SHA-256 hash is stored.** A database dump does not yield usable refresh tokens. The token
itself is 256 bits of CSPRNG output, so a hash without a salt is fine — there is no dictionary to attack.

`parent` forms the rotation chain, which is what makes reuse detection possible: presenting an
already-`used_at` token means it leaked, so the **entire family** (walk `parent` to the root, then all
descendants) is revoked. Detail in [token-and-session-design.md](token-and-session-design.md).

### `identity_login_attempt`

```python
class LoginAttempt(models.Model):
    username = models.CharField(max_length=64, db_index=True)   # NOT an FK — records failures
                                                                # for usernames that do not exist
    ip       = models.GenericIPAddressField(db_index=True)
    outcome  = models.CharField(max_length=24, choices=LoginOutcome.choices)
    user_agent = models.CharField(max_length=400, blank=True)
    at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["username", "-at"], name="attempt_username_recent_idx"),
            models.Index(fields=["ip", "-at"], name="attempt_ip_recent_idx"),
        ]
```

`username` is deliberately a plain string, not a foreign key: we must record attempts against usernames
that do not exist, which is exactly the signal for enumeration attacks.

`LoginOutcome` = `success` · `bad_password` · `unknown_user` · `locked` · `mfa_required` ·
`mfa_failed` · `suspended` · `throttled`.

Drives progressive lockout, counted per username **and** per IP. **90-day retention** — this table is
the highest-volume one in IAM and it is PII-adjacent. Purged by a beat task.

### `identity_password_reset`

```python
class PasswordReset(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_hash    = models.CharField(max_length=64)      # HMAC-SHA256, server-keyed
    attempts    = models.PositiveSmallIntegerField(default=0)
    expires_at  = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    reset_token_hash = models.CharField(max_length=64, null=True, blank=True)
    reset_token_expires_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
```

This is a faithful port of the **legacy monolith's OTP flow**, which is genuinely well built
(`applications/globals/models.py` `PasswordResetOTP`): HMAC-keyed OTP hash, 10-minute TTL, 5 attempts,
3 per hour, then a single-use SHA-256 reset token with a 15-minute TTL. Reusing a proven design rather
than inventing one.

---

## `rbac` — what someone may do

Full semantics in [rbac-model.md](rbac-model.md); the schema is here.

```python
class Permission(models.Model):
    code         = models.CharField(max_length=100, unique=True)   # module.resource.action
    module       = models.ForeignKey("registry.Module", on_delete=models.PROTECT,
                                     related_name="permissions")
    description  = models.CharField(max_length=200)
    is_dangerous = models.BooleanField(default=False)

class Role(models.Model):
    code                     = models.CharField(max_length=64, unique=True)
    name                     = models.CharField(max_length=120)
    kind                     = models.CharField(max_length=20, choices=RoleKind.choices)
    is_assignable            = models.BooleanField(default=True)
    is_builtin               = models.BooleanField(default=False)
    legacy_projectable       = models.BooleanField(default=False)
    legacy_designation_name  = models.CharField(max_length=20, null=True, blank=True, unique=True)
    created_at               = models.DateTimeField(auto_now_add=True)

class RolePermission(models.Model):
    role       = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    effect     = models.CharField(max_length=8, choices=Effect.choices, default=Effect.ALLOW)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["role", "permission"],
                                               name="roleperm_unique")]

class RoleInherits(models.Model):
    parent = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="child_links")
    child  = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="parent_links")
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["parent", "child"], name="roleinherit_unique"),
            models.CheckConstraint(check=~Q(parent=F("child")), name="roleinherit_no_self"),
        ]

class UserRole(models.Model):
    user       = models.ForeignKey("identity.User", on_delete=models.CASCADE,
                                   related_name="role_assignments")
    role       = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    scope_type = models.CharField(max_length=32, null=True, blank=True)
    scope_id   = models.CharField(max_length=64, null=True, blank=True)
    kind       = models.CharField(max_length=16, choices=AssignmentKind.choices,
                                  default=AssignmentKind.PERMANENT)
    is_primary = models.BooleanField(default=False)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to   = models.DateTimeField(null=True, blank=True)
    granted_by = models.ForeignKey("identity.User", null=True, on_delete=models.SET_NULL,
                                   related_name="grants_made")
    reason     = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role", "scope_type", "scope_id"],
                                    name="userrole_unique"),
            models.CheckConstraint(check=Q(valid_to__isnull=True) | Q(valid_to__gt=F("valid_from")),
                                   name="userrole_valid_window"),
            models.UniqueConstraint(fields=["role", "scope_type", "scope_id"],
                                    condition=Q(is_primary=True),
                                    name="userrole_one_primary_per_scope"),
        ]
        indexes = [
            models.Index(fields=["user"], condition=Q(valid_to__isnull=True),
                         name="userrole_user_open_idx"),
            models.Index(fields=["role", "scope_type", "scope_id"], name="userrole_role_scope_idx"),
            models.Index(fields=["valid_to"], condition=Q(valid_to__isnull=False),
                         name="userrole_expiring_idx"),
        ]
```

`RoleKind` = `academic` · `administrative` · `functional` · `system`.
`AssignmentKind` = `permanent` · `officiating` · `delegated`.
`Effect` = `allow` · `deny`. **Deny always wins** — see [rbac-model.md](rbac-model.md).

Three constraints carry real weight:

- **`userrole_one_primary_per_scope`** is what makes hazard **H1** tractable. The legacy
  `globals_holdsdesignation` allows only one holder per designation institute-wide, so the projector
  needs a deterministic answer to "which holder do we project?". This partial unique index guarantees
  exactly one primary per `(role, scope)`.
- **`legacy_designation_name` is `max_length=20`**, deliberately narrower than `Role.code`'s 64, because
  `ExtraInfo.last_selected_role` in the ERP is `max_length=20` (hazard **H3**). Validated at role
  creation rather than silently truncated at projection time.
- **`Role` is `PROTECT`ed** from deletion while assignments exist. Roles are retired by
  `is_assignable = False`, never deleted — a deleted role would orphan audit history.

`RoleInherits` cycles are prevented in the service layer by a DFS check on write; the
`roleinherit_no_self` constraint catches only the trivial case. A `CheckConstraint` cannot express
acyclicity.

---

## `registry` — modules and navigation

```python
class Module(models.Model):
    code               = models.CharField(max_length=48, unique=True)   # placement_cell
    label              = models.CharField(max_length=80)                # "Placement Cell"
    icon               = models.CharField(max_length=48)                # "FaBriefcase"
    base_path          = models.CharField(max_length=80)                # "/placement"
    nav_section        = models.CharField(max_length=48)                # "Placement"
    sort_order         = models.PositiveSmallIntegerField(default=100)
    status             = models.CharField(max_length=16, choices=ModuleStatus.choices,
                                          default=ModuleStatus.PLANNED)
    legacy_column_name = models.CharField(max_length=64, null=True, blank=True, unique=True)

class NavItem(models.Model):
    module              = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="nav_items")
    code                = models.CharField(max_length=80, unique=True)  # placement.postings
    label               = models.CharField(max_length=80)
    icon                = models.CharField(max_length=48)
    to                  = models.CharField(max_length=160)              # "/placement/postings"
    required_permission = models.ForeignKey("rbac.Permission", null=True, blank=True,
                                            on_delete=models.SET_NULL)
    sort_order          = models.PositiveSmallIntegerField(default=100)

class RoleModuleGrant(models.Model):
    role       = models.ForeignKey("rbac.Role", on_delete=models.CASCADE, related_name="module_grants")
    module     = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="role_grants")
    granted_by = models.ForeignKey("identity.User", null=True, on_delete=models.SET_NULL)
    granted_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["role", "module"],
                                               name="rolemodulegrant_unique")]
```

`ModuleStatus` = `planned` · `active` · `deprecated`.

**`Module.code` is the join key to the frontend.** A CI check asserts the set of `code` values equals the
`MODULE_REGISTRY` key set in `apps/shell/src/modules/registry.ts`, so a mismatch fails the build rather
than silently hiding a menu item — which is precisely the failure mode of today's
`sidebarContent.jsx`.

**`legacy_column_name`** maps a module onto its `globals_moduleaccess` boolean column
(`placement_cell` → `placement_cell`, `hr` → `hr`). Null means the module has no legacy equivalent and is
not projected. A CI check compares these values against the ERP's live column list — this is the
mechanical guard against hazard **H2**, where production has an `inventory_management` column that no
monolith migration knows about.

`NavItem.required_permission` filters individual links within a granted module, so a coordinator and an
officer can share the `placement_cell` grant and still see different sub-links.

---

## `auditing`

```python
class AuditEvent(models.Model):
    id          = models.BigAutoField(primary_key=True)
    at          = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_user  = models.ForeignKey("identity.User", null=True, on_delete=models.SET_NULL,
                                    related_name="audit_events")
    actor_ip    = models.GenericIPAddressField(null=True)
    request_id  = models.CharField(max_length=64, db_index=True)
    action      = models.CharField(max_length=80, db_index=True)   # rbac.role.assigned
    target_type = models.CharField(max_length=48)
    target_id   = models.CharField(max_length=64)
    before      = models.JSONField(null=True, blank=True)
    after       = models.JSONField(null=True, blank=True)
    outcome     = models.CharField(max_length=16)                  # success | denied | error

    class Meta:
        indexes = [
            models.Index(fields=["target_type", "target_id", "-at"], name="audit_target_idx"),
            models.Index(fields=["actor_user", "-at"], name="audit_actor_idx"),
        ]
```

**Append-only.** `UPDATE` and `DELETE` are revoked for `iam_app`
([ADR-0012](../01-architecture/adr/0012-postgres-roles-and-least-privilege.md)) — the same technique used
for `academics_resultsnapshot`. Written for: every role and module grant change, every credential change,
every `is_dangerous` permission use, every `is_superadmin` request, and every login-lockout event.

`before`/`after` are redacted through the same structlog PII processor, so no secret or PII reaches the
audit table. `request_id` ties an audit row to its HTTP request and to its log lines.

**3-year retention** ([data-retention-and-privacy.md](../06-crosscutting/data-retention-and-privacy.md)),
then archived to cold storage rather than deleted.

### `outbox_event` / `inbox_event`

Standard shape from
[ADR-0006](../01-architecture/adr/0006-outbox-plus-celery-for-integration-events.md), one pair per
service:

```python
class OutboxEvent(models.Model):
    id          = models.BigAutoField(primary_key=True)
    topic       = models.CharField(max_length=80)
    payload     = models.JSONField()
    dedupe_key  = models.CharField(max_length=160, unique=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts    = models.PositiveSmallIntegerField(default=0)
    last_error  = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["id"], condition=Q(consumed_at__isnull=True),
                                name="outbox_pending_idx")]
```

The partial index is what keeps `publish_outbox` cheap forever — it scans only unconsumed rows, so the
table's total size is irrelevant to dispatch cost.

---

## Entity relationships

```
identity_user 1──1 identity_credential
              1──* identity_password_history
              1──* identity_mfa_factor
              1──* identity_session 1──* identity_refresh_token (parent → self)
              1──* rbac_user_role *──1 rbac_role
                                        1──* rbac_role_permission *──1 rbac_permission *──1 registry_module
                                        *──* rbac_role (via rbac_role_inherits)
                                        1──* registry_role_module_grant *──1 registry_module 1──* registry_nav_item

identity_user.erp_user_id ┄┄logical, no FK, other database┄┄> ERP auth_user.id
```

---

## Migration and seed order

`registry_module` → `rbac_permission` → `rbac_role` → `rbac_role_permission` →
`registry_role_module_grant` → `identity_user` → `rbac_user_role`.

Permissions reference modules (`PROTECT`), so modules seed first. Built-in roles (`is_builtin = True`) are
created by a data migration and cannot be deleted or renamed through the API — only their permission sets
may change.

The Phase 2 import maps the legacy tables:

| Legacy | IAM |
|---|---|
| `auth_user` | `identity_user` (+ `erp_user_id`), `identity_credential` (hash copied verbatim, `algo = pbkdf2_sha256`) |
| `globals_extrainfo.user_type` | `identity_user.kind` |
| `globals_designation` | `rbac_role` (`legacy_projectable = True`, `legacy_designation_name = name`) |
| `globals_holdsdesignation` | `rbac_user_role` (`working` → holder; `user ≠ working` → `kind = officiating`) |
| `globals_moduleaccess` | `registry_module` + `registry_role_module_grant`, one grant per true column |

The gate before anything depends on it: a nightly job recomputes IAM's `accessible_modules` for every user
and diffs it against the legacy `/api/auth/me` output. **Seven consecutive empty diffs** is the Phase 2
exit criterion — see [auth-migration-runbook.md](auth-migration-runbook.md).

---

## Sizing

| Table | Expected rows | Growth |
|---|---|---|
| `identity_user` | ~3,300 | ~800/year (one intake) |
| `identity_session` | ~5k live | purged at expiry + 7 days |
| `identity_refresh_token` | ~30k | purged with sessions |
| `identity_login_attempt` | ~200k/year | **90-day retention** — the volume table |
| `rbac_user_role` | ~6k | slow |
| `rbac_permission` | ~400 at 20 modules | slow |
| `registry_module` | ~25 | very slow |
| `audit_event` | ~500k/year | 3-year retention, then archived |

Nothing here is large. The indexes exist for latency on the login and `/me` paths, not for volume — which
is worth stating, because the legacy system has **one** index across 424 models and its login path does a
sequential scan per designation.
