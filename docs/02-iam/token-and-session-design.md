---
owner: iam-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Token & Session Design

Concrete mechanics of login, tokens, refresh, revocation and idle handling. Decisions and their rationale
are in [ADR-0003](../01-architecture/adr/0003-rs256-jwt-access-plus-opaque-refresh.md) and
[ADR-0004](../01-architecture/adr/0004-cookie-auth-and-csrf-strategy.md); this document is the
specification. Lifecycle diagram: [`_diagrams/auth-token-lifecycle.mmd`](../_diagrams/auth-token-lifecycle.mmd).

---

## Cookies

| Cookie | Contents | Attributes | Lifetime |
|---|---|---|---|
| `fusion_at` | access JWT, RS256 | `HttpOnly; Secure; SameSite=Lax; Path=/` | **10 min** |
| `fusion_rt` | opaque refresh, 256-bit CSPRNG | `HttpOnly; Secure; SameSite=Strict; Path=/app/api/iam/v1/auth` | 12 h sliding, **7 d absolute** |
| `fusion_csrf` | random CSRF value | `Secure; SameSite=Lax; Path=/` — **readable by JS, by design** | session |

`Path=/` on the access cookie is what lets the legacy monolith at `/` see the credential. That is the
reason the legacy `DEBUG = True` must be fixed first — a traceback page renders `request.META`, cookies
included.

`fusion_rt` is scoped to the refresh path with `SameSite=Strict`, so it is **never** in flight during
ordinary API traffic. If the access cookie leaks from a proxy log, the attacker gets 10 minutes; the
refresh token was not in that request at all.

In development over plain HTTP, `Secure` is dropped by settings — and a startup assertion refuses to
start with `Secure=False` when `DEBUG=False`, so it cannot reach production.

---

## Access token

```json
{
  "iss": "https://fusion.iiitdmj.ac.in/app/api/iam",
  "sub": "018f4c2a-7b31-7c4e-9a02-6f1d8e3b5c91",
  "erp_uid": 1234,
  "sid": "018f4c2a-8a01-7d20-b3c4-9e2f1a0b7d55",
  "rol": "placement_coordinator",
  "mod": ["dashboard", "placement_cell", "profile"],
  "pv": 1187,
  "amr": ["pwd", "otp"],
  "aud": ["fusion-platform", "fusion-legacy", "fusion-sysops"],
  "iat": 1785312000,
  "exp": 1785312600,
  "jti": "018f4c2a-9012-7e11-8f03-1a2b3c4d5e6f"
}
```

| Claim | Purpose |
|---|---|
| `sub` | `identity_user.id` (UUIDv7) |
| `erp_uid` | `auth_user.id` — what the platform and the legacy app join on |
| `sid` | session id; the unit of revocation |
| `rol` | active role code — the single role whose permissions apply |
| `mod` | granted module codes; `HasModuleGrant` reads this, so a module check costs nothing |
| `pv` | permission version, for staleness diagnostics and cache keying |
| `amr` | how they authenticated; `["pwd","otp"]` satisfies MFA-required endpoints |
| `aud` | audiences; a validator rejects a token not naming it |
| `jti` | for denylisting one specific token if ever needed |

**No PII.** No name, no email, no roll number. Anyone holding the token can read it.

**Size:** capped at 3 KB encoded by a CI assertion. `mod` holds short codes, not labels; at ~40 modules
this is comfortable.

### Validation, in every service

```python
class IamJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        raw = request.COOKIES.get("fusion_at") or _bearer(request)
        if not raw:
            return None
        claims = jwt.decode(raw, key=jwks.public_key_for(kid_of(raw)),
                            algorithms=["RS256"], audience=settings.IAM_AUDIENCE,
                            issuer=settings.IAM_ISSUER,
                            options={"require": ["exp", "iat", "sub", "sid", "aud"]})
        if redis.exists(f"iam:revoked_sid:{claims['sid']}"):
            raise AuthenticationFailed("Session revoked.")
        return Principal.from_claims(claims), None
```

Signature verification is local against JWKS fetched from `/.well-known/jwks.json`, cached in Redis for 10
minutes and served by nginx with a 10-minute `proxy_cache`. **No per-request call into IAM**, which is what
makes IAM's availability non-critical to the academic monolith.

A `leeway` of 30 seconds absorbs clock skew. `chrony` runs on the host.

### Key rollover

Two keys live at once, selected by `kid`. Rotation: publish the new public key to JWKS, wait for the JWKS
cache TTL (10 min) so every validator has it, then switch the signer, then retire the old key after one
access-token lifetime. Zero downtime.
Procedure: [rotate-signing-key.md](../07-ops/runbooks/rotate-signing-key.md).

