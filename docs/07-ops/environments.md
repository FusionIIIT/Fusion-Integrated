---
owner: ops
status: authoritative
last-reviewed: 2026-08-01
---

# Environments

Four: **local**, **test** (CI), **staging**, **production**. The differences are deliberate and listed here so
nobody has to infer them from a settings file.

---

## Matrix

| | local | test (CI) | staging | production |
|---|---|---|---|---|
| Settings module | `config.settings.dev` | `config.settings.test` | `.staging` | `.prod` |
| `DEBUG` | `True` | `False` | `False` | `False` |
| Cookie `Secure` | `False` | `False` | `True` | `True` |
| Host | docker-compose | GitHub runner | `fusion-vm` (own DBs) | `fusion-vm` |
| Postgres | container 16 | service container 16 | same cluster, own DBs | own disk |
| PgBouncer | no | no | yes | yes |
| Redis | 2 containers | 1 container, 2 DBs | 2 instances | 2 instances |
| Celery | **eager** | **eager** | workers | workers |
| Email | console | in-memory | file | institute SMTP |
| ClamAV | skipped | mocked | real | real |
| Sentry | off | off | on | on |
| `NPLUSONE_RAISE` | **`True`** | **`True`** | `False` | `False` |
| Throttling | 100× limits | **disabled** | real | real |
| ERP data | small anonymized fixture | factories | **anonymized snapshot** | real |
| Feature flags | all on | per test | mirrors production | see the runbook |

Two rows deserve explanation.

**`NPLUSONE_RAISE=True` in local *and* test.** A lazy relation load fails the build. Combined with the
per-endpoint `django_assert_max_num_queries` budgets, this is what stops the legacy pattern of a list view
issuing one query per row.

**Throttling disabled in test, not merely raised.** A suite that logs in repeatedly would otherwise trip the
5/min login throttle and fail intermittently — which teaches everyone to rerun CI instead of reading it.
Throttles get their own dedicated tests instead.

---

## Local

```bash
git clone <repo> && cd Fusion-Integrated
cp .env.example .env          # committed, no real secrets
make up                       # postgres, 2× redis, mailhog
make migrate seed
make dev                      # platform :8000, iam :8002
```

Frontend:

```bash
cd ../fusion-frontend && pnpm install && pnpm dev     # :5173, proxies /api
```

Requirements: Docker, Python 3.12, `uv`, Node 20, pnpm 9.

`.env.example` documents every variable with a comment and a safe placeholder. A CI check compares its keys
against the variables `base.py` actually reads, so **a new setting cannot be added without documenting it**.

### Seed data

`make seed` builds factory data plus a small anonymized ERP fixture. The academic fixture deliberately includes
**the awkward grade cases**, because they are the ones that break CPI handling:

| Student | Case |
|---|---|
| `22bcs001` | ordinary transcript, CPI 8.10, Sem 5 declared |
| `22bcs002` | an **`S`** grade — earns credit, excluded from the average |
| `22bcs003` | an **`X`** grade — excluded from credits *and* units |
| `22bcs004` | an **`F`** grade — **2.0 points and its credit counted** |
| `22bcs005` | a backlog retake — dedup keeps the best attempt |
| `22bcs006` | a `course_replacement` / swayam substitution |
| `22bcs007` | a **Summer** semester (stored under an even `semester`) |
| `22bcs008` | **no declared result** — must be ineligible, not "CPI 0.0" |

Plus placement fixtures: an active year with each `pool_after_offer` policy, companies across tiers, published
and draft postings, applications in every state, and an already-placed student for policy testing.

