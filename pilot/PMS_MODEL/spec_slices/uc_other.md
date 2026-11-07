# PMS use cases: prior art, deadlines, licensing, reports, admin, audit (read-only spec)

### UC-PMS-004 — Search and Attach Prior Art
Actor: Applicant or Attorney
Goal: Search prior-art sources and attach selected references to an application.
Preconditions: Actor has a valid PMS role; external search access/integration is available when an external query is required.
Main flow:
  1. Actor enters or optimizes search terms/classification information.
  2. PMS queries available patent/publication sources and displays ranked results.
  3. Actor reviews results and selects references.
  4. PMS attaches selected references to the application and logs the search session.
Alternatives:
  • Actor may refine keywords/classification mapping and repeat the search.
Exceptions:
  • If an external source is unavailable, PMS does not represent the external source as successfully queried; any already-recorded PMS data remains intact.
Postcondition: Selected references, if any, are attached and the search session is logged.
Rules: BR-PMS-126; BR-PMS-141

### UC-PMS-016 — Monitor Deadlines and Escalations
Actor: PCC_ADMIN
Goal: Monitor calculated deadlines, reminders, missed-deadline escalations, and pending actions.
Preconditions: PCC_ADMIN has an active authorized role; deadline records may exist.
Main flow:
  1. PMS calculates/maintains applicable review, revision, office-action, and maintenance deadlines using available rules/data.
  2. PMS generates configured 30/15/5-day alerts where applicable and triggers notifications.
  3. PCC_ADMIN reviews upcoming/missed deadlines and escalation records.
  4. PCC_ADMIN routes or handles delayed-action exceptional cases within PMS scope.
  5. PMS logs deadline-tracking/escalation activity.
Alternatives:
  • Where deadline rules/data are unavailable, PMS does not fabricate a deadline; the item remains flagged as requiring applicable data/configuration.
Exceptions:
  • A missed deadline may be escalated according to the configured chain; legal consequences outside PMS are not inferred.
Postcondition: Deadline and escalation records are current and visible to authorized actors.
Rules: BR-PMS-097; BR-PMS-098; BR-PMS-099; BR-PMS-100; BR-PMS-101; BR-PMS-102; BR-PMS-103; BR-PMS-104; BR-PMS-116; BR-PMS-126

### UC-PMS-020 — Submit Licensing or Technology-Transfer Request
Actor: Applicant
Goal: Submit a licensing or technology-transfer request linked to patent/IP records.
Preconditions: Applicant has access to the relevant patent/IP record.
Main flow:
  1. Applicant selects the request type and enters the required request information.
  2. Applicant submits the request.
  3. PMS routes the request to the appropriate committee or Director according to the applicable institutional process and records the routing/tracking state.
Alternatives:
  • Licensing and technology-transfer requests use the same submission goal with different request type.
Exceptions:
  • If the applicable routing target/process cannot be determined from configuration/policy, PMS does not invent a committee decision.
Postcondition: The request is submitted and routed/tracked.
Rules: BR-PMS-088; BR-PMS-091; BR-PMS-126

### UC-PMS-021 — Review Licensing or Technology-Transfer Request
Actor: Director
Goal: Review a request routed to the Director and record negotiation/final-agreement information within PMS authority.
Preconditions: Request exists and the Director is the applicable routing target.
Main flow:
  1. Director reviews the request information.
  2. PMS records negotiation-process information as it becomes available.
  3. Authorized PMS users record the final agreement when one exists.
  4. Where integration is available, PMS updates/shares the applicable financial-system information and maintains the license record with confidentiality controls.
Alternatives:
  • If the institutional process routes the request to a committee instead of the Director, the committee's decision process remains outside the defined PMS actor model; PMS may record resulting information.
Exceptions:
  • PMS does not invent approval/rejection semantics that are not stated in the frozen PS.
Postcondition: Available negotiation/agreement/license information is recorded and protected.
Rules: BR-PMS-088; BR-PMS-091; BR-PMS-139; BR-PMS-126; BR-PMS-130

### UC-PMS-024 — Generate System-Wide PMS Reports and Analytics
Actor: PCC_ADMIN
Goal: Generate authorized system-wide PMS reports, dashboards, analytics, schedules, and exports.
Preconditions: PCC_ADMIN has the active authorized role.
Main flow:
  1. PCC_ADMIN selects the report/analytics type and applicable filters.
  2. PMS generates the requested authorized output using recorded PMS data.
  3. Where supported, PCC_ADMIN schedules, customizes, or exports the report.
  4. PMS logs report access.
Alternatives:
  • Available report types include status/progress, financial/budget, deadlines/pending actions, inventors, portfolio, and workload/assignment views.
Exceptions:
  • Unauthorized data is excluded; unavailable data is not fabricated.
Postcondition: Requested authorized report/analytics output is produced and access is logged.
Rules: BR-PMS-126; BR-PMS-131

### UC-PMS-025 — Manage PMS Roles and Configuration
Actor: PCC_ADMIN
Goal: Manage PMS-specific configuration and role assignments within module scope.
Preconditions: Exactly one active PCC_ADMIN exists and the actor is authorized.
Main flow:
  1. PCC_ADMIN reviews PMS configuration and role assignments.
  2. PCC_ADMIN creates/updates PMS-specific role mappings or configuration values within module scope.
  3. PMS validates that role/access constraints and the single-active-PCC_ADMIN rule remain satisfied.
  4. PMS records the configuration/role change for audit.
