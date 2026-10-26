# Employee Leave Management

ELM is an API-only Fusion domain module. It owns leave policies, requests,
approval tasks, balances, transactions, calendars and audit events. It keeps
IAM user IDs as references; it does not copy directory identity or add a
cross-module foreign key. No client screen or sidebar link is included until a
client route exists.

## Setup

Apply migrations and regenerate the IAM permission manifest:

```bash
make migrate
make permissions
```

An ELM administrator must configure active leave categories, employee
contexts, approval routes and accounts before staff can submit requests.
Category policy is current state: updates apply directly, with no draft or
publish lifecycle. The administrator must supply the institution's approved
CL/SCL day-counting rule; the source requirements say those categories are not
continuous, but do not define their exact working-day formula.

Publish the current Holiday/RH calendar before RH applications. Calendar
revisions are created separately and then published; a published calendar is
immutable. Vacation periods are entered from the external Academic Calendar
with its source reference. Account entitlements and opening balances are
maintained from authorized HR records.

IAM must map the generic ELM designation keys in `registry.py` to the
institution's actual designations. The manifest lists the permissions and
module grants; creating those IAM grants is an operator task outside this
repository.

## API

All routes are under `/api/v1/elm/` and require both the ELM module grant and
the action permission. Employee reads are scoped to the authenticated user ID.

| Route | Purpose |
|---|---|
| `GET, POST requests` | Own request history; submit a leave application |
| `GET balances?year=YYYY` | Own configured balances and reservations |
| `POST requests/{id}/withdraw` | Immediate withdrawal while processing is pending |
| `POST requests/{id}/substitute` | Substitute consent or applicant replacement |
| `POST requests/{id}/cancellations` | Request cancellation before approved leave starts |
| `POST requests/{id}/extensions` | Request an EL/COL/VL extension while leave is ongoing |
| `POST requests/{id}/resumption` | Report actual return for authority review |
| `GET tasks` | Tasks assigned to the current user, with request details |
| `POST requests/{id}/review` | Unit Head recommendation/final decision, Establishment routing, or final decision |
| `POST resumptions/{id}/review` | Review actual return and balance adjustment |
| `GET notifications` | Own ELM in-app notifications |
| `GET export.csv` | Export the caller's own leave representation |
| `POST admin/categories, employee-contexts, routes` | Configure policy, employee context and current routing |
| `POST admin/calendars, calendars/{id}/entries, calendars/{id}/publish` | Maintain and publish holiday/RH calendar |
| `POST admin/vacations` | Record external Academic Calendar vacation periods |
| `POST admin/accounts, accounts/adjustments` | Maintain balances and evidence-backed corrections |
| `POST admin/records/offline` | Synchronize previously sanctioned offline leave without another approval |
| `GET, POST admin/sla` | Configure reminder/escalation thresholds |
| `GET admin/audit` | Review policy and account administration events |
| `GET admin/audit` | Review policy and account administration events |

CL and RH go to the Unit Head for the final decision. SCL, EL, COL and VL go to
the Unit Head for a recommendation, then optional Establishment review, then
the configured final authority. A Director applicant is assigned a self-
sanction task. Route and actor decisions are captured in request events and
task assignments.

Balances use annual entitlement plus opening balance and signed ledger entries,
less active pending reservations. Final approval posts a charge; cancellation
approval posts a reversal. The year-end command carries EL/COL, lapses CL/RH/SCL,
and converts unused VL to EL at 2:1, including fractional balances.

## Operations

```bash
python manage.py run_elm_sla
python manage.py run_elm_year_end 2026
```

The SLA command creates one in-app reminder/escalation notification and records
an event for each overdue pending task. Schedule it in the deployment's existing
job runner. The year-end command runs once per year; it records accounts with
active reservations or negative balances as exceptions for operator follow-up.

## Known boundaries

The module does not include a React client, an attendance connector, an
automatic Academic Calendar feed, email/SMS delivery, or an institution IAM
designation mapping. Resumption review updates the ELM leave dates and ledger;
a Fusion attendance service is not present in this repository, so attendance
synchronization remains an integration task. Configure authoritative policy
and sample data before pilot use.
