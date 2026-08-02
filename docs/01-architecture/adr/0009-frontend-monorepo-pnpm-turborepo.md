# ADR-0009 — One pnpm + Turborepo monorepo: four packages, one app

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0010](0010-server-driven-navigation.md)

## Context

The requirement is one login and one sidebar showing whichever modules a role can access. That is a
single-shell requirement.

There are already two React applications, both React 18.3 + Vite 5 + Mantine 7.13, and they have
diverged in every way that matters:

| | `Fusion-client` | `Fusion_System_Administrator/client` |
|---|---|---|
| State | Redux Toolkit | `useState` + one context |
| HTTP | bare axios, **no instance, no interceptors** | shared `axiosInstance` **with** a 401 interceptor |
| Auth | token in `sessionStorage` **and** `localStorage` | httpOnly cookie, no token in JS |
| Idle timeout | 5 min | 30 min |
| Login page | one 1,709-line file | componentized `pages/Login/{components,hooks,constants}` |
| Types | JSX, no TypeScript | JSX, no TypeScript |
| Tests | none | none |
| Code splitting | none — everything statically imported | none |

The sysadmin client is clearly the better one, and its `AppLayout` + `theme.js` is the design the new UI
must match exactly. Duplicating that design system into a third application would guarantee three
divergent copies within a year.

## Decision

One monorepo, `fusion-frontend/`, using **pnpm workspaces + Turborepo**. Deliberately small:

```
packages/config/       eslint-config · tsconfig · vitest-preset
packages/ui/           @fusion/ui         — the design system, extracted verbatim
packages/api-client/   @fusion/api-client — orval-generated from committed OpenAPI
packages/auth/         @fusion/auth       — AuthProvider, guards, refresh, idle, cross-tab
packages/testing/      renderWithProviders · MSW handlers generated from OpenAPI examples
apps/shell/            the single SPA
```

**TypeScript, strict** — `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`,
`noImplicitOverride`, `verbatimModuleSyntax`.

**Internal packages ship source**, not builds: `"exports": {".": "./src/index.ts"}`. Vite transpiles them,
so there is no build step for `packages/*` and HMR crosses package boundaries. `turbo typecheck` runs
`tsc --noEmit` per package in parallel.

**Mantine pinned to 7.13.x**, matching the sysadmin client exactly, so the extracted CSS behaves
identically.

**Redux is dropped.** The only global state in `Fusion-client` is `user`, `role` and
`accessibleModules` — all of which are *server* state and belong in TanStack Query.

`Fusion-client` is not migrated into the monorepo. It stays where it is, linked from the sidebar as an
external link, until Phase 8 absorbs it.

## Consequences

**Good**

- One design system, one auth implementation, one HTTP client, one set of conventions. A fix lands
  everywhere at once.
- The generated API client means a backend field rename becomes a **TypeScript compile error** rather than
  a runtime `undefined` in production. CI runs `git diff --exit-code openapi/`, so the schema cannot drift.
- Modules are lazy route bundles, so the shell's initial payload does not grow with the twentieth module —
  a real improvement over both existing apps, which statically import everything.
- `packages/testing` generates MSW handlers from the OpenAPI examples, so frontend mocks cannot drift from
  the API.
- Playwright visual baselines captured from today's `/sysadmin/` **prove** the design-system extraction is
  pixel-identical, instead of asserting it.

**Bad, and accepted**

- **The team is new to monorepos.** This is the main cost. Mitigated deliberately: four packages and one
  app — no further splitting — plus a `Makefile` of named tasks and a `CONTRIBUTING.md` walkthrough. Every
  instinct to add a fifth package should be resisted.
- pnpm's symlinked `node_modules` occasionally confuses tools expecting a flat layout. Mitigated by
  `.npmrc` with `shamefully-hoist=false` and documenting the two known cases.
- Turborepo caching can mask a stale build. Mitigated by including `tsconfig` and lockfile hashes in task
  inputs, and by CI never using a local cache.
- Two frontends live simultaneously through Phases 3–7. Mitigated by the legacy app accepting the JWT
  cookie after a two-file patch (`validateauth.jsx`, `login.jsx` gain `withCredentials`), with a fallback
  of IAM also minting a legacy DRF token at login.
- Strict TypeScript on a team used to JSX will slow the first weeks. Accepted — it is why the generated
  client and the typed nav contract are worth having at all.

## Alternatives considered

**Three separate repos sharing a published `@fusion/ui` npm package.** Rejected: version skew between
publisher and consumers, a publish step in every design change, three logins to keep synchronized, and the
unified single-sidebar experience becomes cross-app SSO glue rather than one component.

**Module Federation micro-frontends.** Genuinely how large organizations do this, and it allows independent
per-module deploys. Rejected: runtime shared-dependency version pinning, runtime contract drift, harder
local development, and a much worse debugging story — all to solve independent-deployment for a single
team. Same reasoning as [ADR-0001](0001-modular-monolith-over-microservices.md): take the boundaries,
skip the deployables. Lazy route bundles give most of the payload benefit with none of the runtime risk.

**Extend `Fusion-client` in place.** Rejected: JSX with no types, no tests, Redux, tokens in
`localStorage`, no code splitting, and a 1,709-line login page. We would be building the new platform on
the weaker of the two existing frontends.

**Extend `Fusion_System_Administrator/client` in place.** Closer to viable — it is the better codebase.
Rejected because it is a single-purpose admin console with a static unfiltered sidebar and its own
repository lifecycle; the shell needs server-driven navigation, module lazy-loading and a shared design
package. We extract from it rather than growing inside it.

**Nx instead of Turborepo.** Rejected: more capability than four packages need, and a steeper learning
curve for a team new to monorepos.

## Revisit if

The team splits into independent squads with genuinely independent release cadences — at which point
Module Federation on a per-module basis becomes worth its complexity, and the manifest-based module
registry is already the right seam for it.
