# MMS implementation blueprint

## Module

- Name: Mess Management System
- Code: `mms`
- Documentation folder: `docs/16-mms/`
- Specification folder: `docs/mms-specs/`
- Environment: `module-only`

## Architecture

MMS remains an independent Django module with:

- framework-free domain rules
- Django models and migrations
- role-scoped selectors
- transactional service functions
- thin DRF API views and serializers
- Celery tasks and beat schedules
- server-filtered frontend routes

The public module module-grant and permission prefix is `mms`. Semantic display labels remain “Mess Management”.

## Boundary decisions

- MMS does not own identity or employee master data.
- Person references use numeric IAM/directory IDs.
- Cross-module directory reads use `modules.directory.contracts`.
- MMS has no direct `modules.directory.models` import.
- Employee identity checks use `get_users([user_id])` plus `held_employee_ids()`.
- Active student notification recipients use `get_active_student_ids()`.

## Known policy gaps

- Mess Admin menu visibility remains unresolved (`ISS-MMS-012`). No Mess Admin menu grant is added.
- The special-food decision period remains unset until institution policy supplies it (`ISS-MMS-013`). No default is applied.
- **ISS-MMS-014 resolved as a specification reading:** Student 1 agrees that the active Mess Caretaker records Served/Cancelled updates. MMS-UC-021 names the Mess Caretaker as Primary Actor and assigns those actions in its main success scenario (steps 1–5); Student 2 approved the same reading. The Problem Statement describes the post-approval states but leaves the actor unstated. This applies the more specific use-case requirement; it does not decide cancellation billing (ISS-MMS-015) or create institutional policy.
- Cancelled special-food billing remains unresolved (`ISS-MMS-015`). MMS does not invent a reversal or suppression rule.
- Vacation reminder cadence remains unspecified (`ISS-MMS-019`). No guessed beat entry is added.
- Rebate date modification remains unavailable until external policy is supplied.
- **Special-food charge policy remains unavailable:** the frozen PS §3.3.7 and BR-MMS-030 require approved requests to be chargeable and the charge to be added to the monthly bill, but provide no authoritative charge source, amount/rate, or rule for selecting a value per request. Until the institution supplies those decisions, MMS blocks approval (HTTP 409, `special_food_charge_policy_unavailable`) and permits rejection. No caller-entered amount is accepted as policy; no charge is added.

## Registration

Selective integration uses:

- `modules.mms` in `DOMAIN_MODULES`
- `/api/v1/mms/` URL mount
- MMS beat schedule/task-route merge
- MMS import-linter module and layer contracts
- `mms` frontend registry entry
- generated `registry/permissions.json`
- generated OpenAPI schema
- generated permission catalog

