# Employee Leave Management

ELM is an independent Fusion domain module mounted at `/api/v1/elm/` and
`/elm`. It uses the shared Fusion IAM session, active-role permissions,
navigation shell, database, and API error envelope.

## Deployment and setup

1. Apply the module schema with `python manage.py migrate`.
2. Regenerate and publish the IAM permission manifest with
   `python manage.py permission_manifest`. The designation labels in
   `modules/elm/registry.py` are defaults; align them with the institution's
   actual IAM roles before granting ELM access.
3. Grant employee profiles and organization units through the ELM
   Configuration screen or `POST /api/v1/elm/employees` and
   `POST /api/v1/elm/organization-units`. The IAM user id is the key; ELM does
   not create a second login or local user table.
4. Configure final-sanction routes for SCL, EL, COL, and VL using the
   Configuration screen or `POST /api/v1/elm/approval-routes`. Unit Heads are
   resolved from their employee's organization unit. A route may be unit
   specific, assign a named IAM user, and include an Establishment step.
5. Maintain restricted holidays, closed holidays, and vacation dates in the
   calendar. Validation only uses published entries. Vacation entries are
   supplied to ELM by the institute Academic Calendar integration or its
   authorized calendar maintainer.

The initial migration creates the synchronized baseline policy: CL 8, RH 2,
SCL 15, non-faculty EL 30, COL 20, and faculty VL 60. Year-end processing runs
as an event-triggered system operation:

```sh
python manage.py process_elm_year_end --year 2025
```

The command reports account exceptions and exits unsuccessfully when manual
review is required. It is safe to re-run; already-created next-year accounts
are not processed twice.

Schedule `python manage.py send_elm_notifications` as a recurring worker
command to deliver the ELM transactional email outbox. Delivery errors and
directory records without email are retained with an explicit failed status.

## Workflow and data

Leave applications are immutable after submission. Pending withdrawal is
immediate; approved-leave cancellation, extensions, and resumptions are
separate, auditable cases. Unit Head review is final for CL/RH and a recorded
recommendation for higher-sanction leave. The final authority route is read
from current ELM configuration. Account debits, credits, lapse, conversion,
and corrections are retained as leave transactions.

All access requires both the `elm` module grant and action-specific
permissions. Request ownership, assigned Unit Head, substitute, and
configured sanction routing are checked in the service layer; client-side
permission checks only control the user experience.
