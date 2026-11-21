# HR-EIS browser journeys

The builder-owned Chromium suite uses real Fusion IAM sessions, real React forms,
the versioned API and PostgreSQL. It never intercepts HR endpoints or fabricates
successful HTTP responses. Fixture policies, financial references and employee
records are synthetic and have no institutional authority.

## Repeat the suite

Use Linux/WSL, the installed Python environment, Node 20.19 or newer supported
Node LTS, PostgreSQL/Redis from Docker Compose, and a separately running IAM on
8001 restored from the synthetic `fusion-dev.dump`. Seed the platform permission
manifest in that IAM before running:

```bash
cd ../Fusion_System_Administrator/Backend/backend
../venv/bin/python manage.py seed_iam_permissions \
  --manifest ../../../Fusion-Integrated/registry/permissions.json
cd ../../../Fusion-Integrated
E2E_IAM_DIR=../Fusion_System_Administrator \
HREIS_E2E_IAM_SYNTHETIC=1 bash client/e2e/hreis/run-isolated.sh
```

Set `E2E_IAM_DIR` to an absolute checkout path if it is elsewhere. The existing
global setup grants the named **synthetic** test accounts their test designations.
The HOD account is faculty, matching IAM's role policy. Accountant uses the
existing provisional `Accounts Admin` mapping; tests do not certify that mapping
for institutional use.

The runner refuses occupied platform/client ports, creates a unique `hreis_e2e_`
database, migrates, reverses/reapplies HR migrations, and confirms that an
unconfigured installation is not ready. Global setup resolves real IAM IDs and
loads fixtures only into that explicitly named disposable database. The runner
then verifies readiness and drops the database, including when tests fail.

Provide an existing local `IAM_SERVICE_TOKEN`, or explicitly opt in with
`HREIS_E2E_IAM_SYNTHETIC=1` to mint a temporary token in the synthetic IAM. Its
value is held in process memory, never printed or committed, and revoked during
cleanup. Do not use the opt-in against institutional IAM. Evidence goes to
`E2E_EVIDENCE_DIR`, or a unique temporary directory by default. Failure screenshots
and traces use Playwright's ignored `client/test-results/` directory.

The workflow file requires this isolated setup and fails with an actionable
message when invoked against an ordinary unprepared database. To run a particular
journey, pass normal Playwright arguments after the script, for example
`--grep 'appraisal assignment'`.

## Live use-case mapping

| Live use case | Browser evidence |
| --- | --- |
| HR-UC-001 | Employee reads own record; HR-created official record is read-only to its employee |
| HR-UC-002 | HR creates an official record, rejects a stale revision, and updates the original employee record |
| HR-UC-003 | Leave form submits; invalid duration and insufficient balance are rejected; CSRF and owner override checks |
| HR-UC-004 | Current HOD forwards to Registrar; final authority approves; reason-required rejection; rejected LTC/CPDA cannot enter finance |
| HR-UC-005 | Owner sees approved/rejected request status; final approval debits leave once; repeated decisions fail |
| HR-UC-006 | Appraisal form submits inside the fixture window; duplicate period is rejected |
| HR-UC-007 | HR assigns a verified directory reviewer; owner cannot be assigned as own reviewer |
| HR-UC-008 | Assigned reviewer reads submitted form, forwards, and final authority archives it into employee service history |
| HR-UC-009 | LTC advance submission through HR verification and two authority decisions |
| HR-UC-010 | LTC reimbursement submission through HR verification and two authority decisions |
| HR-UC-011 | HR verification requires documentary evidence and eligibility basis; authority cannot bypass it |
| HR-UC-012 | Accountant reviews approved LTC, records pending then paid external status, and owner reads the two historical entries |
| HR-UC-013 | CPDA advance with purpose, positive amount and document references |
| HR-UC-014 | CPDA reimbursement through HR verification and approval |
| HR-UC-015 | CPDA verification refuses missing evidence and routes only after HR attestation |
| HR-UC-016 | Accountant correctness review and two auditable CPDA status records; terminal status removes update action |
| HR-UC-017 | HR publishes a future immutable policy; malformed route is rejected without a server error |
| HR-UC-018 | Restricted audit and redacted compliance screens; compliance API excludes private form payloads |
| HR-UC-019 | Employee sees workflow/policy notices; other recipients' notices are absent; mark-read is owner-scoped |
| HR-UC-021 | Real reminder service runs against an aged pending fixture; responsible reviewer sees one reminder; repeat generation creates none |
| HR-UC-022 | Real configured deadline service generates one employee notice; repeat generation creates none |

The last two are event-triggered use cases. The fixture advances the pending
record's age, invokes the production notification services and checks that state,
version and route step do not change. Chromium then verifies actual recipient
dashboard rendering. This is not proof of a deployed scheduler or official SMTP.

These tests cover implemented module boundaries. They do not certify external
payments, document storage, institutional policies, Student 2 approvals or the
independent specification suites. Those boundaries remain explicit in the quality
report and traceability record.
