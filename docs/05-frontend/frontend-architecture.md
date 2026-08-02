---
owner: frontend-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Frontend Architecture

One SPA, one login, one sidebar. Monorepo rationale:
[ADR-0009](../01-architecture/adr/0009-frontend-monorepo-pnpm-turborepo.md).

---

## Tree

```
fusion-frontend/
├── package.json  pnpm-workspace.yaml  turbo.json  .npmrc
├── tsconfig.base.json  eslint.config.js  .prettierrc
├── vitest.workspace.ts  playwright.config.ts  Makefile
├── packages/
│   ├── config/                    eslint-config · tsconfig · vitest-preset
│   ├── ui/                        @fusion/ui — see design-system.md
│   │   └── src/{theme/, layout/, components/, charts/, feedback/, hooks/, icons/}
│   ├── api-client/                @fusion/api-client
│   │   ├── openapi/{iam.v1.yaml, platform.v1.yaml, sysops.v1.yaml}   ← synced by CI
│   │   ├── orval.config.ts
│   │   └── src/{http.ts, errors.ts, csrf.ts, index.ts, generated/**}
│   ├── auth/                      @fusion/auth
│   │   └── src/{AuthProvider.tsx, useAuth.ts, usePermission.ts, useModule.ts,
│   │            RequireAuth.tsx, RequirePermission.tsx, RequireModule.tsx,
│   │            RoleSwitcher.tsx, refresh.ts, idleTimeout.ts, crossTabSync.ts, types.ts}
│   └── testing/                   renderWithProviders · MSW handlers · factories
├── apps/shell/
│   ├── index.html  vite.config.ts  tsconfig.json
│   ├── src/
│   │   ├── main.tsx  App.tsx  router.tsx  env.ts
│   │   ├── layout/{ShellLayout.tsx, navigation.ts}
│   │   ├── modules/
│   │   │   ├── registry.ts
│   │   │   ├── dashboard/{manifest.ts, routes.tsx, pages/}
│   │   │   ├── placement/{manifest.ts, routes.tsx, pages/, components/, hooks/, api/, utils/}
│   │   │   ├── hr/  leave/  profile/
│   │   │   └── sysops/{manifest.ts, routes.tsx, pages/}       ← Phase 7
│   │   ├── pages/{Login/, NotFound.tsx, Forbidden.tsx, ServerError.tsx}
│   │   ├── providers/{QueryProvider.tsx, ThemeProvider.tsx}
│   │   └── boundaries/{RouteErrorBoundary.tsx, ModuleErrorBoundary.tsx}
│   └── e2e/{auth.spec.ts, navigation.spec.ts, placement.spec.ts, visual.spec.ts}
└── tools/sync-openapi.mjs
```

**Four packages, one app. Resist a fifth.** The team is new to monorepos, and the main risk here is
onboarding drag ([ADR-0009](../01-architecture/adr/0009-frontend-monorepo-pnpm-turborepo.md)).

---

## Stack

| Concern | Choice | Note |
|---|---|---|
| Language | **TypeScript 5, strict** | `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitOverride`, `verbatimModuleSyntax` |
| Framework | React 18.3 | matching both existing clients |
| Build | Vite 5 | |
| UI | **Mantine 7.13.x, pinned** | pinned so the extracted CSS behaves identically to `/sysadmin/` |
| Server state | **TanStack Query v5** | |
| Global state | **none** | Redux is dropped — see below |
| Router | react-router 6.4+, `lazy` | splits loaders too |
| Forms | `@mantine/form` + zod | a dependency in both existing clients, unused by their pages |
| HTTP | axios via **one** shared instance | with interceptors, unlike `Fusion-client` |
| Icons | `react-icons/fa`, named imports | |
| Charts | recharts + `@mantine/charts` | |
| Tests | vitest + RTL + MSW + Playwright | neither existing client has any tests |
| Monorepo | pnpm workspaces + Turborepo | |

### Redux is dropped

`Fusion-client` keeps `user`, `role` and `accessibleModules` in Redux. All three are **server** state — they
come from `GET /me` and are invalidated by server events. They belong in a query, not a store.

What remains genuinely client-side (sidebar open, active tab) is `useState` or a URL parameter. There is no
global store, and adding one needs a justification in review.

### Internal packages ship source

```json
{ "name": "@fusion/ui", "exports": { ".": "./src/index.ts" } }
```

Vite transpiles them, so `packages/*` has **no build step** and HMR crosses package boundaries. `turbo
typecheck` runs `tsc --noEmit` per package in parallel.

