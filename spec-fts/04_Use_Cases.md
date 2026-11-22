# Fusion ERP – File Tracking System (FTS)
## Use Case Specifications — Final v1.3

| Project | Fusion ERP |
| --- | --- |
| Module Code | FTS |
| Module | File Tracking System (FTS) |
| Artifact | Use Case Specifications |
| Version | v1.3 |
| Date | 2026-08-30 |
| Basis | v1.2 synchronized baseline + DIRECT_FINAL_v2 capsule |
| Status | FINAL |
| Active Use Cases | 10 |
| Retired Legacy Use Cases | 1 |
| UC Trigger Types | All active UCs are Actor-triggered; no separate SF artifact is used |

### 1. Use Case Index
| UC ID | Name | UC Type | Primary Actor | Related Workflow(s) |
| --- | --- | --- | --- | --- |
| FTS-UC-001 | Create New File | Actor-triggered | Institute Employee | BW-FTS-05, BW-FTS-06, BW-FTS-07, BW-FTS-08, CW-FTS-02 |
| FTS-UC-002 | Edit or Discard Draft File | Actor-triggered | Institute Employee | BW-FTS-06, BW-FTS-07, BW-FTS-08, CW-FTS-02 |
| FTS-UC-003 | Send / Forward File to Employee | Actor-triggered | Institute Employee (Sender / Current Holder) | BW-FTS-01, BW-FTS-02, BW-FTS-05, BW-FTS-06, CW-FTS-01, CW-FTS-02 |
| FTS-UC-004 | Return Received File | Actor-triggered | Institute Employee (Recipient / Current Holder) | BW-FTS-03, CW-FTS-01 |
| FTS-UC-005 | View Inbox, Outbox, and Open Files | Actor-triggered | Institute Employee | N/A |
| FTS-UC-006 | View File Tracking History | Actor-triggered | Institute Employee | N/A |
| FTS-UC-007 | Archive Completed File | Actor-triggered | Institute Employee / File Owner | BW-FTS-04, CW-FTS-01 |
| FTS-UC-008 | Select Assigned Role Context for FTS | Actor-triggered | Institute Employee | N/A |
| FTS-UC-009 | Administer FTS User Access Context | Actor-triggered | System Admin | N/A |
| FTS-UC-010 | Use FTS Workflow-Support APIs | Actor-triggered | Authorized Consuming Fusion Module | N/A |

### 2. Use Case Specifications

#### FTS-UC-001 — Create New File
- **UC Type**: Actor-triggered
- **Primary Actor**: Institute Employee
- **Supporting Actors / Systems**: None
- **Goal / Description**: Create a new FTS file under an assigned role with the required initial comment and optional attachments, leaving a valid pre-circulation file that may be retained as a draft or subsequently sent through FTS-UC-003.
- **Trigger**: Employee selects Create File from the Fusion/FTS interface.
- **Preconditions**: Employee is authenticated, has an assigned role context, and is authorized to create files.
- **Main Success Scenario**:
  1. Employee opens the file-creation function.
  2. Employee enters the initial mandatory comment.
  3. Employee optionally adds attachments.
  4. Employee saves the created file as a draft/pre-circulation file.
  5. FTS validates the required comment, persists the file object and records creation/comment/attachment audit information.
- **Alternative Flows**:
  1. If the employee chooses immediate circulation instead of retaining the draft, the valid created file proceeds through the independent actor goal FTS-UC-003 (Send/Forward File to Employee).
  2. If no attachment is supplied, creation proceeds because attachments are optional.
- **Exception Flows**:
  1. If the initial comment is missing, FTS does not accept creation/save until the comment is supplied.
  2. If the selected role is not authorized to create files, FTS denies the action.
- **Success Postcondition**: A valid file exists in a draft/pre-circulation state with its initial comment and any attachments preserved; creation/audit information is recorded.
- **Failure / Minimal Guarantee**: No circulated file is created. A file record exists only if a valid save/create operation completed.
- **Related Business Rules**: BR-FTS-001, BR-FTS-003, BR-FTS-004, BR-FTS-005, BR-FTS-010, BR-FTS-011
- **Related Workflow(s)**: BW-FTS-05, BW-FTS-06, BW-FTS-07, BW-FTS-08, CW-FTS-02

#### FTS-UC-002 — Edit or Discard Draft File
- **UC Type**: Actor-triggered
- **Primary Actor**: Institute Employee
- **Supporting Actors / Systems**: None
- **Goal / Description**: Edit a saved draft before circulation or discard that draft before submission.
- **Trigger**: Employee opens an existing draft file.
- **Preconditions**: The file exists as a draft/pre-circulation file and the employee is authorized to edit it.
- **Main Success Scenario**:
  1. Employee opens an authorized draft.
  2. Employee edits the draft comment and/or attachments as needed.
  3. Employee saves the updated draft.
  4. FTS persists the update and records applicable audit/version information.
