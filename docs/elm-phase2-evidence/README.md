# ELM Phase 2 — evidence

**Students:** Nikhil (24BCS171), Nehant (24BCS167)

## Provenance

| Stage | Tool | Where |
|---|---|---|
| Initial ELM generation (PR #102) | DeepSeek-Coder 6.7B via Ollama (Q4_K_M), local | commit `429f92d` |

The refinement was **not** produced by the local model. It is labelled here so the
pilot data stays accurate.

## What was broken in PR #102

1. `modules/elm/apps.py`: `default_auto_field` typo and `name = "elm"`, so Django would not start.
2. No `migrations/` package, so no tables.
3. Models used `ForeignKey(User)`. This platform has no user table (ADR-0013).
4. Any signed-in user could approve or reject any request. No state checks.
5. No business rules: day counting, balance, overlap, eligibility.
6. Frontend: wrong API URL, field names that did not match the backend, an `onChanget` typo,
   leave types that do not exist in the spec, raw axios, and no route or nav entry.
7. No tests.

## Verification (run locally, macOS, Python 3.12, Node 26.10.0)

| Check | Result |
|---|---|
| `python manage.py check` | no issues |
| `makemigrations --check` | no changes |
| `pytest modules/elm modules/accesscontrol` | 73 passed (52 ELM: 39 domain + 13 API) |
| `ruff check .` | all checks passed |
| `lint-imports` | 5 contracts kept (incl. new `elm-layers`, pure `elm.domain`) |
| `ops/checks/no_cross_module_fk.py`, `nav_matches_routes.py` | pass |
| `permission_manifest --check` | matches the registries |
| `spectacular --fail-on-warn` | schema regenerated, 0 warnings |
| `npm run typecheck`, `npm test`, `npm run build` | pass (35 client tests) |

**Caveat:** no PostgreSQL was available locally. The pytest run used SQLite with
`--nomigrations`, so `select_for_update` locking and the migration itself were not
exercised against Postgres. CI should run the suite on Postgres.
