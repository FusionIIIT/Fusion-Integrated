# ADR-0004 — Credentials in httpOnly cookies; double-submit CSRF token

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0003](0003-rs256-jwt-access-plus-opaque-refresh.md)

## Context

`Fusion-client` stores its token in **both** `sessionStorage` and `localStorage`, and every call site
reads storage and builds its own `Authorization: Token …` header — there is no shared axios instance and
no interceptors. Any XSS anywhere in that 73k-LOC application exfiltrates a working credential, and a
`BroadcastChannel` handshake in `App.jsx` exists purely to guess whether a `localStorage` token survived
a browser restart.

`Fusion_System_Administrator` already does the right thing: an httpOnly `auth_token` cookie, no token in
JavaScript at all, and only a non-secret `isAuthenticated` hint in `localStorage`. That is the pattern to
generalize.

The complication is that the credential must be visible to **two separately-served applications** — the
shell at `/app/` and the legacy monolith at `/` — on the same origin.

## Decision

Credentials live in **httpOnly cookies**. No token is ever readable from JavaScript.

| Cookie | Contents | Attributes | TTL |
|---|---|---|---|
| `fusion_at` | access JWT | `HttpOnly; Secure; SameSite=Lax; Path=/` | 10 min |
| `fusion_rt` | opaque refresh | `HttpOnly; Secure; SameSite=Strict; Path=/app/api/iam/v1/auth` | 12 h sliding / 7 d absolute |
| `fusion_csrf` | random CSRF value | `Secure; SameSite=Lax; Path=/` — **readable by JS, by design** | session |

**CSRF: double-submit cookie.** Every unsafe method (`POST`, `PUT`, `PATCH`, `DELETE`) must carry
`X-CSRF-Token` matching the `fusion_csrf` cookie. A custom header cannot be set by a cross-origin form or
image, and reading the cookie to forge the header requires same-origin script access — which an attacker
does not have. Enforced by one middleware in `fusion_auth`, applied by default, with an explicit opt-out
list containing only login and the JWKS endpoint.

`SameSite=Lax` on the access cookie already blocks cross-site `POST`s. The double-submit check is the
second layer, and it is what protects against a same-site subdomain compromise, which `Lax` does not.

`SameSite=Strict` on the refresh cookie plus its narrow `Path` means it is attached **only** to the
refresh endpoint — it is never in flight during ordinary API traffic.

The frontend keeps a **non-secret** `isAuthenticated` hint in `localStorage` (copied from the sysadmin
client's `AuthContext`) purely so the shell can render the right first frame without a network
round trip. It grants nothing; the server ignores it entirely.

**Single-flight refresh** in `packages/api-client/src/http.ts`: concurrent 401s queue behind **one**
`POST /auth/refresh` and replay on success. Without this, ten parallel requests on a cold token fire ten
refreshes, and rotation-with-reuse-detection then revokes the family and logs the user out — a
self-inflicted outage.

## Consequences

**Good**

- XSS can no longer steal a credential. It can still *act* as the user while the page is open, which is
  why CSP is strict, but the credential does not leave the browser.
- Both the shell and the legacy monolith authenticate from the same cookie with no token-passing between
  applications, no URL fragments, no `postMessage`.
- No token synchronization logic. The `BroadcastChannel` handshake and the dual
  `sessionStorage`/`localStorage` storage both disappear.
- Logout is genuinely server-side: clear the cookies, revoke the session, add `sid` to the denylist.

**Bad, and accepted**

- CSRF becomes our problem, whereas a bearer header is immune by construction. Handled by default-on
  middleware with a tiny opt-out list — the failure mode is a blocked legitimate request, not a silent
  hole.
- Cookies are sent on every request to the origin, including static assets under `/app/`. Mitigated by
  serving hashed assets from a path nginx excludes from proxying, so the overhead is bytes on a static
  GET.
- Non-browser clients (scripts, service-to-service) cannot use cookies conveniently. Handled by
  accepting `Authorization: Bearer` as a fallback for `kind = service` principals only, with its own
  scopes and audience.
- `Path=/` on the access cookie means the legacy monolith receives it. **This is why
  `DEBUG = True` in the legacy production settings is a hard blocker** — a traceback page renders
  `request.META`, which would include the cookie. Fixed in Phase 0, before any cookie is issued.
- Cookie size is bounded; `mod` claims are short codes, with a CI assertion capping the encoded token at
  3 KB.

## Alternatives considered

**`Authorization: Bearer` from memory, refresh in a cookie.** The textbook SPA pattern and immune to CSRF.
Rejected because the legacy monolith is a separately-served application that must see the credential;
there is no shared memory between it and the shell. Revisit when the monolith is retired.

**Keep tokens in `localStorage`.** Rejected. It is the current design and it is the single largest
credential-exposure risk in the estate.

**Django's built-in `CsrfViewMiddleware`.** Partially reused for the legacy monolith's session paths, but
not for the new services: it is coupled to Django sessions and to a `csrftoken` cookie name, and it
interacts awkwardly with DRF's `SessionAuthentication` enforcement. A ~40-line explicit double-submit
check is clearer and easier to test.

**Origin/Referer checking instead of a token.** Rejected as a sole mechanism — `Referer` can be absent
under some privacy settings, producing intermittent failures. Used as an **additional** check on
`is_dangerous` endpoints, not as the primary one.

## Verification

- A cross-origin `POST` without `X-CSRF-Token` returns 403. Tested.
- A `POST` with a mismatched token returns 403. Tested.
- `document.cookie` in the browser console shows `fusion_csrf` and **not** `fusion_at` or `fusion_rt`.
  Asserted in a Playwright test.
- Ten parallel requests against an expired access token produce exactly **one** refresh call. Tested.
- The refresh cookie is absent from the request headers of a non-refresh API call. Asserted in a
  Playwright test.
