# Fusion ERP – File Tracking System (FTS)
## Two-Level Requirement Registry (CFR → AFR) — Final v1.3

| Project | Fusion ERP |
| --- | --- |
| Module Code | FTS |
| Module | File Tracking System (FTS) |
| Artifact | Two-Level Requirement Registry (CFR + AFR) |
| Version | v1.3 |
| Date | 2026-08-30 |
| Basis | v1.2 synchronized baseline + DIRECT_FINAL_v2 capsule |
| Status | FINAL |
| CFR Count | 12 |
| AFR Count | 72 |
| Historical Active FR Baseline | 71 entries from v1.2; preserved through crosswalk |
| Reclassified Historical Constraints | 3 |

### 1. Registry Discipline
The final registry uses two explicit levels. CFRs preserve complete, independently understandable obligations; AFRs preserve distinct verifiable sub-obligations. The earlier FTS-FR identifiers and wording are not retrospectively rewritten: they are retained in the historical crosswalk. Historical FTS-FR-001 is treated as an umbrella statement rather than a final AFR, and historical FTS-FR-007 is decomposed because its three governance responsibilities are independently verifiable.

### 2. Coherent / Consolidated Requirements (CFRs)
| CFR ID | CFR Statement | Semantic Profile | PS Source | Child AFRs |
| --- | --- | --- | --- | --- |
| CFR-FTS-001 | FTS shall manage each institutional file as a persistent collaborative record whose accumulated contents and lifecycle trace are preserved after circulation, with completed circulated files closed through owner-controlled archival rather than deletion. | System-action + Rule/Constraint | Overview; §§3.1, 3.4, 3.5 | AFR-FTS-001, AFR-FTS-002, AFR-FTS-003, AFR-FTS-004 |
| CFR-FTS-002 | FTS shall support Institute Employees as operational file users under assigned role contexts and System Admin as the FTS governance actor, while keeping operational file processing with Institute Employees. | Actor-service + Rule/Constraint | §2 Actors; §3.6 | AFR-FTS-005, AFR-FTS-006, AFR-FTS-007, AFR-FTS-008, AFR-FTS-009, AFR-FTS-010 |
| CFR-FTS-003 | FTS shall allow an authorized Institute Employee to create a new file under an assigned role with a mandatory initial comment and optional attachments. | Actor-service | §3.1 | AFR-FTS-011, AFR-FTS-012, AFR-FTS-013 |
| CFR-FTS-004 | FTS shall support pre-circulation draft save, edit, and discard and transition a valid file into circulation on submission, while preventing draft deletion and preserving accumulated contents after circulation. | Workflow/progression + Rule/Constraint | §3.1 | AFR-FTS-014, AFR-FTS-015, AFR-FTS-016, AFR-FTS-017, AFR-FTS-018, AFR-FTS-019 |
| CFR-FTS-005 | FTS shall support authorized forwarding and return of active files between Institute Employees, with mandatory movement comments, optional attachments, routing/holder updates, and chronological movement recording. | Workflow/progression + Actor-service | §3.2 | AFR-FTS-020, AFR-FTS-021, AFR-FTS-022, AFR-FTS-023, AFR-FTS-024, AFR-FTS-025, AFR-FTS-026, AFR-FTS-027, AFR-FTS-028 |
| CFR-FTS-006 | FTS shall present received and sent files through Inbox/Outbox and allow authorized associated users to open and act on files according to role and file state until archival. | Info-access + Actor-service | §3.3 | AFR-FTS-029, AFR-FTS-030, AFR-FTS-031, AFR-FTS-032, AFR-FTS-033, AFR-FTS-034 |
| CFR-FTS-007 | FTS shall maintain complete chronological tracking history for each file and allow authorized associated users to view the required movement details. | Info-access + System-action | §3.4 | AFR-FTS-035, AFR-FTS-036, AFR-FTS-037, AFR-FTS-038, AFR-FTS-039, AFR-FTS-040, AFR-FTS-041 |
| CFR-FTS-008 | FTS shall allow only the file owner to archive a completed circulated file and shall enforce permanent readable, non-modifiable, non-forwardable archival state. | Workflow/progression + Rule/Constraint | §3.5 | AFR-FTS-042, AFR-FTS-043, AFR-FTS-044, AFR-FTS-045, AFR-FTS-046, AFR-FTS-047 |
| CFR-FTS-009 | FTS shall enforce role-based and file-association authorization for FTS operations and preserve file ownership and historical audit identity across role switching. | Rule/Constraint | §3.6 | AFR-FTS-048, AFR-FTS-049, AFR-FTS-050, AFR-FTS-051, AFR-FTS-052, AFR-FTS-053 |
| CFR-FTS-010 | FTS shall maintain audit records and chronological version history for auditable file and integration actions. | System-action + Rule/Constraint | §3.7; §3.9 | AFR-FTS-054, AFR-FTS-055, AFR-FTS-056, AFR-FTS-057, AFR-FTS-058, AFR-FTS-059, AFR-FTS-060 |
| CFR-FTS-011 | FTS shall trigger the required file and role notification events and hand them to Fusion integrated notification mechanisms for delivery. | Notification | §3.8 | AFR-FTS-061, AFR-FTS-062, AFR-FTS-063, AFR-FTS-064, AFR-FTS-065, AFR-FTS-066 |
| CFR-FTS-012 | FTS shall expose authorized file/workflow-tracking APIs to other Fusion modules while applying FTS RBAC/audit controls and leaving consuming modules responsible for domain-specific approval semantics. | Actor-service + Rule/Constraint | §3.9; §3.10 | AFR-FTS-067, AFR-FTS-068, AFR-FTS-069, AFR-FTS-070, AFR-FTS-071, AFR-FTS-072 |

