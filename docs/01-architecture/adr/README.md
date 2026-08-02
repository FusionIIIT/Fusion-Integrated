# Architecture Decision Records

A decision belongs here when reversing it later would be expensive. The point is not to justify
choices — it is to record what we knew at the time, so a future reader can tell whether the reasoning
still holds.

## Format

Each ADR has: **Context** (the forces, including what we measured) · **Decision** (imperative, one
paragraph) · **Consequences** (good and bad, honestly) · **Alternatives considered** (and why they
lost) · **Status**.

Statuses: `proposed` · `accepted` · `superseded by ADR-nnnn` · `deprecated`. An accepted ADR is
**never edited** to change its decision — it gets superseded by a new one. Typos and clarifications
are fine.

## Index

| ADR | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith-over-microservices.md) | Build the non-academic platform as a modular monolith, not microservices | accepted |
| [0002](0002-separate-iam-service-and-database.md) | `auth_user` stays in the ERP; IAM references it by id | accepted, amended by 0014 |
| [0003](0003-rs256-jwt-access-plus-opaque-refresh.md) | RS256 JWT access token + opaque rotating refresh token, validated locally against JWKS | accepted |
| [0004](0004-cookie-auth-and-csrf-strategy.md) | Credentials in httpOnly cookies; double-submit CSRF token | accepted |
| [0005](0005-drf-over-django-ninja.md) | DRF at the HTTP edge; pydantic inside the domain | accepted |
| [0006](0006-outbox-plus-celery-for-integration-events.md) | Transactional outbox + Celery for events; no external broker | accepted |
| [0007](0007-read-only-erp-access-via-acl.md) | Read the ERP only through `modules/academics`, on a read-only Postgres role | accepted |
| [0008](0008-declared-academic-snapshot-for-cpi.md) | Snapshot the ERP's own CPI at declaration; never recompute it | accepted |
| [0009](0009-frontend-monorepo-pnpm-turborepo.md) | One pnpm + Turborepo monorepo, four packages and one app | accepted |
| [0010](0010-server-driven-navigation.md) | The server sends navigation in render shape; the client does zero filtering | accepted |
| [0011](0011-no-multi-tenancy.md) | Single tenant. No `tenant_id`, no per-tenant schemas | accepted |
| [0012](0012-postgres-roles-and-least-privilege.md) | Per-service Postgres roles with least privilege; snapshot immutability in the database | accepted |
| [0013](0013-no-cross-module-foreign-keys.md) | No foreign key crosses a module boundary | accepted |
| [0014](0014-identity-ownership-migration-path.md) | The identity projection becomes the source of truth; only the sync direction flips | accepted |

## Reading order for newcomers

0001 → 0002 → 0014 → 0003 → 0008 → 0013. Those six carry most of the load; the rest are consequences
or narrower choices.
