# 05_SA_Workflow_Specifications_v1.1_FINAL

Workflow Specifications

Super Admin (SA) Module | v1.1 | FINAL SYNCHRONIZED

Artifact status

FINAL SYNCHRONIZED

Source baseline

SA v1.0 STUDENT BASELINE + resolved thread decisions

Synchronization rule

DIRECT_FINAL_v2 (2026-08-30)

1. Workflow Eligibility and Derivation

DIRECT_FINAL_v2 defines a workflow as an ordered, meaningful, connected progression through business states. A workflow may contain automatic System transitions when they are meaningful state changes; the System remains not an actor of its own UCs. Informational and notification-only UCs remain outside STT rows. The prior purge workflows remain semantically valid; role-validity, archived-user reversibility, and historical-data archive/restore progressions are added because the new formalism no longer excludes them solely for lacking a second human actor.

2. Canonical Basis and Composite Workflows

BW-SA-01 - Permanent Data Purge — Approved Path

Type

Basis

Purpose / Scope

Represent the finite path in which retention-expired archived data is requested for permanent purge and the IT Head supplies the second required authorization.

Trigger

Super Admin decides to purge an eligible archived data set after its retention period.

Participants

Super Admin; IT Head

Constituent Workflows

N/A

Related Workflows

CW-SA-01; alternative outcome BW-SA-02

Related CFRs / key AFRs

Related UCs

UC-SA-022; UC-SA-023

Related BRs

BR-SA-021; BR-SA-022; BR-SA-025; BR-SA-029; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

Archived — Retention Eligible

Super Admin

UC-SA-022 / Request Permanent Data Purge

Retention period elapsed; authenticated destructive-action confirmation succeeds

Purge Request Pending IT Head Authorization

BR-SA-021; BR-SA-022; BR-SA-029; BR-SA-025; BR-SA-033

2

Purge Request Pending IT Head Authorization

IT Head

UC-SA-023 / Authorize Permanent Data Purge

Decision = Approve

Permanently Purged

BR-SA-022; BR-SA-025; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

BW-SA-02 - Permanent Data Purge — Rejected Path

Type

Basis

Purpose / Scope

Represent the finite path in which an eligible purge request is rejected by the IT Head and archived data remains retained.

Trigger

Super Admin decides to purge an eligible archived data set after its retention period.

 Participants

Super Admin; IT Head

Constituent Workflows

N/A

Related Workflows

CW-SA-01; alternative outcome BW-SA-01

Related CFRs / key AFRs

Related UCs

UC-SA-022; UC-SA-023

Related BRs

BR-SA-021; BR-SA-022; BR-SA-025; BR-SA-029; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

Archived — Retention Eligible

Super Admin

UC-SA-022 / Request Permanent Data Purge

Retention period elapsed; authenticated destructive-action confirmation succeeds

Purge Request Pending IT Head Authorization

BR-SA-021; BR-SA-022; BR-SA-029; BR-SA-025; BR-SA-033

2

Purge Request Pending IT Head Authorization

IT Head

UC-SA-023 / Authorize Permanent Data Purge

Decision = Reject

Purge Request Rejected; Data Remains Archived

BR-SA-022; BR-SA-025; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

CW-SA-01 - Permanent Data Purge Authorization Lifecycle

Type

Composite

Purpose / Scope

Integrate the approved and rejected purge basis workflows around their common Super Admin request and IT Head decision point.

Trigger

Super Admin submits a retention-eligible permanent-purge request.

Participants

Super Admin; IT Head

Constituent Workflows

BW-SA-01; BW-SA-02

Related Workflows

BW-SA-01; BW-SA-02

Related CFRs / key AFRs

Related UCs

UC-SA-022; UC-SA-023

Related BRs

BR-SA-021; BR-SA-022; BR-SA-025; BR-SA-029; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

Archived — Retention Eligible

Super Admin

UC-SA-022 / Request Permanent Data Purge

Retention period elapsed and confirmation/authentication succeeds

Purge Request Pending IT Head Authorization

BR-SA-021; BR-SA-022; BR-SA-029; BR-SA-025; BR-SA-033

2A

