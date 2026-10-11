---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
---

# Settings & Configuration

Twelve-factor, `django-environ`, **no secret ever committed**. The reference for what this is fixing:
the legacy monolith hardcodes its `SECRET_KEY`, its database password (in four files including
`README.md:272`), and its Google OAuth client secret — and ships `DEBUG = True` in `production.py`.

---

## Layout

```
config/settings/
├── base.py        everything shared. Reads env. No secret has a usable default.
├── dev.py         DEBUG=True, debug-toolbar, relaxed cookies, console email
├── test.py        in-memory/eager where safe, NPLUSONE_RAISE=True, deterministic
├── staging.py     production-shaped, separate data, verbose logging
└── prod.py        strict. Fails to start on a missing secret.
```

`DJANGO_SETTINGS_MODULE` is set explicitly by systemd and `docker-compose`. There is **no default** —
`manage.py` requires it. The legacy monolith defaults to `Fusion.settings.development` in both `manage.py`
and `wsgi.py`, which is how a development setting reaches production.

```python
# config/settings/base.py
import environ

env = environ.Env()
environ.Env.read_env(env.str("ENV_FILE", default=".env"))   # dev convenience only

SECRET_KEY = env("DJANGO_SECRET_KEY")        # NO default — deliberately crashes if absent
DEBUG = False                                # overridden only in dev.py
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
```

`SECRET_KEY` having no default is the point. A fallback default is how a development key reaches
production and stays there.

---

## Environment variables

### Core

| Variable | Required | Default | Notes |
|---|---|---|---|
| `DJANGO_SETTINGS_MODULE` | ✔ | — | no fallback |
| `DJANGO_SECRET_KEY` | ✔ | — | ≥50 chars; a startup assertion rejects known dev values |
| `ALLOWED_HOSTS` | ✔ | — | comma-separated; `*` rejected when `DEBUG=False` |
| `CSRF_TRUSTED_ORIGINS` | ✔ | — | full scheme+host |
| `CORS_ALLOWED_ORIGINS` | ✔ | — | explicit list. **`CORS_ORIGIN_ALLOW_ALL` does not exist in this codebase.** |

### Databases

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | ✔ | `postgres://platform_app@pgbouncer:6432/fusion_nonacad` |
| `ERP_DATABASE_URL` | ✔ | role **must** be `platform_erp_ro` — asserted at startup |
| `PGBOUNCER` | | `1` in prod. Forces the two settings below to be checked. |

```python
DATABASES = {"default": env.db("DATABASE_URL"), "erp": env.db("ERP_DATABASE_URL")}
DATABASE_ROUTERS = ["core.db.routers.ErpReadOnlyRouter"]

CONN_MAX_AGE = 0                        # MANDATORY under transaction pooling
DISABLE_SERVER_SIDE_CURSORS = True      # MANDATORY under transaction pooling
```

**These two are not tuning.** PgBouncer in transaction mode hands a different backend connection to each
transaction. Persistent connections (`CONN_MAX_AGE > 0`) or server-side cursors let one request inherit
another's session state — a silent data-correctness failure, not an error. A startup assertion fails the
boot if either is wrong while `PGBOUNCER=1`.

PgBouncer: `pool_mode=transaction`, `default_pool_size=25`, `max_client_conn=500`.

### Redis — two instances, deliberately

| Variable | Instance | Eviction | Why |
|---|---|---|---|
| `REDIS_CACHE_URL` | `:6379` | `allkeys-lru` | Losing a cache entry is fine — that is what a cache is |
| `REDIS_BROKER_URL` | `:6380` | **`noeviction`** | **An LRU-evicting broker silently drops queued Celery tasks.** No error, no trace. That is the bug that loses a season's offer notifications. |

A startup assertion reads `CONFIG GET maxmemory-policy` on the broker and refuses to start if it is not
`noeviction`.

```python
CACHES = {"default": env.cache("REDIS_CACHE_URL")}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"   # not the database
CELERY_BROKER_URL = env("REDIS_BROKER_URL")
```

