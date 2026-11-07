# PMS use cases: budget, attorney, patentability, filing, office actions, maintenance (read-only spec)

### UC-PMS-009 — Review and Decide Patent Budget
Actor: Director
Goal: Review filing/prosecution costs and record a budget decision or escalation.
Preconditions: Application status is Approved.
Main flow:
  1. PMS presents filing fees, attorney fees, administrative costs, and available budget information where such data is available.
  2. Director reviews the proposed cost.
  3. If the cost is within the configured threshold, Director records the budget decision.
  4. If the cost exceeds the configured threshold, PMS routes/escalates the case to the applicable higher authority.
  5. PMS records financial/authorization metadata and triggers the applicable budget notification.
Alternatives:
  • Within-threshold outcome may be Budget Approved or Budget Rejected.
  • Above-threshold cases result in Escalated rather than an invented higher-authority decision.
Exceptions:
  • If budget-availability data is required and available but validation fails, PMS does not record approval.
Postcondition: Budget decision or escalation state is recorded with audit/financial metadata.
Rules: BR-PMS-048; BR-PMS-049; BR-PMS-050; BR-PMS-051; BR-PMS-052; BR-PMS-053; BR-PMS-126

### UC-PMS-010 — Assign Attorney to Approved Application
Actor: PCC_ADMIN
Goal: Select and assign an eligible Attorney to an Approved application.
Preconditions: Application status is Approved; PCC_ADMIN is authorized.
Main flow:
  1. PCC_ADMIN reviews eligible attorneys using approved-panel status, expertise, workload, conflict-of-interest, and permitted Applicant preference.
  2. PMS blocks a non-panel attorney unless a recorded institutional exception permits the assignment.
  3. PCC_ADMIN selects and records the Attorney assignment.
  4. PMS records the assignment and notifies the Attorney for acceptance/decline.
Alternatives:
  • A preferred Attorney is considered only when that Attorney is in the approved panel.
  • An approved institutional exception may permit a non-panel attorney.
Exceptions:
  • If conflict-of-interest or other assignment constraints fail, PMS does not record the assignment.
Postcondition: An Attorney assignment is recorded and is awaiting/subject to the Attorney response.
Rules: BR-PMS-040; BR-PMS-041; BR-PMS-042; BR-PMS-043; BR-PMS-044; BR-PMS-045; BR-PMS-127; BR-PMS-126

### UC-PMS-011 — Accept or Decline Attorney Assignment
Actor: Attorney
Goal: Record the assigned Attorney's acceptance or decline decision.
Preconditions: An assignment to the Attorney exists.
Main flow:
  1. Attorney reviews the assignment.
  2. Attorney chooses Accept or Decline.
  3. PMS records the response.
  4. On acceptance, PMS records the assignment as accepted/Attorney Assigned; on decline, PMS records Pending Review as applicable and notifies PCC_ADMIN.
Alternatives:
  • Accept and Decline are the two supported outcomes.
Exceptions:
  • If no active assignment exists for the Attorney, PMS does not accept a response.
Postcondition: The Attorney response and applicable assignment/application state are recorded.
Rules: BR-PMS-126

### UC-PMS-012 — Conduct Patentability Assessment
Actor: Attorney
Goal: Record legal/patentability analysis and a supported filing recommendation.
Preconditions: Attorney has the assigned application and required access.
Main flow:
  1. Attorney reviews the application and performs/records relevant prior-art research.
  2. Attorney evaluates novelty, non-obviousness, and utility.
  3. Attorney records a detailed patentability opinion.
  4. Attorney selects one recommendation: File Patent, Do Not File, or Needs Amendment.
  5. PMS records the opinion and notifies relevant stakeholders.
Alternatives:
  • Attorney may request additional information or an extension where PMS/the applicable process supports it.
Exceptions:
  • If the opinion does not contain one supported recommendation, PMS does not finalize the opinion.
Postcondition: A patentability opinion and recommendation are recorded.
Rules: BR-PMS-046; BR-PMS-126; BR-PMS-141

### UC-PMS-013 — Prepare and Record External Patent Filing
Actor: Attorney
Goal: Prepare a filing package, perform supported validation, submit externally, and record filing confirmation in PMS.
Preconditions: Required approvals and budget allocation are complete; inventor agreements are complete; Attorney has filing authority/access.
Main flow:
  1. Attorney prepares the application package.
  2. Where validation rules are available, PMS validates the package against applicable patent-office standards.
  3. For an international filing, Attorney records the required additional justification.
  4. Attorney submits the package to the selected patent office outside PMS.
  5. Attorney/PMS records the external filing ID, filing date, and confirmation.
  6. PMS sets application status to Filed, records audit/history, and triggers filing confirmation.
Alternatives:
  • National and international filings use their applicable requirements; international filing additionally requires justification.
