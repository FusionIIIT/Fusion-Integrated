# Gymkhana Workflow Specifications (v1.1 SYNCHRONIZED)

## BW-GYM-01 — Club Membership Enrollment

- **Type**: Basis
- **Purpose / Scope**: Represent the connected progression from no membership application to an open application and then to confirmed membership after Club Head approval.
- **Trigger**: A student decides to apply to a confirmed club.
- **Participants**: Student; Club Head
- **Constituent Workflows**: N/A
- **Related Workflows**: N/A
- **Related UCs**: UC-GYM-004, UC-GYM-005
- **Related BRs**: BR-GYM-007 to BR-GYM-011

### State Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | No Membership Application | Student | UC-GYM-004 / Apply for Club Membership | Club is confirmed; no duplicate same-club application; submission succeeds | Membership Application Open | BR-GYM-007, BR-GYM-008, BR-GYM-009 |
| 2 | Membership Application Open | Club Head | UC-GYM-005 / Approve Club Membership | Actor is applicable Club Head; application remains open; approval selected | Membership Confirmed | BR-GYM-010, BR-GYM-011 |

---

## BW-GYM-02 — Targeted Poll Participation

- **Type**: Basis
- **Purpose / Scope**: Represent one finite path from Club Head poll creation to one eligible targeted student recording one vote.
- **Trigger**: A Club Head creates a poll for selected student groups.
- **Participants**: Club Head; Student
- **Constituent Workflows**: N/A
- **Related Workflows**: N/A
- **Related UCs**: UC-GYM-006, UC-GYM-007
- **Related BRs**: BR-GYM-010, BR-GYM-012 to BR-GYM-015

### State Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Poll Not Available | Club Head | UC-GYM-006 / Create Voting Poll | Actor is applicable Club Head; at least two choices; valid target groups; poll created | Poll Open / Target Audience Defined / Student Not Yet Voted | BR-GYM-010, BR-GYM-012, BR-GYM-013 |
| 2 | Poll Open / Target Audience Defined / Student Not Yet Voted | Student | UC-GYM-007 / Vote in Poll | Poll active/unexpired; student belongs to target audience; student has not voted; vote accepted | Poll Open / Target Audience Defined / Student Vote Recorded | BR-GYM-013, BR-GYM-014, BR-GYM-015 |

---

## BW-GYM-03 — Club Establishment and Confirmation

- **Type**: Basis
- **Purpose / Scope**: Represent the Student Admin-controlled club lifecycle from no club record through open creation to confirmed club.
- **Trigger**: Student Admin decides to establish a new Gymkhana club.
- **Participants**: Student Admin
- **Constituent Workflows**: N/A
- **Related Workflows**: N/A
- **Related UCs**: UC-GYM-001, UC-GYM-011
- **Related BRs**: BR-GYM-001 to BR-GYM-004

### State Transition Table

| S. No. | From State | Actor | Use Case ID / Name | Guard / Outcome | Resulting State | BR Reference(s) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Club Not Created | Student Admin | UC-GYM-001 / Create New Club | Required data supplied; coordinator/co-coordinator are valid students; Faculty Councillor is valid faculty; category allowed; creation succeeds | Club Open | BR-GYM-001, BR-GYM-002, BR-GYM-003, BR-GYM-004 |
| 2 | Club Open | Student Admin | UC-GYM-011 / Approve Club | Club remains open; Student Admin approves; update succeeds | Club Confirmed | BR-GYM-004 |

---