- **Alternative Flows**:
  1. Employee may choose Discard instead of Save; FTS removes the draft because it has not yet been submitted/circulated.
- **Exception Flows**:
  1. If the file has already been submitted/circulated, FTS does not permit draft discard.
  2. If the employee is not authorized for the draft, FTS denies access/action.
- **Success Postcondition**: The draft is either updated and retained or discarded before circulation.
- **Failure / Minimal Guarantee**: A circulated file is never deleted through this use case; unauthorized or invalid-state actions leave the file unchanged.
- **Related Business Rules**: BR-FTS-005, BR-FTS-010, BR-FTS-011
- **Related Workflow(s)**: BW-FTS-06, BW-FTS-07, BW-FTS-08, CW-FTS-02

#### FTS-UC-003 — Send / Forward File to Employee
- **UC Type**: Actor-triggered
- **Primary Actor**: Institute Employee (Sender / Current Holder)
- **Supporting Actors / Systems**: Recipient Institute Employee
- **Goal / Description**: Send an active file to another Institute Employee, including initial circulation or onward forwarding of a received file.
- **Trigger**: Authorized employee selects Send/Forward on an actionable file.
- **Preconditions**: File exists and is not archived; sender is authorized to act; a valid recipient Institute Employee can be selected.
- **Main Success Scenario**:
  1. Sender opens the actionable file and selects a recipient Institute Employee.
  2. Sender enters the mandatory movement comment.
  3. Sender optionally adds attachments for this movement stage.
  4. Sender confirms Send/Forward.
  5. FTS validates authorization, file state, recipient, and mandatory comment.
  6. FTS records sender, receiver, timestamp, movement comment, and any attachments chronologically; updates the current holder/pending recipient; and records audit/version information.
  7. FTS triggers the applicable file-forwarded/file-received notification event(s) for delivery through Fusion notification mechanisms.
- **Alternative Flows**:
  1. A recipient of an earlier movement may use the same goal to forward the received file onward to another Institute Employee.
  2. If no attachment is supplied, forwarding proceeds because attachments are optional.
- **Exception Flows**:
  1. Missing mandatory movement comment: forwarding is blocked.
  2. Invalid recipient: forwarding is blocked.
  3. Unauthorized action or archived file: forwarding is blocked and file state is unchanged.
- **Success Postcondition**: The file remains active/circulated and is held by the selected recipient; movement/history/audit records are updated and the required notification event(s) are triggered.
- **Failure / Minimal Guarantee**: No movement occurs and the prior holder/state remains authoritative.
- **Related Business Rules**: BR-FTS-001, BR-FTS-003, BR-FTS-005, BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-010, BR-FTS-011, BR-FTS-012, BR-FTS-013
- **Related Workflow(s)**: BW-FTS-01, BW-FTS-02, BW-FTS-05, BW-FTS-06, CW-FTS-01, CW-FTS-02

#### FTS-UC-004 — Return Received File
- **UC Type**: Actor-triggered
- **Primary Actor**: Institute Employee (Recipient / Current Holder)
- **Supporting Actors / Systems**: Previous Sender Institute Employee
- **Goal / Description**: Return an active received file to its sender with the required movement comment and optional attachment.
- **Trigger**: Recipient selects Return on a received actionable file.
- **Preconditions**: The file is active, associated with the recipient, has a known sender for the current movement, and the recipient is authorized to return it.
- **Main Success Scenario**:
  1. Recipient opens the received file and selects Return.
  2. Recipient enters the mandatory movement comment.
  3. Recipient optionally adds attachments for this movement stage.
  4. Recipient confirms Return.
  5. FTS validates authorization, active file state, and mandatory comment.
  6. FTS records the return chronologically, including movement details; updates the current holder/pending recipient to the previous sender; and records audit/version information.
  7. FTS triggers the file-returned notification event for delivery through Fusion notification mechanisms.
- **Alternative Flows**:
  1. If no attachment is supplied, return proceeds because attachments are optional.
- **Exception Flows**:
  1. Missing mandatory movement comment: return is blocked.
  2. Unauthorized action or archived/completed file state: return is blocked and the file remains unchanged.
- **Success Postcondition**: The file remains active/circulated and is returned to the previous sender; history/audit records are updated and the return notification event is triggered.
- **Failure / Minimal Guarantee**: No return movement occurs and the current holder/state remains unchanged.
- **Related Business Rules**: BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-010, BR-FTS-011, BR-FTS-012, BR-FTS-013
- **Related Workflow(s)**: BW-FTS-03, CW-FTS-01