Purge Request Pending IT Head Authorization

IT Head

UC-SA-023 / Authorize Permanent Data Purge

Decision = Approve

Permanently Purged

BR-SA-022; BR-SA-025; BR-SA-033

2B

Purge Request Pending IT Head Authorization

IT Head

UC-SA-023 / Authorize Permanent Data Purge

Decision = Reject

Purge Request Rejected; Data Remains Archived

BR-SA-022; BR-SA-025; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

BW-SA-03 - Immediate Time-Bound Role Assignment to Expiry

Type

Basis

Purpose / Scope

Represent a time-bound role assigned for immediate effect and later automatically expired without extension.

Trigger

Super Admin assigns a valid time-bound role whose start date is effective immediately.

Participants

Super Admin; System

Constituent Workflows

N/A

Related Workflows

CW-SA-02; related BW-SA-04 and BW-SA-05

Related CFRs / key AFRs

Related UCs

UC-SA-008; UC-SA-029

Related BRs

BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-009; BR-SA-010; BR-SA-011; BR-SA-015; BR-SA-025; BR-SA-032; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

No Applicable Role Assignment

Super Admin

UC-SA-008 / Assign Role

Eligibility, singularity, conflict and date rules satisfied; start date effective now

Active Time-Bound Role

BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-010; BR-SA-011; BR-SA-025; BR-SA-032; BR-SA-033

2

Active Time-Bound Role

System

UC-SA-029 / Expire Time-Bound Role

Applicable end date reached; assignment not superseded by extension, reassignment, or revocation

Role Expired / Inactive

BR-SA-009; BR-SA-015; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

BW-SA-04 - Future-Dated Role Assignment to Expiry

Type

Basis

Purpose / Scope

Represent a future-dated role assignment that automatically activates on its start date and later expires.

Trigger

Super Admin assigns a valid time-bound role with a future start date.

Participants

Super Admin; System

Constituent Workflows

N/A

Related Workflows

CW-SA-02; related BW-SA-03 and BW-SA-05

Related CFRs / key AFRs

Related UCs

UC-SA-008; UC-SA-028; UC-SA-029

Related BRs

BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-009; BR-SA-010; BR-SA-011; BR-SA-015; BR-SA-025; BR-SA-032; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

No Applicable Role Assignment

Super Admin

UC-SA-008 / Assign Role

Eligibility, singularity, conflict and date rules satisfied; start date is in the future

Scheduled Role Assignment

BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-010; BR-SA-011; BR-SA-025; BR-SA-032; BR-SA-033

2

Scheduled Role Assignment

System

UC-SA-028 / Activate Scheduled Role Assignment

Configured start date reached; assignment remains valid and not superseded

Active Time-Bound Role

BR-SA-009; BR-SA-015; BR-SA-025; BR-SA-033

3

Active Time-Bound Role

System

UC-SA-029 / Expire Time-Bound Role

Applicable end date reached; no later lifecycle action supersedes expiry

Role Expired / Inactive

BR-SA-009; BR-SA-015; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

BW-SA-05 - Role Validity Extension — One Traversal

Type

Basis

Purpose / Scope

Represent exactly one validity extension of an active time-bound role followed by expiry at the revised end date.

Trigger

Super Admin extends a currently active time-bound role before its current end date.

Participants

Super Admin; System

Constituent Workflows

N/A

Related Workflows

CW-SA-02; loop companion to direct-expiry paths

Related CFRs / key AFRs

Related UCs

UC-SA-011; UC-SA-029

Related BRs

BR-SA-007; BR-SA-008; BR-SA-009; BR-SA-011; BR-SA-015; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

Notes

The loop rule is represented by one extension traversal; repeated extensions are not enumerated.

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

Active Time-Bound Role

Super Admin

UC-SA-011 / Extend Role Validity

Before expiry; new end date and reason valid; compatibility/singularity remain valid

Active Role — Extended Validity

BR-SA-007; BR-SA-008; BR-SA-011; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

2

Active Role — Extended Validity

System

UC-SA-029 / Expire Time-Bound Role

Revised end date reached; no later lifecycle action supersedes expiry

Role Expired / Inactive

