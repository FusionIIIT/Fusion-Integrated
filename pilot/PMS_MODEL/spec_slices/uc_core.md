# PMS use cases: submission, Director review, revision, withdrawal, appeal, documents (read-only spec)

### UC-PMS-001 — Submit Patent Application
Actor: Applicant
Goal: Create and submit a complete patent application for institutional processing.
Preconditions: Applicant has a valid PMS role. A submission draft can be created.
Main flow:
  1. Applicant enters title, abstract, detailed description, claims, inventor information, and supporting documents.
  2. PMS validates required-field completeness and validates each submitted document as PDF, under 50 MB, and malware-free.
  3. PMS classifies accepted documents by sensitivity.
  4. Applicant confirms submission.
  5. PMS accepts the application, assigns a unique application ID, sets status to Submitted, records history/audit data, and triggers the submission notification.
Alternatives:
  • If required information is incomplete, PMS identifies the missing information and keeps the application unsubmitted.
  • If a document fails format, size, or malware validation, PMS rejects that document and keeps the valid prior application state.
Exceptions:
  • If an external validation dependency is unavailable, PMS does not treat the application as successfully accepted unless the required validation has completed.
Postcondition: An accepted application has a unique ID and status Submitted; its submission/history/audit record exists.
Rules: BR-PMS-014; BR-PMS-015; BR-PMS-016; BR-PMS-017; BR-PMS-126; BR-PMS-130

### UC-PMS-002 — Track Application Status and History
Actor: Applicant
Goal: View the current status, progress, and recorded history of the Applicant's own applications.
Preconditions: Applicant has a valid PMS role and access to the selected application.
Main flow:
  1. Applicant selects one of their patent applications.
  2. PMS displays current status/progress and the recorded application history available to the Applicant.
Alternatives:
  • Applicant may navigate among their own applications and available history entries.
Exceptions:
  • If the Applicant is not authorized for the selected record, PMS blocks access.
Postcondition: The Applicant has viewed current status/progress/history; no business state changes.
Rules: BR-PMS-003; BR-PMS-126; BR-PMS-130

### UC-PMS-003 — Manage Co-Inventors and Agreements
Actor: Applicant
Goal: Maintain inventor identities, ownership shares, consents, and agreements for an application.
Preconditions: Applicant has access to the application and the current role/status permits the requested change.
Main flow:
  1. Applicant adds or updates inventor information and ownership shares.
  2. PMS validates inventor information and ownership percentages.
  3. Where required, PMS records inventor consent and, where legally permitted and configured, collects/validates electronic signatures.
  4. PMS records agreement information and notifies affected parties when inventor information changes.
Alternatives:
  • Applicant may update the inventor set or ownership shares before filing, subject to applicable access/state rules.
Exceptions:
  • Invalid inventor information, ownership percentages, consent, or signature validation prevents the affected change from being accepted.
Postcondition: Valid inventor/agreement information is stored; agreement-completion state is available for the filing prerequisite.
Rules: BR-PMS-020; BR-PMS-073; BR-PMS-074; BR-PMS-075; BR-PMS-076; BR-PMS-077; BR-PMS-078; BR-PMS-126; BR-PMS-130

### UC-PMS-005 — Revise and Resubmit Application
Actor: Applicant
Goal: Revise an application after a Needs Revision or Rejected decision and resubmit it for a new review cycle.
Preconditions: Application status is Needs Revision or Rejected; the 60-day resubmission period has not expired.
Main flow:
  1. Applicant reviews the Director feedback.
  2. Applicant edits permitted application content/documents and uploads revised versions.
  3. PMS validates that the resubmission addresses the Director feedback and applies document/version rules.
  4. Applicant submits the revision.
  5. PMS records the revised version and starts a new review cycle.
Alternatives:
  • The Applicant may save revisions before final resubmission while the permitted revision state remains active.
Exceptions:
  • If the deadline has expired, PMS changes the application to Expired and does not accept a late resubmission.
  • If the submitted revision does not address the recorded Director feedback, PMS rejects the resubmission and retains the prior valid state.
Postcondition: A revised application is recorded for a new review cycle.
Rules: BR-PMS-033; BR-PMS-034; BR-PMS-035; BR-PMS-036; BR-PMS-038; BR-PMS-082; BR-PMS-087; BR-PMS-126

### UC-PMS-006 — Withdraw Patent Application
Actor: Applicant
Goal: Withdraw an application when the applicable pre-filing status permits withdrawal.
Preconditions: Application has not reached Filed status and the current application status is configured/defined as withdrawal-eligible.
Main flow:
  1. PMS checks that withdrawal is allowed for the current application status and before filing.
  2. Applicant provides a withdrawal reason.
  3. Where the applicable process requires it, PMS records co-inventor consent.
  4. Applicant confirms withdrawal.
  5. PMS sets status to Withdrawn, removes the application from the active queue, and records withdrawal history/status change.
Alternatives:
  • None beyond the conditional co-inventor-consent requirement.