---

## Providers

```tsx
// apps/shell/src/App.tsx
export default function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="light" getStyleNonce={getNonce}>
      <Notifications />
      <QueryProvider>
        <BrowserRouter basename={BASE_PATH}>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </BrowserRouter>
      </QueryProvider>
    </MantineProvider>
  );
}
```

`AuthProvider` is **inside** the router, because it redirects on 401 and needs `useNavigate`. `getStyleNonce`
is what lets the strict CSP avoid `style-src 'unsafe-inline'`.

`basename` comes from `import.meta.env.BASE_URL`, so the app deploys under `/app/` without hardcoding it —
the fix for the sysadmin client's base-path-unaware `window.location.assign("/login")`.

---

## Routing

```tsx
// apps/shell/src/router.tsx
function AppRoutes() {
  const { session, status } = useAuth();
  if (status === "loading") return <FullPageLoader />;

  const moduleRoutes = (session?.modules ?? [])
    .map(m => MODULE_REGISTRY[m.code])
    .filter(Boolean)
    .map(m => ({
      path: `${m.basePath}/*`,
      lazy: async () => {
        const { routes } = await m.load();
        return {
          element: <ModuleErrorBoundary code={m.code}><Outlet /></ModuleErrorBoundary>,
          children: routes,
        };
      },
    }));

  return useRoutes([
    { path: "/login", element: <LoginPage /> },
    { path: "/", element: <RequireAuth><ShellLayout /></RequireAuth>,
      errorElement: <RouteErrorBoundary />,
      children: [
        { index: true, element: <Navigate to="/dashboard" replace /> },
        ...moduleRoutes,
        { path: "forbidden", element: <Forbidden /> },
        { path: "*", element: <NotFound /> },
      ] },
  ]);
}
```

**A module the server did not grant produces no route at all.** Deep-linking `/placement/postings` without the
grant falls through to `<NotFound/>`; `RequireModule` renders `<Forbidden/>` where the distinction matters. Not
a blank screen, which is what today's client-side filtering produces.

Vite `manualChunks` names each bundle `module-<code>`, so the network tab is legible.

`ModuleErrorBoundary` handles the stale-chunk-after-deploy case: on `ChunkLoadError` it reloads once, guarded
by a `sessionStorage` flag so it cannot loop.

---

## Auth on the client

Credentials are httpOnly cookies; **no token is ever readable from JavaScript**
([ADR-0004](../01-architecture/adr/0004-cookie-auth-and-csrf-strategy.md)).

```tsx
// packages/auth/src/AuthProvider.tsx
const { data: session, status } = useQuery({
  queryKey: ["session"],
  queryFn: getMe,
  staleTime: 5 * 60_000,
  retry: false,
});
```

`localStorage` holds only a non-secret `isAuthenticated` hint (copied from the sysadmin client's
`AuthContext`) so the first frame renders correctly without a round trip. It grants nothing; the server ignores
it.

Preserved from the sysadmin client because it is already correct: a throttled activity writer, a 60-second
interval idle check, and **cross-tab logout via the `storage` event**. The idle timeout comes from the server
(`idle_timeout_seconds` in `/me`), so it is configurable without a frontend deploy.

### The HTTP client

```ts
// packages/api-client/src/http.ts
const http = axios.create({ baseURL: `${import.meta.env.BASE_URL}api`, withCredentials: true });

http.interceptors.request.use(cfg => {
  if (!SAFE_METHODS.has(cfg.method!.toUpperCase())) {
    cfg.headers["X-CSRF-Token"] = readCsrfCookie();
  }
  cfg.headers["X-Request-ID"] = crypto.randomUUID();
  return cfg;
});

// Single-flight refresh: concurrent 401s queue behind ONE refresh, then replay.
http.interceptors.response.use(r => r, async error => {
  if (error.response?.status !== 401 || error.config._retried) throw error;
  await refreshOnce();                       // module-level promise, shared by all callers
  error.config._retried = true;
  return http(error.config);
});
```

**Single-flight is not an optimization — it is a correctness requirement.** Ten parallel requests on a cold
token would otherwise fire ten refreshes; nine present the same not-yet-rotated token, the server's
reuse-detection revokes the family, and the user is logged out. A self-inflicted outage.

This generalizes the sysadmin client's already-correct 401 interceptor and fixes the gap in `Fusion-client`,
which has **no shared instance and no interceptors at all**.

### Guards

```tsx
<RequireAuth>                              // no session → /login?next=<path>
<RequireModule code="placement_cell">      // not granted → <Forbidden/>, URL preserved
<RequirePermission code="placement_cell.offer.issue" fallback={<Forbidden/>}>

const { can } = usePermission();
{can("placement_cell.offer.revoke") && <Button color="red">Revoke</Button>}
```

**Client permission checks are UX only.** Every one has a server counterpart. A review that finds a
client-only check rejects the PR.

---

## The typed API client

`orval` generates hooks and types from the **committed** OpenAPI schemas. CI runs
`git diff --exit-code openapi/` on the backend, so the schema cannot drift from the code — and a backend field
rename therefore surfaces as a **TypeScript compile error** rather than a runtime `undefined` in production.

```ts
const { data, isPending } = useListPlacementPostings({ status: "published" });
const { mutate } = useCreatePlacementApplication();
```

`tools/sync-openapi.mjs` copies the schemas from the backend repo in CI. Nobody hand-writes a request path or
a response type.

---

## Module structure

`apps/shell/src/modules/<code>/`, following the sysadmin client's best-structured feature
(`pages/UpcomingBatches/`):

```
placement/
├── manifest.ts        code · basePath · load() · indexPermission
├── routes.tsx         RouteObject[]
├── pages/             one file per route
├── components/        module-local; anything reusable is promoted to @fusion/ui
├── hooks/             useBatches-style data hooks
├── api/               thin wrappers over the generated client where needed
└── utils/
```

`manifest.code` **must** equal `registry_module.code`. A CI check asserts the two sets match exactly.
Recipe: [module-authoring-guide-frontend.md](module-authoring-guide-frontend.md).

---

## Error boundaries

| Boundary | Catches | Shows |
|---|---|---|
| `RouteErrorBoundary` | render errors in a route subtree | `<ErrorState>` with the `request_id` and a retry |
| `ModuleErrorBoundary` | a module's chunk failing to load, and its render errors | reload once for `ChunkLoadError`; otherwise "This module is unavailable" with the rest of the shell intact |
| axios interceptor | 401 → refresh; 403 → `<Forbidden/>`; 5xx → toast + Sentry | |

Every error surface displays the **`request_id`** from the error envelope. That single id is what turns "it
broke" into a `journalctl` grep.

---

## Configuration

`apps/shell/src/env.ts` validates `import.meta.env` with zod at startup and **throws on a missing
variable** — a misconfigured build fails at load, not on the first API call.

`VITE_API_BASE_PATH` · `VITE_LEGACY_APP_URL` (the sidebar's "Academics" external link) · `VITE_SENTRY_DSN` ·
`VITE_ENVIRONMENT`.

No secret is ever in a `VITE_*` variable — everything prefixed `VITE_` is compiled into the bundle and public.

---

## Coexistence with `Fusion-client`

Through Phases 3–7 both frontends are live. The shell links to the legacy app via `externalLinks` in the
sidebar, labelled "Academics", so a user does not have to know two URLs.

The legacy app accepts the JWT cookie after a **two-line change** (`withCredentials: true` in
`src/helper/validateauth.jsx` and `src/pages/login.jsx`). Fallback if that is undesirable: IAM also mints a
legacy DRF token at login and the old client works untouched
([legacy-compatibility-and-erp-projection.md](../02-iam/legacy-compatibility-and-erp-projection.md)).

Idle timeout is unified at 30 minutes. `Fusion-client`'s 5-minute timeout is raised to match, otherwise a user
switching between the two applications is logged out by whichever is stricter.

---

## Performance

- **Route-level code splitting** by module. Neither existing client splits at all — both statically import
  everything.
- `size-limit` budgets: shell entry ≤ 220 kB gz, each module chunk ≤ 150 kB gz. Enforced in CI.
- TanStack Query `staleTime` per query type: reference data 10 min, lists 30 s, the session 5 min.
- `react-window` for genuinely long lists, as `UserDirectory.jsx` already does.
- Debounced search (200 ms), matching the existing client.
- `<img loading="lazy">` and explicit dimensions to avoid layout shift.

---

## Local development

```bash
pnpm install
pnpm dev                # shell on :5173, proxying /api → localhost:8000
pnpm turbo lint typecheck test
pnpm playwright test
```

`vite.config.ts` proxies `/api` so cookies are same-origin in development — the pattern from the sysadmin
client's `vite.config.js`, which already does this correctly.