### 3. Atomic Requirements (AFRs)

#### CFR-FTS-001 — Persistent Record & Archival
- **AFR-FTS-001**: FTS shall treat each file as a persistent composite object consisting of mandatory user comments and optional file attachments. (Source: Overview / §2 Actors, Historical: FTS-FR-002)
- **AFR-FTS-002**: FTS shall preserve circulated files and their accumulated contents without deletion after circulation. (Source: Overview / §2 Actors, Historical: FTS-FR-003)
- **AFR-FTS-003**: FTS shall allow a file owner to archive a completed file instead of deleting it. (Source: Overview / §2 Actors, Historical: FTS-FR-004)
- **AFR-FTS-004**: FTS shall maintain traceability of file creation, movement, comments, attachments, and archival actions. (Source: Overview / §2 Actors, Historical: FTS-FR-005)

#### CFR-FTS-002 — Operational Users & Admin Governance
- **AFR-FTS-005**: FTS shall support Institute Employee users, including Faculty and Staff, as operational users of file workflows. (Source: Overview / §2 Actors, Historical: FTS-FR-006)
- **AFR-FTS-006**: FTS shall support System Admin administration of FTS-relevant role assignments, reassignments, and access-control context. (Source: §2.2 System Admin; §3.6, Historical: FTS-FR-007)
- **AFR-FTS-007**: FTS shall support System Admin monitoring of FTS system usage within the available governance scope. (Source: §2.2 System Admin, Historical: FTS-FR-007)
- **AFR-FTS-008**: FTS shall support System Admin security and audit-log oversight, including viewing and any maintenance functions represented within the available FTS governance scope. (Source: §2.2 System Admin; §3.7, Historical: FTS-FR-007)
- **AFR-FTS-009**: FTS shall not allow the System Admin to perform operational file workflow actions on behalf of Institute Employees. (Source: Overview / §2 Actors, Historical: FTS-FR-008)
- **AFR-FTS-010**: FTS shall allow an Institute Employee assigned multiple institutional roles to operate under the selected assigned role through the Fusion dashboard. (Source: Overview / §2 Actors, Historical: FTS-FR-009)

#### CFR-FTS-003 — File Creation
- **AFR-FTS-011**: FTS shall allow any Institute Employee to create a new file under an assigned role. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-010)
- **AFR-FTS-012**: FTS shall require an initial mandatory comment when an Institute Employee creates a new file. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-011)
- **AFR-FTS-013**: FTS shall allow optional attachments to be added during file creation. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-012)

#### CFR-FTS-004 — Draft Handling & Circulation Boundary
- **AFR-FTS-014**: FTS shall allow an Institute Employee to save a newly created file as a draft. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-013)
- **AFR-FTS-015**: FTS shall allow an Institute Employee to edit a saved draft file before submission. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-014)
- **AFR-FTS-016**: FTS shall allow an Institute Employee to discard a draft file before submission. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-015)
- **AFR-FTS-017**: FTS shall prevent deletion of a file once it has been submitted and circulated. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-016)
- **AFR-FTS-018**: FTS shall change a file from draft/submission preparation to circulated workflow state when it is submitted to another employee. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-017)
- **AFR-FTS-019**: FTS shall preserve comments and attachments accumulated in a file after submission. (Source: §3.1 File Creation and Draft Management, Historical: FTS-FR-018)