A developer meets these cases on day one rather than in production
([academic-snapshot-integration.md](../04-placement/academic-snapshot-integration.md#1-what-the-erp-actually-does)).

---

## Test (CI)

`postgres:16` and `redis:7` service containers. A **fresh database per run**; no shared state.

```yaml
pytest -n auto --cov --cov-fail-under=75
```

Two things about the database configuration matter:

```python
# config/settings/test.py
DATABASES["default"]["USER"] = "platform_app"       # NOT superuser
```

**Tests run as the real application role.** Running as superuser would make every missing Postgres grant
invisible until production, and would make the immutability tests
(`UPDATE academics_resultsnapshot` → `InsufficientPrivilege`) impossible to write. A separate `CREATEDB` role
is used for `--create-db`.

`ops/db/roles.sql` runs before the suite, so grants under test match production.

Full gate list: [testing-strategy.md](../06-crosscutting/testing-strategy.md#ci-gates).

---

## Staging

Same VM, separate databases: `fusion_system_db_staging`, `fusion_nonacad_staging`,
`fusion_newui_prod_staging`. Served at `/staging/app/`.

Staging exists for exactly three things that cannot be done anywhere else:

1. **The legacy-contract assertion.** `test_iam_me_matches_legacy_me` runs against staging with a real
   ERP-shaped dataset — this is the Phase 3 gate
   ([auth-migration-runbook.md](../02-iam/auth-migration-runbook.md)).
2. **Alert rehearsal.** Each of the six alerts is fired against a synthetic condition, and its runbook is
   walked. An alert whose runbook has never been executed is not a control.
3. **Migration timing.** How long a migration takes on production-sized data, before it runs on production.

### The anonymized snapshot

Refreshed weekly by `ops/db/refresh_staging.sh`: `pg_dump` production → restore into staging → run
`ops/db/anonymize.sql`.

```sql
-- ops/db/anonymize.sql (extract)
UPDATE auth_user SET first_name = 'Test', last_name = 'User' || id,
                     email = 'user' || id || '@example.invalid';
UPDATE globals_extrainfo SET phone_no = 9999999999, address = 'Redacted',
                             date_of_birth = make_date(EXTRACT(YEAR FROM date_of_birth)::int, 1, 1);
-- PRESERVED deliberately: grades, CPI inputs, batch, discipline, placement outcomes.
```

Names, emails, phones and addresses are replaced; **CPI inputs, batch, discipline and placement outcomes are
preserved**, because those are exactly what makes staging useful for testing eligibility rules.

**A production dump is never copied to a laptop.** `make seed` exists so nobody has a reason to
([data-retention-and-privacy.md](../06-crosscutting/data-retention-and-privacy.md)).

Staging holds anonymized-but-real-shaped data, so it is access-restricted like production. It is not a
sandbox.

---

## Production

`fusion-vm`, as in [deployment-topology.md](deployment-topology.md). Deploys on a `v*` tag, atomic symlink swap,
automated rollback on smoke-test failure.

Feature flags per [settings-and-configuration.md](../03-platform/settings-and-configuration.md#feature-flags),
with rollbacks in [auth-migration-runbook.md](../02-iam/auth-migration-runbook.md). Flags are environment
variables, not database rows — flipping one is a config change plus a restart, auditable in the deploy log and
impossible to do by accident from an admin screen.

---

## Promotion

```
local ──PR──► test (CI) ──merge to main──► staging (auto) ──tag v*──► production
```

Rules:

- Nothing reaches staging without green CI.
- Nothing reaches production without at least **24 hours** on staging, and longer for anything touching auth.
- A migration is timed on staging before it runs on production.
- Expand → migrate → contract across **two** releases; never a destructive migration alongside the code that
  stops using the column.
- Auth-touching changes go out behind a flag defaulting to off.

---

## Access

| Environment | Who | How |
|---|---|---|
| local | any developer | own machine |
| test | CI only | GitHub Actions |
| staging | developers + ops | SSH via the institute network; **restricted, real-shaped data** |
| production | ops only | SSH via the institute network, key-based, logged |

Production database access is via `psql` on the host as a named role — never a shared superuser, never a
GUI client over a tunnel.

---

## Cleanup

| | Frequency |
|---|---|
| CI databases | destroyed per run |
| Staging refresh (re-anonymized) | weekly |
| Old releases | keep 5 (`prune.sh`) |
| Docker volumes, local | `make clean` |
| `outbox_event`, sessions, login attempts | beat tasks per [data-retention-and-privacy.md](../06-crosscutting/data-retention-and-privacy.md) |

---

## Verification

- A fresh clone reaches a working local stack with `make up && make migrate seed && make dev` — tested on a
  machine that has never run it.
- `.env.example` keys match what `base.py` reads (CI check).
- CI connects as `platform_app`; the immutability tests pass, proving grants are in force.
- Staging contains no recognizable name, email, phone or address after refresh; CPI and placement outcomes
  survive.
- All six alerts fire and resolve against staging, at least once per quarter.
- A production-sized migration's duration is recorded before it runs on production.
