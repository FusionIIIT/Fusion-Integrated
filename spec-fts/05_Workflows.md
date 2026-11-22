# Fusion ERP – File Tracking System (FTS)
## Workflow Specifications — Final v1.3

| Project | Fusion ERP |
| --- | --- |
| Module Code | FTS |
| Module | File Tracking System (FTS) |
| Artifact | Workflow Specifications |
| Version | v1.3 |
| Date | 2026-08-30 |
| Basis | v1.2 synchronized baseline + DIRECT_FINAL_v2 capsule |
| Status | FINAL |
| Basis Workflows | 8 |
| Composite Workflows | 2 |
| Complete Workflow | Not forced |

### 1. Workflow Re-derivation Note
DIRECT_FINAL_v2 defines a workflow by meaningful connected progression through business states, not by a minimum actor count. Therefore the prior v1.2 exclusion of state-changing new-file/draft progression is no longer justified. Existing BW-FTS-01..04 and CW-FTS-01 IDs are retained; new BW-FTS-05..08 and CW-FTS-02 are appended. Informational viewing UCs, generic API handoff, and role-context/governance operations remain outside the WF layer because the baseline does not define a necessary connected business-state progression for them.

### 2. Legacy Workflow Disposition
| Legacy WF | Final Disposition | Replacement | Reason |
| --- | --- | --- | --- |
| FTS-WF-001 | Reconstructed | BW-FTS-05..08; CW-FTS-02 | Connected Draft → Edit/Discard/Circulate state progression |
| FTS-WF-002 | Reconstructed | BW-FTS-01, BW-FTS-02; CW-FTS-01 | Forwarding remains explicit holder-state progression |
| FTS-WF-003 | Reconstructed | BW-FTS-03; CW-FTS-01 | Return remains an explicit state transition to the sender |
| FTS-WF-004 | Retired | N/A | Inbox/Outbox viewing/opening is informational |
| FTS-WF-005 | Retired | N/A | History viewing is informational; history maintenance is a side effect |
| FTS-WF-006 | Reconstructed | BW-FTS-04; CW-FTS-01 | Archival is a lifecycle-closing transition |
| FTS-WF-007 | Retired | N/A | Role selection/governance does not form connected file-state workflow |
| FTS-WF-008 | Retired | N/A | Generic API handoff does not itself define persistent FTS business-state progression |

### 3. Workflow Registry
| WF ID | Workflow Name | Type | Participants | Constituent Workflows |
| --- | --- | --- | --- | --- |
| BW-FTS-01 | Forward File to Recipient — Zero Onward Traversal | Basis | Institute Employee (Sender); Recipient Institute Employee | N/A |
| BW-FTS-02 | Onward Forwarding — One Loop Traversal | Basis | Institute Employee (Current Holder); Next Recipient Institute Employee | N/A |
| BW-FTS-03 | Return File to Previous Sender | Basis | Institute Employee (Current Recipient); Previous Sender Institute Employee | N/A |
| BW-FTS-04 | Archive Completed Circulated File | Basis | Institute Employee (File Owner); Associated Institute Employees (affected users) | N/A |
| BW-FTS-05 | Prepare and Circulate New File — Zero Draft-Edit Traversal | Basis | Institute Employee (Creator/Sender); Recipient Institute Employee | N/A |
| BW-FTS-06 | Prepare and Circulate New File — One Draft-Edit Traversal | Basis | Institute Employee (Creator/Sender); Recipient Institute Employee | N/A |
| BW-FTS-07 | Create and Discard Draft — Zero Draft-Edit Traversal | Basis | Institute Employee | N/A |
| BW-FTS-08 | Edit Once and Discard Draft — One Draft-Edit Traversal | Basis | Institute Employee | N/A |
| CW-FTS-01 | Collaborative File Circulation and Completion | Composite | Institute Employees acting as Sender, Recipient/Current Holder, Previous Sender, and File Owner | BW-FTS-01, BW-FTS-02, BW-FTS-03, BW-FTS-04 |
| CW-FTS-02 | New File Preparation and Initial Outcome | Composite | Institute Employee (Creator/Sender); Recipient Institute Employee | BW-FTS-05, BW-FTS-06, BW-FTS-07, BW-FTS-08 |

### 4. Canonical Workflow Specifications

