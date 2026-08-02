# ADR-0003 — RS256 JWT access token + opaque rotating refresh token

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0002](0002-separate-iam-service-and-database.md), [0004](0004-cookie-auth-and-csrf-strategy.md)

## Context

Three separate backends must authenticate the same user: `fusion-iam`, `fusion-platform`, and the
legacy monolith. A fourth (the sysadmin console) joins until Phase 7 absorbs it.

What exists today is the constraint that matters. The monolith uses DRF `authtoken` — an opaque key,
**rotated on every login** (so logging in on a phone silently logs out the laptop), with expiry bolted on
by monkey-patching `TokenAuthentication.authenticate_credentials` at import time. Validating it costs a
database round trip. The monolith already writes a session row to Postgres on **every request**
(`SESSION_SAVE_EVERY_REQUEST = True`), and its middleware re-queries designations per request. Adding
another per-request database hit for auth is not affordable.

There is also an availability requirement discovered while designing the cutover: if every request into
the legacy monolith had to call IAM to validate a token, **IAM becoming unavailable would take down the
academic system**. Today the monolith has no such dependency, and the migration must not introduce one.

## Decision

**Access token:** RS256-signed JWT, **10-minute TTL**, delivered in an httpOnly cookie `fusion_at` with
`Path=/` so the legacy app can see it. Claims: `sub`, `erp_uid`, `sid`, `rol` (active role), `mod`
(granted module codes), `pv` (permission version), `amr`, `aud`, `exp`, `iat`, `kid`.

**Refresh token:** opaque, 256 bits of CSPRNG, stored only as a SHA-256 hash in
`identity_refresh_token`. 12-hour sliding window, 7-day absolute cap. Delivered in cookie `fusion_rt`
scoped `Path=/app/api/iam/v1/auth` with `SameSite=Strict`, so it is sent **only** to the refresh
endpoint and is never attached to an ordinary API call.

**Validation is local.** Every service verifies the JWT signature against JWKS fetched from
`/.well-known/jwks.json`, cached in Redis for 10 minutes and served by nginx with a 10-minute
`proxy_cache`. **No per-request call into IAM.**

**Rotation with reuse detection.** Every refresh issues a new refresh token and marks the old one used,
linked by `parent`. Presenting an already-used token means it leaked, so the **entire token family is
revoked** and the user must log in again.

**Revocation** writes `identity_session.revoked_at` and adds `sid` to a Redis denylist held for 10
minutes — one access-token lifetime. Services check the denylist on each request (one Redis `GET`, not a
database query), so a revoked *session* dies immediately.

**Key rollover:** two signing keys live at once, selected by `kid`. Rotation needs no downtime.

## Consequences

**Good**

- Authorization costs one signature verification and one Redis `GET`. No database round trip.
- **IAM going down does not log anyone out** — existing sessions keep working for up to 10 minutes, and
  legacy DRF tokens keep working indefinitely during transition. This is the property that makes the
  Phase 3 cutover safe.
- Multiple concurrent sessions per user work correctly. The current rotate-on-login behaviour, which
  silently kills other devices, goes away.
- A leaked refresh token is detected and contained rather than silently exploited.
- The legacy monolith needs one new authentication class and no other change.

**Bad, and accepted**

- **A permission or role change takes up to 10 minutes to reach a live token.** This is the central
  trade-off. Mitigations: `pv` in the claims makes staleness detectable; the shell refreshes on role
  switch; and if something must be cut off *now*, you revoke the **session** (immediate, via the
  denylist) rather than the role. This is written down in
  [data-ownership-and-sync.md](../data-ownership-and-sync.md#6-consistency-guarantees-stated-plainly)
  because it is the kind of thing that otherwise gets rediscovered during an incident.
- JWTs are readable by anyone holding them. Therefore **no PII in claims** — no email, no name, no
  roll number. `sub` and `erp_uid` are opaque identifiers.
- Signing-key compromise is catastrophic. Mitigated by systemd `LoadCredential`, a rotation runbook,
  and short access-token lifetimes.
- Claim size grows with granted modules. `mod` holds short codes, not labels; measured at ~40 modules
  the cookie stays well under 4 KB. A CI assertion caps encoded token size at 3 KB.
- Two token types to reason about. Mitigated by keeping refresh strictly scoped to one path.

## Alternatives considered

**Opaque token + introspection endpoint.** The most secure option — instant revocation, nothing
readable client-side. Rejected because it puts IAM in the hot path of every request to every service,
making IAM a hard dependency for the academic monolith's availability. That is precisely the coupling we
must not introduce.

**Keep DRF `authtoken` everywhere.** Rejected: a database hit per request on a system already doing a
write per request, no expiry without a monkey-patch, no multi-device support, no claims, and no way for
the platform to authorize without querying the ERP database.

**HS256 with a shared secret.** Rejected: every validating service would hold the *signing* key, so
compromising the legacy monolith would let an attacker mint tokens. RS256 means validators hold only the
public key.

**Long-lived access token (1 hour) with no refresh.** Rejected: a one-hour window for a revoked role is
not acceptable, and it makes logout meaningless without a denylist held for an hour.

**Access token in memory only (no cookie), refresh in a cookie.** The standard SPA pattern, and it
avoids CSRF concerns on the access token. Rejected because the **legacy monolith must see the
credential**, and it is a separately-served application at `/`. A `Path=/` httpOnly cookie is the only
mechanism both applications share. CSRF is then handled explicitly
([ADR-0004](0004-cookie-auth-and-csrf-strategy.md)).

## Revisit if

- A regulatory or policy requirement demands instant permission revocation, in which case introspection
  for a subset of `is_dangerous` endpoints is the incremental answer.
- The legacy monolith is retired, removing the `Path=/` cookie constraint and allowing an
  in-memory access token.
