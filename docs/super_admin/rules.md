# 04_SA_Business_Rule_Specifications_v1.1_FINAL

Business Rule Specifications

Super Admin (SA) Module | v1.1 | FINAL SYNCHRONIZED

Artifact status

FINAL SYNCHRONIZED

Source baseline

SA v1.0 STUDENT BASELINE + resolved thread decisions

Synchronization rule

DIRECT_FINAL_v2 (2026-08-30)

Rules capture reusable policy, eligibility, authorization, timing, validation, security, retention, and audit constraints. They constrain UCs and workflow transitions; a BR is not modeled as a workflow activity. Valid existing BR IDs are preserved. BR-SA-033..035 are added only where the prior baseline lacked reusable rules needed to preserve PS-defined audit coverage/schema, active-role permission enforcement, and the permitted configuration boundary.

BR-SA-001 - Institute Identity Uniqueness and Immutability

Rule Type

Validation / Constraint

Rule Statement

A user account must have an Institute ID that is unique across Fusion. Once created, the Institute ID cannot be changed.

Applies To

User creation and profile maintenance

Condition / Trigger

When creating or updating a user profile

Required Outcome / Constraint

Reject creation if the Institute ID already exists; reject any attempt to alter an existing Institute ID.

Exceptions / Exclusions

None stated.

Source / Rationale

PS 3.1.1; 4.1

Related CFRs / AFRs

Related UCs

UC-SA-001; UC-SA-003; UC-SA-006

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-002 - Institute Email Validation

Rule Type

Validation

Rule Statement

Only a valid institute email address may be associated with a basic user account.

Applies To

User creation and permitted profile updates

Condition / Trigger

When an email address is supplied or changed

Required Outcome / Constraint

Reject the operation if the address is not a valid institute email.

Exceptions / Exclusions

None stated.

Source / Rationale

PS 3.1.1; 4.1

Related CFRs / AFRs

Related UCs

UC-SA-001; UC-SA-003; UC-SA-006

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-003 - User-Type Required Data

Rule Type

Validation / Constraint

Rule Statement

Students must have valid program and batch information; Faculty and Staff must have a valid employee ID and department. Common mandatory user data must also be present.

Applies To

Individual and bulk user creation

Condition / Trigger

Before account creation

Required Outcome / Constraint

Reject incomplete or type-inconsistent records and report the missing/invalid fields.

Exceptions / Exclusions

Field-level mandatory set follows the approved user template.

Source / Rationale

PS 3.1.1; 3.1.3; 4.1

Related CFRs / AFRs

Related UCs

UC-SA-001; UC-SA-003; UC-SA-006

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-004 - User Archival Eligibility

Rule Type

Eligibility / Lifecycle

Rule Statement

Only a deactivated user may be archived, and the configured minimum interval between deactivation and archival must have elapsed. A user with pending transactions is not eligible for archival until those transactions are resolved.

Applies To

User archival

Condition / Trigger

When the Super Admin submits an archival request

Required Outcome / Constraint

Allow archival only when all eligibility conditions hold; otherwise reject with reason.

Exceptions / Exclusions

No emergency bypass is stated.

Source / Rationale

PS 3.3.1; 4.1; 4.3

Related CFRs / AFRs

Related UCs

UC-SA-015

Related WFs

BW-SA-07; BW-SA-08; CW-SA-03

Status / Notes / TODO

Accepted

BR-SA-005 - Archived User Reversibility Window

Rule Type

Lifecycle / Authorization

Rule Statement

An archived user may be restored only during the configured reversible period and only when the required authorization is present. Once the reversible period expires, the archived user account is permanently non-restorable.

Applies To

Archived user restoration

Condition / Trigger

When restoration is requested

Required Outcome / Constraint

Permit restoration only inside the configured reversible period with required authorization. Reject any restoration request after the period expires and keep the account permanently archived and non-restorable.

Exceptions / Exclusions

None. Post-window restoration is not permitted.

Source / Rationale

