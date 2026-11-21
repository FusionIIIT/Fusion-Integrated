# AGENTS.md — Fusion-Integrated

Django 5.2 + React 18 (Vite) modular platform. Identity/RBAC/directory come from external IAM (`Fusion_System_Administrator`); this repo holds no user table. Python 3.12, uv-managed venv at `.venv`.

## Commands

- Setup: `make install` (uv venv + deps), `make up` (postgres + redis), `cp .env.example .env`, `make migrate seed`
- Dev server: `make dev` → http://127.0.0.1:8002
- Client: `cd client && npm install && npm run dev` (:5173, proxies /api to :8002)
- Tests (backend): `make test` (`.venv/bin/python -m pytest`); single file: `.venv/bin/pytest modules/<module>/tests/test_x.py`; filter: `-k name`
- Tests (client): `cd client && npm test` (vitest); typecheck: `npm run typecheck`; build: `npm run build`
- Full gate: `make check` (backend) + `make check-client` (frontend). Run both before claiming done.
- Generate: `make schema` (OpenAPI), `make permissions` (permission manifest), `make module-structure`.

Env: `.env` is auto-loaded by `config/settings/base.py` via `os.environ.setdefault` — real env vars win. Tests use `config.settings.test` (in-memory fake IAM, no network). `DJANGO_SETTINGS_MODULE` is pinned in pytest config; don't override casually.

## Architecture

- Backend modules are independent Django apps under `modules/`: `directory`, `accesscontrol`, `placement`. Each owns its tables + migrations + `contracts.py` (the only cross-module import surface).
- `core/` is a leaf — must not import `modules` or `fusion_auth`.
- `fusion_auth/` = IAM client, `Principal`, auth, permission gates.
- Module registration: add to `DOMAIN_MODULES` in `config/settings/base.py`, write `registry.py`, run `make seed`. No central menu/boolean column.
- Client routes are built only for server-granted modules; ungranted module deep-links hit NotFound.

## Hard boundaries (CI-enforced)

- Modules reach each other ONLY via `contracts.py` — never internal models/services/selectors/api/domain.
- No FK crosses a module boundary (`ops/checks/no_cross_module_fk.py`).
- `domain/` may not import Django/DRF/Celery.
- Cross-module getters must be PLURAL (`get_*s(user_ids)`), never singular.
- `core/` may not import `modules`/`fusion_auth`.

## Conventions

- Authorization: every view uses `permission_classes = [HasModuleGrant(...), HasPermission(...)]`; default deny. Ownership filtering happens in selectors (queryset filter), yielding 404 not 403.
- Sidebar is server-driven via `GET /api/v1/me`; client does no filtering.
- Domain tests are pure Python (no DB) — keep them fast; don't add Django imports to `domain/`.
- IAM is never contacted in tests: `conftest.py` swaps an in-memory `FakeIam`. If adding an IAM client method, add it to `FakeIam` too.
- Recruiter passwords use argon2 (strongest KDF); institute users never have a local password.
- Migrations: `make migrate`; CI checks `makemigrations --check --dry-run`. Don't edit migrations by hand unless regenerating.
- OpenAPI schema is committed (`openapi/fusion-integrated.v1.yaml`); regenerate with `make schema` when endpoints change.
- Plural contracts getter naming enforced by `contracts_are_plural.py`.

## Gotchas

- Redis is split: cache on :6379/1, broker on :6380/0 (separate instances). Prod requires both; LocMem/memory broker silently breaks throttling/notifications.
- `DB_CONN_MAX_AGE=0` must stay 0 if PgBouncer transaction mode is ever used.
- Client uses Mantine 7.13.4 pinned to match sysadmin client; don't bump alone.
- `devtools` is dev/test only (seed fixtures) — never in production `INSTALLED_APPS`.
- `.env` loading uses `setdefault`; exporting vars in shell overrides file.
- On Windows, use `.venv/Scripts/python` (not `.venv/bin/python`) and PowerShell; Makefile paths assume Unix. Prefer running pytest/vitest directly.

## Verification before done

Backend: `ruff check .`, `lint-imports`, `python ops/checks/no_cross_module_fk.py`, `python ops/checks/contracts_are_plural.py`, `python ops/checks/nav_matches_routes.py`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py permission_manifest --check`, schema-check, then pytest.
Frontend: `npm run typecheck && npm test && npm run build`.
