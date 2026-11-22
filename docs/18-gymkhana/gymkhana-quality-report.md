# Gymkhana Quality Report

## Approval Record

- Blueprint: dated written approval by Student 2 on 2026-11-23: “Student 2 approves the Gymkhana Architecture Blueprint exactly as written, with no changes.”
- Scope: no changes outside the Gymkhana module and directly related platform registration, schema, and permission artifacts.
- Known out-of-scope behavior: membership rejection/cancellation and online budget approval/rejection.

## Verification

| Gate | Result | Evidence |
|---|---|---|
| `make check` | Passed | Django checks, migration check, Ruff, import contracts, cross-module-FK check, contract count check, navigation check, permission manifest, OpenAPI check, and full pytest suite |
| `make check-client` | Passed | TypeScript typecheck, 38 Vitest tests, and Vite production build |
| Gymkhana pytest coverage | Passed | Exact module gate: 90.15% total coverage |
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