PS 3.3.1; 3.3.3; 4.1; 4.3

Related CFRs / AFRs

Related UCs

UC-SA-018; UC-SA-031

Related WFs

BW-SA-07; BW-SA-08; CW-SA-03

Status / Notes / TODO

Accepted - ISS-SA-004 resolved: post-window restoration is prohibited.

BR-SA-006 - Multiple Concurrent Roles

Rule Type

Entitlement

Rule Statement

A basic user may hold multiple additional roles simultaneously unless another rule makes a particular combination invalid.

Applies To

Role assignment

Condition / Trigger

When assigning an additional role

Required Outcome / Constraint

Do not reject merely because the user already holds another role.

Exceptions / Exclusions

Singular-role and compatibility/conflict rules still apply.

Source / Rationale

PS 3.2.1; 4.2

Related CFRs / AFRs

Related UCs

UC-SA-008; UC-SA-013

Related WFs

BW-SA-03; BW-SA-04; CW-SA-02

Status / Notes / TODO

Accepted

BR-SA-007 - Singular Role Occupancy

Rule Type

Constraint

Rule Statement

A role marked as singular may have only one active holder for the same applicable scope at any time.

Applies To

Role assignment and reassignment

Condition / Trigger

When a singular-role assignment would become active

Required Outcome / Constraint

Reject an overlapping second active holder; use reassignment where transfer is intended.

Exceptions / Exclusions

None stated.

Source / Rationale

PS 3.2.1; 3.2.2; 4.2

Related CFRs / AFRs

Related UCs

UC-SA-008; UC-SA-009; UC-SA-011

Related WFs

BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02

Status / Notes / TODO

Accepted

BR-SA-008 - Role Assignment Dating

Rule Type

Validation

Rule Statement

Every role assignment must have a start date. A time-bound role must also have an end date.

Applies To

Role assignment and validity extension

Condition / Trigger

When role-assignment parameters are submitted

Required Outcome / Constraint

Reject an assignment missing required dates.

Exceptions / Exclusions

Permanent roles may omit an end date.

Source / Rationale

PS 3.2.1; 4.2

Related CFRs / AFRs

Related UCs

UC-SA-008

Related WFs

BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02

Status / Notes / TODO

Accepted

BR-SA-009 - Automatic Role Activation and Expiry

Rule Type

Lifecycle / Trigger

Rule Statement

A future-dated assignment becomes active automatically on its start date, and a time-bound role becomes inactive automatically on its end date.

Applies To

Role lifecycle

Condition / Trigger

Configured start/end time is reached

Required Outcome / Constraint

Update role status and effective access without a separate Super Admin action.

Exceptions / Exclusions

Earlier reassignment or revocation supersedes the scheduled end.

Source / Rationale

PS 3.2.1; 3.2.4; 4.2

Related CFRs / AFRs

Related UCs

UC-SA-008; UC-SA-028; UC-SA-029

Related WFs

BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02

Status / Notes / TODO

Accepted

BR-SA-010 - Role User-Type Eligibility

Rule Type

Eligibility

Rule Statement

A role may be assigned only to a user type allowed by the role metadata. In particular, a Student cannot be assigned a Faculty/Staff-specific role.

Applies To

Role assignment and reassignment

Condition / Trigger

Before an assignment is activated

Required Outcome / Constraint

Reject incompatible assignments and identify the eligibility conflict.

Exceptions / Exclusions

No override is stated.

Source / Rationale

PS 3.2.1; 4.2; 3.5.1

Related CFRs / AFRs

Related UCs

UC-SA-008; UC-SA-009

Related WFs

BW-SA-03; BW-SA-04; CW-SA-02

Status / Notes / TODO

Accepted

BR-SA-011 - Role Conflict Validation

Rule Type

Constraint

Rule Statement

The system must check configured role conflicts before assignment, including overlapping assignments or scope conflicts represented in the role compatibility metadata.

Applies To

Role assignment and reassignment

Condition / Trigger

Before activation