Exceptions:
  • If a required approval/budget/agreement prerequisite is missing, PMS blocks filing.
  • If external submission or confirmation is not obtained, PMS does not represent the filing as successfully Filed.
Postcondition: External filing details are recorded and application status is Filed.
Rules: BR-PMS-020; BR-PMS-055; BR-PMS-056; BR-PMS-128; BR-PMS-138; BR-PMS-142; BR-PMS-126

### UC-PMS-014 — Record Patent Office Communication
Actor: Attorney
Goal: Record official patent-office communication, including an office action, for lifecycle tracking.
Preconditions: Application/family record exists; Attorney has access.
Main flow:
  1. Attorney records the communication type, date, details, and supporting document/identifier.
  2. PMS logs the communication.
  3. If the communication is an office action, PMS creates/updates the office-action tracking information and triggers the office-action notification.
Alternatives:
  • Non-office-action official communications are recorded without initiating an office-action response path.
Exceptions:
  • Invalid/unrelated communication data is not attached to another application.
Postcondition: The official communication is recorded; office actions are available for response tracking.
Rules: BR-PMS-138; BR-PMS-142; BR-PMS-126

### UC-PMS-015 — Respond to Office Action
Actor: Attorney
Goal: Prepare, finalize, and record submission of an office-action response within applicable timing rules.
Preconditions: Office action exists; Attorney has access; applicable deadline/extension data is available where required.
Main flow:
  1. Attorney reviews the office action and prepares a draft response.
  2. If Applicant review is required, PMS makes the draft available for UC-PMS-029 and records the response as awaiting Applicant approval.
  3. If Applicant review is not required, or after required Applicant approval is recorded, Attorney finalizes the response.
  4. Attorney submits the response externally and records submission/status in PMS.
  5. PMS updates response tracking and audit/history information.
Alternatives:
  • If additional time is needed and the applicable process permits an extension, Attorney records/files an extension request.
Exceptions:
  • PMS does not mark a response submitted unless the required Applicant approval (when applicable) and submission record exist.
  • A missed deadline is handled by the deadline/escalation rules; PMS does not invent a legal outcome.
Postcondition: Response submission/extension status is recorded.
Rules: BR-PMS-065; BR-PMS-066; BR-PMS-146; BR-PMS-138; BR-PMS-126

### UC-PMS-017 — Manage Post-Grant Tracking and Maintenance
Actor: Attorney
Goal: Track granted patents, maintenance schedules, renewal decisions, and recorded maintenance actions.
Preconditions: Patent status is Granted for post-grant tracking.
Main flow:
  1. PMS activates post-grant tracking and calculates the applicable maintenance schedule where schedule rules/data are available.
  2. Attorney monitors the upcoming maintenance deadline and requests an explicit renewal decision from the Director.
  3. After a Renew decision is recorded through UC-PMS-018, Attorney processes/records the maintenance action, transaction information, and resulting status.
  4. PMS maintains renewal history and schedules the next maintenance cycle.
Alternatives:
  • If the Director records Do Not Renew, no renewal maintenance action is recorded as approved.
Exceptions:
  • If schedule rules/data are unavailable, PMS does not fabricate a maintenance schedule.
Postcondition: Post-grant maintenance state/history is updated according to the Director decision.
Rules: BR-PMS-059; BR-PMS-060; BR-PMS-061; BR-PMS-100; BR-PMS-126

### UC-PMS-018 — Make Maintenance Renewal Decision
Actor: Director
Goal: Record the required Renew or Do Not Renew decision for an upcoming maintenance deadline.
Preconditions: Patent is in post-grant tracking and a renewal decision is due.
Main flow:
  1. Director reviews the patent and available maintenance information.
  2. Director chooses Renew or Do Not Renew.
  3. PMS records the decision and makes it available to the Attorney for the next applicable maintenance action.
Alternatives:
  • Renew and Do Not Renew are the supported outcomes.
Exceptions:
  • If the patent is not in the applicable Granted/post-grant context, PMS does not accept the renewal decision.
Postcondition: One renewal decision is recorded for the maintenance cycle.
Rules: BR-PMS-059; BR-PMS-061; BR-PMS-126

### UC-PMS-029 — Review Office-Action Response
Actor: Applicant
Goal: Review and approve an Attorney-prepared office-action response when the applicable process requires Applicant review.
Preconditions: The applicable process requires Applicant review; a draft response exists.
Main flow:
  1. Applicant reviews the draft response.
  2. Applicant records approval of the response.
  3. PMS records the approval so the Attorney can finalize/submit the response.
Alternatives:
  • If Applicant review is not required, this use case is not invoked.
Exceptions:
  • If approval is not recorded, PMS must not treat the response as Applicant-approved; the PS does not define an alternate Applicant decision outcome.
Postcondition: Required Applicant approval is recorded.
Rules: BR-PMS-146; BR-PMS-126