#### CFR-FTS-005 — Forwarding and Return
- **AFR-FTS-020**: FTS shall allow an Institute Employee to send a file to another Institute Employee. (Source: §3.2 File Forwarding and Workflow Handling, Historical: FTS-FR-019)
- **AFR-FTS-021**: FTS shall allow a file to be sent to any other Institute Employee regardless of the receiver's role. (Source: §3.2 File Forwarding and Workflow Handling, Historical: FTS-FR-020)
- **AFR-FTS-022**: FTS shall require the acting user to add a mandatory comment for every file-movement action, including forwarding and return. (Source: Overview ¶5 / §3.2, Historical: FTS-FR-021)
- **AFR-FTS-023**: FTS shall allow optional attachments to be added at each file-movement stage, including forwarding and return. (Source: Overview ¶5 / §3.2, Historical: FTS-FR-022)
- **AFR-FTS-024**: FTS shall allow a recipient user to forward a received file to another user. (Source: §3.2 File Forwarding and Workflow Handling, Historical: FTS-FR-023)
- **AFR-FTS-025**: FTS shall allow a recipient user to return a received file to the sender. (Source: §3.2 File Forwarding and Workflow Handling, Historical: FTS-FR-024)
- **AFR-FTS-026**: FTS shall record each forwarding action in chronological order. (Source: §3.2 File Forwarding and Workflow Handling, Historical: FTS-FR-025)
- **AFR-FTS-027**: FTS shall record each return action in chronological order. (Source: §3.2 File Forwarding and Workflow Handling, Historical: FTS-FR-026)
- **AFR-FTS-028**: FTS shall update the current file holder or pending recipient after a file is forwarded or returned. (Source: §3.2 File Forwarding and Workflow Handling, Historical: FTS-FR-027)

#### CFR-FTS-006 — Inbox & Outbox
- **AFR-FTS-029**: FTS shall show files received by a user in the user's Inbox. (Source: §3.3 Inbox and Outbox Management, Historical: FTS-FR-028)
- **AFR-FTS-030**: FTS shall show files sent by a user in the user's Outbox. (Source: §3.3 Inbox and Outbox Management, Historical: FTS-FR-029)
- **AFR-FTS-031**: FTS shall allow users to view and open files from their Inbox. (Source: §3.3 Inbox and Outbox Management, Historical: FTS-FR-030)
- **AFR-FTS-032**: FTS shall allow users to view and open files from their Outbox. (Source: §3.3 Inbox and Outbox Management, Historical: FTS-FR-031)
- **AFR-FTS-033**: FTS shall allow a user to act on actionable files from Inbox or Outbox according to the file state and user authorization. (Source: §3.3 Inbox and Outbox Management, Historical: FTS-FR-032)
- **AFR-FTS-034**: FTS shall keep files accessible to associated users until the file owner archives the file. (Source: §3.3 Inbox and Outbox Management, Historical: FTS-FR-033)

#### CFR-FTS-007 — Tracking History
- **AFR-FTS-035**: FTS shall maintain complete movement history for every file from creation onward. (Source: §3.4 File Tracking and History, Historical: FTS-FR-034)
- **AFR-FTS-036**: FTS shall record sender details for each file movement event. (Source: §3.4 File Tracking and History, Historical: FTS-FR-035)
- **AFR-FTS-037**: FTS shall record receiver details for each file movement event. (Source: §3.4 File Tracking and History, Historical: FTS-FR-036)
- **AFR-FTS-038**: FTS shall record timestamps for each file movement event. (Source: §3.4 File Tracking and History, Historical: FTS-FR-037)
- **AFR-FTS-039**: FTS shall record comments added at each file movement event. (Source: §3.4 File Tracking and History, Historical: FTS-FR-038)
- **AFR-FTS-040**: FTS shall record attachments added at each file movement event. (Source: §3.4 File Tracking and History, Historical: FTS-FR-039)
- **AFR-FTS-041**: FTS shall allow any user associated with a file to view that file's tracking history. (Source: §3.4 File Tracking and History, Historical: FTS-FR-040)

#### CFR-FTS-008 — Archival
- **AFR-FTS-042**: FTS shall allow the file owner to archive a file. (Source: §3.5 File Archival, Historical: FTS-FR-041)
- **AFR-FTS-043**: FTS shall prevent users other than the file owner from archiving the file. (Source: §3.5 File Archival, Historical: FTS-FR-042)
- **AFR-FTS-044**: FTS shall treat archival as completion of the collaborative file workflow. (Source: §3.5 File Archival, Historical: FTS-FR-043)
- **AFR-FTS-045**: FTS shall keep archived files permanently stored and readable. (Source: §3.5 File Archival, Historical: FTS-FR-044)
- **AFR-FTS-046**: FTS shall prevent modification of archived files. (Source: §3.5 File Archival, Historical: FTS-FR-045)
- **AFR-FTS-047**: FTS shall prevent forwarding of archived files. (Source: §3.5 File Archival, Historical: FTS-FR-046)