Required Outcome / Constraint

Reject a conflicting assignment and report the conflict.

Exceptions / Exclusions

The exact conflict matrix is maintained as role metadata and is not edited by the Super Admin.

Source / Rationale

PS 3.2.1; 4.2; 3.5.1

Related CFRs / AFRs

Related UCs

UC-SA-008; UC-SA-009; UC-SA-011

Related WFs

BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02

Status / Notes / TODO

Accepted

BR-SA-012 - Reassignment Handover

Rule Type

Lifecycle / Routing

Rule Statement

On role reassignment, all pending tasks/requests under the role are transferred to the new role holder, and singular roles must not have two active holders during the transfer.

Applies To

Role reassignment

Condition / Trigger

Reassignment reaches its effective date

Required Outcome / Constraint

Transfer pending work, remove old access, and grant new access as one effective handover.

Exceptions / Exclusions

Emergency reassignment is immediate.

Source / Rationale

PS 3.2.2; 4.2

Related CFRs / AFRs

Related UCs

UC-SA-009

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-013 - Previous Holder Audit Access

Rule Type

Entitlement / Lifecycle

Rule Statement

After reassignment, the previous holder retains read-only access to their own prior actions for the configured audit period.

Applies To

Role reassignment

Condition / Trigger

After role access is removed

Required Outcome / Constraint

Permit read-only access to prior actions only; do not retain role-operational authority.

Exceptions / Exclusions

Duration is configurable/policy-defined; the original 30-day value is illustrative.

Source / Rationale

PS 3.2.2

Related CFRs / AFRs

Related UCs

UC-SA-009

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-014 - Role Revocation Handling

Rule Type

Lifecycle / Constraint

Rule Statement

A standard role revocation requires at least one day's notice; a revocation must record a reason and specify whether pending tasks are transferred or closed. Emergency revocation may be immediate.

Applies To

Role revocation

Condition / Trigger

When revocation is scheduled

Required Outcome / Constraint

Enforce notice for standard revocation, execute chosen pending-task handling, and remove access on the effective date.

Exceptions / Exclusions

Emergency revocation bypasses the standard notice period.

Source / Rationale

PS 3.2.3; 4.2

Related CFRs / AFRs

Related UCs

UC-SA-010

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-015 - Automatic Revocation

Rule Type

Lifecycle / Trigger

Rule Statement

A role is automatically revoked/inactivated when its validity expires or when the associated user account is deactivated.

Applies To

Role lifecycle

Condition / Trigger

Role end date reached or user becomes deactivated

Required Outcome / Constraint

Remove effective role access and preserve history.

Exceptions / Exclusions

None stated.

Source / Rationale

PS 3.2.3

Related CFRs / AFRs

Related UCs

UC-SA-004; UC-SA-007; UC-SA-010; UC-SA-028; UC-SA-029

Related WFs

BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02

Status / Notes / TODO

Accepted

BR-SA-016 - Role Expiry Reminder and Extension

Rule Type

Trigger / Validation

Rule Statement

Roles with end dates generate expiry reminders at the configured lead time. An extension requires a new end date and a reason.

Applies To

Role validity management

Condition / Trigger

Expiry approaches or extension is submitted

Required Outcome / Constraint

Send reminders; validate extension data; preserve history.

Exceptions / Exclusions

The original 30-day reminder value is illustrative rather than frozen.

Source / Rationale

PS 3.2.4; 3.6

Related CFRs / AFRs

Related UCs

UC-SA-011; UC-SA-029; UC-SA-030

Related WFs

BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02

Status / Notes / TODO

Accepted

BR-SA-017 - Historical Data Archival Eligibility

Rule Type

Eligibility

Rule Statement

Historical data is eligible for archival only when the applicable retention-age criterion is met, the business cycle/transaction is complete with no pending action, and any required module archival marking/dependency checks are satisfied.

Applies To

Historical data archival

Condition / Trigger

Before archival execution

Required Outcome / Constraint