#### FTS-UC-005 — View Inbox, Outbox, and Open Files
- **UC Type**: Actor-triggered
- **Primary Actor**: Institute Employee
- **Supporting Actors / Systems**: None
- **Goal / Description**: View received and sent files and open files the employee is authorized to access.
- **Trigger**: Employee opens Inbox or Outbox.
- **Preconditions**: Employee is authenticated in an FTS role context.
- **Main Success Scenario**:
  1. Employee opens Inbox or Outbox.
  2. FTS lists files received by the employee in Inbox and files sent by the employee in Outbox, subject to authorization.
  3. Employee selects an authorized file.
  4. FTS displays the file contents, comments, attachments, status, and actions currently permitted by role and file state.
- **Alternative Flows**:
  1. If an authorized file is archived, FTS presents it as readable/read-only.
- **Exception Flows**:
  1. If the employee is not authorized to view a file, FTS does not expose/open that file.
  2. If an action is not authorized for the current file state/role, the action is unavailable or denied.
- **Success Postcondition**: Authorized file information is displayed; viewing alone does not change the business state.
- **Failure / Minimal Guarantee**: No unauthorized file content or action is exposed.
- **Related Business Rules**: BR-FTS-009, BR-FTS-010, BR-FTS-012
- **Related Workflow(s)**: N/A

#### FTS-UC-006 — View File Tracking History
- **UC Type**: Actor-triggered
- **Primary Actor**: Institute Employee
- **Supporting Actors / Systems**: None
- **Goal / Description**: View the complete chronological tracking history of a file with which the employee is authorized/associated.
- **Trigger**: Employee selects View History for a file.
- **Preconditions**: File exists and employee is authorized/associated with it.
- **Main Success Scenario**:
  1. Employee selects an associated file.
  2. Employee requests its tracking history.
  3. FTS retrieves the chronological history from creation onward.
  4. FTS displays movement events with sender, receiver, timestamp, movement comments, and movement attachments, together with recorded chronological updates.
- **Alternative Flows**:
  1. History may include creation, forward, return, and archival-related audit/version records as maintained by FTS.
- **Exception Flows**:
  1. If the employee is not authorized/associated with the file, FTS denies history access.
- **Success Postcondition**: Tracking history is displayed; viewing does not change file state.
- **Failure / Minimal Guarantee**: No unauthorized history is disclosed and stored history remains unchanged.
- **Related Business Rules**: BR-FTS-008, BR-FTS-010, BR-FTS-011
- **Related Workflow(s)**: N/A

#### FTS-UC-007 — Archive Completed File
- **UC Type**: Actor-triggered
- **Primary Actor**: Institute Employee / File Owner
- **Supporting Actors / Systems**: Associated Institute Employees (affected users)
- **Goal / Description**: Archive a completed circulated file as its owner, ending collaborative movement while retaining permanent read access for authorized users.
- **Trigger**: File owner selects Archive after the intended collaborative objective is complete.
- **Preconditions**: File has been circulated, is not already archived, the actor is the file owner, and the intended collaborative objective is complete.
- **Main Success Scenario**:
  1. Owner opens the active circulated file.
  2. Owner selects Archive.
  3. FTS verifies ownership and applicable authorization.
  4. FTS changes the file to Archived / Read-only state.
  5. FTS prevents subsequent modification and further forwarding/movement, while retaining permanent readable access for authorized users.
  6. FTS records the archival audit/version event and triggers the file-archived notification event.
- **Alternative Flows**:
  1. If the file is already archived, FTS presents the existing read-only state and performs no new archival transition.
- **Exception Flows**:
  1. A non-owner archival attempt is denied.
  2. If required authorization is absent, the file remains active and unchanged.
- **Success Postcondition**: File is Archived / Read-only, permanently retained for authorized reading, and no longer available for collaborative modification/forwarding.
- **Failure / Minimal Guarantee**: The file remains in its prior active state; no archival event is recorded.
- **Related Business Rules**: BR-FTS-009, BR-FTS-010, BR-FTS-011, BR-FTS-012, BR-FTS-013
- **Related Workflow(s)**: BW-FTS-04, CW-FTS-01

