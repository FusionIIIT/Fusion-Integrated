# Fusion Platform — Documentation

This is the design record for the **Fusion Non-Academic Platform** and the **central identity
service (`fusion-iam`)** that both it and the existing academic monolith authenticate against.

These documents are written **before** the code. If an implementation disagrees with a document,
one of the two is wrong and it must be resolved — not left to drift. Every doc has an owner and a
review date in its front matter.

---

## Start here

| If you are… | Read, in this order |
|---|---|
| **New to the project** | [Vision & scope](00-overview/vision-and-scope.md) → [Current-state assessment](00-overview/current-state-assessment.md) → [Glossary](00-overview/glossary.md) → [System architecture](01-architecture/system-architecture.md) |
| **About to write a backend module** | [Platform structure](03-platform/platform-structure.md) → [Module authoring guide](03-platform/module-authoring-guide.md) → [Shared kernel reference](03-platform/shared-kernel-reference.md) → [API conventions](01-architecture/api-conventions.md) → [Testing strategy](06-crosscutting/testing-strategy.md) |
| **About to write a frontend module** | [Frontend architecture](05-frontend/frontend-architecture.md) → [Design system](05-frontend/design-system.md) → [Navigation contract](05-frontend/navigation-contract.md) → [Module authoring guide (frontend)](05-frontend/module-authoring-guide-frontend.md) → [State & data fetching](05-frontend/state-and-data-fetching.md) |
| **Working on auth / roles / permissions** | [IAM domain model](02-iam/iam-domain-model.md) → [RBAC model](02-iam/rbac-model.md) → [Token & session design](02-iam/token-and-session-design.md) → [Legacy compatibility & ERP projection](02-iam/legacy-compatibility-and-erp-projection.md) |
| **Working on Placement Cell** | [Placement domain model](04-placement/placement-domain-model.md) → [Academic snapshot integration](04-placement/academic-snapshot-integration.md) → [Application state machine](04-placement/application-state-machine.md) → [Eligibility rules spec](04-placement/eligibility-rules-spec.md) → [Offer & tier policy](04-placement/offer-and-tier-policy.md) |
| **On call / operating the system** | [Deployment topology](07-ops/deployment-topology.md) → [Environments](07-ops/environments.md) → [Runbooks](07-ops/runbooks/) → [Observability](06-crosscutting/observability.md) |
| **Reviewing a pull request** | [API conventions](01-architecture/api-conventions.md) → [Platform structure](03-platform/platform-structure.md) (the boundary rules) → [Security baseline](06-crosscutting/security-baseline.md) → the relevant [ADR](01-architecture/adr/) |
| **Deciding what ships next** | [Roadmap & phases](08-delivery/roadmap-and-phases.md) → [Definition of done](08-delivery/definition-of-done.md) → [Risk register](08-delivery/risk-register.md) |

---

## Full index

### 00 — Overview
| Doc | Scope |
|---|---|
| [vision-and-scope.md](00-overview/vision-and-scope.md) | What we are building, what we are explicitly **not** building |
| [glossary.md](00-overview/glossary.md) | Ubiquitous language. Read this before arguing about a word. |
| [current-state-assessment.md](00-overview/current-state-assessment.md) | The three existing repos, what is production vs deprecated, the verified debt list |

### 01 — Architecture
| Doc | Scope |
|---|---|
| [system-architecture.md](01-architecture/system-architecture.md) | C4 L1/L2, deployables, databases, request paths |
| [context-map.md](01-architecture/context-map.md) | Bounded contexts and the relationship pattern between each pair |
| [data-ownership-and-sync.md](01-architecture/data-ownership-and-sync.md) | Which store owns which fact; the one-way IAM→ERP projection contract |
| [event-catalog.md](01-architecture/event-catalog.md) | Every topic: payload, producer, consumers, ordering and idempotency guarantees |
| [api-conventions.md](01-architecture/api-conventions.md) | Versioning, error envelope, pagination, filtering, idempotency, naming |
| [adr/](01-architecture/adr/) | 13 decision records — see [ADR index](01-architecture/adr/README.md) |

### 02 — Identity & Access Management
| Doc | Scope |
|---|---|
| [iam-domain-model.md](02-iam/iam-domain-model.md) | Every IAM table, column, constraint and index, with rationale |
| [rbac-model.md](02-iam/rbac-model.md) | Roles, permissions, scopes, deny-wins resolution, naming convention |
| [token-and-session-design.md](02-iam/token-and-session-design.md) | Claims, TTLs, rotation, reuse detection, revocation, cookies, CSRF |
| [legacy-compatibility-and-erp-projection.md](02-iam/legacy-compatibility-and-erp-projection.md) | The `/api/auth/me` contract, the `globals_*` projection, and its three hazards |
| [auth-migration-runbook.md](02-iam/auth-migration-runbook.md) | The live cutover: switches, order, verification, rollback, user comms |
| [permission-catalog.md](02-iam/permission-catalog.md) | Every permission code. **CI-generated — do not hand-edit.** |

