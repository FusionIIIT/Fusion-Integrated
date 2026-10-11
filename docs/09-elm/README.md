# Employee Leave Management generated implementation

This submission is a fresh integrated ELM implementation containing backend and
frontend code in one pull request. It contains no implementation copied from the previous
Llama or Qwen trial folders. See [the blueprint](elm-blueprint.md) for source versions,
module boundaries, and intended workflows.

The generator used for this work is Codex. DeepSeek Coder 6.7B and Qwen2.5-Coder 3B
were not run for these pull requests. This work does not supply the two local-model
experiments required by the original Assignment 6 pilot instructions.

## Mechanical integration

1. Install the existing project dependencies with `make install`.
2. Configure the existing Fusion database and IAM connection using the repository setup guide.
3. Run `make migrate`, `make seed`, and `make permissions`.
4. Publish `registry/permissions.json` to the IAM using the role-assignment guide.
5. Assign the `Leave Administrator` designation to a synthetic faculty/staff account.
6. Start the platform backend and standalone client. In the administrator role, save
   the current policy, each employee's eligibility/hierarchy, and a published holiday/RH calendar.
7. Assign the relevant employee and authority designations in IAM. Log out and back in
   after changing role assignments, then use the role switcher to select the role.

The backend namespace is `/api/v1/elm/`; the client namespace is `/elm/`. `registry.py`
defines permissions and navigation. Policies use current settings directly; calendar
replacements become effective when published. IAM users remain integer references.

## External interfaces

VL needs `ELM_VACATION_PERIODS_PROVIDER` configured as the dotted path of a read-only
callable with signature `(user_ids, start_date, end_date)`. It returns a mapping from
IAM user ID to a list of `(start_date, end_date)` vacation intervals, using Python dates.
ELM does not maintain the institute Academic Calendar itself. With no provider configured,
the generated API returns `vacation_calendar_unavailable`.

Resumption creates an `AttendanceOutbox` row for an external attendance consumer.
The administrative configuration API exposes pending outbox records. No attendance
consumer is included in this submission; external delivery is not demonstrated.

The Celery schedule registers an SLA sweep and a previous-year account-processing job.
The equivalent manual entry points are `python manage.py process_elm` and
`python manage.py process_elm --year YYYY`. These workflows were not functionally tested.

## Professor's clarification

The user supplied a clarification limiting corrections to file placement, imports,
registration, dependencies/configuration, expected interface names, database wiring,
and Fusion structural mismatches. This submission records mechanical build checks
only. It does not claim business-rule correctness, workflow correctness, complete
requirement coverage, or production readiness. Generated defects may remain.

## Submission packaging

This PR contains the Django module, migrations, registration, scheduled-task wiring,
generated permission/OpenAPI artifacts, the React module, client registry entry, and
this documentation. It targets `FusionIIIT/Fusion-Integrated:main`. A separately
generated partner submission is not included in this branch.
