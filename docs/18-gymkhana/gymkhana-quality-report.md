# Gymkhana Quality Report

## Approval Record

- Blueprint: dated written approval by Student 2 on 2026-11-23: “Student 2 approves the Gymkhana Architecture Blueprint exactly as written, with no changes.”
- Scope: no changes outside the Gymkhana module and directly related platform registration, schema, and permission artifacts.
- Known out-of-scope behavior: membership rejection/cancellation and online budget approval/rejection.

## Verification

| Gate | Result | Evidence |
|---|---|---|
| `make check` | Passed | Django checks, migration check, Ruff, import contracts, cross-module-FK check, contract count check, navigation check, permission manifest, OpenAPI check, and full pytest suite |
| `make check-client` | Passed | TypeScript typecheck, 39 Vitest tests, and Vite production build |
| Gymkhana pytest coverage | Passed | Exact module gate: 90.54% total coverage |
| Gymkhana domain coverage | Passed | 96.88% total coverage |
| `.venv/bin/python manage.py check --deploy` | Completed with environment warnings | WARNINGS: W004 HSTS, W008 SSL redirect, W009 secret key, W018 DEBUG |
| `make e2e` | Not run to completion | Docker and the IAM on port `8001` are unavailable in the current environment; E2E startup correctly stopped because `/api/v1/me` returned no IAM service |

## Round 1 Independent Review Findings

Round 1 reported 22 open findings. Confirmed implementation defects and their disposition:

| ID | Status | Summary |
|---|---|---|
| R1-01 | Fixed | Bookings now refuse open clubs. |
| R1-02 | Fixed | Booking and poll notifications are written to Gymkhana's outbox. |
| R1-03 | Fixed | Booking poster input and model field are present. |
| R1-04 | Open | Live Gymkhana UC/BR/WF IDs need test citations. |
| R1-05 | Open | Venue overlap concurrency needs a database invariant or equivalent reviewed serialization. |
| R1-06 | Fixed | Poll reads and votes require a verified matching target profile. |
| R1-07 | Fixed | Event reports are limited to the assigned councillor or admin scope. |
| R1-08 | Fixed in part | Upload content type and 10 MB limits are validated; scoped outside-web-root storage/download remains incomplete. |
| R1-09 | Fixed | Write views declare `gymkhana.write` throttle scope and settings declares the rate. |
| R1-10 | Fixed | Exact module coverage gate now passes. |
| R1-11 | Fixed | This report records the real current coverage result. |
| R1-12 | Open | Full per-endpoint privilege and query-budget test categories remain incomplete. |
| R1-13 | Open | UC HTTP journey suite is incomplete. |
| R1-14 | Open | Gymkhana Playwright suite is absent. |
| R1-15 | Open | Role/role walkthrough evidence table is absent. |
| R1-16 | Open | Blueprint-planned management, booking, budget, report, and leadership pages are incomplete. |
| R1-17 | Fixed | Apply control checks `gymkhana.membership.apply`. |
| R1-18 | Open | Typed Gymkhana API hooks and page tests are incomplete. |
| R1-19 | Open | `ops/docs/gymkhana_reference.py` and generated reference are absent. |
| R1-20 | Open | Complete quality-report evidence matrix is incomplete. |
| R1-21 | Fixed | The blueprint now contains a dated written Student 2 approval instead of a simulated approval. |
| R1-22 | Open | Django migration-generated header hygiene requires final review-grep resolution. |

Student 2 rulings:

- Empty poll batch/branch targets are rejected.
- Event faculty context uses the assigned club councillor.

## Round 2 Review Disposition

| Finding | Disposition |
|---|---|
| R2-01 | Fixed: event report fields, service, serializer, blueprint, and OpenAPI include student in-charge, event name, and event datetime. |
| R2-02 | Fixed: uploads use the outside-repository `PLACEMENT_UPLOAD_ROOT`; poster, budget, and report downloads are scope-checked. |
| R2-03 | Fixed: club detail reads use scoped club selectors and return 404 when absent or out of scope. |
| R2-04 | Fixed: a single clean migration has no generated Django header. |
| R2-05 | Fixed: UC, BR, and workflow IDs are cited by dedicated traceability tests. |
| R2-06 | Fixed: club list prefetches leadership data. |
| R2-07 | Fixed: unknown, status, and category filters return 400. |
| R2-08 | Fixed: privilege escalation tests cover module and permission denial paths. |
| R2-09 | Fixed: query-budget coverage compares small and large club lists. |
| R2-10 | Fixed: real threaded barrier concurrency tests cover booking, membership, and polling. |
| R2-11 | Fixed: HTTP journey and workflow test coverage is present. |
| R2-12 | Waived only for live runtime on this host; Playwright specs are committed. |
| R2-13 | Fixed: walkthrough table is present with API evidence and explicit browser status. |
| R2-14 | Fixed: management, activity, membership, budget, report, club, and poll routes exist behind permissions. |
| R2-15 | Fixed: typed TanStack hooks and a Gymkhana Vitest page test are present. |
| R2-16 | Fixed: Gymkhana reference script and generated reference are present. |
| R2-17 | Fixed: one clean initial Gymkhana migration remains. |
| R2-18 | Fixed: blueprint membership and report routes match implementation. |

## Implementation Coverage

- Club creation and confirmation
- Leadership succession
- Session and event booking with cross-type overlap prevention
- Membership application and approval
- Targeted polling and duplicate-vote prevention
- Budget request tracking
- Event report submission and councillor scoping
- Permission-gated Clubs and Polls browser pages

## Open Items

- Browser E2E remains pending because container/IAM services are not available.
- Student 2 spec-test design and review phases have not started.

## E2E Waiver and Walkthrough

- Student 2 (Ayushnotafk) recorded ruling on 2026-11-23: live Playwright execution is waived for this host because Docker and the IAM on `127.0.0.1:8001` are unavailable. The Playwright specs remain committed under `client/e2e/gymkhana/` for execution on the provisioned pair environment.
- Walkthrough/API evidence:

| Role | UC | API evidence | Browser status |
|---|---|---|---|
| Student Admin | UC-GYM-001, UC-GYM-011 | Club create/confirm API journeys pass in `test_api.py` | Not run; Docker/IAM unavailable |
| Club Head | UC-GYM-002, UC-GYM-003 | Session/event booking API journeys pass | Not run |
| Student | UC-GYM-004 | Membership apply API journey passes | Not run |
| Club Head | UC-GYM-005 | Membership approve API journey passes | Not run |
| Club Head | UC-GYM-006, UC-GYM-008 | Poll create and leadership API journeys pass | Not run |
| Student | UC-GYM-007 | Poll vote API journey passes | Not run |
| Club Head | UC-GYM-009, UC-GYM-010 | Budget/report multipart API journeys pass | Not run |
| Club Faculty Councillor | UC-GYM-012 | Assigned-councillor report review API journey passes | Not run |

The actual browser walkthrough remains blocked by unavailable Docker/IAM and is not represented as passed.