#### CFR-FTS-009 — Access Control & Role Context
- **AFR-FTS-048**: FTS shall enforce role-based access control for file operations. (Source: §3.6 Access Control and Security, Historical: FTS-FR-047)
- **AFR-FTS-049**: FTS shall allow users to access only files they are authorized to view. (Source: §3.6 Access Control and Security, Historical: FTS-FR-048)
- **AFR-FTS-050**: FTS shall allow users to act only on files they are authorized to act upon. (Source: §3.6 Access Control and Security, Historical: FTS-FR-049)
- **AFR-FTS-051**: FTS shall preserve file ownership when a user switches roles. (Source: §3.6 Access Control and Security, Historical: FTS-FR-050)
- **AFR-FTS-052**: FTS shall preserve audit history when a user switches roles. (Source: §3.6 Access Control and Security, Historical: FTS-FR-051)
- **AFR-FTS-053**: FTS shall restrict sensitive actions according to assigned roles. (Source: §3.6 Access Control and Security, Historical: FTS-FR-052)

#### CFR-FTS-010 — Audit Logs & Versioning
- **AFR-FTS-054**: FTS shall maintain an audit log for file creation actions. (Source: §3.7 Audit Logs and Versioning, Historical: FTS-FR-053)
- **AFR-FTS-055**: FTS shall maintain an audit log for comments added to files. (Source: §3.7 Audit Logs and Versioning, Historical: FTS-FR-054)
- **AFR-FTS-056**: FTS shall maintain an audit log for attachments added to files. (Source: §3.7 Audit Logs and Versioning, Historical: FTS-FR-055)
- **AFR-FTS-057**: FTS shall maintain an audit log for forwarding actions. (Source: §3.7 Audit Logs and Versioning, Historical: FTS-FR-056)
- **AFR-FTS-058**: FTS shall maintain an audit log for return actions. (Source: §3.7 Audit Logs and Versioning, Historical: FTS-FR-057)
- **AFR-FTS-059**: FTS shall maintain an audit log for archival actions. (Source: §3.7 Audit Logs and Versioning, Historical: FTS-FR-058)
- **AFR-FTS-060**: FTS shall maintain file versioning implicitly through chronological file updates. (Source: §3.7 Audit Logs and Versioning, Historical: FTS-FR-059)

#### CFR-FTS-011 — Notifications
- **AFR-FTS-061**: FTS shall generate a notification when a file is received by a user. (Source: §3.8 Notifications, Historical: FTS-FR-061)
- **AFR-FTS-062**: FTS shall generate a notification when a file is forwarded. (Source: §3.8 Notifications, Historical: FTS-FR-062)
- **AFR-FTS-063**: FTS shall generate a notification when a file is returned. (Source: §3.8 Notifications, Historical: FTS-FR-063)
- **AFR-FTS-064**: FTS shall generate a notification when a file is archived. (Source: §3.8 Notifications, Historical: FTS-FR-064)
- **AFR-FTS-065**: FTS shall generate a notification when a role is assigned or reassigned. (Source: §3.8 Notifications, Historical: FTS-FR-065)
- **AFR-FTS-066**: FTS shall deliver notifications through Fusion's integrated notification mechanisms. (Source: §3.8 Notifications, Historical: FTS-FR-066)

#### CFR-FTS-012 — Fusion Module Integration
- **AFR-FTS-067**: FTS shall expose APIs to other Fusion modules for module-specific workflows. (Source: §3.9 Integration with Fusion Modules, Historical: FTS-FR-067)
- **AFR-FTS-068**: FTS shall expose APIs to other Fusion modules for approval chains. (Source: §3.9 Integration with Fusion Modules, Historical: FTS-FR-068)
- **AFR-FTS-069**: FTS shall expose APIs to other Fusion modules for file-based request tracking. (Source: §3.9 Integration with Fusion Modules, Historical: FTS-FR-069)
- **AFR-FTS-070**: FTS shall apply RBAC requirements to integrations with other Fusion modules. (Source: §3.9 Integration with Fusion Modules, Historical: FTS-FR-070)
- **AFR-FTS-071**: FTS shall apply audit requirements to integrations with other Fusion modules. (Source: §3.9 Integration with Fusion Modules, Historical: FTS-FR-071)
- **AFR-FTS-072**: FTS shall not define the domain-specific approval rules of consuming Fusion modules that use FTS APIs. (Source: §3.9 Integration with Fusion Modules, Historical: FTS-FR-072)
