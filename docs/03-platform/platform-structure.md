---
owner: platform-lead
status: authoritative
last-reviewed: 2026-08-01
enforced-by: .importlinter, ops/checks/no_cross_module_fk.py, ruff, mypy — all in CI
---

# Platform Structure

`fusion-platform` is a modular monolith ([ADR-0001](../01-architecture/adr/0001-modular-monolith-over-microservices.md)).
This document defines the layout, the layering rules, and the CI checks that make those rules real.

**The rules only hold because CI holds them.** Without `import-linter` and the FK check, this degenerates
into the 34-app tangle we are replacing — which had no boundaries, one index across 424 models, and modules
freely importing each other.

---

## Repository layout

```
Fusion-Integrated/
├── pyproject.toml  uv.lock  Makefile  docker-compose.yml
├── .importlinter                       ← the boundary contracts
├── ruff.toml  mypy.ini  pytest.ini
├── docs/
├── ops/
│   ├── db/roles.sql                    ← Postgres roles, idempotent
│   ├── checks/no_cross_module_fk.py
│   ├── nginx/  systemd/  deploy/  runbooks/
├── packages/
│   ├── fusion_common/                  logging · request-id · error envelope · pagination
│   ├── fusion_contracts/               pydantic event schemas — the only shared vocabulary
│   └── fusion_auth/                    IamJWTAuthentication · HasPermission · HasModuleGrant · Principal
├── services/
│   ├── iam/                            see 02-iam/
│   └── platform/
│       ├── manage.py
│       ├── config/
│       │   ├── settings/{base,dev,test,staging,prod}.py
│       │   ├── urls.py  celery.py  wsgi.py  asgi.py
│       ├── core/                       ← shared kernel; admission is deliberately hard
│       │   ├── db/{fields.py, mixins.py, functions.py, introspection.py}
│       │   ├── api/{pagination.py, exceptions.py, filters.py, schema.py,
│       │   │        throttling.py, defaults.py, hydrate.py, idempotency.py}
│       │   ├── events/{outbox.py, inbox.py, publisher.py, registry.py}
│       │   ├── files/{validators.py, storage.py, scanning.py}
│       │   ├── rules/{engine.py, ast.py}
│       │   └── observability/{logging.py, middleware.py, metrics.py}
│       ├── modules/
│       │   ├── directory/
│       │   ├── academics/
│       │   ├── placement/
│       │   ├── hr/
│       │   └── leave/
│       └── openapi/platform.v1.yaml    ← committed; CI diffs it
└── .github/workflows/{backend.yml, security.yml, deploy.yml}
```

---

## Module anatomy

Every module has the same shape. No exceptions, including small ones — a module that starts "too small for
layers" is the one that grows a 900-line `views.py`.

```
modules/placement/
├── __init__.py
├── apps.py                     PlacementConfig — registers event handlers in ready()
├── contracts.py                ← THE ONLY public surface to other modules
├── permissions.py              rbac_permission seed data for this module
├── registry.py                 registry_module + registry_nav_item seed data
├── events.py                   topics produced · handlers consumed
├── tasks.py                    Celery. Ids only in arguments.
├── models.py                   Django ORM. No business logic.
├── admin.py                    Django admin, staff-only, read-mostly
├── migrations/
├── domain/                     ← PURE PYTHON. Importing Django here fails CI.
│   ├── entities.py             frozen dataclasses / pydantic DTOs
│   ├── state_machine.py        the transition table
│   ├── rules/
│   │   ├── eligibility.py
│   │   └── offer_policy.py     can_accept() — a pure function
│   └── errors.py               domain exceptions, no HTTP awareness
├── selectors/                  ← ALL reads
│   ├── postings.py
│   ├── applications.py
│   └── offers.py
├── services/                   ← ALL writes. Transaction boundaries. Emits events.
│   ├── postings.py
│   ├── applications.py
│   └── offers.py
├── api/                        ← thin
│   ├── serializers/{read.py, write.py}
│   ├── views/{postings.py, applications.py, offers.py}
│   ├── filters.py
│   ├── permissions.py
│   └── urls.py
└── tests/
    ├── factories.py            the only way tests create data
    ├── test_domain.py          90% coverage target — pure functions, no excuse
    ├── test_services.py
    ├── test_selectors.py
    ├── test_api.py
    └── test_events.py
```

### The layers, and what each may not do

| Layer | May import | May **not** | Coverage |
|---|---|---|---|
| `domain/` | stdlib, pydantic, `fusion_contracts` | **Django, models, selectors, services, HTTP** | 90% |
| `models.py` | Django, `core.db` | selectors, services, api, other modules' models | — |
| `selectors/` | own models, `core`, other modules' `contracts` | services, api, Django's `request` | 85% |
| `services/` | own models, own selectors, own domain, `core`, other modules' `contracts` | api, HTTP status codes, serializers | 85% |
| `api/` | own selectors, own services, `core.api`, `fusion_auth` | own models directly, other modules' anything | 80% |
| `contracts.py` | own selectors, own domain DTOs | own services (a contract never mutates), api | 100% of functions |