Exclude ineligible records and report dependencies/blocks.

Exceptions / Exclusions

Audit logs are excluded from archival because BR-SA-025 requires permanent retention.

Source / Rationale

PS 3.3.2; 4.3; 4.5

Related CFRs / AFRs

Related UCs

UC-SA-016

Related WFs

BW-SA-09

Status / Notes / TODO

Accepted

BR-SA-018 - Backup Before Archival

Rule Type

Constraint

Rule Statement

A backup must be created before historical system data is moved to the archive database.

Applies To

Historical data archival

Condition / Trigger

After archival confirmation and before data movement

Required Outcome / Constraint

Abort archival if the required backup cannot be completed.

Exceptions / Exclusions

None stated.

Source / Rationale

PS 3.3.2; 4.3

Related CFRs / AFRs

Related UCs

UC-SA-016

Related WFs

BW-SA-09

Status / Notes / TODO

Accepted

BR-SA-019 - Archive Retention Policy

Rule Type

Retention

Rule Statement

Archived data must be retained for the period defined by institutional and module-specific retention policy.

Applies To

Archived users and historical data

Condition / Trigger

While records are archived

Required Outcome / Constraint

Prevent purge before the applicable retention period has elapsed.

Exceptions / Exclusions

The original 7-10 year figures are illustrative/policy-dependent.

Source / Rationale

PS 3.3.2; 4.3

Related CFRs / AFRs

Related UCs

UC-SA-015; UC-SA-016; UC-SA-021; UC-SA-031

Related WFs

BW-SA-07; BW-SA-08; BW-SA-09; CW-SA-03

Status / Notes / TODO

Accepted

BR-SA-020 - Archived Data Access Mode

Rule Type

Access Constraint

Rule Statement

Archived records exposed through the Super Admin archive interface are read-only and remain subject to the module's data-isolation rules.

Applies To

Archive search, reporting, export, restoration

Condition / Trigger

When archived records are accessed

Required Outcome / Constraint

Allow permitted retrieval/search without edit access or unauthorized module-content exposure.

Exceptions / Exclusions

Restoration changes lifecycle state but does not make the archive interface editable.

Source / Rationale

PS 3.3.2; 3.7.2

Related CFRs / AFRs

Related UCs

UC-SA-015; UC-SA-017; UC-SA-018; UC-SA-019; UC-SA-020; UC-SA-021

Related WFs

BW-SA-07; BW-SA-09; CW-SA-03

Status / Notes / TODO

Accepted

BR-SA-021 - Permanent Purge Eligibility

Rule Type

Eligibility / Destructive Action

Rule Statement

Permanent purge may be requested only after the applicable retention period has elapsed.

Applies To

Permanent purge

Condition / Trigger

When a purge is requested

Required Outcome / Constraint

Reject a purge request for data still within retention.

Exceptions / Exclusions

None stated.

Source / Rationale

PS 3.3.3; 4.3

Related CFRs / AFRs

Related UCs

UC-SA-022; UC-SA-023

Related WFs

BW-SA-01; BW-SA-02; CW-SA-01

Status / Notes / TODO

Accepted

BR-SA-022 - Dual Authorization for Purge

Rule Type

Authorization

Rule Statement

Permanent purge requires authorization by both a Super Admin and the IT Head.

Applies To

Permanent purge

Condition / Trigger

After an eligible purge request is submitted

Required Outcome / Constraint

Execute permanent purge only after IT Head approval is recorded in addition to the Super Admin request; rejection leaves the data archived.

Exceptions / Exclusions

None stated.

Source / Rationale

PS 4.3

Related CFRs / AFRs

Related UCs

UC-SA-022; UC-SA-023

Related WFs

BW-SA-01; BW-SA-02; CW-SA-01

Status / Notes / TODO

Accepted

BR-SA-023 - Role Change Notification Timing

Rule Type

Timing / Notification

Rule Statement

Affected users must receive role-assignment or role-revocation notification within one hour of the corresponding effective operation.