Alternatives:
  • Configuration may include applicable thresholds, deadlines, routing rules, escalation rules, or integration references where the PS leaves values configurable.
Exceptions:
  • Platform-wide account administration and HR master-data changes are outside PMS.
Postcondition: PMS-specific configuration/role assignments are updated consistently.
Rules: BR-PMS-126; BR-PMS-131

### UC-PMS-026 — Maintain Attorney Panel and Expertise Mappings
Actor: PCC_ADMIN
Goal: Maintain approved attorney-panel membership and expertise mappings used by assignment.
Preconditions: PCC_ADMIN is authorized.
Main flow:
  1. PCC_ADMIN adds/updates/removes approved-panel information and expertise mappings within PMS scope.
  2. PMS records the maintained panel/expertise information.
  3. The updated information becomes available to attorney-assignment validation/routing.
Alternatives:
  • Institutional exceptions may be recorded separately when an assignment outside the panel is permitted.
Exceptions:
  • Invalid/unauthorized panel changes are not committed.
Postcondition: Attorney panel/expertise data is current for assignment use.
Rules: BR-PMS-041; BR-PMS-042; BR-PMS-126

### UC-PMS-027 — Monitor Workflow and Handle Exceptional Cases
Actor: PCC_ADMIN
Goal: Monitor PMS workflows and handle/route conflicts, delayed actions, escalations, and exceptional cases within PMS scope.
Preconditions: PCC_ADMIN is authorized; workflow/exception records may exist.
Main flow:
  1. PCC_ADMIN reviews workflow state, pending actions, assignment conflicts, delayed items, and escalation records.
  2. PCC_ADMIN resolves a case where the frozen PS gives PCC_ADMIN authority, or routes it to the configured/institutional authority where the outcome is external.
  3. PMS records the handling/routing action and resulting tracking state.
Alternatives:
  • Examples include no eligible assignee, conflict-of-interest cases, and delayed-action escalations.
Exceptions:
  • PMS does not grant PCC_ADMIN an unstated legal, patent-office, financial-payment, or higher-authority decision power.
Postcondition: Exceptional-case handling/routing is recorded within PMS scope.
Rules: BR-PMS-025; BR-PMS-044; BR-PMS-051; BR-PMS-104; BR-PMS-126

### UC-PMS-028 — View Audit Trail and Compliance Logs
Actor: PCC_ADMIN
Goal: View audit/compliance records for authorized verification or forensic analysis.
Preconditions: Actor has access to audit/compliance information.
Main flow:
  1. Actor selects an application, time range, user, or action scope.
  2. PMS displays available audit records including required audit fields.
  3. Actor reviews/export/views the records within authorization.
Alternatives:
  • Director access, where available, is limited by the applicable authority/domain.
Exceptions:
  • Unauthorized audit access is blocked.
Postcondition: Audit/compliance information is viewed; no business state changes.
Rules: BR-PMS-121; BR-PMS-122; BR-PMS-126; BR-PMS-130

### UC-PMS-030 — View Own Application Reports
Actor: Applicant
Goal: View report information for the Applicant's own patent applications.
Preconditions: Applicant has a valid PMS role.
Main flow:
  1. Applicant selects an available personal application report.
  2. PMS restricts the dataset to the Applicant's own applications and displays the report.
Alternatives:
  • Available presentation/export options are provided only where the authorized report function supports them.
Exceptions:
  • PMS blocks access to another Applicant's report data.
Postcondition: Applicant views authorized personal report data.
Rules: BR-PMS-003; BR-PMS-126

### UC-PMS-031 — View PMS Reports and Analytics
Actor: Director
Goal: Generate/view PMS reports and analytics within the Director's authorized scope.
Preconditions: Director has an authorized PMS role.
Main flow:
  1. Director selects an available report/analytics view.
  2. PMS generates the output using PMS data within the Director's authorized scope/domain.
  3. PMS logs report access.
Alternatives:
  • Where authorized, scheduled/export/customized report functions may be used.
Exceptions:
  • Unauthorized report scope is blocked.
Postcondition: Director views authorized report/analytics output.
Rules: BR-PMS-005; BR-PMS-006; BR-PMS-126

### UC-PMS-032 — View Application Workflow Oversight
Actor: Director
Goal: View workflow oversight information for applications in the Director's domain.
Preconditions: Director has an authorized role and domain scope.
Main flow:
  1. Director selects the relevant workflow/application scope.
  2. PMS displays workflow states, pending actions, and oversight information within the Director's domain.
Alternatives:
  • None.
Exceptions:
  • Out-of-domain information is not disclosed.
Postcondition: Director views domain-scoped workflow oversight.
Rules: BR-PMS-006; BR-PMS-126

### UC-PMS-033 — Record Patent Legal Advice
Actor: Attorney
Goal: Record legal advice associated with a patent application throughout its lifecycle.
Preconditions: Attorney has a valid role and access to the application.
Main flow:
  1. Attorney selects the application/context.
  2. Attorney records the legal advice note/opinion information.
  3. PMS associates the advice with the application history/audit record as applicable.
Alternatives:
  • This use case may occur at different lifecycle stages; it does not itself impose a new application-state transition.
Exceptions:
  • Unauthorized access or invalid application reference prevents the record from being stored.
Postcondition: Legal advice information is recorded for the application.
Rules: BR-PMS-126; BR-PMS-130