BR-SA-009; BR-SA-015; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

CW-SA-02 - Time-Bound Role Validity Lifecycle

Type

Composite

Purpose / Scope

Integrate immediate assignment, future activation, direct expiry, and one extension traversal into the role-validity state model. Non-state-changing expiry reminders are related services but are not STT rows.

Trigger

A valid time-bound role assignment is created or an active time-bound role is extended.

Participants

Super Admin; System

Constituent Workflows

BW-SA-03; BW-SA-04; BW-SA-05

Related Workflows

BW-SA-03; BW-SA-04; BW-SA-05

Related CFRs / key AFRs

Related UCs

UC-SA-008; UC-SA-011; UC-SA-028; UC-SA-029

Related BRs

BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-009; BR-SA-010; BR-SA-011; BR-SA-015; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

Notes

UC-SA-030 Send Role-Expiry Reminder is intentionally excluded from STT because it does not change role state.

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1A

No Applicable Role Assignment

Super Admin

UC-SA-008 / Assign Role

Valid assignment; start date effective now

Active Time-Bound Role

BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-010; BR-SA-011; BR-SA-025; BR-SA-032; BR-SA-033

1B

No Applicable Role Assignment

Super Admin

UC-SA-008 / Assign Role

Valid assignment; start date in the future

Scheduled Role Assignment

BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-010; BR-SA-011; BR-SA-025; BR-SA-032; BR-SA-033

2

Scheduled Role Assignment

System

UC-SA-028 / Activate Scheduled Role Assignment

Start date reached; assignment remains valid

Active Time-Bound Role

BR-SA-009; BR-SA-015; BR-SA-025; BR-SA-033

3A

Active Time-Bound Role

System

UC-SA-029 / Expire Time-Bound Role

End date reached without extension/reassignment/revocation

Role Expired / Inactive

BR-SA-009; BR-SA-015; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

3B

Active Time-Bound Role

Super Admin

UC-SA-011 / Extend Role Validity

Valid extension before expiry

Active Role — Extended Validity

BR-SA-007; BR-SA-008; BR-SA-011; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

4

Active Role — Extended Validity

System

UC-SA-029 / Expire Time-Bound Role

Revised end date reached without later superseding lifecycle action

Role Expired / Inactive

BR-SA-009; BR-SA-015; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

BW-SA-06 - Deactivated User Reactivation

Type

Basis

Purpose / Scope

Represent the finite path in which a policy-eligible deactivated user is reactivated rather than archived.

Trigger

Super Admin selects Reactivate User for a deactivated, non-archived account.

Participants

Super Admin

Constituent Workflows

N/A

Related Workflows

CW-SA-03; alternative to archival paths

Related CFRs / key AFRs

Related UCs

UC-SA-005

Related BRs

BR-SA-025; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

Deactivated User

Super Admin

UC-SA-005 / Reactivate User

Reactivation allowed by applicable policy; user is not archived

Active User

BR-SA-025; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

BW-SA-07 - Archived User Restoration Within Reversible Window

Type

Basis

Purpose / Scope

Represent archival of an eligible deactivated user followed by restoration within the configured reversible window.

Trigger

Super Admin archives an eligible deactivated user and later requests restoration before the reversible period expires.

Participants

Super Admin

Constituent Workflows

N/A

Related Workflows

CW-SA-03; alternative outcome BW-SA-08

Related CFRs / key AFRs

Related UCs

UC-SA-015; UC-SA-018

Related BRs

BR-SA-004; BR-SA-005; BR-SA-019; BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-032; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

Deactivated User

Super Admin

UC-SA-015 / Archive User

Configured deactivation interval elapsed; no pending transaction blocks archival; critical confirmation succeeds

Archived User — Reversible

BR-SA-004; BR-SA-019; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-032; BR-SA-033

2

Archived User — Reversible

Super Admin

UC-SA-018 / Restore Archived User

Within reversible period; required authorization present; authenticated confirmation succeeds where designated critical

User Restored from Archive

BR-SA-005; BR-SA-020; BR-SA-025; BR-SA-029; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

BW-SA-08 - Archived User Reversibility Window Expiry