Applies To

Role assignment and revocation

Condition / Trigger

Assignment/revocation becomes effective

Required Outcome / Constraint

Dispatch notification within one hour.

Exceptions / Exclusions

Reassignment notification timing is not separately fixed by the source.

Source / Rationale

PS 4.4

Related CFRs / AFRs

Related UCs

UC-SA-008; UC-SA-010

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-024 - Security Alert Threshold and Channels

Rule Type

Trigger / Notification

Rule Statement

Failed login attempts must be logged, and a security alert is triggered after five consecutive failed attempts. Critical security alerts use multiple channels; SMS is an optional channel supported by the module.

Applies To

Super Admin authentication monitoring

Condition / Trigger

Failed authentication events occur

Required Outcome / Constraint

Trigger alert at the stated threshold and use configured critical-alert channels.

Exceptions / Exclusions

SMS availability is optional/configurable.

Source / Rationale

PS 3.6; 4.4; 4.6

Related CFRs / AFRs

Related UCs

UC-SA-032; UC-SA-033

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-025 - Audit Immutability and Retention

Rule Type

Compliance / Retention

Rule Statement

All Super Admin actions are auditable. Audit logs cannot be modified or deleted and are retained permanently; role-assignment history remains available after role expiry.

Applies To

All Super Admin operations and role history

Condition / Trigger

Whenever an auditable operation occurs

Required Outcome / Constraint

Write immutable audit evidence and preserve it permanently.

Exceptions / Exclusions

Other non-audit historical logs/reports may be archived subject to policy.

Source / Rationale

PS 3.7.1; 4.5

Related CFRs / AFRs

Related UCs

UC-SA-001; UC-SA-002; UC-SA-003; UC-SA-004; UC-SA-005; UC-SA-006; UC-SA-007; UC-SA-008; UC-SA-009; UC-SA-010; UC-SA-011; UC-SA-012; UC-SA-015; UC-SA-016; UC-SA-017; UC-SA-018; UC-SA-019; UC-SA-020; UC-SA-021; UC-SA-022; UC-SA-023; UC-SA-024; UC-SA-025; UC-SA-026; UC-SA-027; UC-SA-028; UC-SA-029; UC-SA-031; UC-SA-032; UC-SA-033; UC-SA-034

Related WFs

BW-SA-01; BW-SA-02; BW-SA-03; BW-SA-04; BW-SA-05; BW-SA-06; BW-SA-07; BW-SA-08; BW-SA-09; CW-SA-01; CW-SA-02; CW-SA-03

Status / Notes / TODO

Accepted

BR-SA-026 - Super Admin Data Isolation

Rule Type

Authorization / Access Constraint

Rule Statement

The Super Admin may access user identification/profile data, role information, audit logs, user activity metadata, and archive-management functions, but may not access module-specific operational content such as grades, financial details, medical/complaint content, requests/approvals, documents, and submissions.

Applies To

All Super Admin views, reports, archival functions, and handovers

Condition / Trigger

Whenever data is displayed or queried

Required Outcome / Constraint

Expose only the permitted metadata/control plane and prevent operational-content access.

Exceptions / Exclusions

System services may transfer or archive operational records without exposing their content to the Super Admin.

Source / Rationale

PS 2.1; 3.7.2; 4.5

Related CFRs / AFRs

Related UCs

UC-SA-002; UC-SA-009; UC-SA-010; UC-SA-012; UC-SA-014; UC-SA-015; UC-SA-016; UC-SA-017; UC-SA-020; UC-SA-021; UC-SA-023; UC-SA-024; UC-SA-025; UC-SA-026

Related WFs

BW-SA-07; BW-SA-08; BW-SA-09; CW-SA-03

Status / Notes / TODO

Accepted

BR-SA-027 - Super Admin Authentication and Session Controls

Rule Type

Security / Authorization

Rule Statement

Super Admin access requires a strong-password policy and mandatory two-factor authentication. Only one active Super Admin session is permitted, inactivity timeout is enforced at the configured duration, and session activity is logged.