Exceptions:
  • If the current status is not withdrawal-eligible, PMS blocks withdrawal and retains the current state.
Postcondition: The application is Withdrawn and no longer appears in the active queue.
Rules: BR-PMS-067; BR-PMS-068; BR-PMS-069; BR-PMS-070; BR-PMS-126

### UC-PMS-007 — Assign Application to Director
Actor: PCC_ADMIN
Goal: Assign a Submitted application to an eligible Director and start the review timeline.
Preconditions: Application status is Submitted; PCC_ADMIN is authorized, or configured automatic routing is enabled.
Main flow:
  1. PMS/PCC_ADMIN evaluates Director expertise, workload, and conflict-of-interest constraints.
  2. PMS prevents assignment to a Director who is listed as an inventor; PCC_ADMIN cannot act as reviewer where they are an inventor.
  3. PCC_ADMIN confirms the selected Director, or PMS performs configured automatic routing using the same rules.
  4. PMS records the assignment, sets status to Under Review, notifies the Director, and initiates the review deadline.
Alternatives:
  • Automatic routing may perform the assignment without treating the System as a primary actor.
Exceptions:
  • If no eligible assignment is available, PMS leaves the application Submitted and records/raises the exceptional case for PCC_ADMIN handling.
Postcondition: The application is assigned and status is Under Review, or remains Submitted if assignment is blocked.
Rules: BR-PMS-022; BR-PMS-023; BR-PMS-024; BR-PMS-025; BR-PMS-026; BR-PMS-027; BR-PMS-126

### UC-PMS-008 — Review Patent Application
Actor: Director
Goal: Review an assigned application and record one supported technical-merit decision.
Preconditions: Director is the assigned, non-conflicted reviewer; the application is Under Review.
Main flow:
  1. Director reviews application details, documents, and supporting materials.
  2. Director selects exactly one outcome: Approve, Reject, or Needs Revision.
  3. Director enters a detailed justification of at least 50 characters.
  4. Director submits the decision within the 15-business-day review period.
  5. PMS records the decision/audit trail. Approved applications become eligible for attorney assignment; Reject/Needs Revision decisions trigger detailed feedback to the Applicant.
Alternatives:
  • Reject and Needs Revision are valid alternative outcomes to Approve.
Exceptions:
  • A decision without the required justification is not accepted.
  • A conflicted/unassigned Director is not allowed to submit the review decision.
Postcondition: One review outcome is recorded with justification and audit history.
Rules: BR-PMS-026; BR-PMS-029; BR-PMS-030; BR-PMS-031; BR-PMS-126

### UC-PMS-019 — Manage Document Versions
Actor: Applicant (also Attorney/Director/PCC_ADMIN when authorized)
Goal: Upload, version, archive, and access application documents under role/status controls.
Preconditions: User has a valid PMS role; requested action is permitted for the role and application status.
Main flow:
  1. User uploads a new document version where permitted.
  2. PMS assigns the next version number and archives the previous version.
  3. PMS records the modification user and timestamp.
  4. Authorized users may access previous versions according to role/status rules.
Alternatives:
  • Applicants may edit application documents only in Needs Revision status.
  • Other roles may upload/access versions only where their role/status permission permits.
Exceptions:
  • Unauthorized upload/access is blocked and logged according to applicable audit/security behavior.
Postcondition: Document version history and access metadata are updated consistently.
Rules: BR-PMS-082; BR-PMS-084; BR-PMS-086; BR-PMS-087; BR-PMS-130; BR-PMS-140; BR-PMS-126

### UC-PMS-022 — File Appeal Against Rejection
Actor: Applicant
Goal: Submit a supported appeal against a Rejected application within the applicable appeal period.
Preconditions: Application is Rejected; the configured/institutional appeal period has not expired.
Main flow:
  1. Applicant enters grounds and justification for appeal.
  2. Applicant submits the appeal.
  3. PMS validates appeal eligibility/timing and records the appeal for Director review.
Alternatives:
  • None.
Exceptions:
  • An appeal submitted for a non-Rejected application or outside the allowed period is not accepted.
Postcondition: An eligible appeal is recorded as submitted for review.
Rules: BR-PMS-092; BR-PMS-093; BR-PMS-094; BR-PMS-126

### UC-PMS-023 — Review Appeal
Actor: Director
Goal: Review an appeal and record one permitted appeal outcome.
Preconditions: Appeal exists and is assigned/available for Director review.
Main flow:
  1. Director reviews the appeal and supporting documentation.
  2. Director selects one outcome: Uphold Rejection, Remand for Amendment, or Modify Decision.
  3. PMS records the appeal outcome and initiates the next applicable process step without inventing unspecified legal/process details.
Alternatives:
  • The three listed outcomes are alternative success results.
Exceptions:
  • An unsupported appeal outcome is not accepted.
Postcondition: Appeal outcome is recorded and the corresponding next-step state is initiated where defined.
Rules: BR-PMS-095; BR-PMS-126
