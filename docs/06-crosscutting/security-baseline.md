---
owner: security-owner
status: authoritative
last-reviewed: 2026-08-01
---

# Security Baseline

Every item has an **owner** and a **verification method**. An item nobody verifies is an aspiration, not a
control.

Column key: **V** = how it is checked — `CI` (automated, blocks merge) · `Test` (in the suite) ·
`Startup` (a Django system check refuses to boot) · `Review` (human, on the checklist) ·
`Ops` (periodic, with a named cadence).

---

## 0. Blocking prerequisites

These gate the whole programme. None is optional.

| # | Item | Owner | V | Status |
|---|---|---|---|---|
| P1 | **`DEBUG = False` in legacy production.** `Fusion/settings/production.py:3` currently ships `True`. Any unhandled 500 renders a traceback page including `request.META` — which will contain the `Path=/` auth cookie. **No cookie is issued until this is fixed.** | iam-lead | CI (`check --deploy`) | Phase 0 |
| P2 | `SECRET_KEY`, DB credentials, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` out of source and into env, in the legacy app | iam-lead | CI + `gitleaks` | Phase 0 |
| P3 | `CORS_ORIGIN_ALLOW_ALL = True` removed (`common.py:285`) | iam-lead | CI | Phase 0 |
| P4 | Committed Google OAuth client id/secret rotated and moved to env (`common.py:23-24`) | iam-lead | Ops | Phase 0 |
| P5 | Committed DB password rotated (present in `development.py`, `production.py`, `docker-compose.yml`, `README.md:272`) | ops | Ops | Phase 0 |

---

## 1. Authentication

| # | Item | Owner | V |
|---|---|---|---|
| 1.1 | Argon2id (`time_cost=3, memory_cost=65536, parallelism=4`). PBKDF2 accepted for imported legacy hashes, **transparently upgraded on next login** | iam-lead | Test |
| 1.2 | Password policy: ≥12 chars staff / ≥10 students · zxcvbn score ≥3 · blocklist `{fusion, iiitdm, jabalpur, username, roll_no, first_name}` · history 5 | iam-lead | Test |
| 1.3 | **No forced rotation** (NIST SP 800-63B). Expiry exists only for deliberately time-boxed accounts | iam-lead | Review |
| 1.4 | Optional HIBP k-anonymity range check on password set | iam-lead | Test |
| 1.5 | Progressive lockout: 5→60 s, 8→5 min, 10→30 min, 15→admin unlock. Counted per **username and per IP** | iam-lead | Test |
| 1.6 | Generic error on bad credentials — never reveals whether the username exists | iam-lead | Test |
| 1.7 | Constant-time comparison against a dummy hash for unknown users, so response time does not leak existence | iam-lead | Test (1,000 samples, means within 5 ms) |
| 1.8 | TOTP mandatory for any role holding an `is_dangerous` permission; secrets Fernet-encrypted at rest | iam-lead | Test |
| 1.9 | Step-up re-auth (≤5 min) for offer revocation, debarment, PII export, role assignment, backup restore | iam-lead | Test |
| 1.10 | Refresh rotation with **reuse detection**: a replayed token revokes the whole family | iam-lead | Test |
| 1.11 | Access token 10 min; refresh 12 h sliding / **7 d absolute** | iam-lead | Test |
| 1.12 | Password change revokes **all** the user's sessions | iam-lead | Test |
| 1.13 | Session revocation is immediate via a Redis `sid` denylist held one access-token lifetime | iam-lead | Test |
| 1.14 | **No PII in JWT claims** — no name, email or roll number | iam-lead | Test |
| 1.15 | RS256, not HS256: validators hold only the public key | iam-lead | Review |
| 1.16 | Two signing keys live (`kid` rollover), so rotation needs no downtime | ops | Test |
| 1.17 | Signing keys via systemd `LoadCredential=`, never an env var | ops | Review |

---

## 2. Authorization

| # | Item | Owner | V |
|---|---|---|---|
| 2.1 | Deny by default: `DEFAULT_PERMISSION_CLASSES = [IsAuthenticatedPrincipal]`, and every view declares explicitly | platform-lead | CI |
| 2.2 | **Deny always wins** in permission resolution — not "most specific wins" | iam-lead | Test (property-based) |
| 2.3 | Only the **active role's** permissions apply; no union across held roles | iam-lead | Test |
| 2.4 | Object access enforced by **filtering the queryset in the selector**, never fetch-then-check | platform-lead | Review + Test |
| 2.5 | Out-of-scope object returns **404, not 403** — 403 makes any id an enumeration oracle | platform-lead | Test |
| 2.6 | Module grant checked per request (`HasModuleGrant`), not only in the sidebar | platform-lead | Test |
| 2.7 | Client-side permission checks are UX only; every one has a server counterpart | frontend-lead | Review |
| 2.8 | Every `is_dangerous` permission use writes an `audit_event`, success **or** failure | iam-lead | Test |
| 2.9 | `is_superadmin` held by ≤2 active accounts; every request under it audited | iam-lead | CI |
| 2.10 | Fail closed: unknown permission code, no roles, or an unrebuildable cache → deny | iam-lead | Test |

---

## 3. Rate limits

Redis-backed, so counters are shared across gunicorn workers. **An in-memory throttle with 5 workers is a 5×
throttle** — the legacy app has no `CACHES` setting at all, so this must not be inherited.

| Scope | Limit |
|---|---|
| `login` | 5/min per IP **and** 10/hour per username |
| `password_reset_send` | 3/hour per username, 10/hour per IP |
| `mfa_verify` | 5 per 5 min per user |
| `refresh` | 60/hour per session |
| `anon` | 30/min |
| `user` (read) | 600/min |
| `write` | 120/min |
| `apply` (placement) | 30/hour per user |
| `export` | 5/hour per user |
| `upload` | 20/hour per user |

Owner: platform-lead. V: Test (one per scope) + Ops (429 rate on the dashboard). 429 always carries
`Retry-After`.

---

## 4. Input and output

| # | Item | Owner | V |
|---|---|---|---|
| 4.1 | Uploads: extension allowlist **∩** magic-byte sniff (`python-magic`) **∩** size cap **∩** filename sanitized to `[A-Za-z0-9._-]` **∩** UUID storage key. All five — each alone is bypassable | platform-lead | Test |
| 4.2 | Served with `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff` via `X-Accel-Redirect` | ops | Test |
| 4.3 | ClamAV scan in a Celery task **gates download**; `scan_status = pending` blocks it | platform-lead | Test |
| 4.4 | `pikepdf` sanitize pass strips embedded JavaScript from PDFs | platform-lead | Test |
| 4.5 | Size caps: resume 2 MB, document 5 MB. Enforced at nginx **and** in the app | ops | Test |
| 4.6 | No `raw()`/`extra()`/`RawSQL` outside `core/db/sql/`, parameterized, one file per query | platform-lead | CI (grep + bandit) |
| 4.7 | All output JSON; **no server-rendered HTML** in the new services — no XSS sink | platform-lead | Review |
| 4.8 | `dangerouslySetInnerHTML` banned | frontend-lead | CI (ESLint) |
| 4.9 | Markdown fields (`role_summary`) rendered through a sanitizing pipeline with a tag allowlist | frontend-lead | Test |
| 4.10 | **CSV/XLSX formula-injection escaping**: any cell starting `= + - @ \t \r` prefixed with `'` | platform-lead | Test |
| 4.11 | Unknown query parameter → **422**, never silently ignored | platform-lead | Test |
| 4.12 | Request body size capped (1 MB JSON, 6 MB multipart) at nginx | ops | Test |
| 4.13 | Every `POST` that creates accepts `Idempotency-Key`; same key + different body → 409 | platform-lead | Test |

