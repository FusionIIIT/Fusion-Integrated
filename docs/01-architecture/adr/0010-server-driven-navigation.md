# ADR-0010 — The server sends navigation in render shape; the client does zero filtering

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0009](0009-frontend-monorepo-pnpm-turborepo.md), [0003](0003-rs256-jwt-access-plus-opaque-refresh.md)
- **Detail:** [navigation-contract.md](../../05-frontend/navigation-contract.md)

## Context

The requirement: after login, any role sees in their sidebar whichever modules they have access to.

How it works today, in two different ways, neither of them good:

**`Fusion-client`** keeps a static `Modules` array in `src/components/sidebarContent.jsx:44-173` where each
entry has an `id`, then filters it client-side:

```js
const filterModules = Modules.filter(
  (module) => accessibleModules[module.id] || module.id === "home",
);
```

Those `id` strings **must exactly match column names** in the legacy `globals_moduleaccess` table
(`course_registration`, `program_and_curriculum`, `examinations`, `database`, `phc`, `fts`, …). A rename on
either side silently breaks a menu entry with no error. Several entries also hardcode role-dependent URLs
inline (`role === "acadadmin" ? "/programme_curriculum/acad_view_all_programme" : …`). Most entries still
point at `url: "/"`.

**`Fusion_System_Administrator/client`** keeps a static `NAV_GROUPS` in
`components/AppLayout/navConfig.jsx` with **no filtering at all** — every authenticated operator sees every
link, because authorization is entirely server-side. Correct for a single-purpose console, wrong for a
shell serving students, faculty, staff and operators.

Adding a module today therefore means editing a hardcoded array in the client, a boolean column in the
database, and a shadow model — in three repositories.

## Decision

**`GET /app/api/iam/v1/me` returns `navigation` already filtered and already in render shape.** The client
does no filtering whatsoever.

```json
"navigation": [
  {"section": "Overview", "items": [
    {"code": "dashboard", "label": "Dashboard", "icon": "FaThLarge", "to": "/dashboard"}]},
  {"section": "Placement", "items": [
    {"code": "placement_cell", "label": "Placement Cell", "icon": "FaBriefcase", "links": [
      {"code": "placement.postings", "label": "Job Postings",
       "icon": "FaClipboardList", "to": "/placement/postings"}]}]}
]
```

The shape is deliberately **identical to the existing `NAV_GROUPS`** structure, so
`AppShellLayout` renders it with no transformation:

```tsx
<AppShellLayout navGroups={session.navigation} activePath={pathname} onNavigate={navigate} />
```

Built by `iam/registry/services/navigation.py::build_navigation(user, active_role)` from
`registry_module` and `registry_nav_item` filtered by module grants for the active role and by each
item's `required_permission`. Cached at `iam:nav:<user_id>:<active_role>:<permission_version>` — the
version in the key makes invalidation free.

**Icons cross the wire as strings** (`"FaBriefcase"`) resolved through `ICON_REGISTRY` in
`packages/ui/src/icons/index.ts`, with **named imports only** — `import * as Fa` would ship about a
megabyte.

**Routing follows grants.** `apps/shell/src/router.tsx` builds module routes only from `session.modules`.
A module the server did not grant produces **no route at all**, so deep-linking `/placement/postings`
without the grant lands on `<Forbidden/>` rather than a blank screen or a broken page.

**This is UX, not security.** Every module and permission is independently enforced server-side on every
request (`HasModuleGrant` + `HasPermission`). Navigation is a convenience; hiding a link is never the
control.

## Consequences

**Good**

- Adding a module is a **data change**: insert `registry_module` + `registry_nav_item` rows, add a
  frontend manifest entry. No client array to edit, no boolean column to migrate, no shadow model to
  update.
- The `id`-must-match-a-column-name coupling disappears entirely. A CI check asserts the
  `registry_module.code` set equals the frontend `MODULE_REGISTRY` key set, so a mismatch fails the build
  instead of silently hiding a menu item.
- Role-dependent landing paths move server-side, so the inline ternaries in `sidebarContent.jsx` go away.
- The sidebar cannot show something the user cannot use — the same query drives the menu and the grant.
- Live sidebar search (over the flattened link list) keeps working unchanged, since the shape is the same.

**Bad, and accepted**

- Navigation is now on the login critical path. Mitigated by Redis caching keyed on `pv`, and by
  `/me` being one query on a warm cache.
- A nav change requires a `/me` refetch, not just a client deploy. Accepted — that is the point — and the
  shell refetches on role switch and on window focus.
- The server now knows about frontend paths (`to: "/placement/postings"`). This is a real coupling. Accepted
  because the alternative — the client mapping module codes to paths — reintroduces exactly the hardcoded
  array we are removing. The CI code-set check keeps the two honest.
- Icon names are strings, so a typo yields a fallback icon rather than a compile error. Mitigated by
  `resolveIcon` falling back to `FaCircle` and by a CI check that every `registry_nav_item.icon` exists in
  `ICON_REGISTRY`.
- The `/me` payload grows with granted modules. Measured at ~40 modules it is a few kilobytes; it is
  fetched once per session and cached.

## Alternatives considered

**Keep client-side filtering against a `{module: bool}` map.** Rejected: it is the current design. The
`id`-to-column coupling is fragile, the client must know every possible module whether or not the user has
it, and role-dependent URLs end up as inline ternaries.

**Send raw grants and let the client build navigation.** Rejected: the client would hold the labels, icons,
ordering, sections and paths — i.e. the hardcoded array again, just fed a filter list. All the coupling,
none of the benefit.

**Static navigation, no filtering, rely on 403s.** Rejected: it is the sysadmin console's model, which
works only because every operator is privileged. A student seeing an HR link that 403s is a bug report.

**Derive navigation from the frontend module manifests at build time.** Rejected: build-time cannot know
runtime grants, so filtering returns to the client.

## Verification

- A Playwright test logs in as a student and asserts the sidebar contains exactly the granted sections; then
  as a placement coordinator and asserts it changes.
- Deep-linking an ungranted module path renders `<Forbidden/>` with the URL preserved.
- A CI check asserts `registry_module.code` set == `MODULE_REGISTRY` key set.
- A CI check asserts every `registry_nav_item.icon` resolves in `ICON_REGISTRY`.
- Visual baselines confirm the rendered sidebar is pixel-identical to the sysadmin original for an
  equivalent nav tree.
