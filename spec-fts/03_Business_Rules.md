# Fusion ERP – File Tracking System (FTS)
## Business Rule Specifications — Final v1.3

| Project | Fusion ERP |
| --- | --- |
| Module Code | FTS |
| Module | File Tracking System (FTS) |
| Artifact | Business Rule Specifications |
| Version | v1.3 |
| Date | 2026-08-30 |
| Basis | v1.2 synchronized baseline + DIRECT_FINAL_v2 capsule |
| Status | FINAL |
| Active Business Rules | 14 |
| Retired/Reclassified Legacy Rules | 1 |

### 1. Business Rule Index
| BR ID | Name | Rule Type | Status |
| --- | --- | --- | --- |
| BR-FTS-001 | Institute Employee Operational Access Rule | Authorization | Active |
| BR-FTS-002 | Role Switching Preservation Rule | Constraint | Active |
| BR-FTS-003 | Persistent Composite File Rule | Data / Lifecycle Constraint | Active |
| BR-FTS-004 | Initial Comment Requirement | Validation | Active |
| BR-FTS-005 | Draft Boundary Rule | Lifecycle Constraint | Active |
| BR-FTS-006 | File-Movement Comment Requirement | Validation | Active |
| BR-FTS-007 | Receiver and Return Eligibility Rule | Eligibility / Routing | Active |
| BR-FTS-008 | Chronological Movement Record Rule | Audit / Record Constraint | Active |
| BR-FTS-009 | Associated File Access Rule | Authorization | Active |
| BR-FTS-010 | Role-Based Access and Sensitive Action Rule | Authorization | Active |
| BR-FTS-011 | Audit Log and Chronological Versioning Rule | Audit / Lifecycle | Active |
| BR-FTS-012 | Archival Rule | Lifecycle / Authorization | Active |
| BR-FTS-013 | Notification Trigger and Delivery Boundary Rule | Trigger / Scope Boundary | Active |
| BR-FTS-014 | FTS Integration Boundary Rule | Scope / Integration Constraint | Active |

### 2. Business Rule Specifications

#### BR-FTS-001 — Institute Employee Operational Access Rule
- **Rule Type**: Authorization
- **Rule Statement**: Only Institute Employee users (Faculty/Staff operating under assigned roles) may perform operational file-processing actions in FTS.
- **Applies To**: Operational file actions
- **Condition / Trigger**: Whenever an operational file action is requested.
- **Required Outcome / Constraint**: Allow operational processing only for authorized Institute Employees; System Admin remains outside routine operational file processing.
- **Exceptions / Exclusions**: System Admin governance actions are permitted only within the separate governance scope.
- **Source / Rationale**: PS §2 Actors; §3.6 Access Control
- **Status**: Active

#### BR-FTS-002 — Role Switching Preservation Rule
- **Rule Type**: Constraint
- **Rule Statement**: Switching assigned role context shall not change existing file ownership or previously recorded audit history.
- **Applies To**: Role-context switching
- **Condition / Trigger**: An Institute Employee selects another assigned role context.
- **Required Outcome / Constraint**: Apply the selected role to authorization while preserving ownership and historical audit identity.
- **Exceptions / Exclusions**: None stated.
- **Source / Rationale**: PS §2 Actors; §3.6
- **Status**: Active

#### BR-FTS-003 — Persistent Composite File Rule
- **Rule Type**: Data / Lifecycle Constraint
- **Rule Statement**: An FTS file is a persistent composite object containing mandatory user comments at creation/movement stages and optional attachments; circulated contents and movement records are retained.
- **Applies To**: File object and accumulated contents
- **Condition / Trigger**: File creation or movement adds content to a file.
- **Required Outcome / Constraint**: Persist the file and accumulated contents after circulation; do not delete circulated contents through draft-discard behavior.
- **Exceptions / Exclusions**: A pre-submission draft may be discarded under BR-FTS-005.
- **Source / Rationale**: PS Overview ¶5; §3.1
- **Status**: Active

#### BR-FTS-004 — Initial Comment Requirement
- **Rule Type**: Validation
- **Rule Statement**: A new FTS file requires an initial mandatory user comment.
- **Applies To**: File creation
- **Condition / Trigger**: Employee attempts to create/save a new file.
- **Required Outcome / Constraint**: Block acceptance of file creation until the initial comment is present.
- **Exceptions / Exclusions**: None stated.
- **Source / Rationale**: PS Overview ¶5; §3.1
- **Status**: Active

#### BR-FTS-005 — Draft Boundary Rule
- **Rule Type**: Lifecycle Constraint
- **Rule Statement**: Draft save/edit/discard behavior is permitted only before submission/circulation; a circulated file is not deleted as a draft.
- **Applies To**: Draft management and initial circulation
- **Condition / Trigger**: Draft management or first circulation is attempted.
- **Required Outcome / Constraint**: Permit draft operations only in pre-circulation state and prevent draft deletion after circulation.
- **Exceptions / Exclusions**: None stated.
- **Source / Rationale**: PS §3.1
- **Status**: Active

#### BR-FTS-006 — File-Movement Comment Requirement
- **Rule Type**: Validation
- **Rule Statement**: Every file-movement action requires a mandatory comment from the acting user.
- **Applies To**: Forwarding and return
- **Condition / Trigger**: Employee attempts to forward or return a file.
- **Required Outcome / Constraint**: Block the movement until the mandatory movement comment is supplied.
- **Exceptions / Exclusions**: None stated.
- **Source / Rationale**: PS Overview ¶5; §3.2
- **Status**: Active