---

## 5. Transport and headers

| # | Item | Owner | V |
|---|---|---|---|
| 5.1 | TLS only; HTTP → HTTPS redirect | ops | Ops |
| 5.2 | `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` | ops | Test |
| 5.3 | CSP with a **style nonce** (Mantine's `getStyleNonce`), no `unsafe-inline` | frontend-lead | Test |
| 5.4 | `X-Content-Type-Options: nosniff` · `X-Frame-Options: DENY` · `frame-ancestors 'none'` | ops | Test |
| 5.5 | `Referrer-Policy: strict-origin-when-cross-origin` | ops | Test |
| 5.6 | `Permissions-Policy: camera=(), microphone=(), geolocation=(), interest-cohort=()` | ops | Test |
| 5.7 | `Cross-Origin-Opener-Policy: same-origin` | ops | Test |
| 5.8 | Cookies: `HttpOnly` + `Secure` + `SameSite` per [ADR-0004](../01-architecture/adr/0004-cookie-auth-and-csrf-strategy.md); refresh scoped to its own path | iam-lead | Test |
| 5.9 | CSRF double-submit on every unsafe method, default-on with a two-entry opt-out list | iam-lead | Test |
| 5.10 | Startup refuses to boot with `Secure=False` while `DEBUG=False` | platform-lead | Startup |

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-<n>';
  style-src 'self' 'nonce-<n>'; img-src 'self' data:; font-src 'self';
  connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self';
  object-src 'none'; upgrade-insecure-requests
```

---

## 6. Data and PII

| # | Item | Owner | V |
|---|---|---|---|
| 6.1 | PII classified **structurally** via `PIIField` / `SensitivePIIField` in `core/db/fields.py`, not by comment | platform-lead | Review |
| 6.2 | structlog processor recursively redacts `{password, token, otp, secret, authorization, cookie, phone, address, date_of_birth, category, aadhaar}` | platform-lead | Test |
| 6.3 | Sentry `send_default_pii=False` plus a `before_send` scrubber | platform-lead | Test |
| 6.4 | PII export requires an `is_dangerous` permission + step-up, and writes an audit row containing **the exact filter and the row count** | placement-lead | Test |
| 6.5 | Statistics suppress any cell with `placed < 5` — a single-student cell plus a public median is that student's salary | placement-lead | Test |
| 6.6 | `gender` / `category` in an eligibility rule writes an `audit_event` and appears in the weekly review | placement-lead | Test |
| 6.7 | Retention enforced by beat tasks: applications 7 y · audit 3 y (then archived) · login attempts 90 d · documents graduation + 2 y · sessions expiry + 7 d | platform-lead | Test |
| 6.8 | TOTP secrets Fernet-encrypted; a database dump alone does not yield them | iam-lead | Test |
| 6.9 | Refresh tokens stored as SHA-256 only | iam-lead | Test |
| 6.10 | Download tokens are lookup keys, authorization-checked per fetch — **not** bearer credentials | platform-lead | Test |

---

## 7. Database privilege

| # | Item | Owner | V |
|---|---|---|---|
| 7.1 | One Postgres role per service per purpose; `ops/db/roles.sql` idempotent, applied on deploy | ops | Startup |
| 7.2 | `platform_erp_ro` is `SELECT`-only on an allowlist. **A platform write to the ERP fails in Postgres** | ops | Test |
| 7.3 | `iam_erp_projector` can write exactly `globals_{designation,holdsdesignation,moduleaccess}` | ops | Test |
| 7.4 | `UPDATE`/`DELETE` **revoked** on `academics_resultsnapshot` — immutability is a database guarantee | platform-lead | Test |
| 7.5 | `UPDATE`/`DELETE` revoked on `audit_event` — append-only | iam-lead | Test |
| 7.6 | Migrations run as `platform_migrator`; the runtime role has **no DDL** | ops | Review |
| 7.7 | **Tests run as the real application role**, not superuser — otherwise a missing grant is invisible and this whole section is decorative | platform-lead | CI |
| 7.8 | CI fails if a table in `fusion_nonacad` has no explicit grant | ops | CI |

→ [ADR-0012](../01-architecture/adr/0012-postgres-roles-and-least-privilege.md)

---

## 8. Secrets

| # | Item | Owner | V |
|---|---|---|---|
| 8.1 | systemd `EnvironmentFile`, mode `0640`, owner `root:fusion` | ops | Ops |
| 8.2 | Key material via `LoadCredential=`, never in `/proc/<pid>/environ` | ops | Review |
| 8.3 | `gitleaks` + `detect-secrets` on every PR | platform-lead | CI |
| 8.4 | No secret in a `VITE_*` variable — everything so prefixed is compiled into the public bundle | frontend-lead | CI |
| 8.5 | `SECRET_KEY` has **no default**; startup rejects known dev values | platform-lead | Startup |
| 8.6 | Rotation runbooks, tested: `DJANGO_SECRET_KEY` annually · IAM signing key quarterly · DB passwords annually · `FERNET_KEY` (the one non-zero-downtime rotation) | ops | Ops |

---

## 9. Dependencies and supply chain

| # | Item | Owner | V |
|---|---|---|---|
| 9.1 | `uv.lock` and `pnpm-lock.yaml` committed; CI installs `--frozen` | platform-lead | CI |
| 9.2 | `pip-audit` + `pnpm audit --prod`, weekly and on PR | platform-lead | CI |
| 9.3 | CodeQL (python + javascript) | platform-lead | CI |
| 9.4 | Trivy on images | ops | CI |
| 9.5 | Dependabot grouped weekly; a security advisory is triaged within 7 days | platform-lead | Ops |
| 9.6 | `bandit -r -ll` | platform-lead | CI |

---

## 10. Operational

| # | Item | Owner | V |
|---|---|---|---|
| 10.1 | systemd hardening: `NoNewPrivileges` · `PrivateTmp` · `ProtectSystem=strict` · `ProtectHome` · `MemoryMax` | ops | Review |
| 10.2 | Services on unix sockets, not TCP ports; only nginx is exposed | ops | Ops |
| 10.3 | The internal snapshot endpoint bound to `127.0.0.1`, never proxied by nginx | ops | Test |
| 10.4 | Off-box nightly backups; WAL archiving; **a restore actually performed and timed** in Phase 1 | ops | Ops |
| 10.5 | Alerts: `iam_refresh_reuse_detected_total` > 0 · login 5xx > 1% · `reconcile_drift_total` > 0 | ops | Ops |
| 10.6 | Weekly privileged-access review: `is_dangerous` usage, `is_superadmin` requests, PII exports | security-owner | Ops |
| 10.7 | `manage.py check --deploy --fail-level WARNING` clean on every service | platform-lead | CI |

---

## Review checklist

Reject a change that:

- adds an endpoint without explicit `permission_classes`
- fetches an object then checks ownership, instead of filtering the queryset
- returns 403 where 404 would avoid leaking existence
- adds `fields = "__all__"`
- interpolates into SQL, or uses `raw()` outside `core/db/sql/`
- adds a `SensitivePIIField` to a serializer without an audit path
- adds a client-side permission check with no server counterpart
- catches `Exception` and continues
- logs a request body, a token, or a header block
- adds a `VITE_*` variable containing anything secret
- writes to the ERP from the platform
- reads `Student.cpi` or `academic_information.Spi` (both dead — CI greps for this)
- recomputes CPI ([NG5](../00-overview/vision-and-scope.md#non-goals))

## Cadence

| Activity | Frequency |
|---|---|
| Automated scans (`gitleaks`, `pip-audit`, CodeQL, Trivy) | every PR + weekly |
| Privileged-access review | weekly |
| Dependency triage | weekly |
| This document reviewed against reality | quarterly |
| Threat model revisited | quarterly, and on any new external integration |
| Restore drill | quarterly |
| Signing-key rotation | quarterly |
| Penetration test | before the first full placement season, then annually |
