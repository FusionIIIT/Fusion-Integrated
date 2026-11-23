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
- MMS-UC-021 assigns Served/Cancelled updates to the active Mess Caretaker, and Student 2 approves that specification reading. Student 1's explicit joint agreement is not recorded, so ISS-MMS-014 remains pending and those transitions are not treated as settled.
- Cancelled special-food billing remains unresolved (`ISS-MMS-015`). MMS does not invent a reversal or suppression rule.
- Vacation reminder cadence remains unspecified (`ISS-MMS-019`). No guessed beat entry is added.
- Rebate date modification remains unavailable until external policy is supplied.
- The special-food charge source and value remain unavailable. Approval does not invent a charge.

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

