---
owner: iam-lead
status: authoritative
last-reviewed: 2026-08-01
---

# RBAC Model

How authorization is decided. Schema is in [iam-domain-model.md](iam-domain-model.md); this document is
the semantics.

---

## The shape

```
User ──holds──> Role ──grants──> Permission
                 │
                 ├──inherits──> Role  (transitive, acyclic)
                 └──granted───> Module   (what appears in the sidebar and is routable)
```

**Users never hold permissions directly.** There is no `user_permission` table, deliberately. Direct
grants are how an access-control system becomes unauditable: within a year nobody can answer "who can
revoke an offer?" without a full-table scan and a guess. If someone needs a capability, either their role
gets it or a new role exists.

**Two independent checks on every request:**

| Check | Question | Source | Cost |
|---|---|---|---|
| `HasModuleGrant` | may this role enter this module at all? | token `mod` claim | zero — in the JWT |
| `HasPermission` | may this role perform this action? | Redis, key includes `pv` | one Redis `GET` on a warm cache |

Both must pass. Module grant is coarse and drives navigation; permission is fine and drives actions. A
user can hold the `placement_cell` grant and still be unable to issue an offer.

---

## Permission codes

```
<module>.<resource>.<action>
```

```
placement.job_posting.view          placement.job_posting.create
placement.job_posting.publish       placement.application.review
placement.offer.issue               placement.offer.revoke        ← is_dangerous
placement.export.pii                                              ← is_dangerous
hr.employee.view                    leave.request.approve
iam.role.assign                                                    ← is_dangerous
sysops.backup.restore                                              ← is_dangerous
```

Rules, enforced by a CI regex over the seed data:

- Lowercase `snake_case`, exactly three segments.
- The first segment **must** equal an existing `registry_module.code`.
- The second is a **singular** resource noun.
- The third comes from a closed vocabulary: `view` · `create` · `update` · `delete` · `approve` ·
  `publish` · `review` · `assign` · `revoke` · `export` · `import` · `restore` · `manage`.
- `manage` is a deliberate escape hatch, allowed only where finer actions genuinely do not exist. A
  reviewer should push back on it.

`view` is read for the resource **within the user's visible scope** — it never means "read everyone's".
Row visibility is enforced by queryset filtering in the selector, not by a separate permission
([api-conventions.md](../01-architecture/api-conventions.md)).

### `is_dangerous`

Marks a permission whose use is irreversible, financially or reputationally significant, or
privilege-escalating. Consequences are automatic:

1. Any role holding one sets `identity_user.mfa_required = True` on its holders.
2. The endpoint requires **step-up re-authentication** — a fresh password or TOTP within the last 5
   minutes, tracked on the session.
3. Every use writes an `audit_event`, success or failure.
4. It appears in the weekly privileged-access report.

---

## Resolution

```python
def effective_permissions(user, active_role) -> frozenset[str]:
    """Deny always wins. Fail closed."""
    roles = _transitive_closure(active_role)          # active_role + all inherited ancestors
    allow, deny = set(), set()
    for rp in RolePermission.objects.filter(role__in=roles).select_related("permission"):
        (deny if rp.effect == Effect.DENY else allow).add(rp.permission.code)
    return frozenset(allow - deny)
```

Four properties, in order of importance:

**1. Deny wins, unconditionally.** Not "the most specific wins", not "the nearest ancestor wins". If any
role in the closure denies a permission, it is denied — even if a more derived role allows it. Precedence
rules that depend on inheritance depth are impossible to reason about at 2 a.m., and a security decision
must be reasoned about at 2 a.m.

**2. Only the active role counts.** A user holding `student` and `placement_coordinator` has, at any
moment, the permissions of exactly one of them. Switching is an explicit server operation. This prevents
the accidental privilege union that the legacy system produces, where a `HoldsDesignation` query returns
every designation a user has ever held.

**3. Fail closed.** No permission, no role, no cached entry that cannot be rebuilt, an unknown permission
code — all deny. There is no default-allow path anywhere.

**4. Scope narrows rows, never permissions.** A `placement_coordinator` scoped to `department:CSE` has the
*same* permission set as an unscoped one; the difference is which rows the selector returns. Keeping these
orthogonal is what stops the permission set from combinatorially exploding.

### Inheritance

Acyclic, checked by DFS in the service layer on every write to `RoleInherits` — a
`CheckConstraint` cannot express acyclicity, so the constraint only catches self-reference.

```
placement_officer  ──inherits──> placement_coordinator ──inherits──> placement_viewer
   +offer.issue                     +application.review                job_posting.view
   +offer.revoke                    +round.manage                      application.view
   +export.pii
```

Depth is capped at 4 by a validator. Deeper hierarchies are a modelling smell and become impossible to
audit.

### Scopes

`(scope_type, scope_id)` on the assignment. Currently defined types: `department` (id = discipline
acronym, e.g. `CSE`), `batch` (id = `Batch` primary key), `hall` (reserved for hostel). `NULL` means
institute-wide.

The selector applies it — one place per module:

```python
def visible_applications(principal):
    qs = Application.objects.all()
    scope = principal.active_assignment.scope
    if scope and scope.type == "department":
        user_ids = directory.user_ids_in_department(scope.id)   # contracts call, batched
        qs = qs.filter(user_id__in=user_ids)
    return qs
```

Because every read goes through `selectors/`, a scoping predicate has exactly one place to live per
module rather than being sprinkled across views — which is also what makes it testable.

---

## Caching, and why invalidation is not a problem