#### BW-FTS-01 — Forward File to Recipient — Zero Onward Traversal
- **Type**: Basis
- **Purpose / Scope**: One valid send/forward transition from current sender to another Institute Employee, with no further onward-forward traversal represented in this basis path.
- **Trigger**: Authorized current holder chooses Send/Forward.
- **Participants**: Institute Employee (Sender); Recipient Institute Employee
- **Related UCs**: FTS-UC-003
- **Related BRs**: BR-FTS-001, BR-FTS-005, BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-010, BR-FTS-011, BR-FTS-012, BR-FTS-013
- **State Transition**:
  - From State: Prepared/Draft or Active file held by Sender
  - Actor: Institute Employee (Sender)
  - Use Case: FTS-UC-003 / Send / Forward File to Employee
  - Guard / Outcome: Sender authorized; file not archived; valid Institute Employee recipient; mandatory movement comment present. Movement/history/audit updated; required notification event(s) triggered.
  - Resulting State: Active / Circulated file held by Recipient

#### BW-FTS-02 — Onward Forwarding — One Loop Traversal
- **Type**: Basis
- **Purpose / Scope**: Represent exactly one traversal of the meaningful onward-forward loop after an employee has received an active circulated file.
- **Trigger**: Current recipient chooses to forward the received file onward.
- **Participants**: Institute Employee (Current Holder); Next Recipient Institute Employee
- **Related UCs**: FTS-UC-003
- **Related BRs**: BR-FTS-001, BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-010, BR-FTS-011, BR-FTS-012, BR-FTS-013
- **State Transition**:
  - From State: Active / Circulated file held by Current Recipient
  - Actor: Institute Employee (Current Holder)
  - Use Case: FTS-UC-003 / Send / Forward File to Employee
  - Guard / Outcome: Current holder authorized; file not archived; valid next recipient; mandatory movement comment present. Movement/history/audit updated; required notification event(s) triggered.
  - Resulting State: Active / Circulated file held by Next Recipient

#### BW-FTS-03 — Return File to Previous Sender
- **Type**: Basis
- **Purpose / Scope**: One valid return transition from current recipient back to sender of received movement.
- **Trigger**: Current recipient chooses Return.
- **Participants**: Institute Employee (Current Recipient); Previous Sender Institute Employee
- **Related UCs**: FTS-UC-004
- **Related BRs**: BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-010, BR-FTS-011, BR-FTS-012, BR-FTS-013
- **State Transition**:
  - From State: Active / Circulated file held by Recipient; previous sender known
  - Actor: Institute Employee (Recipient)
  - Use Case: FTS-UC-004 / Return Received File
  - Guard / Outcome: Recipient authorized; active file; mandatory movement comment present. Return/history/audit updated; required return notification event triggered.
  - Resulting State: Active / Circulated file held by Previous Sender

#### BW-FTS-04 — Archive Completed Circulated File
- **Type**: Basis
- **Purpose / Scope**: Represent the lifecycle-closing archival transition after intended collaborative objective is complete.
- **Trigger**: File owner selects Archive.
- **Participants**: Institute Employee (File Owner); Associated Institute Employees (affected users)
- **Related UCs**: FTS-UC-007
- **Related BRs**: BR-FTS-009, BR-FTS-010, BR-FTS-011, BR-FTS-012, BR-FTS-013
- **State Transition**:
  - From State: Active / Circulated file; intended collaborative objective complete
  - Actor: Institute Employee (File Owner)
  - Use Case: FTS-UC-007 / Archive Completed File
  - Guard / Outcome: Requester is file owner; file is not already archived; objective complete. Archive/audit recorded; archive notification event triggered.
  - Resulting State: Archived / Read-only / Permanently retained

#### BW-FTS-05 — Prepare and Circulate New File — Zero Draft-Edit Traversal
- **Type**: Basis
- **Purpose / Scope**: Represent creation followed by initial circulation with zero draft-edit traversal.
- **Trigger**: Authorized Institute Employee creates a new file and proceeds to initial circulation without a draft edit.
- **Participants**: Institute Employee (Creator/Sender); Recipient Institute Employee
- **Related UCs**: FTS-UC-001, FTS-UC-003
- **Related BRs**: BR-FTS-001, BR-FTS-003, BR-FTS-004, BR-FTS-005, BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-010, BR-FTS-011, BR-FTS-013
- **State Transitions**:
  1. (No FTS file record) --[Creator / FTS-UC-001]--> Draft / Pre-circulation file
  2. Draft / Pre-circulation file --[Sender / FTS-UC-003]--> Active / Circulated file held by Recipient

