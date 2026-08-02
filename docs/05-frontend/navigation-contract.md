---
owner: frontend-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Navigation Contract

`GET /app/api/iam/v1/me` returns navigation **already filtered and already in render shape**. The client does
**zero** filtering.

Decision and rationale: [ADR-0010](../01-architecture/adr/0010-server-driven-navigation.md).

---

## The payload

```json
{
  "user": {
    "id": "018f4c2a-7b31-7c4e-9a02-6f1d8e3b5c91",
    "erp_user_id": 1234,
    "username": "22bcs001",
    "display_name": "Asha Verma",
    "kind": "student",
    "email": "22bcs001@iiitdmj.ac.in"
  },
  "roles": [
    {"code": "student", "name": "Student", "kind": "academic", "scope": null},
    {"code": "placement_coordinator", "name": "Placement Coordinator",
     "kind": "functional", "scope": {"type": "department", "id": "CSE"}}
  ],
  "active_role": "placement_coordinator",
  "permissions": [
    "placement_cell.job_posting.view",
    "placement_cell.application.review",
    "placement_cell.round.manage"
  ],
  "permission_version": 1187,
  "modules": [
    {"code": "dashboard",      "base_path": "/dashboard",  "status": "active"},
    {"code": "placement_cell", "base_path": "/placement",  "status": "active"},
    {"code": "profile",        "base_path": "/profile",    "status": "active"}
  ],
  "navigation": [
    {"section": "Overview", "items": [
      {"code": "dashboard", "label": "Dashboard", "icon": "FaThLarge", "to": "/dashboard"}
    ]},
    {"section": "Placement", "items": [
      {"code": "placement_cell", "label": "Placement Cell", "icon": "FaBriefcase", "links": [
        {"code": "placement.postings",     "label": "Job Postings",
         "icon": "FaClipboardList",  "to": "/placement/postings"},
        {"code": "placement.applications", "label": "Applications",
         "icon": "FaUsers",          "to": "/placement/applications"},
        {"code": "placement.rounds",       "label": "Rounds",
         "icon": "FaCalendarAlt",    "to": "/placement/rounds"}
      ]}
    ]},
    {"section": "Personal", "items": [
      {"code": "profile", "label": "My Profile", "icon": "FaUser", "to": "/profile"}
    ]}
  ],
  "external_links": [
    {"code": "legacy_academics", "label": "Academics", "icon": "FaExternalLinkAlt",
     "to": "https://fusion.iiitdmj.ac.in/dashboard"}
  ],
  "idle_timeout_seconds": 1800,
  "server_time": "2026-08-01T10:00:00Z"
}
```

## Field reference

| Field | Used for |
|---|---|
| `user` | header display, `erp_user_id` for "is this mine?" comparisons |
| `roles` | the role switcher. `scope` renders as a subtitle ("CSE"). |
| `active_role` | which role the switcher shows as current |
| `permissions` | `usePermission().can(...)` — **hiding buttons only** |
| `permission_version` | query-key segment, so a permission change invalidates cached data |
| `modules` | **route registration.** Only these produce routes. |
| `navigation` | rendered verbatim by `AppShellLayout` |
| `external_links` | sidebar links out of the SPA (the legacy academic app) |
| `idle_timeout_seconds` | the client idle timer — server-configurable, no frontend deploy |
| `server_time` | clock-skew correction for countdowns (offer deadlines) |

`modules` and `navigation` are **separate on purpose**. `modules` is the routing and authorization fact;
`navigation` is presentation. A module can be granted with no nav entry (an embedded sub-feature), and a nav
entry always belongs to a granted module.

---

## Shape rules

`navigation` is `NavGroup[]`, deliberately **identical** to the existing `NAV_GROUPS` structure in
`Fusion_System_Administrator/client/src/components/AppLayout/navConfig.jsx`, so `AppShellLayout` renders it
with no transformation:

```ts
interface NavGroup     { section: string; items: NavGroupItem[] }
interface NavGroupItem { code: string; label: string; icon: IconKey;
                         to?: string; links?: NavLinkItem[] }   // `to` XOR `links`
interface NavLinkItem  { code: string; label: string; icon: IconKey; to: string }
```

- **One nesting level only.** `links` may not contain further `links` — the sidebar accordion is
  single-level and deeper nesting is unusable at 280px.