Private keys are delivered by systemd `LoadCredential=` — never in an env var, never in the repository.

---

## Refresh token

256 bits from `secrets.token_urlsafe(32)`. **Only the SHA-256 hash is stored** in
`identity_refresh_token.token_hash`. A database dump yields nothing usable. No salt is needed: the input is
256 bits of entropy, so there is no dictionary to attack.

### Rotation with reuse detection

```python
def refresh(raw_token: str) -> TokenPair:
    tok = RefreshToken.objects.select_for_update().get(token_hash=sha256(raw_token))

    if tok.used_at is not None:                       # ← replay
        _revoke_family(tok)                           # walk to root, revoke all descendants
        tok.reuse_detected = True
        tok.save(update_fields=["reuse_detected"])
        audit("identity.refresh.reuse_detected", tok.session)
        metrics.incr("iam_refresh_reuse_detected_total")
        raise AuthenticationFailed("Token reuse detected. Please sign in again.")

    if tok.expires_at < now() or tok.session.revoked_at:
        raise AuthenticationFailed("Session expired.")
    if tok.session.absolute_expires_at < now():
        _revoke_session(tok.session, "absolute")
        raise AuthenticationFailed("Session expired.")

    tok.used_at = now()
    tok.save(update_fields=["used_at"])
    child = RefreshToken.objects.create(session=tok.session, parent=tok,
                                        token_hash=sha256(new := _new_raw()),
                                        expires_at=now() + REFRESH_SLIDING)
    return TokenPair(access=_mint_access(tok.session), refresh=new)
```

Presenting an already-used token means it leaked — the legitimate client would have the child. So the whole
family dies and the user re-authenticates. `select_for_update` makes two simultaneous refreshes serialize;
the second sees `used_at` set and correctly identifies a replay.

Two windows: **12-hour sliding** (each refresh extends it) and **7-day absolute** on
`identity_session.absolute_expires_at`, which no amount of activity extends.

### Single-flight on the client

`packages/api-client/src/http.ts` queues concurrent 401s behind **one** refresh call and replays them on
success. Without this, ten parallel requests against a cold token fire ten refreshes; nine present the
same not-yet-rotated token, rotation detects a "replay", and the family is revoked — a self-inflicted
logout. This is the single most important client-side detail in the design.

---

## Login

```
POST /app/api/iam/v1/auth/login   {username, password, otp?}
```

1. **Throttle** — `5/min` per IP **and** `10/hour` per username, Redis-backed so the counter is shared
   across gunicorn workers.
2. **Lockout check** against `identity_login_attempt`.
3. **Verify** with Argon2id (`time_cost=3, memory_cost=65536, parallelism=4`). A PBKDF2 hash from the
   legacy import is verified with PBKDF2 and **transparently rehashed to Argon2id** on success — this is
   what makes the Phase 2 import a copy rather than a reset for 3,277 people.
4. **Timing** — a `constant_time_compare` against a dummy hash runs when the user does not exist, so
   response time does not reveal existence.
5. **MFA** — if `mfa_required` and no valid TOTP, return `202` with `{"mfa_required": true}` and a
   short-lived MFA challenge token. Never `401`; the password was correct and the client needs to know.
6. **Create** `identity_session` (+ `amr`) and the first `identity_refresh_token`.
7. **Set** all three cookies. Return the `/me` payload directly, saving a round trip.

**Errors are generic.** `bad_password` and `unknown_user` both return the same message and status. This
mirrors `mapAuthError` in `Fusion_System_Administrator/client/src/pages/Login/hooks/useLogin.js`, which
already collapses 400/401 deliberately.

### Progressive lockout

| Consecutive failures | Lockout |
|---|---|
| 5 | 60 s |
| 8 | 5 min |
| 10 | 30 min |
| 15 | until an admin unlocks |

Counted per username **and** per IP, whichever trips first. A successful login resets the username
counter. Manual unlock: [unlock-account.md](../07-ops/runbooks/unlock-account.md).

---

## Role switching

```
PATCH /app/api/iam/v1/me/active-role   {"role": "student"}
```

1. **Verify the user actually holds the role**, currently valid. Never trust the client.
2. Persist `identity_session.active_role`.
3. Emit `iam.session.role_switched` → projects `ExtraInfo.last_selected_role` (subject to hazard **H3**,
   the 20-character column).
4. Mint a **new** access cookie with updated `rol`, `mod`, `pv`.
5. Return the full `/me` payload.