### 03 — Platform
| Doc | Scope |
|---|---|
| [platform-structure.md](03-platform/platform-structure.md) | Folder layout, the five layers, import-linter contracts, the no-cross-module-FK check |
| [module-authoring-guide.md](03-platform/module-authoring-guide.md) | The 8-step recipe for adding a module |
| [shared-kernel-reference.md](03-platform/shared-kernel-reference.md) | What is in `core/`, and the admission test for adding to it |
| [settings-and-configuration.md](03-platform/settings-and-configuration.md) | Every env var, defaults, secret handling, the PgBouncer constraints |

### 04 — Placement Cell
| Doc | Scope |
|---|---|
| [placement-domain-model.md](04-placement/placement-domain-model.md) | All entities, fields, constraints, indexes |
| [application-state-machine.md](04-placement/application-state-machine.md) | The transition table, diagram, guards and effects |
| [job-posting-lifecycle.md](04-placement/job-posting-lifecycle.md) | Posting FSM, approval flow, rule-locking on publish |
| [eligibility-rules-spec.md](04-placement/eligibility-rules-spec.md) | The rule AST, field vocabulary, fail-closed semantics, worked examples |
| [offer-and-tier-policy.md](04-placement/offer-and-tier-policy.md) | Policy knobs, the `can_accept` decision table, race safety |
| [academic-snapshot-integration.md](04-placement/academic-snapshot-integration.md) | **The declared-CPI contract.** Read before touching anything CPI-shaped. |
| [placement-reports-and-statistics.md](04-placement/placement-reports-and-statistics.md) | Snapshot dimensions, refresh policy, export permissions |

### 05 — Frontend
| Doc | Scope |
|---|---|
| [frontend-architecture.md](05-frontend/frontend-architecture.md) | Monorepo layout, package boundaries, build, routing, guards |
| [design-system.md](05-frontend/design-system.md) | Tokens, the exact layout spec, component inventory, do/don't |
| [navigation-contract.md](05-frontend/navigation-contract.md) | The `/me` payload schema and exactly how it renders |
| [module-authoring-guide-frontend.md](05-frontend/module-authoring-guide-frontend.md) | Manifest, routes, lazy loading, error boundary |
| [state-and-data-fetching.md](05-frontend/state-and-data-fetching.md) | Query key conventions, invalidation, optimistic updates |

### 06 — Cross-cutting
| Doc | Scope |
|---|---|
| [security-baseline.md](06-crosscutting/security-baseline.md) | The checklist, with an owner and a verification method per item |
| [threat-model.md](06-crosscutting/threat-model.md) | STRIDE over login, refresh, role assignment, apply, offer accept, file download |
| [observability.md](06-crosscutting/observability.md) | Log schema, request IDs, dashboards, the six alerts |
| [performance-and-capacity.md](06-crosscutting/performance-and-capacity.md) | Budgets, index policy, load-test plan and committed results |
| [testing-strategy.md](06-crosscutting/testing-strategy.md) | Layers, factories, contract tests, coverage gates |
| [data-retention-and-privacy.md](06-crosscutting/data-retention-and-privacy.md) | PII classification, retention schedule, export controls |

### 07 — Operations
| Doc | Scope |
|---|---|
| [deployment-topology.md](07-ops/deployment-topology.md) | nginx, systemd, sockets, Redis instances, PgBouncer |
| [environments.md](07-ops/environments.md) | dev / staging / prod matrix, seeding, anonymized snapshots |
| [runbooks/](07-ops/runbooks/) | deploy · rollback · restore-from-backup · rotate-signing-key · incident-auth-outage · reingest-academic-snapshot · sync-identity-projection · unlock-account |

### 08 — Delivery
| Doc | Scope |
|---|---|
| [roadmap-and-phases.md](08-delivery/roadmap-and-phases.md) | The nine phases, gates, and what each one may not do |
| [definition-of-done.md](08-delivery/definition-of-done.md) | Per-phase exit criteria |
| [risk-register.md](08-delivery/risk-register.md) | Risks with owner, likelihood, impact, mitigation, trigger |

---

## Conventions for these documents

- **Markdown, one topic per file.** Diagrams are Mermaid sources in [`_diagrams/`](_diagrams/),
  rendered by CI — never paste a rendered image.
- **Front matter on every doc:** `owner`, `status` (`draft` | `reviewed` | `authoritative`),
  `last-reviewed`.
- **Line-referenced claims.** When a doc asserts something about existing code, it cites
  `path:line`. Those citations are checked during each review pass; a stale one is a bug.
- **`MUST` / `SHOULD` / `MAY`** are used in the RFC 2119 sense. `MUST` means CI or review blocks it.
- **Decisions belong in ADRs.** If a doc explains *why* at length, that reasoning probably wants to
  be an ADR with the doc linking to it.
- **Non-goals are as binding as goals.** See [vision-and-scope.md](00-overview/vision-and-scope.md).

## Keeping these honest

| Doc | Generated / verified by |
|---|---|
| `02-iam/permission-catalog.md` | `manage.py export_permission_catalog` in CI; committed diff must be empty |
| `01-architecture/event-catalog.md` | Contract tests assert every topic listed here has a `fusion_contracts` schema, and vice versa |
| `06-crosscutting/performance-and-capacity.md` | Load-test results are committed here per phase; a phase cannot close without them |
| `03-platform/platform-structure.md` | The import-linter contracts it documents live in `.importlinter` and run in CI |
| `05-frontend/design-system.md` | Playwright visual baselines prove the layout claims |