Four rules with real teeth:

**1. `domain/` cannot import Django.** This is what keeps rules unit-testable at 90% with no database. The
offer-acceptance policy is a pure function of `(policy, state, offer)`, so its 12 branches are 12 fast tests
rather than 12 fixture-heavy integration tests.

**2. `api/` never touches models directly.** Every read goes through a selector, every write through a
service. This is what keeps ownership filtering in one place per module, and it is why a foreign id yields a
404 without a special case in the view.

**3. `services/` knows nothing about HTTP.** A service raises `OfferNotAcceptable`, not
`ValidationError(422)`. The mapping lives in `core/api/exceptions.py`, so the same service is callable from a
Celery task, a management command or a test.

**4. `contracts.py` is read-only and plural.** It never mutates. If module A needs module B to *change*
something, that is an event, not a contract call.

---

## Boundaries in CI

### `.importlinter`

```ini
[importlinter]
root_packages = config, core, modules, packages

[importlinter:contract:modules-are-independent]
name = Modules may only touch each other via contracts
type = forbidden
source_modules =
    modules.placement
    modules.hr
    modules.leave
    modules.academics
    modules.directory
forbidden_modules =
    modules.placement.models
    modules.placement.services
    modules.placement.selectors
    modules.placement.api
    modules.placement.domain
    modules.hr.models
    modules.hr.services
    ...
allow_indirect_imports = false
# contracts.py is deliberately absent from forbidden_modules — it is the door.

[importlinter:contract:domain-is-pure]
name = domain/ must not import Django
type = forbidden
source_modules = modules.*.domain
forbidden_modules = django, rest_framework, celery

[importlinter:contract:layers]
name = Layering within a module
type = layers
layers =
    modules.placement.api
    modules.placement.services
    modules.placement.selectors
    modules.placement.models
    modules.placement.domain

[importlinter:contract:erp-shadow-is-contained]
name = ERP shadow models live only in modules/academics/erp
type = forbidden
source_modules = modules.placement, modules.hr, modules.leave, modules.directory, core
forbidden_modules = modules.academics.erp

[importlinter:contract:core-is-a-leaf]
name = core/ must not import any module
type = forbidden
source_modules = core
forbidden_modules = modules
```

### `ops/checks/no_cross_module_fk.py`

```python
def main() -> int:
    """No ForeignKey/OneToOne/ManyToMany may target another module's model."""
    violations = []
    for model in apps.get_models():
        src = model._meta.app_label
        for field in model._meta.get_fields():
            if not field.is_relation or not field.related_model:
                continue
            dst = field.related_model._meta.app_label
            if dst != src and dst not in ALLOWED_TARGETS:      # {"core", "contenttypes"}
                violations.append(f"{src}.{model.__name__}.{field.name} -> {dst}")
    for v in violations:
        print(f"cross-module FK: {v}", file=sys.stderr)
    return 1 if violations else 0
```

→ [ADR-0013](../01-architecture/adr/0013-no-cross-module-foreign-keys.md)

### Additional CI checks

| Check | Fails when |
|---|---|
| `makemigrations --check --dry-run` | models and migrations disagree |
| `django-migration-linter` | an unsafe operation (`NOT NULL` without a default, a rename, a drop) |
| `spectacular --validate` + `git diff --exit-code openapi/` | the committed schema drifts from the code |
| `module_registry_parity` | `registry_module.code` set ≠ frontend `MODULE_REGISTRY` keys |
| `legacy_column_parity` | `registry_module.legacy_column_name` not in the ERP's live columns (hazard H2) |
| `permission_naming` | a permission code fails the three-segment regex or names an unknown module |
| `export_permission_catalog` diff | [permission-catalog.md](../02-iam/permission-catalog.md) is stale |
| `grep` guard | `Student.cpi` or the `Spi` model referenced anywhere |
| `grep` guard | `raw()` / `extra()` / `RawSQL` outside `core/db/sql/` |
| `contracts_are_plural` | a `contracts.py` function takes a singular id where a sequence is expected |
| `nplusone` with `NPLUSONE_RAISE=True` | a lazy relation load in any test |

---

## Cross-module reads

```python
# modules/placement/selectors/applications.py
from modules.directory import contracts as directory
from modules.academics import contracts as academics

def applications_for_posting(posting_id: int) -> list[ApplicationRow]:
    apps = list(Application.objects.filter(posting_id=posting_id)
                                   .select_related("posting", "resume"))
    ids = [a.user_id for a in apps]
    users     = directory.get_users(ids)       # ONE call
    standings = academics.get_standings(ids)   # ONE call
    return [ApplicationRow(app=a, user=users.get(a.user_id),
                           standing=standings.get(a.user_id)) for a in apps]
```

Three queries total, regardless of how many applications. **Plural-by-signature is what makes the N+1
impossible to write** — there is no `get_user(id)` to call in a loop, because it does not exist.

