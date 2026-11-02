# OAP implementation brief for the local coding model

Implement the **Other Academic Procedures** bounded context in this Django/DRF
platform and its React client.  The source specifications are in the sibling
folder `../4-OtherAcademicProcedure/`; this brief is the implementation-ready
extract.  Follow the shape of `modules/placement`, but do not copy its
placement-specific behaviour.  No cross-module foreign keys: identities are
integer `user_id` values and Directory is read only.

## Required actors and permissions

Use module code `other_academic_procedure`, route prefix `/api/v1/oap`, and
frontend prefix `/oap`.  Define least-privilege permissions and registry grants
for these roles: student; faculty; hod; academic_administrator;
department_administrator; librarian; hostel_warden; mess_incharge;
department_verifier; lab_supervisor; academic_section_verifier; and
student_section_verifier.  A faculty user acting as thesis or TA supervisor
uses the faculty role.  Every endpoint must enforce the corresponding
permission and restrict student-owned records to `request.user.user_id`.

## Data and lifecycle requirements

1. **Leave:** a student creates an application with details and optional
   supporting-document URL.  It is `submitted`, then only an HoD may set it to
   `approved` or `rejected`.  Students see only their own history.
2. **Bonafide:** a student creates a request; only Academic Administrator
   approves/rejects it.  A certificate download/link is exposed only for an
   approved request and only to its student.
3. **No dues:** student initiation creates exactly seven independent clearance
   rows: library, hostel, mess, department, lab, academic_section,
   student_section.  Each named authority can decide only its own domain.
   Academic Administrator may finalize only after all seven are recorded as
   `cleared`; it cannot finalize when any is pending or dues_outstanding.
   Students see their own per-domain status and final certificate only after
   finalization.
4. **Assistantship:** only PG students may submit a claim.  The claim records
   the thesis-supervisor and TA-supervisor user IDs at submission, based on
   Department Administrator assignments.  Both verification roles are required
   even when the same faculty member has both assignments: each decision is
   independently recorded.  Department Administrator can review/forward only
   after both supervisors approve.  HoD then approves/rejects.  Academic
   Administrator alone marks a HoD-approved claim `disbursed`.  Students see
   only their own claims.  Department Administrator records thesis and TA
   assignments; a TA assignment may associate subject/course and supervisor.
5. **Graduate seminars:** PG students request scheduling; Department
   Administrator schedules it; PG students and faculty can view schedules.
   Keep a scheduling history/audit timestamp.  There is no cancellation,
   reschedule, duplicate, conflict, notification schedule, or finance-policy
   requirement.

## Technical requirements

- Create a conventional module layout: app, models, migrations, registry,
  contracts, domain/state-machine or service choke points, API serializers,
  views, urls, tests.  Register in settings, root URLs, permissions registry,
  and import-linter where the project pattern requires it.
- Model state transitions with validated service functions.  Do not let generic
  serializers or direct model updates bypass guards.
- Use project error classes and normal DRF patterns.  Return 404 for a record
  outside a caller's scope; do not leak its existence with 403.
- Write focused tests for authorization, ownership isolation, state guards,
  seven independent no-dues records, and the two supervisor-verification gate.
- Add a small typed React OAP area with routes/pages for the student requests
  and staff queues/actions.  Reuse the existing client API, React Query,
  Mantine, and UI components.  Make it compile even if no data exists.
- Do not add infrastructure integrations not supported by the specifications
  (email delivery can be represented by a local notification/audit event).

## Verification

Run targeted Django tests for the OAP module, the relevant platform checks, and
the client typecheck/test command if practical.  Fix the failures you create.
Keep edits coherent and do not commit: the calling agent will inspect, test,
and make the single requested Git commit.