Sessions in the cache, not the database. The legacy monolith uses database-backed sessions with
`SESSION_SAVE_EVERY_REQUEST = True` — a write per request.

### IAM integration

| Variable | Required | Notes |
|---|---|---|
| `IAM_ISSUER` | ✔ | must match the `iss` claim exactly |
| `IAM_AUDIENCE` | ✔ | this service's own audience; a token not naming it is rejected |
| `IAM_JWKS_URL` | ✔ | cached 10 min in Redis, and by nginx |
| `IAM_INTERNAL_BASE_URL` | ✔ | for service-to-service calls |
| `IAM_SERVICE_TOKEN_KEY_PATH` | ✔ | via systemd `LoadCredential` |

IAM-only: `IAM_SIGNING_KEY_PATH`, `IAM_SIGNING_KID`, `IAM_PREVIOUS_KID` (both live during rollover),
`IAM_ACCESS_TTL_SECONDS` (600), `IAM_REFRESH_SLIDING_SECONDS` (43200),
`IAM_REFRESH_ABSOLUTE_SECONDS` (604800), `IAM_IDLE_TIMEOUT_SECONDS` (1800),
`FERNET_KEY` (encrypts TOTP secrets), `IAM_IS_ROLE_WRITER`, `IAM_MINT_LEGACY_TOKEN`.

### Academic integration

| Variable | Default | Notes |
|---|---|---|
| `ERP_SNAPSHOT_URL` | — | `http://127.0.0.1:8000/api/examination/internal/academic-snapshot/` |
| `ERP_SNAPSHOT_CHUNK_SIZE` | `50` | Raising this is how you overload the ERP during a declaration |
| `ERP_SNAPSHOT_CHUNK_DELAY_SECONDS` | `2` | The gap that keeps the ERP's connection pool comfortable |
| `ACADEMICS_VERIFY_SAMPLE_PCT` | `2` | Nightly byte-equality re-pull sample |

### Files, mail, observability

`MEDIA_ROOT` (`/var/lib/fusion/platform/media`), `PROTECTED_MEDIA_URL` (`/_protected/`, the
`X-Accel-Redirect` target), `MAX_UPLOAD_BYTES_RESUME` (2 MB), `MAX_UPLOAD_BYTES_DOCUMENT` (5 MB),
`CLAMAV_HOST`/`PORT`, `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `EMAIL_DAILY_CAP_PER_USER` (20),
`SENTRY_DSN` (per service), `SENTRY_TRACES_SAMPLE_RATE` (0.1), `LOG_LEVEL`, `LOG_FORMAT` (`json`).

### Feature flags

| Flag | Default | Purpose |
|---|---|---|
| `IAM_JWT_AUTH_ENABLED` | `false` | legacy/console accept IAM cookies |
| `IAM_LOGIN_ENABLED` | `false` | shell login goes to IAM |
| `IAM_IS_ROLE_WRITER` | `false` | projector writes the `globals_*` tables |
| `IAM_MINT_LEGACY_TOKEN` | `true` | also mint a legacy DRF token at login — the safety net |
| `LEGACY_LOGIN_ENABLED` | `true` | legacy `/api/auth/login/` still works |
| `ACADEMICS_INGEST_ENABLED` | `false` | the declaration pull |

Flags are **environment variables, not database rows**, so flipping one is a config change plus a restart —
auditable in the deploy log, and impossible to do accidentally from an admin UI. Every flag has a documented
rollback in [auth-migration-runbook.md](../02-iam/auth-migration-runbook.md).

Flags are for **migration**, not for product configuration. A flag with no removal date is technical debt;
each one above has a phase in which it is deleted.

---

## Secrets

**Delivery.** systemd `EnvironmentFile=/etc/fusion/platform.env`, mode `0640`, owner `root:fusion`. Key
material (signing keys, Fernet key) uses `LoadCredential=` so it is never in an env var and never in
`/proc/<pid>/environ`.

**Never** in: the repository, a Docker image, a build log, a CI variable that is echoed, a Sentry event, or a
log line. `gitleaks` and `detect-secrets` run in CI on every PR.

**Rotation** — documented, tested procedures in
[rotate-signing-key.md](../07-ops/runbooks/rotate-signing-key.md): `DJANGO_SECRET_KEY` (annually),
IAM signing key (quarterly, zero-downtime via dual `kid`), database passwords (annually), `FERNET_KEY`
(requires re-encrypting TOTP secrets — the one rotation that is not zero-downtime).

---

## Startup assertions

`config/checks.py`, registered as Django system checks, run on every boot. **A misconfigured deployment fails
immediately and loudly rather than at 3 a.m. on the first bad query.**

```python
@register(Tags.security, deploy=True)
def check_production_config(app_configs, **kwargs):
    errors = []
    if not settings.DEBUG:
        if "*" in settings.ALLOWED_HOSTS:
            errors.append(Error("ALLOWED_HOSTS contains '*'", id="fusion.E001"))
        if not settings.SESSION_COOKIE_SECURE or not settings.CSRF_COOKIE_SECURE:
            errors.append(Error("Cookies must be Secure in production", id="fusion.E002"))
        if settings.SECRET_KEY in KNOWN_DEV_KEYS:
            errors.append(Error("SECRET_KEY is a known development value", id="fusion.E003"))
    if env.bool("PGBOUNCER", default=False):
        if settings.CONN_MAX_AGE != 0:
            errors.append(Error("CONN_MAX_AGE must be 0 under PgBouncer", id="fusion.E010"))
        if not settings.DISABLE_SERVER_SIDE_CURSORS:
            errors.append(Error("Server-side cursors must be disabled under PgBouncer",
                                id="fusion.E011"))
    if _broker_maxmemory_policy() != "noeviction":
        errors.append(Error("Celery broker Redis must be noeviction", id="fusion.E020"))
    if _erp_role() != "platform_erp_ro":
        errors.append(Error("ERP connection must use the read-only role", id="fusion.E030"))
    if _effective_search_path()[0] != EXPECTED_SCHEMA:
        errors.append(Error("search_path is wrong; tables would land in the wrong schema",
                            id="fusion.E031"))
    return errors