Type

Basis

Purpose / Scope

Represent archival of an eligible deactivated user followed by automatic transition to permanently non-restorable status when the reversible period expires.

Trigger

Super Admin archives an eligible deactivated user; the configured reversible period later expires without a completed restoration.

Participants

Super Admin; System

Constituent Workflows

N/A

Related Workflows

CW-SA-03; alternative outcome BW-SA-07

Related CFRs / key AFRs

Related UCs

UC-SA-015; UC-SA-031

Related BRs

BR-SA-004; BR-SA-005; BR-SA-019; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-032; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

Deactivated User

Super Admin

UC-SA-015 / Archive User

Archival eligibility satisfied; critical confirmation succeeds

Archived User — Reversible

BR-SA-004; BR-SA-019; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-032; BR-SA-033

2

Archived User — Reversible

System

UC-SA-031 / Finalize Archived User as Permanently Non-Restorable

Configured reversible period expires and no valid restoration completed

Archived User — Permanent / Non-Restorable

BR-SA-005; BR-SA-019; BR-SA-025; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

CW-SA-03 - Deactivated User Resolution and Archive Lifecycle

Type

Composite

Purpose / Scope

Integrate reactivation, archival with restoration, and archival-window expiry from the common Deactivated User state.

Trigger

A basic-user account is in Deactivated state and a valid lifecycle transition is requested or a configured archival time event occurs.

Participants

Super Admin; System

Constituent Workflows

BW-SA-06; BW-SA-07; BW-SA-08

Related Workflows

BW-SA-06; BW-SA-07; BW-SA-08

Related CFRs / key AFRs

Related UCs

UC-SA-005; UC-SA-015; UC-SA-018; UC-SA-031

Related BRs

BR-SA-004; BR-SA-005; BR-SA-019; BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-032; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1A

Deactivated User

Super Admin

UC-SA-005 / Reactivate User

Reactivation allowed; user not archived

Active User

BR-SA-025; BR-SA-033

1B

Deactivated User

Super Admin

UC-SA-015 / Archive User

Archival eligibility satisfied; confirmation succeeds

Archived User — Reversible

BR-SA-004; BR-SA-019; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-032; BR-SA-033

2A

Archived User — Reversible

Super Admin

UC-SA-018 / Restore Archived User

Within reversible period with required authorization

User Restored from Archive

BR-SA-005; BR-SA-020; BR-SA-025; BR-SA-029; BR-SA-033

2B

Archived User — Reversible

System

UC-SA-031 / Finalize Archived User as Permanently Non-Restorable

Reversible period expires without completed restoration

Archived User — Permanent / Non-Restorable

BR-SA-005; BR-SA-019; BR-SA-025; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.

BW-SA-09 - Historical Data Archive and Restore

Type

Basis

Purpose / Scope

Represent archival of eligible historical data and a later approved restoration to the active system.

Trigger

Super Admin initiates archival for eligible historical data; later, required approval exists for restoration.

Participants

Super Admin

Constituent Workflows

N/A

Related Workflows

Related to permanent-purge workflows when archived data instead reaches purge eligibility

Related CFRs / key AFRs

Related UCs

UC-SA-016; UC-SA-019

Related BRs

BR-SA-017; BR-SA-018; BR-SA-019; BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-033

Notes

N/A

Authoritative State-Transition Table

S. No.

From State

Actor

Use Case ID / Name

Guard / Outcome

Resulting State

BR Reference(s)

1

Archive-Eligible Historical Data

Super Admin

UC-SA-016 / Archive Historical Data

Retention/completion/dependency criteria satisfied; authenticated confirmation succeeds; backup completed

Archived Historical Data

BR-SA-017; BR-SA-018; BR-SA-019; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-033

2

Archived Historical Data

Super Admin

UC-SA-019 / Restore Archived Historical Data

Required approval exists; restoration allowed by policy; critical confirmation succeeds where applicable

Historical Data Restored to Active System

BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-033

Diagram: see the corresponding page in 05a_SA_Workflow_Diagrams_v1.1_FINAL.drawio. The diagram is generated from this STT and introduces no additional states, guards, actors, or outcomes.