```
iam:perms:<role_code>:<permission_version>   → frozenset of permission codes
iam:nav:<user_id>:<role_code>:<permission_version> → the navigation payload
```

**The version is in the key, and entries are never deleted.** Anything that changes effective permissions
bumps a global `permission_version` counter; a new version simply misses the old key, and the old entries
expire on their own TTL.

This removes the entire "forgot to invalidate" bug class — which in an authorization system is not a
performance bug but a security bug, since a stale cache can grant a revoked permission.

`pv` also travels in the access token, so a service can tell that a token was minted under an older
permission generation. That is diagnostic rather than enforcing: the authoritative bound on staleness is
the 10-minute access-token TTL
([ADR-0003](../01-architecture/adr/0003-rs256-jwt-access-plus-opaque-refresh.md)).

Per-request, the principal and its permission set are memoized in a `contextvar`, so a view checking three
permissions performs one lookup.

---

## Enforcement in code

```python
class OfferIssueView(APIView):
    permission_classes = [HasModuleGrant("placement_cell"),
                          HasPermission("placement.offer.issue")]

class OfferRevokeView(APIView):
    permission_classes = [HasModuleGrant("placement_cell"),
                          HasPermission("placement.offer.revoke"),
                          RequiresStepUp(max_age_seconds=300)]      # is_dangerous
```

The design intentionally mirrors `applications/globals/access.py` in the legacy monolith, which is the one
piece of legacy authorization worth keeping: fail-closed permission classes plus a factory. The difference
is that it checks **permissions** rather than designation-name strings, so renaming a role does not silently
open an endpoint.

**Object-level access is queryset filtering, never post-hoc checking:**

```python
# right — a foreign id is a 404, with no special case
def get_queryset(self):
    return selectors.visible_applications(self.request.principal)

# wrong — leaks existence, and one forgotten branch is a data breach
obj = Application.objects.get(pk=pk)
if obj.user_id != request.principal.erp_user_id and not can_review:
    raise PermissionDenied
```

Returning 403 rather than 404 for an out-of-scope object turns any id column into an enumeration oracle
([api-conventions.md](../01-architecture/api-conventions.md#status-codes)).

**Client-side checks are UX only.** `usePermission().can("placement.offer.revoke")` hides a button. Every
one has a server counterpart; a review that finds a client-only check rejects the PR.

---

## Built-in roles

Seeded by a data migration, `is_builtin = True`, undeletable and unrenameable through the API. Their
permission sets may change.

| Code | Kind | Notes |
|---|---|---|
| `student` | academic | The default. Everyone with `kind = student` holds it. |
| `faculty` | academic | |
| `staff` | administrative | |
| `acadadmin` | administrative | Maps to the legacy `acadadmin` designation |
| `dean_academic` | administrative | Maps to legacy `Dean Academic` |
| `placement_officer` | functional | Inherits `placement_coordinator` |
| `placement_coordinator` | functional | Usually scoped by department; typically multi-holder |
| `hr_officer` | functional | |
| `iam_admin` | system | Manages roles and grants. Holds `is_dangerous` permissions. |
| `sysops` | system | Backups, archives, batch onboarding |

`legacy_projectable` and `legacy_designation_name` are set on exactly those roles that correspond to an
existing `globals_designation` row. Everything else is `/app/`-only.

---

## Where this deliberately differs from the legacy model

| Legacy | Here | Why |
|---|---|---|
| Authorization by designation **name string** matching | permission codes | Renaming a designation currently changes who can do what, silently |
| Three disagreeing enforcement paths (`Q(working)\|Q(user)`, `user=` only, `working=` only) | one resolver | The current inconsistency is a real, exploitable difference in outcome between endpoints |
| Effective union of every held designation | exactly one active role | Prevents accidental privilege union |
| `ModuleAccess`: one boolean column per module, keyed by free text | `registry_module` + grants | Adding a module is data, not a schema migration; no name-to-column coupling |
| Module access gates **menus only** | module grant enforced per request | Today, knowing a URL is often enough |
| No scopes | `(scope_type, scope_id)` | "Coordinator for CSE" is currently unrepresentable |
| One holder per designation (`unique_together`) | multi-holder with one `is_primary` | Two coordinators is a normal requirement — hazard **H1** |
| No expiry on an assignment | `valid_from` / `valid_to` | Officiating roles currently have to be removed by hand |
| No audit of role changes | `audit_event` on every change | Currently unanswerable: who granted this, when, why |

---

## Verification

- **Deny-wins:** a role inheriting an allow while denying directly resolves to denied. Also the reverse
  order. Property-tested with hypothesis over generated role graphs.
- **Cycle rejection:** `A → B → C → A` is rejected on write.
- **Depth cap:** a 5-deep chain is rejected.
- **Fail-closed:** an unknown permission code, a user with no roles, and a cache miss with the database
  unavailable all deny.
- **Scope isolation:** a `department:CSE`-scoped coordinator cannot see an ECE student's application, and
  requesting one by id returns **404**, not 403.
- **Active-role isolation:** a user holding `student` and `placement_officer`, acting as `student`, is
  denied `placement.offer.issue`.
- **Step-up:** an `is_dangerous` endpoint without recent re-auth returns 403 with
  `code = "step_up_required"`.
- **Superadmin audit:** every request under `is_superadmin` writes an `audit_event`; a CI check fails if
  more than two active users hold the flag.
- **Catalog integrity:** every permission code matches the naming regex, its first segment resolves to a
  module, and `manage.py export_permission_catalog` produces an empty diff against
  [permission-catalog.md](permission-catalog.md).
