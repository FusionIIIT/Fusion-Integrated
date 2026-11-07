# PMS problem statement (read-only spec)

2.1 Overview
The Patent Management System (PMS) digitizes and streamlines institutional patent application management and intellectual property protection within Fusion ERP.
The module supports application submission, application documentation, review and decision workflows, revision and resubmission, attorney assignment, legal and patentability assessment, budget approval and financial tracking, external patent-office filing support, post-grant tracking, maintenance fee tracking, office-action response tracking, withdrawal, co-inventor and agreement management, prior-art search support, document version management, patent licensing and technology-transfer request tracking, appeal handling, deadline management, notifications, audit trails, and reporting.
PMS is intended to improve correctness, transparency, compliance support, timely communication, auditability, and operational coordination while reducing manual effort.
PMS records and tracks patent-management information. Legal decisions, patent-office decisions, actual payment execution, external accounting operations, and external patent-office processing remain outside PMS unless explicitly recorded, validated, notified, routed, logged, or reported within PMS.
2.2 Actors
2.2.1 Applicant
Submits new patent applications with required documentation.
Tracks application status and progress.
Revises and resubmits applications based on feedback.
Manages co-inventor information and agreements.
Conducts prior-art searches through PMS-supported search functions.
Withdraws applications when withdrawal is allowed by current application status.
Responds to office actions with attorney support.
Views personal application reports.
2.2.2 Director
Reviews assigned patent applications for technical merit.
Approves, rejects, or requests revisions to applications.
Provides detailed justification for decisions.
Reviews and approves budgets for patent filing and prosecution costs.
Makes final decisions on patent maintenance and renewal.
Views reports, dashboards, and analytics available within PMS.
Has oversight over application workflow in the Director domain.
2.2.3 PCC_ADMIN
Assigns applications to Directors based on explicit assignment criteria.
Assigns attorneys from approved panels, subject to stated exceptions.
Coordinates PMS operations and monitors workflow.
Resolves or routes conflict-of-interest and exceptional cases within PMS scope.
Manages PMS-specific configuration and role assignments.
Generates system-wide PMS reports.
Maintains attorney panels and expertise mappings.
2.2.4 Attorney
Conducts legal and patentability assessment.
Performs prior-art searches in relevant databases through PMS-supported search functions.
Provides legal opinions on patent applications.
Prepares applications for external filing.
Files applications with patent offices and records filing details in PMS.
Responds to office actions.
Manages post-grant tracking and maintenance-fee reminders/deadline tracking.
Provides legal advice throughout the patent lifecycle.
2.3 Functional Scope
2.3.1 Application Submission and Management
Applicants submit patent applications with required fields: title, abstract, detailed description, claims, inventor information, and supporting documents.
PMS validates that required application fields are complete before accepting submission.
PMS validates uploaded documents as PDF format, under 50 MB, and malware-free.
PMS classifies documents by sensitivity.
PMS assigns a unique application ID to each accepted application and sets the application status to Submitted.
Inventor agreements must be completed before filing.
PMS records application history and notifies relevant stakeholders.
2.3.2 Application Assignment and Routing
After submission, PCC_ADMIN or PMS automatic routing assigns applications to Directors.
Assignment uses Director expertise matching, workload balance, and conflict-of-interest checks.
Directors or PCC_ADMIN cannot review applications where they are listed as inventors.
PMS updates the application status to Under Review upon assignment.
PMS notifies the assigned Director and initiates the applicable review timeline.
2.3.3 Application Review and Decision
Directors review application details, documents, and supporting materials.
Directors must decide Approve, Reject, or Needs Revision.
Directors must provide detailed justification of at least 50 characters for all decisions.
Director review must be completed within 15 business days of assignment.
If an application is rejected or requires revision, PMS sends detailed feedback to the Applicant.
Approved applications proceed to attorney assignment.
PMS maintains an audit trail of the review process.
2.3.4 Application Revision and Resubmission
Applicants may revise applications with status Needs Revision or Rejected.
Applicants must resubmit revised applications within the applicable 60-day resubmission period from the relevant rejection/revision decision date.
PMS validates that a revision addresses Director feedback.
PMS maintains version control for revised applications and starts a new review cycle after resubmission.
If the resubmission deadline expires, PMS changes the application status to Expired.
Applicants may withdraw applications before the filing stage where current status allows withdrawal.
2.3.5 Attorney Assignment
Only PCC_ADMIN can assign attorneys to approved applications.
Attorneys must be selected from an approved panel unless an institutional exception is recorded or allowed.
Attorney assignment considers attorney expertise, workload, conflict-of-interest checks, and Applicant preference when the preferred attorney is in the approved panel.
The assigned Attorney must accept or decline the assignment.
PMS updates application status to Attorney Assigned or Pending Review as applicable.
2.3.6 Patentability Assessment and Legal Review
Attorney conducts legal and patentability analysis.
Attorney performs prior-art search in relevant databases.
Attorney evaluates novelty, non-obviousness, and utility.
Attorney records a detailed patentability opinion with recommendation: File Patent, Do Not File, or Needs Amendment.
PMS records the opinion and notifies relevant stakeholders.
Attorney may request additional information or extensions as supported by PMS.
2.3.7 Budget Approval and Financial Tracking
Director reviews and approves costs for patent filing and prosecution.
Budget information includes filing fees, attorney fees, and administrative costs.
If total cost exceeds the configured threshold limit, PMS routes/escalates the case to the applicable higher authority.
Budget approval is allowed only for applications with status Approved.
PMS validates budget availability before approval where budget availability information is available to PMS.
PMS logs financial transaction records and authorization levels for audit purposes.
Accounting, payment execution, and external finance-system processing are outside PMS unless recorded or integrated as PMS data.
2.3.8 External Filing and Patent Office Communication
Attorney prepares the application package according to applicable patent-office requirements.
PMS validates format compliance with applicable patent-office standards where validation rules are available to PMS.
Attorney submits the application to the Indian Patent Office or an international patent office.
International filings require additional justification to be recorded in PMS.
PMS captures external filing ID, filing date, and confirmation information.
PMS updates application status to Filed after filing is recorded.
PMS logs official communications with patent offices.
2.3.9 Post-Grant Tracking and Maintenance
Post-grant tracking activates only for patents with status Granted.
PMS calculates maintenance-fee schedules based on grant date and jurisdiction where the applicable schedule rules are available to PMS.
Attorney manages maintenance-fee reminders and deadline tracking in PMS.
Before each maintenance deadline, an explicit renewal decision is required.
Attorney seeks renewal decision from the Director.
Director decides Renew or Do Not Renew.
If renewal is approved, Attorney processes the maintenance action and records the transaction/status in PMS.
PMS maintains renewal history and schedules the next maintenance cycle.
2.3.10 Office Actions and Responses
PMS records office actions received from patent offices.
Attorney reviews office actions and prepares draft responses.
Applicant reviews and approves a response when the applicable process requires Applicant review.
Attorney finalizes and submits responses within applicable deadlines.
Attorney files extension requests when additional time is needed and the process allows extension.
PMS tracks response submission and updates status.
PMS automates timeline and deadline tracking for office-action responses where applicable deadline data is available.
2.3.11 Application Withdrawal
Applicants may withdraw applications before the filing stage.
PMS validates that withdrawal is allowed based on current application status.
Applicant must provide a withdrawal reason.
PMS records co-inventor consent when the applicable process requires consent.
PMS updates application status to Withdrawn and removes the application from the active queue.
PMS maintains withdrawal history.
2.3.12 Co-Inventor and Agreement Management
Applicants manage multiple inventors and ownership shares.
PMS validates inventor information and ownership percentages.
PMS collects and validates inventor consent and electronic signatures where legally permitted and configured.
Inventor agreements must be completed before filing.
PMS sends notifications to affected parties when inventor information changes.
2.3.13 Prior Art Search
Applicants and Attorneys can search for prior-art references through PMS-supported search facilities.
PMS queries relevant patent and publication databases where integrations or search access are available.
PMS displays search results with relevance ranking.
Users can attach selected references to an application.
PMS logs search sessions for audit trail.
PMS supports keyword optimization and classification mapping as part of the search process.
2.3.14 Document Version Management
PMS maintains version history of application documents.
Users can upload new document versions where their role and application status permit upload.
PMS applies automatic version numbering.
Previous document versions are archived and accessible according to role and status access rules.
PMS logs document modifications with user and timestamp.
Document access is controlled based on user role and application status.
Applicants can edit documents only when application status is Needs Revision.
2.3.15 Patent Licensing and Technology Transfer
Applicants can submit licensing or technology-transfer requests.
PMS routes such requests to the appropriate committee or Director as stated by the applicable institutional process.
PMS tracks negotiation process information.
PMS records final agreements.
PMS updates or shares financial-system information where integration is available.
PMS maintains license records with confidentiality controls.
2.3.16 Appeal Process
Applicants may file appeals against rejected applications.
Appeals must be filed within the applicable allowed time period.
Applicant provides grounds and justification for appeal.
Director reviews appeal and supporting documentation.
Director may Uphold Rejection, Remand for Amendment, or Modify Decision.
PMS records the appeal outcome and initiates the next applicable process step.
2.3.17 Deadline Management and Tracking
PMS calculates and monitors patent-management deadlines where deadline rules are available.
Deadlines include review deadlines, revision deadlines, office-action response deadlines, and maintenance-fee deadlines.
PMS generates alerts at configurable intervals, including 30 days, 15 days, and 5 days before deadline where applicable.
PMS sends deadline notifications to relevant stakeholders.
Missed deadlines trigger escalations according to the configured escalation chain.
PMS logs deadline-tracking activities.
2.3.18 Reports and Analytics
PCC_ADMIN and Directors can generate PMS reports.
Available reports include application status and progress reports, financial and budget reports, deadline and pending-action reports, inventor and co-inventor reports, patent portfolio analysis, and workload and assignment reports.
PMS supports scheduled reports, exportable reports, and customizable reports as stated in the source baseline.
PMS logs report access for audit purposes.
PMS provides dashboards, historical data analysis, trend reporting, and workload analytics within the explicitly stated PMS reporting scope.
2.3.19 Notifications
PMS issues system-generated email notifications for application submission and status changes.
PMS issues notifications for assignment to Director or Attorney.
PMS issues notifications for review decisions: approve, reject, or revision.
PMS issues notifications for budget approval or rejection.
PMS issues notifications for filing confirmations and office actions.
PMS issues notifications for deadline reminders and escalations.
PMS issues notifications for maintenance-fee reminders.
PMS issues notifications for document updates and version changes.
PMS notification triggering is within module scope; central email delivery infrastructure is outside PMS scope.
2.3.20 Audit Trail and Compliance
PMS maintains audit trails of PMS actions.
PMS logs user actions, status changes, and document modifications.
PMS logs include user ID, action type, timestamp, application ID, previous state, and new state where applicable.
Critical operations create immutable audit records.
Audit logs support compliance verification and forensic analysis.
PMS supports document sensitivity classification, role-based access control, and version control for confidential patent information.
PMS applies data encryption at rest and in transit where this security requirement is implemented by the platform/module boundary.
2.3.21 PMS Role, Workflow, Integration, and System Boundaries
Exactly one active PCC_ADMIN oversees PMS.
Multiple Directors handle reviews based on expertise domains.
Multiple Attorneys from approved panels conduct legal assessments.
Multiple Applicants submit applications.
PMS supports automated routing based on configurable rules, status-driven workflow, escalation mechanisms for delayed actions, and parallel processing where explicitly applicable.
PMS may integrate with patent office systems, financial systems, email notification systems, and document management systems where available.
External systems remain outside PMS unless PMS explicitly validates, routes, records, notifies, logs, or reports based on their data or events.
The System is not treated as a regular primary actor in later use cases derived from this problem statement. System behavior appears as internal validation, routing, status update, deadline calculation, notification, escalation, postcondition, maintained data, or reporting behavior.
2.4 Scope Boundaries
PMS does not own HR master data, payroll, platform-wide user-account administration, procurement execution, payment execution, external accounting operations, patent-office decision making, external legal decisions, or external database operation.
PMS may reference external policies, laws, patent-office requirements, jurisdiction schedules, and institutional committees only where PMS explicitly validates, restricts, routes, records, notifies, escalates, or reports based on them.
PMS does not define the cost-escalation threshold, office-action response deadlines, jurisdiction maintenance schedules, exact appeal deadline, exact authorization hierarchy, legal/e-signature validity rules, or external patent-office standards unless such values are configured in PMS.
Non-functional items in the source statement are retained only where they create explicit system-relevant functional behavior, such as audit logging, role-based access control, malware validation, document version control, notifications, reporting, deadline tracking, and encryption boundary statements.
End of Synchronized Problem Statement
