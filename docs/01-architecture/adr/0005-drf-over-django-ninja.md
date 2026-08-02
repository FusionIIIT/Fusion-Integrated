# ADR-0005 — DRF at the HTTP edge; pydantic inside the domain

- **Status:** accepted
- **Date:** 2026-08-01
- **Related:** [0001](0001-modular-monolith-over-microservices.md)

## Context

Both new services need an HTTP layer. Django Ninja is the modern choice — pydantic validation, native
async, automatic OpenAPI, and considerably less ceremony than DRF serializers.

Against that:

- The team's existing work is **entirely DRF**. Nineteen legacy apps have DRF `api/` packages, and
  `Fusion_System_Administrator` is a well-built DRF application with cookie authentication, scoped
  throttling and centralized permissions — it already proves the stack works in this environment.
- We need **throttling, pagination, permission classes, content negotiation and a schema generator** on
  day one, integrated with each other. DRF ships all of it. Ninja would mean building or bolting on
  throttling and pagination ourselves.
- The workload is CRUD over Postgres with Celery for anything slow. There is **no async requirement** —
  no websockets, no high-concurrency fan-out to slow third parties. Ninja's async advantage does not
  apply.
- `drf-spectacular` → OpenAPI → `orval` → typed TypeScript client is a mature path we depend on for the
  frontend's type safety.

The genuine appeal of Ninja is pydantic's ergonomics for **complex, nested, non-model data** — and we do
have that: eligibility rule ASTs, event payloads, and offer-policy decisions.

## Decision

**DRF at the HTTP edge.** `drf-spectacular` for OpenAPI. Shared defaults in `core/api/defaults.py`:
cursor pagination, Redis-backed scoped throttling, one exception handler, deny-by-default permissions,
`URLPathVersioning`.

**Pydantic inside the domain**, where it earns its place and DRF has nothing to offer:

- `packages/fusion_contracts` — every event payload, validated on both producer and consumer.
- `core/rules/ast.py` — the eligibility rule AST, parsed and validated as a discriminated union.
- `domain/` DTOs — `StandingDTO`, `PolicyView`, `Decision`, and the objects `contracts.py` returns.

The boundary is clean: DRF serializers own the **wire format** of HTTP requests and responses; pydantic
models own **internal structure**. A DRF serializer may validate input and then hand a pydantic model to a
service. A pydantic model never appears in an OpenAPI schema.

## Consequences

**Good**

- Zero retooling. Every developer can read and write these views on day one.
- Throttling, pagination, permissions and schema generation are integrated and battle-tested, not
  assembled.
- One shared settings block means a new module inherits correct defaults automatically — a new endpoint
  is throttled and paginated whether or not the author thought about it.
- `drf-spectacular`'s `@extend_schema` examples double as the MSW mocks in frontend tests, so frontend
  mocks cannot drift from the API.
- Pydantic where it matters: an event payload or a rule AST is validated with real type discrimination
  rather than hand-rolled `dict` checking.

**Bad, and accepted**

- DRF serializers are verbose, and the read/write split doubles the class count. Accepted deliberately —
  a single serializer doing both grows `read_only_fields` lists nobody can reason about and eventually
  writes a field it should not.
- Two validation libraries in one codebase. Mitigated by the strict rule above, restated in
  [platform-structure.md](../../03-platform/platform-structure.md): serializers at the edge, pydantic
  inside. A pydantic model in `api/` is a review rejection.
- No async views. Accepted; there is no async requirement, and Celery covers slow work.
- `ModelViewSet` invites fat views. Mitigated by requiring all reads through `selectors/` and all writes
  through `services/`, so views stay thin regardless of base class.

## Alternatives considered

**Django Ninja throughout.** Rejected: we would rebuild throttling and pagination, retool the team, and
lose the proven `drf-spectacular` → `orval` path — all to solve an ergonomics problem we can address with
pydantic in the domain instead. Ninja is the better *library*; DRF is the better *decision here*.

**FastAPI + SQLAlchemy, separate from Django.** Rejected: it would mean giving up the Django ORM,
migrations and admin, splitting the codebase across two frameworks, and rewriting the domain logic in a
different idiom — for a performance benefit that a system serving 3,277 users cannot measure.

**Both — DRF for existing shapes, Ninja for new modules.** Rejected as the worst option: two HTTP
layers, two OpenAPI generators, two schema files, two throttling implementations, and a coin flip in every
review.

**Hand-rolled Django views with JSON responses.** Rejected: that is effectively what the legacy monolith
does, and the result is 34 apps with no consistent pagination, error shape or authorization.

## Revisit if

A genuine async workload appears — websockets for live placement dashboards, or an endpoint that must
fan out to slow external services. That would be a Ninja or ASGI-Django decision for **that surface
only**, not a migration of the existing API.