- An item has **either** `to` or `links`, never both. Enforced by the serializer.
- `icon` is a string resolved through `ICON_REGISTRY`. Named imports only
  ([design-system.md](design-system.md#icons)).
- `to` is an app-relative path. `external_links` carry absolute URLs and are rendered separately, with an
  external-link icon.
- Order is authoritative: sections by `registry_module.sort_order`, items by `registry_nav_item.sort_order`.
  The client never re-sorts.

---

## How the server builds it

```python
# services/iam/registry/services/navigation.py
def build_navigation(user, active_role) -> list[dict]:
    """Modules granted to the active role, grouped by section, items filtered by permission."""
    perms = effective_permissions(user, active_role)
    modules = (Module.objects
               .filter(status=ModuleStatus.ACTIVE,
                       role_grants__role=active_role)          # NAV_SCOPE = active_role
               .prefetch_related("nav_items__required_permission")
               .order_by("nav_section", "sort_order"))

    groups: dict[str, list] = defaultdict(list)
    for m in modules:
        items = [n for n in sorted(m.nav_items.all(), key=lambda n: n.sort_order)
                 if n.required_permission_id is None or n.required_permission.code in perms]
        if not items:
            continue                                   # a module with no visible link is omitted
        entry = {"code": m.code, "label": m.label, "icon": m.icon}
        if len(items) == 1 and items[0].to == m.base_path:
            entry["to"] = items[0].to                  # single item → a flat link, no accordion
        else:
            entry["links"] = [{"code": n.code, "label": n.label, "icon": n.icon, "to": n.to}
                              for n in items]
        groups[m.nav_section].append(entry)
    return [{"section": s, "items": v} for s, v in groups.items()]
```

Two behaviours worth naming:

- **A module whose every nav item is permission-filtered away is omitted entirely.** Showing a section that
  expands to nothing is worse than showing nothing.
- **A module with a single item pointing at its own `base_path` collapses to a flat link.** "Dashboard" should
  not be an accordion containing one child.

`NAV_SCOPE` is a config flag: `active_role` (default) shows only the active role's modules; `union` shows all
held roles' modules. Default is `active_role` because the union reintroduces the legacy problem of a user
seeing an accidental privilege blend.

### Caching

```
iam:nav:<user_id>:<active_role>:<permission_version>
```

**Version in the key, entries never deleted.** A permission change bumps `permission_version`, so the next
request misses the old key and the stale entry expires on its own TTL. There is no invalidation call to
forget — which in an authorization-adjacent path matters, because a stale nav entry means a link to a page
the user can no longer open.

---

## How the client consumes it

```tsx
// The entire sidebar integration.
<AppShellLayout
  navGroups={session.navigation}
  externalLinks={session.external_links}
  activePath={pathname}
  onNavigate={navigate}
  brandTitle={<>PDPM IIITDM <span style={{color: BRAND.primary}}>JABALPUR</span></>}
  brandSubtitle="FUSION · NON-ACADEMIC PLATFORM"
  logoSrc={logo}
  user={{ name: session.user.display_name, roleLabel: activeRoleLabel }}
  headerRightSlot={<><RoleSwitcher /><TodayText /><LogoutButton /></>}
  onLogout={logout}
>
  <Outlet />
</AppShellLayout>
```

No `filter`. No role conditionals. No module-id-to-column-name mapping.

Compare what this replaces — `Fusion-client/src/components/sidebarContent.jsx:195-200`:

```js
// GONE. `module.id` had to exactly match a globals_moduleaccess COLUMN NAME.
const filterModules = Modules.filter(
  (module) => accessibleModules[module.id] || module.id === "home",
);
```

…along with the static 20-entry `Modules` array, its inline role ternaries for URLs
(`role === "acadadmin" ? "/programme_curriculum/acad_view_all_programme" : …`), and the entries still pointing
at `url: "/"`.

---

## Role switching

```
PATCH /app/api/iam/v1/me/active-role   {"role": "student"}
  → server re-validates that the user actually holds it (never trust the client)
  → persists identity_session.active_role
  → mints a NEW access cookie with updated rol / mod / pv
  → returns the FULL /me payload
```

```tsx
async function switchRole(code: string) {
  const next = await patchActiveRole(code);
  queryClient.clear();                 // ← essential
  queryClient.setQueryData(["session"], next);
  navigate("/dashboard");
}
```

`queryClient.clear()` matters: cached `placement.*` list data fetched as a coordinator must not survive into
the student view. Clearing everything is blunt and correct — a role switch is rare and a stale privileged list
leaking into a lower-privileged view is not acceptable.

Permissions are always re-derived server-side. A client-side switch grants nothing.

---

## Adding a nav entry

A **data change**, not a code change:

1. Insert a `registry_nav_item` row (module, code, label, icon, `to`, `required_permission`, `sort_order`).
2. Ensure the frontend module's `routes.tsx` has a matching route.

No client array to edit, no boolean column to migrate, no shadow model to update. That is the whole point of
[ADR-0010](../01-architecture/adr/0010-server-driven-navigation.md).

CI parity checks make a mismatch a build failure rather than a silently missing menu item:

| Check | Fails when |
|---|---|
| `module_registry_parity` | `registry_module.code` set ≠ `MODULE_REGISTRY` keys |
| `nav_route_parity` | a `registry_nav_item.to` has no matching route in any module's `routes.tsx` |
| `nav_icon_parity` | a `registry_nav_item.icon` does not resolve in `ICON_REGISTRY` |
| `nav_permission_parity` | a `required_permission` code does not exist |

---

## Verification

- A student sees exactly the expected sections; a placement coordinator sees a different set. Playwright, two
  logins.
- Switching role changes the sidebar without a page reload, and clears cached data.
- Deep-linking an **ungranted** module path renders `<Forbidden/>` (or `<NotFound/>`) with the URL preserved —
  never a blank screen.
- A module whose every nav item is permission-filtered away does not appear at all.
- A module with one item at its `base_path` renders as a flat link, not a one-child accordion.
- Sidebar search filters the flattened list and shows the parent as `description`.
- The accordion keeps at most one group open, seeded from the current pathname.
- `external_links` render with an external-link icon and open the legacy app.
- All four parity checks fail the build when broken — each has a deliberately-broken fixture test.
- The rendered sidebar is **pixel-identical** to the sysadmin original for an equivalent nav tree (visual
  baseline).
