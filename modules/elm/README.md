# Employee Leave Management (ELM)

ELM is an independent Django module mounted at `/api/v1/elm/` and `/elm` in the Fusion client. It uses the IAM principal for authentication and `modules.directory.contracts` for employee identity; employee IDs are stored as integers, never as cross-module foreign keys.

## Implemented capabilities

- CL, RH, SCL, EL, COL and VL eligibility, entitlement credits and ledger-based balances.
- Half-day CL, continuous EL/COL/VL counting, closed-holiday exclusions for CL/RH/SCL, RH calendar validation and VL vacation validation.
- Overlap protection and per-employee transaction locks; substitute nomination, acceptance, decline and replacement.
- Unit Head recommendations/final decisions, configured higher-sanction routes and Director self-sanction; every state change has an append-only transition record.
- Pending withdrawal, approved leave cancellation through the same hierarchy, ongoing EL/COL/VL extensions, resumption verification and early-return restoration.
- Current leave-policy/hierarchy configuration, draft/published holiday/RH/vacation calendars, offline sanction synchronization and authorized offline-record maintenance.
- Configurable reminder/escalation thresholds, event-triggered SLA processing and idempotent year-end rollover (CL/RH/SCL lapse, EL/COL carry forward, VL converts to EL at 2:1).
- Employee screens for requests, substitute responses and balances; reviewer queue; administrator screens for policy, calendar, SLA and offline records.

## Setup

Run these after migrations:

```bash
python manage.py seed_elm_policy
python manage.py seed_modules
make permissions
python manage.py seed_iam_permissions --manifest registry/permissions.json
python manage.py assign_role --user <staff-id> --designation "Leave Administrator"
python manage.py elm_readiness
```

The `Leave Administrator` designation must be provisioned in the institute IAM before assigning it. Configure the current policy's `hierarchy` with `unit_heads` keyed by the exact employee department and configure `sanctioning` / `default_sanctioning` for SCL, EL, COL and VL. Create and publish a calendar containing the relevant closed holidays, restricted holidays and vacation periods. Submission intentionally fails closed until an effective published calendar and required routing are available.

The year-end job runs on 1 January at 00:30 and processes the previous year. The SLA job runs hourly. SLA remains disabled until reminder and/or escalation thresholds are configured.

## Specification decisions and known limits

- The functional specifications state that leave-policy parameters have **no draft/publish/effective-version lifecycle**. Accordingly, ELM maintains the current policy parameters in place. Calendar versions do have draft/published history. This follows the functional requirements and business-rule specification where the blueprint's proposed `PolicyVersion` lifecycle conflicts with them.
- Unit Head self-review is refused because the specifications do not define an alternate route. Missing Unit Head mappings are refused with the affected department named.
- Dean sanctioning is not granted by default; configure it explicitly if the institute establishes which Dean sanctions which category.
- Attendance synchronization (`SRS-EL-084`) remains an integration gap because this repository has no attendance module. ELM records and verifies resumption but does not write to an attendance system.
- The uploaded specs identify `BR-EL-026` as a missing identifier; ELM does not invent a rule for it.

## API overview

All endpoints require the ELM module grant and a specific permission. Main routes include `requests`, `substitutions`, `queue`, `balances`, `resumptions`, `notifications`, `admin/policies`, `admin/calendars`, `admin/offline` and `admin/sla`. See `api/urls.py` for the exact methods and paths.