```python
# modules/directory/contracts.py
def get_users(user_ids: Sequence[int]) -> dict[int, UserRefDTO]:
    """Batched. Missing ids are simply absent from the mapping — a visible case, not silent None."""
```

Returning a mapping rather than a list means a missing id is a `KeyError`-shaped, testable case rather than
a silent `None` that surfaces three layers up.

---

## `core/` — the shared kernel

Admission is deliberately hard. Full inventory and the admission test:
[shared-kernel-reference.md](shared-kernel-reference.md).

The test, in short: a thing belongs in `core/` only if **three or more modules need it**, it has **no domain
semantics**, and a change to it would be reviewed by an owner of each affected module. "Two modules need
it" means duplicate it and wait.

`core/` may not import `modules` — enforced by the `core-is-a-leaf` contract. If something in `core` needs
to know about a module, it belongs in that module.

---

## Settings

`config/settings/` — `base.py` plus per-environment overlays, everything through `django-environ`.
No secret is ever committed. Detail: [settings-and-configuration.md](settings-and-configuration.md).

```python
# config/settings/base.py — the non-negotiable bits
DATABASES = {
    "default": env.db("DATABASE_URL"),
    "erp":     env.db("ERP_DATABASE_URL"),      # platform_erp_ro — SELECT only
}
DATABASE_ROUTERS = ["core.db.routers.ErpReadOnlyRouter"]

CONN_MAX_AGE = 0                        # MANDATORY with PgBouncer transaction pooling
DISABLE_SERVER_SIDE_CURSORS = True      # MANDATORY with PgBouncer transaction pooling

CACHES  = {"default": env.cache("REDIS_CACHE_URL")}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
CELERY_BROKER_URL = env("REDIS_BROKER_URL")     # a DIFFERENT instance: noeviction

USE_TZ = True
APPEND_SLASH = False
```

`CONN_MAX_AGE = 0` and `DISABLE_SERVER_SIDE_CURSORS = True` are not tuning choices. Persistent connections
combined with transaction pooling is a classic silent-corruption pairing — one request can inherit another's
session state. A startup assertion fails the boot if either is wrong while `PGBOUNCER=1`.

---

## Two Django projects, one repository

`services/iam` and `services/platform` are separate Django projects sharing `packages/`. They have separate
settings, migrations, `manage.py` and deployables — and separate Postgres roles.

Shared code goes in `packages/`, never imported across `services/`. `services/platform` importing
`services.iam.something` fails CI; it calls IAM over HTTP or consumes its events.

---

## Naming

| Thing | Convention | Example |
|---|---|---|
| Module directory | `snake_case`, singular domain noun | `placement`, `hr` |
| Model | `PascalCase`, singular | `JobPosting`, `Offer` |
| Table | Django default (`<app>_<model>`) | `placement_jobposting` |
| Selector | `noun_phrase(...)` | `applications_for_posting()` |
| Service | `verb_noun(...)` | `accept_offer()`, `publish_posting()` |
| Contract | `get_<plural>(ids)` | `get_standings(user_ids)` |
| Task | `verb_noun` | `ingest_declaration`, `refresh_stats` |
| Event topic | `<module>.<aggregate>.<past_tense>` | `placement.offer.accepted` |
| Permission | `<module>.<resource>.<action>` | `placement_cell.offer.issue` |
| Index | `<table_abbrev>_<cols>_idx` | `application_posting_status_idx` |
| Constraint | `<table_abbrev>_<rule>` | `offer_one_active_per_year` |

Indexes and constraints are **always explicitly named**. Django's generated names are unstable across
versions, which makes a hand-written migration or an operational `DROP INDEX` unnecessarily risky.

---

## Anti-patterns, with the reason

| Do not | Because |
|---|---|
| Put business logic in `models.py` | It becomes untestable without a database, and `save()` overrides are bypassed by `bulk_update` and `queryset.update()` |
| Query models from a view | Ownership filtering ends up in N places and one of them will be forgotten |
| `import` another module's `models` | It is the first step to a cross-module FK, and CI blocks it |
| Add a cross-module FK | It couples migrations and makes extraction impossible — [ADR-0013](../01-architecture/adr/0013-no-cross-module-foreign-keys.md) |
| Call a service from a selector | A read that writes is the hardest bug class to find |
| `fields = "__all__"` | It exposes the next column someone adds |
| `except Exception: pass` | The legacy monolith has a blanket handler that turns an `ImportError` into a 500 with a misleading message |
| Raise a DRF exception from `services/` | The service stops being reusable from a task or a command |
| Put a singular `get_x(id)` in `contracts.py` | It will be called in a loop |
| Use `db_index=True` casually | Indexes belong in `Meta.indexes` with names and a reason; the legacy has one index across 424 models and it is not the one it needs |
| Read `Student.cpi` or `Spi` | Both are dead — permanently `0.0` and zero-writers respectively. There is a CI grep for this. |
| Recompute CPI | [NG5](../00-overview/vision-and-scope.md#non-goals) |
