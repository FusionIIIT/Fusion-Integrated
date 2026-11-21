# FTS Architecture Documentation

**Module**: File Tracking System (`fts`)  
**Directory**: `modules/fts/`  
**Base Path**: `/fts`  
**API Path**: `/api/v1/fts/`  
**Spec Prefix**: `FTS-`  
**Authors**: `@VarunJalagam` (Student 1 - Builder), `@navasamith9` (Student 2 - Reviewer)

---

## 1. System Overview

The File Tracking System (FTS) is an enterprise workflow module within the Fusion ERP platform designed to model, route, monitor, and audit the lifecycle of official documents and files across institute departments, faculty, staff, and administration.

FTS provides:
- **Sequential Custodial Tracking**: Exact one-person-at-a-time physical/digital custody.
- **Strict State Machine**: Clear lifecycle transitions (`DRAFT` &rarr; `CIRCULATED` &rarr; `ARCHIVED` / `DISCARDED`).
- **Atomic Operations**: Creation of movements, primary remarks, and notification events inside single database transactions.
- **Append-Only Movement & Audit Trail**: Immutable history of every forwarding, return, and lifecycle event.
- **Plural Public Contracts**: Strict cross-module contracts enabling external Fusion modules (e.g., Academics, HR, Finance) to initiate and inspect tracked files without violating modular boundaries.

---

## 2. Architectural Decision Records (ADRs)

### ADR-01: Pure Python Domain Layer
- **Decision**: `modules/fts/domain/` contains zero framework dependencies (no imports from Django, DRF, or Celery).
- **Rationale**: Keeps core domain logic, state machine validation, and invariant enforcement easily unit testable without database or request mock overhead, enforced strictly by `.importlinter`.

### ADR-02: Atomic Movement and Comment Creation (BR-FTS-006)
- **Decision**: Movement creation and its accompanying remark/comment are coupled within a single atomic database transaction (`transaction.atomic()` with `select_for_update()`).
- **Rationale**: Prevents orphaned movements or movements lacking required rationale. Eliminates race conditions in sequence numbering.

### ADR-03: Soft-Delete Auditing for Discarded Drafts
- **Decision**: Discarding a pre-circulation draft transitions the file to `DISCARDED` rather than performing a hard SQL `DELETE`.
- **Rationale**: Preserves reference number continuity and provides an immutable audit trail of file creation and abandonment for governance compliance, while selector functions exclude discarded files from all active inbox and outbox views.

### ADR-04: Centralized Plural Integration Contracts
- **Decision**: Cross-module queries and actions must pass through `modules/fts/contracts.py` with batch/plural signatures (`Sequence[int]`).
- **Rationale**: Prevents N+1 query antipatterns across module boundaries and complies with `ops/checks/contracts_are_plural.py`.

---

## 3. Domain Model & State Machine

### Core Domain Entities (`modules/fts/domain/entities.py`)
- `FileRecord`: Represents an institute file (`id`, `reference_number`, `subject`, `description`, `status`, `owner_user_id`, `current_holder_user_id`).
- `MovementRecord`: Represents a custodial transfer (`sequence`, `movement_type`, `from_user_id`, `to_user_id`).
- `CommentRecord`: Represents remarks attached to a movement or file.
- `AttachmentRecord`: Metadata of an uploaded supporting document.

### State Machine Lifecycle (`modules/fts/domain/state_machine.py`)
```
                     ┌───────────────┐
                     │     DRAFT     │
                     └──┬─────────┬──┘
                        │         │
               Circulate│         │Discard
                        ▼         ▼
               ┌──────────────┐ ┌───────────────┐
      ┌───────▶│  CIRCULATED  │ │   DISCARDED   │ [Terminal]
      │        └──┬─────────┬─┘ └───────────────┘
Forward/Return    │         │
      └───────────┘         │Archive (Owner only)
                            ▼
                     ┌───────────────┐
                     │   ARCHIVED    │ [Terminal]
                     └───────────────┘
```

#### States:
1. `DRAFT`: Pre-circulation stage. File details and initial notes can be edited. Only visible to creator.
2. `CIRCULATED`: Active circulation. File is held by exactly one user (`current_holder`). Can be forwarded or returned.
3. `ARCHIVED`: Final completed state. Only creator/owner may archive a circulated file. Read-only.
4. `DISCARDED`: Abandoned draft. Excluded from active views. Retained for audit purposes.

---

## 4. Layer Boundaries & Import Linter Rules

The module enforces clean architectural layering validated by `.importlinter`:
1. `modules/fts/domain/` (Layer 1): Pure Python only. No dependencies on Django or external libraries.
2. `modules/fts/models/` (Layer 2): Django ORM data models (`File`, `FileMovement`, `FileComment`, `FileAttachment`, `FileAuditLog`).
3. `modules/fts/selectors/` (Layer 3): Read-only querying and scoping. Never mutates database records.
4. `modules/fts/services/` (Layer 4): Business transactions, domain validations, atomic mutations, and audit logging.
5. `modules/fts/api/` (Layer 5): DRF views, serializers, and permission guards.

```
       [ Client UI / Mobile ]
                 │
                 ▼
          [ api/views.py ]
          ┌──────┴──────┐
          ▼             ▼
   [ selectors/ ]   [ services/ ]
          │             │
          │             ▼
          │      [ domain/ ] (Pure Python)
          ▼             ▼
          └──────┬──────┘
                 ▼
            [ models/ ]
                 │
                 ▼
         [ PostgreSQL DB ]
```