#### FTS-UC-008 — Select Assigned Role Context for FTS
- **UC Type**: Actor-triggered
- **Primary Actor**: Institute Employee
- **Supporting Actors / Systems**: Fusion dashboard / role context service
- **Goal / Description**: Use FTS under a selected assigned institutional role without changing existing file ownership or historical audit identity.
- **Trigger**: Employee switches or selects an assigned role context in the Fusion dashboard before/while using FTS.
- **Preconditions**: Employee has at least one assigned role; role switching is available when multiple roles are assigned.
- **Main Success Scenario**:
  1. Employee selects an assigned role context through Fusion.
  2. FTS consumes/applies the selected role context to determine permitted FTS access/actions.
  3. Employee continues using permitted FTS functions under that role context.
  4. FTS preserves existing file ownership and previously recorded audit history across the role switch.
- **Alternative Flows**:
  1. If the employee has only one applicable role, FTS uses that assigned role context without requiring a switch.
- **Exception Flows**:
  1. If the selected role does not authorize a requested sensitive action, FTS denies that action.
- **Success Postcondition**: Selected role context governs subsequent FTS authorization; existing ownership and audit history are unchanged.
- **Failure / Minimal Guarantee**: No unauthorized FTS action is enabled and existing file/audit records remain unchanged.
- **Related Business Rules**: BR-FTS-002, BR-FTS-010
- **Related Workflow(s)**: N/A

#### FTS-UC-009 — Administer FTS User Access Context
- **UC Type**: Actor-triggered
- **Primary Actor**: System Admin
- **Supporting Actors / Systems**: Institute Employee; Fusion administration/identity services
- **Goal / Description**: Administer the role/access context used by FTS and perform FTS governance oversight without participating in operational file processing.
- **Trigger**: System Admin opens an FTS/Fusion governance function relevant to FTS.
- **Preconditions**: System Admin has applicable administrative privileges.
- **Main Success Scenario**:
  1. System Admin assigns or reassigns FTS-relevant role/access context, manages FTS RBAC context, or reviews FTS usage/security/audit information within the available governance scope.
  2. FTS consumes and/or records the resulting role/access context needed for FTS authorization.
  3. For a relevant role assignment/reassignment, FTS triggers the corresponding notification event.
  4. FTS preserves the boundary that System Admin does not create, forward, return, comment on, or archive operational files on behalf of Institute Employees.
- **Alternative Flows**:
  1. Basic user-account creation remains a Fusion/platform administration responsibility where applicable; FTS consumes the resulting identity/account context rather than owning platform-wide user-directory administration.
- **Exception Flows**:
  1. If System Admin attempts an operational file workflow action, FTS denies that operational action.
- **Success Postcondition**: FTS governance/access context is available/updated as applicable; operational file ownership and processing remain with Institute Employees.
- **Failure / Minimal Guarantee**: No unauthorized operational file action occurs and existing file state remains unchanged.
- **Related Business Rules**: BR-FTS-001, BR-FTS-010, BR-FTS-011, BR-FTS-013
- **Related Workflow(s)**: N/A

#### FTS-UC-010 — Use FTS Workflow-Support APIs
- **UC Type**: Actor-triggered
- **Primary Actor**: Authorized Consuming Fusion Module
- **Supporting Actors / Systems**: Fusion identity/RBAC and audit context; Institute Employee context where supplied by caller
- **Goal / Description**: Invoke FTS-supported file/workflow tracking APIs for a consuming Fusion module while keeping domain-specific approval policy in the consuming module.
- **Trigger**: Authorized consuming Fusion module invokes an FTS API.
- **Preconditions**: Integration is authorized and provides the access/context required by FTS RBAC and audit rules.
- **Main Success Scenario**:
  1. Consuming module calls an FTS API for module-specific file workflow support, approval-chain support, or file-based request tracking.
  2. FTS validates integration authorization and applicable RBAC context.
  3. FTS performs the supported file/workflow-tracking service within the FTS boundary.
  4. FTS records applicable audit information for the integration action.
  5. FTS returns the service response to the consuming module.
- **Alternative Flows**:
  1. The consuming module may use different FTS service capabilities (workflow support, approval-chain support, or file-based request tracking) while retaining its own domain semantics.
- **Exception Flows**:
  1. Unauthorized integration is rejected.
  2. A request that asks FTS to define a consuming module’s domain-specific approval policy is outside FTS scope; the consuming module remains responsible for that policy.
- **Success Postcondition**: The authorized FTS service operation is completed/audited or the request is rejected without transferring domain-specific policy ownership to FTS.
- **Failure / Minimal Guarantee**: No unauthorized FTS integration action is performed; FTS does not invent or own consuming-module approval rules.
- **Related Business Rules**: BR-FTS-010, BR-FTS-011, BR-FTS-014
- **Related Workflow(s)**: N/A

### Appendix A — Retired Legacy Use Case
- **FTS-UC-011 — Receive FTS Notifications**: Retired. Represented as cross-cutting notification effects of the source actor UCs plus BR-FTS-013.