Client: `queryClient.clear()`, then navigate to `/dashboard`. Clearing the cache matters — cached
`placement.*` queries from the coordinator role must not survive into the student view.

Because `active_role` is on the **session**, two tabs can hold different roles. Deliberate, and different
from the legacy per-user `last_selected_role`.

---

## Revocation

| Trigger | Effect | Latency |
|---|---|---|
| Logout | `session.revoked_at`, `sid` denylisted 10 min, cookies cleared | immediate |
| Admin revoke | same, `revoke_reason = admin` | immediate |
| Password change | **all** the user's sessions revoked | immediate |
| Refresh reuse | the token family revoked | immediate |
| `status_changed` to suspended/archived | all sessions revoked | immediate |
| **Role or permission change** | nothing is revoked | **up to 10 min**, until token refresh |

The last row is the trade-off from [ADR-0003](../01-architecture/adr/0003-rs256-jwt-access-plus-opaque-refresh.md)
and it is the thing to remember during an incident: **to cut someone off now, revoke the session, not the
role.** Session revocation is a Redis `SET` checked on every request; role changes wait for the next
10-minute token mint.

The denylist entry is held for exactly one access-token lifetime — after that, no unexpired token can
carry that `sid`, so the entry is redundant and expires itself.

---

## Idle and absolute timeouts

| | Value | Enforced |
|---|---|---|
| Idle | **30 min** | client timer + server `last_seen_at` check on refresh |
| Absolute | **7 days** | `session.absolute_expires_at`, server-side |
| Access token | 10 min | `exp` |

30 minutes unifies the current inconsistency — `Fusion-client` uses 5 minutes,
`Fusion_System_Administrator` uses 30. Five minutes is hostile for a coordinator working through a
shortlist; 30 with a 10-minute access token is the right balance.

Client behaviour is ported from `Fusion_System_Administrator/client/src/context/AuthContext.jsx`, which
already does this correctly: a throttled activity writer, a 60-second interval check, and cross-tab logout
via the `storage` event. The `idle_timeout_seconds` value is **sent by the server** in `/me`, so it is
configurable without a frontend deploy.

The server is authoritative: a client with a tampered timer still fails at refresh, because
`last_seen_at` is checked server-side.

---

## Service-to-service tokens

For the platform's academic snapshot pull and similar internal calls:

- `identity_user.kind = "service"`, no credential, no session.
- A signed JWT with `aud = "fusion-legacy"`, a `scope` claim (`academics:snapshot:read`), and a
  **5-minute** TTL, minted on demand by IAM.
- Presented as `Authorization: Bearer` — the one place a bearer header is used.
- The receiving endpoint checks audience **and** scope, is bound to `127.0.0.1`, and is never exposed by
  nginx.

---

## Legacy coexistence

Through Phases 3–7, the legacy monolith runs both authentication classes:

```python
DEFAULT_AUTHENTICATION_CLASSES = [
    "applications.globals.api.iam_auth.IamJWTAuthentication",   # new, first
    "rest_framework.authentication.TokenAuthentication",        # existing, still valid
    "rest_framework.authentication.SessionAuthentication",
]
```

Behind `IAM_JWT_AUTH_ENABLED` (default off). Existing DRF tokens keep working throughout, so **rollback
requires no re-login** — that property is what makes the Phase 3 cutover safe.

Fallback if `Fusion-client` proves difficult to patch for cookies: IAM also mints a legacy
`authtoken_token` row at login, so the old client works unchanged. Detail in
[legacy-compatibility-and-erp-projection.md](legacy-compatibility-and-erp-projection.md).

---

## Verification

- Ten parallel requests on an expired access token produce exactly **one** refresh call.
- Replaying a used refresh token revokes the family and increments `iam_refresh_reuse_detected_total`.
- Two simultaneous refreshes with the same token: one succeeds, one is treated as a replay.
- `document.cookie` exposes `fusion_csrf` and **not** `fusion_at` or `fusion_rt` (Playwright).
- `fusion_rt` is absent from the headers of a non-refresh API call (Playwright).
- A revoked session's still-unexpired access token is rejected within one request.
- Login response time for an unknown username is statistically indistinguishable from a wrong password
  (1,000 samples, means within 5 ms).
- A token with the wrong `aud` is rejected by each service.
- A service refuses to start with `Secure=False` while `DEBUG=False`.
- Key rollover: a token signed by the old `kid` validates throughout the overlap window.
- An imported PBKDF2 hash logs in successfully and is Argon2id afterwards.
