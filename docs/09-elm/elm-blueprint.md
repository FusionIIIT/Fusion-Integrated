# Employee Leave Management implementation blueprint

Implement Employee Leave Management inside Fusion using the supplied synchronized
ELM specification bundle. The module uses IAM identities and active-role permissions,
the existing React shell, the shared API error envelope, and cursor pagination.

## Sources

The supplied folder is `ELM_Specifications_Bundle_v1.4_FINAL (1)`. Sources are the
Problem Statement v1.4, Functional Requirement Specification v1.5, Use Cases v1.4,
Business Rules v1.4, Workflow Specifications v1.6, and Traceability Matrix v1.5.
Source documents remain outside the repository. Specification prefixes are
`CFR-EL-`, `AFR-EL-`, `BR-EL-`, `EL-UC-`, `BW-EL-`, and `CW-EL-`.

## Boundaries

`modules/elm` owns leave policy, employee routing configuration, published holiday
calendar snapshots, annual leave accounts, applications and linked lifecycle requests,
workflow tasks, account transactions, audit history, and durable in-app notifications.
IAM owns users, designations, authentication, and permission grants. User references
are integer IAM IDs. No foreign key crosses a module boundary. Reads live in
selectors, writes in transactional services, and counting/state rules in pure Python.

## Workflow

New applications validate eligibility, balances, dates, overlap, station leave, and
substitute coverage. Required consent precedes routing. CL/RH end at the Unit Head;
higher categories record either recommendation outcome and continue through any
configured Establishment step to final sanction. Director self-sanction requires an
actual Director active role. Ordinary self-approval is denied.

Submitted applications have no edit endpoint. Withdrawal terminates pending tasks.
Cancellation, extension, and resumption are linked requests with separate decisions;
they preserve the original approval until the appropriate final effect occurs.
Account rows are locked before overlap/balance checks and writes to serialize an
employee's submissions and deductions. Each final posting has a unique ledger key.

## Roles and screens

Roles trace to the Problem Statement actor registry and BR-EL-036: Employee
(faculty/staff), Substitute, Unit Head, Deputy Registrar (Estt.), Dean, Registrar,
Director, and Leave Administrator. Being a named approver requires both the assigned
IAM ID and the task's active role/permission; holding a generic approval permission
does not grant access to every employee's application.

`/elm/requests` handles applications, lifecycle requests, printable details and history.
`/elm/balances` displays accounts and transactions. `/elm/tasks` contains assigned work.
`/elm/notifications` contains the caller's notifications. `/elm/configuration` manages
policy, routing, calendars, SLA configuration, offline entries, and record corrections.
Server registry and client manifests both use the module code `elm`.

## External dependencies and limits

The platform has no Academic Calendar contract. VL must fail closed until a configured
read-only vacation-period provider supplies the relevant institute calendar data;
ELM will not invent vacation dates. Attendance synchronization is exposed as a durable
outbox record for an external consumer, with delivery status visible to administrators.
Live IAM login, calendar integration, attendance delivery, and PostgreSQL concurrency
must be reported as unverified unless exercised against those services.

The work is authored with Codex at the user's request. It is separate from Assignment
6's required experiments with two locally deployed models. It must not be attributed
to a local model that did not generate it.

## Assignment 6 verification scope

After the user supplied the professor's clarification, verification is limited to
mechanical integration: Python syntax, Django import/configuration checks, generated
migrations, module and route registration, generated permission manifests, OpenAPI,
and TypeScript/Vite builds. No systematic functional tests, business-rule audit,
workflow repairs, optimization, or post-generation security hardening are performed.
The generated behavior described above is intended behavior, not a correctness claim.
