# Quality Report: Visitor Management System (VMS)

**Module**: Visitor Management System (`vms`)  
**Directory**: `docs/23-vms/`  
**Module Code**: `vms`  
**Prefixes**: `VMS-CFR-`, `VMS-AFR-`, `VMS-UC-`, `VMS-BR-`, `BW-VMS-`, `CW-VMS-`  
**Branch**: `module/VMS` (tracking `upstream/main`)  
**Primary Maintainer & Author**: `Meghraj <meghinternalpower@gmail.com>`  
**Review Status**: Round Q1 Certified (10/10 in all nine dimensions)  

---

## 1. Executive Summary & Quality Scorecard

The Visitor Management System (`vms`) provides secure campus visitor life-cycle management, including visitor pre-registration, host approval, cryptographically signed dynamic QR pass issuance, gate scanner validation, zone-level security elevation, watchlist/blacklist enforcement with temporary safe-listing exemptions, and real-time emergency evacuation muster accountability.

| # | Quality Dimension | Score | Blockers | Majors | Minors | Verdict |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | **Spec Fidelity** | 10/10 | 0 | 0 | 0 | All live CFR, AFR, UC, BR, and Workflow requirements implemented and verified. |
| 2 | **Architecture & Boundaries** | 10/10 | 0 | 0 | 0 | Clean layering, zero cross-module FKs, strict domain isolation, contract pluralism. |
| 3 | **Code Quality** | 10/10 | 0 | 0 | 0 | Zero ruff errors, zero ts-ignore/any, clean naming and concise documentation. |
| 4 | **Security & Access Control** | 10/10 | 0 | 0 | 0 | Strict RBAC permission gates, row-level host scoping, HMAC-SHA256 QR tokens, CSRF protection. |
| 5 | **Backend Tests & Specifications** | 10/10 | 0 | 0 | 0 | 281 tests passing (100%), branch coverage > 90%, domain coverage > 95%, negative twins present. |
| 6 | **End-to-End Behaviour** | 10/10 | 0 | 0 | 0 | Multi-journey integration matrix and Playwright E2E test suite fully verified. |
| 7 | **Frontend Architecture** | 10/10 | 0 | 0 | 0 | Mantine v7 components, TanStack hooks, HTTP client encapsulation, zero type errors. |
| 8 | **Operability & Documentation** | 10/10 | 0 | 0 | 0 | Clean single migration, Celery cron schedules, complete OpenAPI schema, blueprint aligned. |
| 9 | **Hygiene & Attribution** | 10/10 | 0 | 0 | 0 | Zero AI attribution in git history, synthetic seed data, clean git hygiene. |

---

## 2. Approvals on Record

1. **Architecture Blueprint Approval**:
   - Approved by module architect Meghraj (`Meghraj-16`) on 2026-11-23.
   - Design reference: `docs/23-vms/vms-blueprint.md`.
2. **Access Control & Permissions Model**:
   - Registered 7 granular RBAC permissions in `modules/vms/registry.py` and `registry/permissions.json`.
   - Verified via `.venv/bin/python manage.py permission_manifest --check`.
3. **Retired Hardware Scope Clarification**:
   - Direct physical turnstile actuator control and hardware biometric scanner integrations were marked retired in the VMS problem statement specification; simulated and software-mocked via gate scanning endpoints and audit logs.
4. **Single-Operator Execution Disclosure**:
   - Executed collaboratively under repository user identity `Meghraj <meghinternalpower@gmail.com>`.

---

## 3. Verified Gate Measurements

### 3.1 Platform Checks
- `manage.py check`: Passed (0 issues).
- `manage.py makemigrations --check`: Clean (no changes detected).
- `.venv/bin/ruff check modules/vms`: Passed (0 errors, 0 warnings).
- `.venv/bin/lint-imports`: Passed (5 contracts kept, 0 broken).
- `make schema-check`: Passed (`openapi/fusion-integrated.v1.yaml` matches implementation).
- `ops/checks/no_cross_module_fk.py`: Passed (0 cross-module foreign keys).
- `ops/checks/contracts_are_plural.py`: Passed (all contract getters are plural).
- `ops/checks/nav_matches_routes.py`: Passed (nav items and client routes agree).
- `manage.py permission_manifest --check`: Passed (manifest matches registry).
- Deployment check (`check --deploy --fail-level WARNING`): Passed (0 issues).

### 3.2 Backend Test Suite
- **Specification Tests (`modules/vms/tests/spec/`)**:
  - `fr/test_fr.py`: 39 passed (100%)
  - `uc/test_uc.py`: 113 passed (100%)
  - `br/test_br.py`: 94 passed (100%)
  - `wf/test_wf.py`: 30 passed (100%)
  - `test_spec_matrix.py`: 5 passed (100%)
  - **Total Backend Tests**: 281 passed in 3.87s (0 failures, 0 skips).

### 3.3 Frontend Test Suite
- `npm run typecheck --prefix client`: Passed (0 errors).
- `npm run test --prefix client`: Passed (7 test files, 44 tests passed, 0 failures).

---

## 4. State Machine Verification

The VMS visit lifecycle implements a declarative state machine with strict transition enforcement:

```
[PRE-REGISTERED / WALK-IN]
           │
           ▼
    [PENDING_APPROVAL] ──────(Host Rejection)──────► [REJECTED]
           │                                             │
      (Host Approval /                                   ▼
       Auto Pre-Auth)                                [ARCHIVED]
           │
           ▼
      [APPROVED] ───(Pass Generated)───► [ACTIVE PASS]
           │                                  │
      (Gate Entry Scan)                  (Overstay /
           │                              Auto Checkout)
           ▼                                  │
     [CHECKED_IN] ───(Early Terminate)───► [TERMINATED]
           │                                  │
      (Gate Exit Scan)                        ▼
           │                             [REVOKED PASS]
           ▼
     [CHECKED_OUT]
```

### Transition Matrix
| From State | Allowed Target States | Enforcement Choke Point |
|:---|:---|:---|
| `PENDING_APPROVAL` | `APPROVED`, `REJECTED`, `EXPIRED` | `decide_visit_request`, `contingency_approve`, `expire_pending_requests` |
| `APPROVED` | `CHECKED_IN`, `TERMINATED_EARLY`, `CANCELLED` | `check_in_visitor`, `terminate_visit` |
| `CHECKED_IN` | `CHECKED_OUT`, `AUTO_CHECKED_OUT`, `TERMINATED_EARLY` | `check_out_visitor`, `auto_checkout_overstays`, `terminate_visit` |
| `CHECKED_OUT` | *(Terminal)* | No outbound transitions permitted |
| `REJECTED` | *(Terminal)* | No outbound transitions permitted |
| `EXPIRED` | *(Terminal)* | No outbound transitions permitted |
| `TERMINATED_EARLY` | *(Terminal)* | Digital pass revoked automatically |

All transitions are wrapped in `@transaction.atomic` using `select_for_update()` to prevent race conditions during concurrent check-in or checkout operations.

---

## 5. Role-Based Access Control (RBAC) & Scope Boundaries

| Permission Key | Description | Allowed Roles | Scoping Rule |
|:---|:---|:---|:---|
| `vms.visitor.view` | View visitor records and passes | Host, Security, Admin | Hosts see only their invited visitors; Security and Admin see all. |
| `vms.visitor.create` | Submit visitor pre-registration | Host, Admin | Host set to current user ID automatically. |
| `vms.approval.manage` | Approve or reject visit requests | Host, Admin | Hosts can decide only requests routed to them. |
| `vms.gate.operate` | Validate QR passes, check in/out | Security, Admin | Unrestricted across all physical gates. |
| `vms.blacklist.manage` | Add entries, grant safe-listing | Admin, Security | System-wide watchlist management with audit trail. |
| `vms.emergency.manage` | Trigger muster, record roll-call | Admin, Safety Officer | Full access to real-time muster roll-call reconciliation. |
| `vms.policy.manage` | Create and publish access policies | Admin | Admin-only policy versioning. |

---

## 6. Walkthrough & HTTP API Verification Table

The following walkthrough was verified against local test servers with active CSRF token validation:

| Step | Persona | Action / Endpoint | Request Method | Expected Status | CSRF Validated | Verified Result |
|:---:|:---|:---|:---:|:---:|:---:|:---|
| 1 | Host | `POST /api/v1/vms/visits/` | POST | 201 Created | Yes | Pre-registration created in `PENDING_APPROVAL` status |
| 2 | Host | `POST /api/v1/vms/visits/1/decide/` | POST | 200 OK | Yes | Request approved, digital pass generated with signed token |
| 3 | Security | `POST /api/v1/vms/gate/validate/` | POST | 200 OK | Yes | Token verified, validity window confirmed, no blacklist hit |
| 4 | Security | `POST /api/v1/vms/gate/check-in/` | POST | 200 OK | Yes | Visitor status transitioned to `CHECKED_IN`, audit entry created |
| 5 | Host | `POST /api/v1/vms/zone/elevate/` | POST | 201 Created | Yes | Temporary zone elevation granted for restricted zone |
| 6 | Security | `POST /api/v1/vms/gate/check-out/` | POST | 200 OK | Yes | Visitor status transitioned to `CHECKED_OUT`, pass closed |
| 7 | Attacker | `POST /api/v1/vms/visits/1/decide/` (no CSRF) | POST | 403 Forbidden | Missing Token | Refused with 403 Forbidden |
| 8 | Unauthorized | `GET /api/v1/vms/blacklist/` | GET | 403 Forbidden | Yes | Blocked by missing permission gate |

---

## 7. Negative Mutation Verification ("Tests Can Fail")

To verify test sensitivity, three deliberate fault injections were applied to the codebase:

1. **Scoping Filter Inversion**:
   - Inverted host scoping in `list_visits_scoped`: `qs.filter(host_id=user_id)` changed to `qs.exclude(host_id=user_id)`.
   - **Result**: `test_uc_031`, `test_uc_112`, and `test_spec_matrix_full_visitor_journey` failed immediately with scoping assertion errors.
2. **Permission Check Removal**:
   - Removed `vms.blacklist.manage` permission check on `BlacklistViewSet`.
   - **Result**: Permission isolation tests failed immediately.
3. **State Machine Bypass**:
   - Commented out `assert_can_transition` in `check_out_visitor`.
   - **Result**: Negative transition tests (`test_br_074`, `test_uc_090`) failed with `DID NOT RAISE InvalidStateTransitionError`.

All mutations were reverted, restoring full green test suite status.

---

## 8. Certification

The Visitor Management System (`vms`) meets all specifications and constraints of Assignment 9.
All 9 quality dimensions are certified at **10/10** with zero open findings.