#### BW-FTS-06 — Prepare and Circulate New File — One Draft-Edit Traversal
- **Type**: Basis
- **Purpose / Scope**: Represent creation, exactly one draft-edit traversal, and initial circulation.
- **Trigger**: Authorized Institute Employee creates a new file, edits the saved draft once, then sends it.
- **Participants**: Institute Employee (Creator/Sender); Recipient Institute Employee
- **Related UCs**: FTS-UC-001, FTS-UC-002, FTS-UC-003
- **Related BRs**: BR-FTS-001, BR-FTS-003, BR-FTS-004, BR-FTS-005, BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-010, BR-FTS-011, BR-FTS-013
- **State Transitions**:
  1. (No FTS file record) --[Creator / FTS-UC-001]--> Draft / Pre-circulation file
  2. Draft / Pre-circulation file --[Employee / FTS-UC-002 (Edit)]--> Updated Draft / Pre-circulation file
  3. Updated Draft / Pre-circulation file --[Sender / FTS-UC-003]--> Active / Circulated file held by Recipient

#### BW-FTS-07 — Create and Discard Draft — Zero Draft-Edit Traversal
- **Type**: Basis
- **Purpose / Scope**: Represent creation followed by draft discard with zero draft-edit traversal.
- **Trigger**: Authorized Institute Employee creates a draft and chooses Discard before submission.
- **Participants**: Institute Employee
- **Related UCs**: FTS-UC-001, FTS-UC-002
- **Related BRs**: BR-FTS-001, BR-FTS-003, BR-FTS-004, BR-FTS-005, BR-FTS-010, BR-FTS-011
- **State Transitions**:
  1. (No FTS file record) --[Creator / FTS-UC-001]--> Draft / Pre-circulation file
  2. Draft / Pre-circulation file --[Employee / FTS-UC-002 (Discard)]--> Discarded / No active file retained

#### BW-FTS-08 — Edit Once and Discard Draft — One Draft-Edit Traversal
- **Type**: Basis
- **Purpose / Scope**: Represent creation, exactly one draft-edit traversal, and subsequent draft discard before circulation.
- **Trigger**: Authorized Institute Employee creates a draft, edits it once, and later chooses Discard before submission.
- **Participants**: Institute Employee
- **Related UCs**: FTS-UC-001, FTS-UC-002
- **Related BRs**: BR-FTS-001, BR-FTS-003, BR-FTS-004, BR-FTS-005, BR-FTS-010, BR-FTS-011
- **State Transitions**:
  1. (No FTS file record) --[Creator / FTS-UC-001]--> Draft / Pre-circulation file
  2. Draft / Pre-circulation file --[Employee / FTS-UC-002 (Edit)]--> Updated Draft / Pre-circulation file
  3. Updated Draft / Pre-circulation file --[Employee / FTS-UC-002 (Discard)]--> Discarded / No active file retained

#### CW-FTS-01 — Collaborative File Circulation and Completion
- **Type**: Composite (BW-FTS-01, BW-FTS-02, BW-FTS-03, BW-FTS-04)
- **Purpose / Scope**: Combine initial/ongoing forwarding, optional one-time onward-forward traversal, return, return after one onward traversal, and eventual owner archival into the core collaborative file lifecycle.
- **Participants**: Institute Employees acting as Sender, Recipient/Current Holder, Next Recipient, Previous Sender, and File Owner.
- **Related UCs**: FTS-UC-003, FTS-UC-004, FTS-UC-007
- **Related BRs**: BR-FTS-001, BR-FTS-005..013 as applicable

#### CW-FTS-02 — New File Preparation and Initial Outcome
- **Type**: Composite (BW-FTS-05, BW-FTS-06, BW-FTS-07, BW-FTS-08)
- **Purpose / Scope**: Integrate new-file creation, optional one draft-edit traversal, draft discard, or initial circulation without forcing draft operations into unrelated collaborative circulation paths.
- **Participants**: Institute Employee (Creator/Sender); Recipient Institute Employee.
- **Related UCs**: FTS-UC-001, FTS-UC-002, FTS-UC-003
- **Related BRs**: BR-FTS-001, BR-FTS-003..008, BR-FTS-010, BR-FTS-011, BR-FTS-013
