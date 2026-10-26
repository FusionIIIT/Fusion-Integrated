# Assignment 6: Employee Leave Management (ELM)

This module implements the Employee Leave Management (ELM) bounded context for Assignment 6 against `Fusion-Integrated`.

## Phase 2 Overview & Implementation

Phase 2 reviews, hardens, and completes the ELM implementation:

- **Platform & IAM Integration**: Registered as `modules.elm` (`code: "leave_elm"`) with role grants (`Employee`, `Leave Approver`, `Leave Admin`), permission manifest, OpenAPI schema, and client routes under `/leave`.
- **Leave Categories & Eligibility**: Complete validation for `CL`, `RH`, `SCL`, `EL`, `COL`, and `VL` (faculty eligibility for `VL`, published restricted holiday checks for `RH`, and statutory rules).
- **Day Calculation & Overlap Rules**: Half-day (`0.5`) support for `CL`; continuous calendar-day counting across weekends and closed holidays for `EL`, `COL`, and `VL`; working-day counting for `CL`, `RH`, and `SCL`; non-overlap validation across active requests with same-day different-half exception; `2:1` fractional `VL`-to-`EL` conversion respecting the 300-day statutory accumulation cap.
- **Workflow & Lifecycle Repairs**:
  - Substitute overlap validation ensuring nominated substitutes have no active overlapping leave.
  - Substitute-decline recovery workflow allowing applicants to nominate replacement substitutes.
  - Scoped substitute permissions to avoid authorization boundary conflicts.
  - Approved leave cancellation with two-tier review hierarchy and transactional balance restoration.
  - Leave extension for active leaves with linked child records and incremental debits.
  - Duty resumption handling normal, early return refund, and late return deductions.
  - Idempotent year-end rollover service with lapse and carry-forward processing.
  - Offline / paper sanction recording with reference and overlap safeguards.
  - Full React UI and Vitest test suite.

## Verification Commands

```bash
make check
cd client && npm test
```