```

CI runs `manage.py check --deploy --fail-level WARNING` against a production-shaped settings module, so
these fire before a deploy rather than during one.

---

## What differs per environment

| | dev | test | staging | prod |
|---|---|---|---|---|
| `DEBUG` | `True` | `False` | `False` | `False` |
| Cookie `Secure` | `False` | `False` | `True` | `True` |
| Celery | eager | eager | workers | workers |
| Email | console | in-memory | file | SMTP relay |
| ClamAV | skipped | mocked | real | real |
| `NPLUSONE_RAISE` | `True` | **`True`** | `False` | `False` |
| Throttling | 100× | disabled | real | real |
| ERP database | local dump | fixtures | anonymized snapshot | production |
| Sentry | off | off | on | on |

`NPLUSONE_RAISE=True` in dev **and** test is deliberate: an N+1 fails the build rather than being noticed in
production. Combined with the per-endpoint `django_assert_max_num_queries` budgets, this is what prevents
the legacy pattern of a list view issuing one query per row.

Throttling **disabled** in test, not merely raised — otherwise a test suite that logs in repeatedly trips
the 5/min login throttle and fails intermittently, which teaches everyone to distrust the suite.

---

## Local development

```bash
cp .env.example .env      # committed, contains NO real secrets
make up                   # postgres, pgbouncer, 2× redis, clamav
make migrate seed
make dev
```

`.env.example` documents every variable with a comment and a safe placeholder. It is the de facto
configuration reference and is kept in step by a CI check that compares its keys against the variables
`base.py` actually reads — so a new setting cannot be added without documenting it.

`make seed` loads factory-generated data plus a small anonymized ERP fixture: a few batches, students with
**declared** results covering the awkward grade cases (`S`-credit, `X`-exclusion, an `F`, a
`course_replacement` substitution, a Summer semester). Those cases exist in the seed because they are the
ones that break CPI handling, and a developer should meet them on day one rather than in production.