Applies To

Super Admin authentication/session

Condition / Trigger

Login and active session

Required Outcome / Constraint

Deny access or terminate sessions that violate the controls.

Exceptions / Exclusions

IP whitelist enforcement is optional/configurable.

Source / Rationale

PS 3.7.3; 4.6

Related CFRs / AFRs

Related UCs

UC-SA-027; UC-SA-032; UC-SA-033; UC-SA-034

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-028 - No Self-Modification of Super Admin Status

Rule Type

Authorization

Rule Statement

A Super Admin cannot self-assign or modify their own Super Admin status. Super Admin assignment is performed outside this module by the IT team through direct database operation.

Applies To

Super Admin identity/status

Condition / Trigger

A Super Admin attempts to alter own Super Admin status

Required Outcome / Constraint

Reject the operation; no in-module Super Admin assignment use case is provided.

Exceptions / Exclusions

External IT-team procedure is outside this module.

Source / Rationale

PS 3.7.1; 4.6

Related CFRs / AFRs

Related UCs

N/A

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-029 - Critical Operation Reauthentication

Rule Type

Security / Authorization

Rule Statement

Critical operations require a confirmation step with authentication before execution.

Applies To

Destructive or high-impact operations such as archival/purge and other operations designated critical by policy

Condition / Trigger

Immediately before execution

Required Outcome / Constraint

Do not execute without successful confirmation/authentication.

Exceptions / Exclusions

Exact critical-operation catalogue is configuration/policy driven.

Source / Rationale

PS 3.3.2; 4.6

Related CFRs / AFRs

Related UCs

UC-SA-004; UC-SA-015; UC-SA-016; UC-SA-018; UC-SA-019; UC-SA-021; UC-SA-022; UC-SA-027

Related WFs

BW-SA-01; BW-SA-02; BW-SA-07; BW-SA-08; BW-SA-09; CW-SA-01; CW-SA-03

Status / Notes / TODO

Accepted

BR-SA-030 - Bulk Operation Limit

Rule Type

Constraint

Rule Statement

A single bulk operation may contain at most 1000 records.

Applies To

Bulk user operations

Condition / Trigger

When a bulk file/selection is submitted

Required Outcome / Constraint

Reject or require partitioning when the operation exceeds 1000 records.

Exceptions / Exclusions

None stated.

Source / Rationale

PS 4.6

Related CFRs / AFRs

Related UCs

UC-SA-006; UC-SA-007; UC-SA-027

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-031 - Password Rotation

Rule Type

Security / Timing

Rule Statement

A Super Admin password must be changed at the configured rotation interval.

Applies To

Super Admin authentication

Condition / Trigger

Configured password age is reached

Required Outcome / Constraint

Require password change according to configured policy.

Exceptions / Exclusions

The original 90-day figure is illustrative rather than frozen.

Source / Rationale

PS 3.8; 4.6

Related CFRs / AFRs

Related UCs

UC-SA-027; UC-SA-033

Related WFs

N/A

Status / Notes / TODO

Accepted

BR-SA-032 - Notification Channel Policy

Rule Type

Notification

Rule Statement

The module uses system-generated email and in-system notifications for supported events and supports SMS as an optional channel for critical security alerts.

Applies To

Module notifications

Condition / Trigger

A supported notification event occurs

Required Outcome / Constraint

Dispatch through the configured channels appropriate to the event.

Exceptions / Exclusions

SMS is optional/configurable.

Source / Rationale

PS 3.6

Related CFRs / AFRs

Related UCs

UC-SA-001; UC-SA-004; UC-SA-006; UC-SA-007; UC-SA-008; UC-SA-009; UC-SA-010; UC-SA-011; UC-SA-015; UC-SA-029; UC-SA-030; UC-SA-032

Related WFs

BW-SA-03; BW-SA-04; BW-SA-05; BW-SA-07; BW-SA-08; CW-SA-02; CW-SA-03