#### BR-FTS-007 — Receiver and Return Eligibility Rule
- **Rule Type**: Eligibility / Routing
- **Rule Statement**: A file may be sent to another Institute Employee regardless of the receiver’s role, and a received file may be returned to its sender where the current user is permitted to act.
- **Applies To**: Forwarding and return
- **Condition / Trigger**: A recipient is selected or Return is requested.
- **Required Outcome / Constraint**: Accept only a valid Institute Employee recipient for send/forward; route return to the sender of the received movement, subject to authorization/file-state permissions.
- **Exceptions / Exclusions**: The baseline does not further define every role/state permission case.
- **Source / Rationale**: PS §3.2
- **Status**: Active

#### BR-FTS-008 — Chronological Movement Record Rule
- **Rule Type**: Audit / Record Constraint
- **Rule Statement**: FTS shall record forwarding and return events chronologically with sender, receiver, timestamp, movement comment, and movement attachments where present.
- **Applies To**: File movement tracking/history
- **Condition / Trigger**: A forward or return movement succeeds.
- **Required Outcome / Constraint**: Append the movement event and its stated details to chronological history; update holder/pending-recipient information consistently.
- **Exceptions / Exclusions**: None stated.
- **Source / Rationale**: PS §3.2; §3.4
- **Status**: Active

#### BR-FTS-009 — Associated File Access Rule
- **Rule Type**: Authorization
- **Rule Statement**: FTS shall expose file contents/history only to users authorized and associated with the file, including Inbox/Outbox access; archived files remain readable to authorized users.
- **Applies To**: Inbox, Outbox, file/history reading
- **Condition / Trigger**: A user requests file or history access.
- **Required Outcome / Constraint**: Show/open only authorized associated files and retain authorized read access after archival.
- **Exceptions / Exclusions**: Unauthorized files/history are not exposed.
- **Source / Rationale**: PS §3.3; §3.4; §3.5
- **Status**: Active

#### BR-FTS-010 — Role-Based Access and Sensitive Action Rule
- **Rule Type**: Authorization
- **Rule Statement**: FTS shall enforce RBAC, assigned-role restrictions, file association, and file-state authorization for FTS actions, including integrations.
- **Applies To**: All FTS operations and integrations
- **Condition / Trigger**: Any protected FTS action is requested.
- **Required Outcome / Constraint**: Permit only actions authorized by role/context/file association/file state; reject unauthorized sensitive actions.
- **Exceptions / Exclusions**: Platform-wide RBAC administration remains outside FTS except for FTS-relevant governance/context.
- **Source / Rationale**: PS §3.6; §3.9
- **Status**: Active

#### BR-FTS-011 — Audit Log and Chronological Versioning Rule
- **Rule Type**: Audit / Lifecycle
- **Rule Statement**: FTS shall maintain audit records for creation, comments, attachments, forwarding, return, archival, and integration actions, and maintain chronological version history through recorded file updates.
- **Applies To**: Audit/versioning
- **Condition / Trigger**: An auditable FTS action occurs.
- **Required Outcome / Constraint**: Append the applicable audit/version record without rewriting prior chronological history.
- **Exceptions / Exclusions**: Backup implementation is outside this rule and outside the FTS functional scope.
- **Source / Rationale**: PS §3.7; §3.9
- **Status**: Active

#### BR-FTS-012 — Archival Rule
- **Rule Type**: Lifecycle / Authorization
- **Rule Statement**: Only the file owner may archive a completed circulated file; archived files remain permanently stored/readable to authorized users and are no longer modifiable or forwardable in collaborative processing.
- **Applies To**: File archival
- **Condition / Trigger**: Archive is requested or an action is attempted on an archived file.
- **Required Outcome / Constraint**: Allow archival only for the owner after collaborative completion; enforce archived read-only/no-forward state.
- **Exceptions / Exclusions**: The baseline does not define a formal system criterion for determining “objective complete.”
- **Source / Rationale**: PS Overview ¶5; §3.5
- **Status**: Active

#### BR-FTS-013 — Notification Trigger and Delivery Boundary Rule
- **Rule Type**: Trigger / Scope Boundary
- **Rule Statement**: FTS shall trigger notifications for file received, file forwarded, file returned, file archived, and relevant role assignment/reassignment events; delivery uses Fusion integrated notification mechanisms.
- **Applies To**: FTS notification events
- **Condition / Trigger**: A source-listed FTS event occurs.
- **Required Outcome / Constraint**: Create/trigger the required notification event and hand it to the Fusion notification mechanism.
- **Exceptions / Exclusions**: Central notification infrastructure and exact recipient semantics are outside/not fully specified by the FTS baseline.
- **Source / Rationale**: PS §3.8
- **Status**: Active

#### BR-FTS-014 — FTS Integration Boundary Rule
- **Rule Type**: Scope / Integration Constraint
- **Rule Statement**: FTS may provide file/workflow tracking APIs, approval-chain support, and file-based request tracking to other Fusion modules, while consuming modules retain ownership of their domain-specific actors, forms, policies, validations, and workflow semantics.
- **Applies To**: Inter-module API integration
- **Condition / Trigger**: A consuming Fusion module invokes an FTS service.
- **Required Outcome / Constraint**: Provide only authorized FTS capabilities under FTS RBAC/audit rules; do not assume ownership of consuming-module domain policy.
- **Exceptions / Exclusions**: Consuming module retains domain-specific approval rules and semantics.
- **Source / Rationale**: PS §3.9; §3.10
- **Status**: Active

### Appendix A — Reclassified Legacy Rule
- **BR-FTS-015 — System Actor Modeling Constraint**: Reclassified as a specification/modeling convention rather than runtime business logic.