Status / Notes / TODO

Accepted

BR-SA-033 - Audit Event Coverage and Record Content

Rule Type

Audit / Compliance / Data-content

Rule Statement

In addition to the all-Super-Admin-actions audit rule in BR-SA-025, the module must at minimum create audit entries for user creation/profile/status changes, role assignment/reassignment/revocation, login/logout and failed login attempts, archival operations, and permitted system-configuration changes. Each audit entry must record timestamp, actor identifier, action, target user/role where applicable, IP address, result, and available context/reason.

Applies To

All auditable Super Admin-module and authentication events

Condition / Trigger

Whenever an auditable event occurs

Required Outcome / Constraint

Create an audit entry containing the required event identity and context fields; the entry is then governed by BR-SA-025 immutability and retention.

Exceptions / Exclusions

No omission is authorized for the explicitly listed event categories; fields genuinely not applicable may be absent only where the PS says “where applicable/available”.

Source / Rationale

PS 3.4.1; historical FR-SA-062 and FR-SA-063

Related CFRs / AFRs

Related UCs

UC-SA-001; UC-SA-002; UC-SA-003; UC-SA-004; UC-SA-005; UC-SA-006; UC-SA-007; UC-SA-008; UC-SA-009; UC-SA-010; UC-SA-011; UC-SA-012; UC-SA-015; UC-SA-016; UC-SA-017; UC-SA-018; UC-SA-019; UC-SA-020; UC-SA-021; UC-SA-022; UC-SA-023; UC-SA-024; UC-SA-025; UC-SA-026; UC-SA-027; UC-SA-028; UC-SA-029; UC-SA-031; UC-SA-032; UC-SA-033; UC-SA-034

Related WFs

BW-SA-01; BW-SA-02; BW-SA-03; BW-SA-04; BW-SA-05; BW-SA-06; BW-SA-07; BW-SA-08; BW-SA-09; CW-SA-01; CW-SA-02; CW-SA-03

Status / Notes / TODO

Accepted — introduced in DIRECT_FINAL_v2 to close precise audit-schema traceability.

BR-SA-034 - Active Role Selection and Permission Enforcement

Rule Type

Authorization / Constraint

Rule Statement

A user may select only a role that is currently assigned and active for that user. Module access must then be granted or denied according to the permissions of the selected active role; inactive, expired, revoked, or merely historical roles do not grant effective access.

Applies To

Basic-user role switching and module access

Condition / Trigger

When a user selects an active-role context or requests module access

Required Outcome / Constraint

Accept only a valid active assigned role and enforce its permissions as the effective authorization context.

Exceptions / Exclusions

No union of permissions from inactive or unselected roles is implied by the accepted baseline.

Source / Rationale

PS 2.2; 3.2.1; historical FR-SA-045 and FR-SA-046

Related CFRs / AFRs

Related UCs

UC-SA-013; UC-SA-014

Related WFs

N/A

Status / Notes / TODO

Accepted — introduced in DIRECT_FINAL_v2 to make the active-role authorization constraint explicit.

BR-SA-035 - Permitted System Configuration Boundary

Rule Type

Authorization / Constraint

Rule Statement

Super Admin configuration is limited to password policy, session timeout, archival retention periods within institutional policy limits, notification preferences, and bulk-operation limits. Module-specific configuration, academic calendars/schedules, financial rules/policies, and operational module workflows must not be modifiable through this module.

Applies To

Super Admin system configuration

Condition / Trigger

When a configuration change is requested

Required Outcome / Constraint

Allow only values in the permitted configuration set and within policy bounds; reject excluded configuration categories.

Exceptions / Exclusions

No additional configuration authority is implied.

Source / Rationale

PS 3.7; historical FR-SA-076 and FR-SA-077

Related CFRs / AFRs

Related UCs

UC-SA-027

Related WFs

N/A

Status / Notes / TODO

Accepted — introduced in DIRECT_FINAL_v2 to separate the configuration authorization boundary from the configuration UC.


