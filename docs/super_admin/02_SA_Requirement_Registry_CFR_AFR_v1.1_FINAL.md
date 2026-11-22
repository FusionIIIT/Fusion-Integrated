# 02_SA_Requirement_Registry_CFR_AFR_v1.1_FINAL

Requirement Registry — CFR / AFR

Super Admin (SA) Module | v1.1 | FINAL SYNCHRONIZED

Artifact status

FINAL SYNCHRONIZED

Source baseline

SA v1.0 STUDENT BASELINE + resolved thread decisions

Synchronization rule

DIRECT_FINAL_v2 (2026-08-30)

This registry supersedes the FR-only representation for the direct-final package. Historical FR-SA-001..082 IDs and wording are preserved unchanged in Section 4. AFRs are split only where independent verification, traceability, workflow modeling, or policy enforcement materially benefits.

1. Coherent / Consolidated Requirements (CFR)

CFR ID

CFR Name

CFR Statement

CFR-SA-001

Create Basic User Account

The system shall enable an authenticated Super Admin to create a valid Student, Faculty, or Staff basic-user account, validate institutional identity, establish initial credentials and baseline dashboard access, and issue first-login guidance.

CFR-SA-002

View and Maintain Basic User Profile

The system shall enable a Super Admin to view permitted basic-user profile data and update only editable profile information while preserving immutable identity fields.

CFR-SA-003

Manage User Activation Status

The system shall enable a Super Admin to deactivate and, when policy permits, reactivate basic-user accounts with controlled status transitions.

CFR-SA-004

Execute Bulk User Operations

The system shall support PS-authorized bulk user operations—CSV batch creation, bulk deactivation, and permitted bulk status updates—with pre-validation, bounded size, result reporting, detailed logs, and completion notification.

CFR-SA-005

Inspect Role Definitions and Availability

The system shall provide read-only access to system-maintained role definitions, assignment metadata, availability, and current/past holder information needed for role administration.

CFR-SA-006

Assign Additional Roles

The system shall enable a Super Admin to assign an additional role to an eligible basic user with required scope, dates, and reason; enforce eligibility, singularity, and conflict rules; support concurrent roles and scheduled activation; notify the affected user; and preserve assignment history.

CFR-SA-007

Reassign Existing Role

The system shall enable controlled reassignment of an existing role to a new eligible holder with effective-date handover, pending-work transfer, notifications, prior-holder audit access, and history preservation.

CFR-SA-008

Revoke Role

The system shall enable controlled early or emergency role revocation and automatically remove role access when account deactivation requires it, while handling pending work, notifying affected parties, and preserving audit evidence.

CFR-SA-009

Manage Time-Bound Role Validity

The system shall manage time-bound role validity by tracking validity, reminding before expiry, allowing extension, and automatically expiring or inactivating the role at the applicable end date.

CFR-SA-010

Switch Active Role and Enforce Access

The system shall allow a user with multiple valid roles to view and select the active role and shall authorize module access only according to the active role permissions.

CFR-SA-011

Archive User Account

The system shall archive only eligible deactivated users, capture required archival data, disable access, roles, and credentials, move retained information to the archive, and preserve policy-required history.

CFR-SA-012

Restore or Permanently Finalize Archived User

The system shall permit archived-user restoration only within the configured reversible period with required authorization and shall make the archived account permanently non-restorable when that period expires.

CFR-SA-013

Archive Historical Data

The system shall archive eligible historical data by category and date range only after policy and dependency checks, authenticated confirmation, and backup, and shall generate an archival summary.

CFR-SA-014

Access, Report, and Export Archived Records

The system shall provide read-only search and retrieval of permitted archived records and support archive reporting and authorized exports without violating data-isolation policy.

CFR-SA-015

AFR-SA-057

The system shall restore archived historical data to the active system only when the required approval exists.

CFR-SA-016

Permanently Purge Archived Data

The system shall permit permanent purge of archived data only after retention expiry and dual authorization by Super Admin and IT Head.

CFR-SA-017

Maintain Audit Evidence and History

The system shall create, structure, preserve, and protect comprehensive audit evidence and role/user lifecycle history for Super Admin operations.

CFR-SA-018

Audit Reporting and Administrative Monitoring

The system shall provide read-only audit inspection, configurable audit reporting and export, and the defined Super Admin dashboard and monitoring views.

CFR-SA-019

Deliver Administrative Notifications

The system shall deliver the defined account, role, bulk-operation, archival, and security notifications to the required recipients through supported channels and timing.

CFR-SA-020

Protect Administrative Access Boundary

The system shall enforce the Super Admin administrative boundary by preventing access to prohibited operational content and preventing self-modification of Super Admin status.

CFR-SA-021

Secure Super Admin Authentication and Sessions

The system shall secure Super Admin authentication and sessions through configured password controls, mandatory two-factor authentication, optional IP-whitelist enforcement, single-session and inactivity controls, failed-login monitoring, session logging, and password rotation.

CFR-SA-022

Confirm Critical Operations

The system shall require authenticated confirmation before executing operations designated critical.

CFR-SA-023

Configure Only Permitted System Parameters

The system shall allow configuration only of the limited system-wide parameters allocated to Super Admin control and shall deny changes to excluded module, academic, financial, and operational-workflow configuration.

2. Atomic Requirements (AFR)

CFR ID

AFR ID

AFR Statement

Form

Atomicity / Decomposition Rationale

Verification / Acceptance Focus

Source / PS Ref

CFR-SA-001

AFR-SA-001

The system shall allow an authenticated Super Admin to create a basic user account of type Student, Faculty, or Staff.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.1.1

CFR-SA-001

AFR-SA-002

The system shall capture the required user profile data: user type, name, institute email, contact number, Institute ID, department/program information, date of joining, and expected completion/retirement date where applicable.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.1.1

CFR-SA-001

AFR-SA-003A

The system shall validate that the Institute ID is unique across Fusion and reject creation or update that would violate uniqueness.

Rule/Constraint

Separates uniqueness validation from post-creation immutability because they have different triggers and test cases.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.1.1; 4.1

CFR-SA-002

AFR-SA-003B

The system shall prevent the Institute ID from being changed after account creation.

Rule/Constraint

Separates post-creation immutability from uniqueness validation.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.1.1; 4.1

CFR-SA-001

AFR-SA-004

The system shall accept only a valid institute email address for a user account.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.1.1; 4.1

CFR-SA-001

AFR-SA-005

The system shall prevent duplicate user creation through validation of user identity data.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.1

CFR-SA-001

AFR-SA-006

Upon successful user creation, the system shall generate a unique internal user ID.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.1

CFR-SA-001

AFR-SA-007

Upon successful user creation, the system shall generate initial login credentials securely.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.1

CFR-SA-001

AFR-SA-008

Upon successful user creation, the system shall enable basic-user dashboard access.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.1

CFR-SA-001

AFR-SA-009

Upon successful user creation, the system shall send a welcome message containing initial credential information, first-login instructions, and links to update the profile and change the password.

Notification

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.1.1; 3.6

CFR-SA-002

AFR-SA-010

The system shall allow the Super Admin to view the permitted complete profile of a basic user.

Info-access

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Verify permitted visibility/read-only behavior and denial or exclusion of prohibited data.

PS 3.1.2; 3.7.2

CFR-SA-002

AFR-SA-011

The system shall allow the Super Admin to update user information other than the Institute ID.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.1.2; 4.1

CFR-SA-003

AFR-SA-012

The system shall allow the Super Admin to deactivate an active user account.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.1.2

CFR-SA-003

AFR-SA-013

The system shall allow the Super Admin to reactivate a previously deactivated user account when reactivation is allowed by policy.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.1.2; 4.1

CFR-SA-017

AFR-SA-014

The system shall maintain an audit trail of user profile and status changes, including timestamp, reason/context, and status history.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.2; 4.5

CFR-SA-004

AFR-SA-015

The system shall allow the Super Admin to create multiple users from a predefined CSV template.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.1.3

CFR-SA-004

AFR-SA-016

The system shall allow the Super Admin to deactivate multiple users in one bulk operation.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.1.3

CFR-SA-004

AFR-SA-017

The system shall allow the Super Admin to perform permitted bulk status updates on multiple users.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.1.3

CFR-SA-004

AFR-SA-018A

Before processing a bulk user operation, the system shall validate the submitted template or file structure and operation-size constraints.

System-action

Separates batch-level validation from record-level validation.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.3

CFR-SA-004

AFR-SA-018B

Before processing a bulk user operation, the system shall validate individual records and identify invalid entries.

System-action

Separates record-level validation so invalid-record handling is independently verifiable.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.3

CFR-SA-004

AFR-SA-019A

For a bulk user operation, the system shall produce an accurate success/failure summary.

System-action

Separates completion summary from detailed processing log.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.3

CFR-SA-004

AFR-SA-019B

For a bulk user operation, the system shall produce a detailed processing log with per-record outcomes.

System-action

Separates detailed trace evidence from aggregate summary.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.1.3

CFR-SA-004

AFR-SA-020

The system shall notify the Super Admin when a bulk user operation completes.

Notification

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.1.3; 3.6

CFR-SA-005

AFR-SA-021

The system shall allow the Super Admin to view available role definitions and the metadata required for assignment, including role name/description, module or department association, user-type eligibility, singularity, default validity, permissions, and compatibility rules.

Info-access

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Verify permitted visibility/read-only behavior and denial or exclusion of prohibited data.

PS 3.5.1

CFR-SA-006

AFR-SA-022

The system shall allow the Super Admin to assign an additional role to a basic user while specifying the role, target user, start date, end date where applicable, department/module scope where applicable, and reason.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.2.1

CFR-SA-006

AFR-SA-023

The system shall support a basic user holding multiple roles simultaneously.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.2.1; 4.2

CFR-SA-006

AFR-SA-024

For a role marked singular, the system shall prevent more than one active holder for the same applicable scope and time.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.2.1; 4.2

CFR-SA-006

AFR-SA-025

Before assignment, the system shall validate role compatibility with the target user's basic user type and role eligibility metadata.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.1; 4.2

CFR-SA-006

AFR-SA-026

Before assignment, the system shall check configured role conflicts, including overlapping or incompatible assignments.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.1; 4.2

CFR-SA-006

AFR-SA-027

The system shall automatically activate a future-dated role assignment on its start date.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.1; 4.2

CFR-SA-009

AFR-SA-028

The system shall automatically make a time-bound role inactive on its end date.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.1; 3.2.4

CFR-SA-006

AFR-SA-029

The system shall notify the affected user when a role is assigned.

Notification

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.2.1; 3.6

CFR-SA-010

AFR-SA-030

The system shall expose assigned roles on the user's dashboard so that a user with multiple roles can select an active role.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.1; 2.2

CFR-SA-017

AFR-SA-031

The system shall record each role assignment in the audit trail and role-assignment history.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.1; 3.4.1; 4.5

CFR-SA-007

AFR-SA-032

The system shall allow the Super Admin to reassign an existing role to a new user while specifying the new user, effective date, and reason.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.2.2

CFR-SA-007

AFR-SA-033

On the effective date of a reassignment, the system shall remove role access from the previous holder and grant role access to the new holder.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.2

CFR-SA-007

AFR-SA-034

On role reassignment, the system shall transfer all pending tasks/requests associated with that role to the new role holder without exposing their operational content to the Super Admin.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.2; 3.7.2

CFR-SA-007

AFR-SA-035A

On role reassignment, the system shall notify both the previous and new role holders.

Notification

Notification and history retention are independently testable consequences.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.2.2; 3.6

CFR-SA-017

AFR-SA-035B

The system shall maintain complete role-reassignment history.

System-action

History preservation is a cross-cutting audit obligation rather than notification behavior.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.2; 3.6

CFR-SA-007

AFR-SA-036

After reassignment, the system shall retain the previous role holder's read-only access to their own prior actions for the configured audit period.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.2.2

CFR-SA-007

AFR-SA-037

The system shall support emergency reassignment with immediate effect.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.2.2; 4.2

CFR-SA-008

AFR-SA-038

The system shall allow the Super Admin to revoke a role before its scheduled end date while specifying revocation date, mandatory reason, and pending-task handling.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.2.3

CFR-SA-008

AFR-SA-039A

On role revocation, the system shall remove role access on the effective revocation date.

System-action

Separates effective access removal from pending-work, notification, and audit consequences.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.3; 3.6

CFR-SA-008

AFR-SA-039B

On role revocation, the system shall handle pending tasks according to the specified transfer-or-close disposition.

System-action

Pending-work disposition has distinct inputs and acceptance cases.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.3; 3.6

CFR-SA-008

AFR-SA-039C

On role revocation, the system shall notify the affected user and relevant module administrators.

Notification

Notification recipients/timing are independently verifiable.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.2.3; 3.6

CFR-SA-017

AFR-SA-039D

On role revocation, the system shall record the revocation in the audit trail.

System-action

Audit evidence is a cross-cutting obligation.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.3; 3.6

CFR-SA-009

AFR-SA-040A

The system shall automatically revoke or inactivate a time-bound role when its end date is reached.

System-action

End-date expiry and account-deactivation revocation have different triggers.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.3

CFR-SA-008

AFR-SA-040B

The system shall automatically revoke or inactivate assigned roles when the associated user account is deactivated.

System-action

Account-deactivation consequence is distinct from scheduled role expiry.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.3

CFR-SA-009

AFR-SA-041

The system shall track role validity periods and identify roles approaching expiration.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.2.4

CFR-SA-009

AFR-SA-042

The system shall send role-expiry reminders to the Super Admin and affected user at the configured reminder lead time.

Notification

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.2.4; 3.6

CFR-SA-009

AFR-SA-043

Before role expiration, the system shall allow the Super Admin to extend the end date by supplying a new end date and reason.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.2.4

CFR-SA-009

AFR-SA-044A

The system shall notify the affected user when role validity is extended.

Notification

Extension and expiry notifications have different triggers.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.2.4

CFR-SA-009

AFR-SA-044B

The system shall notify the affected user when a time-bound role expires.

Notification

Expiry notification is tied to the automatic expiry event.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.2.4

CFR-SA-010

AFR-SA-045

The system shall allow a logged-in user with multiple assigned roles to view those roles and switch the active role for the session.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 2.2; 3.2.1

CFR-SA-010

AFR-SA-046

The system shall grant or deny module access according to the permissions of the user's active role.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.2.1; module RBAC purpose

CFR-SA-011

AFR-SA-047

The system shall allow the Super Admin to archive an inactive user while specifying archival date, reason, and an allowed retention option.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.3.1

CFR-SA-011

AFR-SA-048

The system shall permit user archival only for a deactivated user after the configured minimum deactivation-to-archival interval and after other stated archival eligibility conditions are satisfied.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.3.1; 4.1; 4.3

CFR-SA-011

AFR-SA-049A

When a user is archived, the system shall disable login credentials and all system access and revoke assigned roles.

System-action

Separates access/credential consequences from archive-placement consequences.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.3.1

CFR-SA-011

AFR-SA-049B

When a user is archived, the system shall move the user record to the archive and list the user under Archived Users.

System-action

Archive placement/listing is independently verifiable.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.3.1

CFR-SA-011

AFR-SA-050

The archive shall retain the required user profile, role-assignment history, module-participation records permitted by retention policy, and activity audit trail.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.3.1

CFR-SA-012

AFR-SA-051A

The system shall allow the Super Admin to restore an archived user only during the configured reversible period and only when the required authorization is present.

Actor-service

Separates permitted restoration conditions from the automatic post-window permanent state.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.3.1; 3.3.3; 4.1; 4.3

CFR-SA-012

AFR-SA-051B

When the configured reversible period expires, the system shall keep the archived user account permanently archived and non-restorable and shall reject any later restoration attempt.

System-action / Rule

The time-triggered permanent state is independently testable and now participates in workflow progression.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.3.1; 3.3.3; 4.1; 4.3

CFR-SA-013

AFR-SA-052

The system shall allow the Super Admin to initiate archival of eligible historical system data by selecting a data category and date range.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.3.2

CFR-SA-013

AFR-SA-053

Before historical data archival, the system shall verify retention-age, completion/no-pending-action, module-marking, and dependency criteria applicable to the selected data.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.3.2; 4.3

CFR-SA-013

AFR-SA-054A

Historical data archival shall require authenticated confirmation immediately before execution.

Rule/Constraint

Reauthentication and backup are different pre-execution controls.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.3.2; 4.3; 4.6

CFR-SA-013

AFR-SA-054B

Before moving historical data to the archive, the system shall create the required backup.

System-action

Backup creation is independently verifiable.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.3.2; 4.3; 4.6

CFR-SA-013

AFR-SA-055A

After successful historical-data archival, the system shall move the eligible data to the archive database.

System-action

Separates state change from report generation.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.3.2

CFR-SA-013

AFR-SA-055B

After successful historical-data archival, the system shall generate an archival summary report.

System-action

Archival summary generation is independently verifiable.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.3.2

CFR-SA-014

AFR-SA-056

The system shall provide read-only, searchable, retrievable access to archived records subject to retention and Super Admin data-isolation constraints.

Info-access

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Verify permitted visibility/read-only behavior and denial or exclusion of prohibited data.

PS 3.3.2; 3.7.2

CFR-SA-015

AFR-SA-057

The system shall allow archived historical data to be restored to the active system when the required approval exists.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.3.2

CFR-SA-014

AFR-SA-058

The system shall allow the Super Admin to view, search, and filter archived users and permitted archived records by supported criteria including user ID/name/date range, user type, department, and role.

Info-access

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Verify permitted visibility/read-only behavior and denial or exclusion of prohibited data.

PS 3.3.3

CFR-SA-014

AFR-SA-059A

The system shall allow the Super Admin to generate archive reports from permitted archived data.

Actor-service

Separates report generation from export of results.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.3.3

CFR-SA-014

AFR-SA-059B

The system shall allow the Super Admin to export archive search or report results to CSV or PDF.

Actor-service

Export format and authorization are independently verifiable.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.3.3

CFR-SA-014

AFR-SA-060

The system shall allow the Super Admin to export archived data for external storage subject to retention and access-control policy.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.3.3

CFR-SA-016

AFR-SA-061A

The system shall permit a permanent-purge request only after the applicable retention period has elapsed.

Rule/Constraint

Separates purge eligibility from dual-authorization progression.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.3.3; 4.3

CFR-SA-016

AFR-SA-061B

The system shall execute permanent purge only after authorization by both the Super Admin and IT Head.

Rule/Constraint

Dual authorization is an independently testable multi-actor progression.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.3.3; 4.3

CFR-SA-017

AFR-SA-062

The system shall maintain logs of user creation/profile changes, role assignment/reassignment/revocation, login/logout, failed login attempts, archival operations, and permitted system-configuration changes.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.4.1

CFR-SA-017

AFR-SA-063

Each Super Admin activity log entry shall record timestamp, actor identifier, action, target user/role where applicable, IP address, result, and available context/reason.

System-action

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.4.1; 4.5

CFR-SA-018

AFR-SA-064

The system shall allow the Super Admin to view and filter audit logs without modifying them.

Info-access

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Verify permitted visibility/read-only behavior and denial or exclusion of prohibited data.

PS 2.1; 3.4.1; 4.5

CFR-SA-018

AFR-SA-065A

The system shall allow the Super Admin to generate audit reports with selectable parameters and date ranges and to sort and filter tabular results.

Actor-service

Separates report definition/tabular interaction from visualization and export.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.4.2

CFR-SA-018

AFR-SA-065B

The system shall provide graphical views for supported audit reports.

Actor-service

Graphical presentation is independently verifiable.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.4.2

CFR-SA-018

AFR-SA-065C

The system shall allow supported audit reports to be exported to PDF or Excel.

Actor-service

Export formats are independently verifiable.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.4.2

CFR-SA-018

AFR-SA-066

The Super Admin dashboard shall display the stated user, role, expiry, recent-operation, archive-volume, system-health, login, role-holder, failed-login, and archival statistics for which monitoring data is available.

Info-access

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Verify permitted visibility/read-only behavior and denial or exclusion of prohibited data.

PS 3.4.3

CFR-SA-005

AFR-SA-067

The system shall allow the Super Admin to view role availability status, search vacant roles, and view current and past role holders.

Info-access

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Verify permitted visibility/read-only behavior and denial or exclusion of prohibited data.

PS 3.5.2

CFR-SA-019

AFR-SA-068

The system shall notify basic users about account creation, role assignment/reassignment/revocation/expiry, account deactivation, and account archival as applicable.

Notification

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.6

CFR-SA-019

AFR-SA-069

The system shall notify the Super Admin about bulk-operation completion, approaching role expiries, failed user-creation attempts, security alerts, and archival-operation completion.

Notification

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.6

CFR-SA-019

AFR-SA-070

The system shall notify relevant module administrators when a role in their module is assigned, reassigned, or revoked.

Notification

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 3.6

CFR-SA-019

AFR-SA-071A

The notification subsystem shall support system-generated email and in-system notifications for supported events.

System-action

Separates mandatory channels from optional SMS support.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.6

CFR-SA-019

AFR-SA-071B

The notification subsystem shall support SMS as an optional channel for critical security alerts.

System-action

Optional SMS has a distinct configuration/availability condition.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.6

CFR-SA-020

AFR-SA-072

The system shall prevent the Super Admin from accessing module-specific operational content such as academic records, financial transactions, medical/complaint content, requests/approvals, documents, and submissions, while allowing the user/profile, role, audit/activity-metadata, and archive-management access defined for this module.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 2.1; 3.7.2; 4.5

CFR-SA-021

AFR-SA-073A

Super Admin login shall enforce the configured strong-password policy.

Rule/Constraint

Strong-password, 2FA, and optional IP whitelist are separately verifiable controls.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.3; 4.6

CFR-SA-021

AFR-SA-073B

Super Admin login shall require two-factor authentication.

Rule/Constraint

Mandatory 2FA is an independent authentication control.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.3; 4.6

CFR-SA-021

AFR-SA-073C

Super Admin login shall enforce the configured IP-whitelist check when that optional control is enabled.

Rule/Constraint

Optional IP-whitelist enforcement has a distinct activation condition.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.3; 4.6

CFR-SA-021

AFR-SA-074A

The system shall permit only one active Super Admin session at a time.

Rule/Constraint

Single-session, inactivity timeout, and session logging are distinct session controls.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.3

CFR-SA-021

AFR-SA-074B

The system shall enforce the configured Super Admin inactivity timeout.

Rule/Constraint

Inactivity timeout is independently testable.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.3

CFR-SA-021

AFR-SA-074C

The system shall maintain auditable Super Admin session logs.

System-action

Session logging is an evidence obligation distinct from session restriction.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.7.3

CFR-SA-020

AFR-SA-075

The system shall prevent a Super Admin from self-assigning or modifying their own Super Admin status.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.1; 4.6

CFR-SA-023

AFR-SA-076

The system shall allow the Super Admin to configure only the permitted system-wide parameters: password policy, session timeout, archival retention periods within policy limits, notification preferences, and bulk-operation limits.

Actor-service

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Execute the service with valid and invalid inputs and verify the stated success, rejection, and minimal-guarantee outcomes.

PS 3.8

CFR-SA-023

AFR-SA-077

The system shall prevent the Super Admin from modifying module-specific configurations, academic calendars/schedules, financial rules/policies, and operational module workflows.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.8

CFR-SA-004

AFR-SA-078

The system shall limit a bulk operation to at most 1000 records.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 4.6

CFR-SA-022

AFR-SA-079

The system shall require confirmation with authentication for critical operations.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 4.6

CFR-SA-021

AFR-SA-080A

The system shall log failed Super Admin login attempts.

System-action

Separates logging of each failed attempt from threshold alerting.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 4.4; 4.6

CFR-SA-021

AFR-SA-080B

The system shall trigger a security alert after five consecutive failed Super Admin login attempts.

System-action / Notification

The threshold alert has a distinct trigger and recipient/channel behavior.

Trigger the event and verify the specified recipients, content/channel/timing constraints, and failure handling.

PS 4.4; 4.6

CFR-SA-017

AFR-SA-081A

All Super Admin actions shall be logged.

System-action

Separates audit coverage, immutability, retention, and role-history retention.

Trigger the stated condition/event and verify the required automatic data/state/evidence change.

PS 3.7.1; 4.5

CFR-SA-017

AFR-SA-081B

Super Admin audit logs shall be immutable and shall not be modified or deleted.

Rule/Constraint

Immutability is an independent compliance constraint.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.1; 4.5

CFR-SA-017

AFR-SA-081C

Super Admin audit logs shall be retained permanently.

Rule/Constraint

Permanent retention is independently verifiable.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.1; 4.5

CFR-SA-017

AFR-SA-081D

Role-assignment history shall be retained after role expiry.

Rule/Constraint

Role-history retention has a distinct lifecycle trigger.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 3.7.1; 4.5

CFR-SA-021

AFR-SA-082

The system shall enforce password change at the configured password-rotation interval.

Rule/Constraint

Retained 1:1 because the historical requirement already expresses one coherent verifiable obligation for this baseline.

Exercise boundary, valid, and invalid conditions and verify that the constraint is enforced without unsupported bypass.

PS 4.6

##

## 3. AFR Representation and Traceability Matrix (108 AFRs)

| AFR ID | CFR ID | Mapped UC(s) | Mapped BR(s) | Mapped WF(s) | Minimum Sufficient Representation | Coverage |
|:---|:---|:---|:---|:---|:---|:---:|
| AFR-SA-001 | CFR-SA-001 | UC-SA-001 | BR-SA-001; BR-SA-002; BR-SA-003; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-002 | CFR-SA-001 | UC-SA-001 | BR-SA-003; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-003A | CFR-SA-001 | UC-SA-001; UC-SA-003 | BR-SA-001 | N/A | UC+BR | Full |
| AFR-SA-003B | CFR-SA-002 | UC-SA-003 | BR-SA-001 | N/A | UC+BR | Full |
| AFR-SA-004 | CFR-SA-001 | UC-SA-001 | BR-SA-002 | N/A | UC+BR | Full |
| AFR-SA-005 | CFR-SA-001 | UC-SA-001; UC-SA-006 | BR-SA-001; BR-SA-003 | N/A | UC+BR | Full |
| AFR-SA-006 | CFR-SA-001 | UC-SA-001 | BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-007 | CFR-SA-001 | UC-SA-001 | BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-008 | CFR-SA-001 | UC-SA-001 | BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-009 | CFR-SA-001 | UC-SA-001 | BR-SA-032; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-010 | CFR-SA-002 | UC-SA-002 | BR-SA-026; BR-SA-025 | N/A | UC+BR | Full |
| AFR-SA-011 | CFR-SA-002 | UC-SA-003 | BR-SA-001; BR-SA-002; BR-SA-003 | N/A | UC+BR | Full |
| AFR-SA-012 | CFR-SA-003 | UC-SA-004 | BR-SA-015; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-013 | CFR-SA-003 | UC-SA-005 | BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-014 | CFR-SA-017 | N/A | BR-SA-025; BR-SA-033 | N/A | BR | Full |
| AFR-SA-015 | CFR-SA-004 | UC-SA-006 | BR-SA-030; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-016 | CFR-SA-004 | UC-SA-007 | BR-SA-030; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-017 | CFR-SA-004 | UC-SA-007 | BR-SA-030; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-018A | CFR-SA-004 | UC-SA-006; UC-SA-007 | BR-SA-030 | N/A | UC+BR | Full |
| AFR-SA-018B | CFR-SA-004 | UC-SA-006; UC-SA-007 | BR-SA-001; BR-SA-002; BR-SA-003 | N/A | UC+BR | Full |
| AFR-SA-019A | CFR-SA-004 | UC-SA-006; UC-SA-007 | BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-019B | CFR-SA-004 | UC-SA-006; UC-SA-007 | BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-020 | CFR-SA-004 | UC-SA-006; UC-SA-007 | BR-SA-032 | N/A | UC+BR | Full |
| AFR-SA-021 | CFR-SA-005 | UC-SA-012 | BR-SA-026; BR-SA-025 | N/A | UC+BR | Full |
| AFR-SA-022 | CFR-SA-006 | UC-SA-008 | BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-010; BR-SA-011; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-023 | CFR-SA-006 | UC-SA-008; UC-SA-013 | BR-SA-006 | N/A | UC+BR | Full |
| AFR-SA-024 | CFR-SA-006 | UC-SA-008 | BR-SA-007 | N/A | UC+BR | Full |
| AFR-SA-025 | CFR-SA-006 | UC-SA-008 | BR-SA-010 | N/A | UC+BR | Full |
| AFR-SA-026 | CFR-SA-006 | UC-SA-008 | BR-SA-011 | N/A | UC+BR | Full |
| AFR-SA-027 | CFR-SA-006 | UC-SA-008; UC-SA-028 | BR-SA-009 | BW-SA-04; CW-SA-02 | UC+BR+WF | Full |
| AFR-SA-028 | CFR-SA-009 | UC-SA-029 | BR-SA-009; BR-SA-015 | BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02 | UC+BR+WF | Full |
| AFR-SA-029 | CFR-SA-006 | UC-SA-008 | BR-SA-023; BR-SA-032 | N/A | UC+BR | Full |
| AFR-SA-030 | CFR-SA-010 | UC-SA-013 | BR-SA-034 | N/A | UC+BR | Full |
| AFR-SA-031 | CFR-SA-017 | N/A | BR-SA-025; BR-SA-033 | N/A | BR | Full |
| AFR-SA-032 | CFR-SA-007 | UC-SA-009 | BR-SA-007; BR-SA-010; BR-SA-011; BR-SA-012; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-033 | CFR-SA-007 | UC-SA-009 | BR-SA-012; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-034 | CFR-SA-007 | UC-SA-009 | BR-SA-012 | N/A | UC+BR | Full |
| AFR-SA-035A | CFR-SA-007 | UC-SA-009 | BR-SA-023; BR-SA-032 | N/A | UC+BR | Full |
| AFR-SA-035B | CFR-SA-017 | UC-SA-009 | BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-036 | CFR-SA-007 | UC-SA-009 | BR-SA-013 | N/A | UC+BR | Full |
| AFR-SA-037 | CFR-SA-007 | UC-SA-009 | BR-SA-012; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-038 | CFR-SA-008 | UC-SA-010 | BR-SA-014; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-039A | CFR-SA-008 | UC-SA-010 | BR-SA-014; BR-SA-015 | N/A | UC+BR | Full |
| AFR-SA-039B | CFR-SA-008 | UC-SA-010 | BR-SA-014 | N/A | UC+BR | Full |
| AFR-SA-039C | CFR-SA-008 | UC-SA-010 | BR-SA-023; BR-SA-032 | N/A | UC+BR | Full |
| AFR-SA-039D | CFR-SA-017 | UC-SA-010 | BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-040A | CFR-SA-009 | UC-SA-029 | BR-SA-009; BR-SA-015 | BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02 | UC+BR+WF | Full |
| AFR-SA-040B | CFR-SA-008 | UC-SA-004; UC-SA-007; UC-SA-010 | BR-SA-015 | N/A | UC+BR | Full |
| AFR-SA-041 | CFR-SA-009 | UC-SA-030 | BR-SA-016 | N/A | UC+BR | Full |
| AFR-SA-042 | CFR-SA-009 | UC-SA-030 | BR-SA-016; BR-SA-032 | N/A | UC+BR | Full |
| AFR-SA-043 | CFR-SA-009 | UC-SA-011 | BR-SA-016 | BW-SA-05; CW-SA-02 | UC+BR+WF | Full |
| AFR-SA-044A | CFR-SA-009 | UC-SA-011 | BR-SA-032 | BW-SA-05; CW-SA-02 | UC+BR+WF | Full |
| AFR-SA-044B | CFR-SA-009 | UC-SA-029 | BR-SA-032 | BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02 | UC+BR+WF | Full |
| AFR-SA-045 | CFR-SA-010 | UC-SA-013 | BR-SA-034 | N/A | UC+BR | Full |
| AFR-SA-046 | CFR-SA-010 | UC-SA-014 | BR-SA-034; BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-047 | CFR-SA-011 | UC-SA-015 | BR-SA-004; BR-SA-019; BR-SA-029 | N/A | UC+BR | Full |
| AFR-SA-048 | CFR-SA-011 | UC-SA-015 | BR-SA-004 | N/A | UC+BR | Full |
| AFR-SA-049A | CFR-SA-011 | UC-SA-015 | BR-SA-019; BR-SA-025; BR-SA-033 | BW-SA-07; BW-SA-08; CW-SA-03 | UC+BR+WF | Full |
| AFR-SA-049B | CFR-SA-011 | UC-SA-015 | BR-SA-019; BR-SA-025; BR-SA-033 | BW-SA-07; BW-SA-08; CW-SA-03 | UC+BR+WF | Full |
| AFR-SA-050 | CFR-SA-011 | UC-SA-015 | BR-SA-019; BR-SA-020; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-051A | CFR-SA-012 | UC-SA-018 | BR-SA-005; BR-SA-020; BR-SA-029 | BW-SA-07; CW-SA-03 | UC+BR+WF | Full |
| AFR-SA-051B | CFR-SA-012 | UC-SA-031 | BR-SA-005; BR-SA-019 | BW-SA-08; CW-SA-03 | UC+BR+WF | Full |
| AFR-SA-052 | CFR-SA-013 | UC-SA-016 | BR-SA-017; BR-SA-025; BR-SA-033 | BW-SA-09 | UC+BR+WF | Full |
| AFR-SA-053 | CFR-SA-013 | UC-SA-016 | BR-SA-017 | N/A | UC+BR | Full |
| AFR-SA-054A | CFR-SA-013 | UC-SA-016 | BR-SA-029 | N/A | UC+BR | Full |
| AFR-SA-054B | CFR-SA-013 | UC-SA-016 | BR-SA-018 | BW-SA-09 | UC+BR+WF | Full |
| AFR-SA-055A | CFR-SA-013 | UC-SA-016 | BR-SA-017; BR-SA-018; BR-SA-019 | BW-SA-09 | UC+BR+WF | Full |
| AFR-SA-055B | CFR-SA-013 | UC-SA-016 | BR-SA-025; BR-SA-033 | BW-SA-09 | UC+BR+WF | Full |
| AFR-SA-056 | CFR-SA-014 | UC-SA-017 | BR-SA-020; BR-SA-026; BR-SA-025 | N/A | UC+BR | Full |
| AFR-SA-057 | CFR-SA-015 | UC-SA-019 | BR-SA-020; BR-SA-029; BR-SA-025 | BW-SA-09 | UC+BR+WF | Full |
| AFR-SA-058 | CFR-SA-014 | UC-SA-017 | BR-SA-020; BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-059A | CFR-SA-014 | UC-SA-020 | BR-SA-020; BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-059B | CFR-SA-014 | UC-SA-020 | BR-SA-020; BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-060 | CFR-SA-014 | UC-SA-021 | BR-SA-019; BR-SA-020; BR-SA-026; BR-SA-029 | N/A | UC+BR | Full |
| AFR-SA-061A | CFR-SA-016 | UC-SA-022 | BR-SA-021 | BW-SA-01; BW-SA-02; CW-SA-01 | UC+BR+WF | Full |
| AFR-SA-061B | CFR-SA-016 | UC-SA-022; UC-SA-023 | BR-SA-022 | BW-SA-01; BW-SA-02; CW-SA-01 | UC+BR+WF | Full |
| AFR-SA-062 | CFR-SA-017 | N/A | BR-SA-025; BR-SA-033 | N/A | BR | Full |
| AFR-SA-063 | CFR-SA-017 | N/A | BR-SA-033 | N/A | BR | Full |
| AFR-SA-064 | CFR-SA-018 | UC-SA-024 | BR-SA-025; BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-065A | CFR-SA-018 | UC-SA-025 | BR-SA-025; BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-065B | CFR-SA-018 | UC-SA-025 | BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-065C | CFR-SA-018 | UC-SA-025 | BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-066 | CFR-SA-018 | UC-SA-026 | BR-SA-025; BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-067 | CFR-SA-005 | UC-SA-012 | BR-SA-026 | N/A | UC+BR | Full |
| AFR-SA-068 | CFR-SA-019 | N/A | BR-SA-032 | N/A | BR | Full |
| AFR-SA-069 | CFR-SA-019 | N/A | BR-SA-032 | N/A | BR | Full |
| AFR-SA-070 | CFR-SA-019 | N/A | BR-SA-032 | N/A | BR | Full |
| AFR-SA-071A | CFR-SA-019 | N/A | BR-SA-032 | N/A | BR | Full |
| AFR-SA-071B | CFR-SA-019 | N/A | BR-SA-032 | N/A | BR | Full |
| AFR-SA-072 | CFR-SA-020 | UC-SA-014 | BR-SA-026; BR-SA-034 | N/A | UC+BR | Full |
| AFR-SA-073A | CFR-SA-021 | UC-SA-033 | BR-SA-027 | N/A | UC+BR | Full |
| AFR-SA-073B | CFR-SA-021 | UC-SA-033 | BR-SA-027 | N/A | UC+BR | Full |
| AFR-SA-073C | CFR-SA-021 | UC-SA-033 | BR-SA-027 | N/A | UC+BR | Full |
| AFR-SA-074A | CFR-SA-021 | UC-SA-033 | BR-SA-027 | N/A | UC+BR | Full |
| AFR-SA-074B | CFR-SA-021 | UC-SA-034 | BR-SA-027 | N/A | UC+BR | Full |
| AFR-SA-074C | CFR-SA-021 | UC-SA-033; UC-SA-034 | BR-SA-025; BR-SA-027; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-075 | CFR-SA-020 | N/A | BR-SA-028 | N/A | BR | Full |
| AFR-SA-076 | CFR-SA-023 | UC-SA-027 | BR-SA-035; BR-SA-027 | N/A | UC+BR | Full |
| AFR-SA-077 | CFR-SA-023 | UC-SA-027 | BR-SA-035 | N/A | UC+BR | Full |
| AFR-SA-078 | CFR-SA-004 | UC-SA-006; UC-SA-007 | BR-SA-030 | N/A | UC+BR | Full |
| AFR-SA-079 | CFR-SA-022 | N/A | BR-SA-029 | N/A | BR | Full |
| AFR-SA-080A | CFR-SA-021 | UC-SA-033; UC-SA-032 | BR-SA-024; BR-SA-025; BR-SA-033 | N/A | UC+BR | Full |
| AFR-SA-080B | CFR-SA-021 | UC-SA-032 | BR-SA-024; BR-SA-032 | N/A | UC+BR | Full |
| AFR-SA-081A | CFR-SA-017 | N/A | BR-SA-025; BR-SA-033 | N/A | BR | Full |
| AFR-SA-081B | CFR-SA-017 | N/A | BR-SA-025 | N/A | BR | Full |
| AFR-SA-081C | CFR-SA-017 | N/A | BR-SA-025 | N/A | BR | Full |
| AFR-SA-081D | CFR-SA-017 | N/A | BR-SA-025; BR-SA-033 | N/A | BR | Full |
| AFR-SA-082 | CFR-SA-021 | UC-SA-033 | BR-SA-031; BR-SA-027 | N/A | UC+BR | Full |

## 4. CFR Rollup Summary (23 CFRs)

| CFR ID | CFR Name | Semantic Profile | UC Roll-up | BR Roll-up | WF Roll-up | Coverage |
|:---|:---|:---|:---|:---|:---|:---:|
| CFR-SA-001 | Create Basic User Account | Actor-service + System-action + Validation | UC-SA-001; UC-SA-003; UC-SA-006 | BR-SA-001; BR-SA-002; BR-SA-003; BR-SA-025; BR-SA-032; BR-SA-033 | N/A | Full |
| CFR-SA-002 | View and Maintain Basic User Profile | Actor-service + Information-access + Validation | UC-SA-002; UC-SA-003 | BR-SA-001; BR-SA-002; BR-SA-003; BR-SA-025; BR-SA-026 | N/A | Full |
| CFR-SA-003 | Manage User Activation Status | Actor-service + Lifecycle | UC-SA-004; UC-SA-005 | BR-SA-015; BR-SA-025; BR-SA-033 | N/A | Full |
| CFR-SA-004 | Execute Bulk User Operations | Actor-service + Validation + Reporting + Notification | UC-SA-006; UC-SA-007 | BR-SA-001; BR-SA-002; BR-SA-003; BR-SA-025; BR-SA-030; BR-SA-032; BR-SA-033 | N/A | Full |
| CFR-SA-005 | Inspect Role Definitions and Availability | Information-access | UC-SA-012 | BR-SA-025; BR-SA-026 | N/A | Full |
| CFR-SA-006 | Assign Additional Roles | Actor-service + Validation + Lifecycle + Notification | UC-SA-008; UC-SA-013; UC-SA-028 | BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-009; BR-SA-010; BR-SA-011; BR-SA-023; BR-SA-025; BR-SA-032; BR-SA-033 | BW-SA-04; CW-SA-02 | Full |
| CFR-SA-007 | Reassign Existing Role | Actor-service + Lifecycle + Handover | UC-SA-009 | BR-SA-007; BR-SA-010; BR-SA-011; BR-SA-012; BR-SA-013; BR-SA-023; BR-SA-025; BR-SA-032; BR-SA-033 | N/A | Full |
| CFR-SA-008 | Revoke Role | Actor-service + Lifecycle + Notification | UC-SA-004; UC-SA-007; UC-SA-010 | BR-SA-014; BR-SA-015; BR-SA-023; BR-SA-025; BR-SA-032; BR-SA-033 | N/A | Full |
| CFR-SA-009 | Manage Time-Bound Role Validity | Lifecycle + Event-triggered + Notification | UC-SA-011; UC-SA-029; UC-SA-030 | BR-SA-009; BR-SA-015; BR-SA-016; BR-SA-032 | BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02 | Full |
| CFR-SA-010 | Switch Active Role and Enforce Access | Actor-service + Authorization | UC-SA-013; UC-SA-014 | BR-SA-026; BR-SA-034 | N/A | Full |
| CFR-SA-011 | Archive User Account | Actor-service + Eligibility + Lifecycle | UC-SA-015 | BR-SA-004; BR-SA-019; BR-SA-020; BR-SA-025; BR-SA-029; BR-SA-033 | BW-SA-07; BW-SA-08; CW-SA-03 | Full |
| CFR-SA-012 | Restore or Permanently Finalize Archived User | Actor-service + Event-triggered + Lifecycle + Authorization | UC-SA-018; UC-SA-031 | BR-SA-005; BR-SA-019; BR-SA-020; BR-SA-029 | BW-SA-07; BW-SA-08; CW-SA-03 | Full |
| CFR-SA-013 | Archive Historical Data | Actor-service + Eligibility + Security + Lifecycle | UC-SA-016 | BR-SA-017; BR-SA-018; BR-SA-019; BR-SA-025; BR-SA-029; BR-SA-033 | BW-SA-09 | Full |
| CFR-SA-014 | Access, Report, and Export Archived Records | Information-access + Reporting + Export + Authorization | UC-SA-017; UC-SA-020; UC-SA-021 | BR-SA-019; BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-029 | N/A | Full |
| CFR-SA-015 | Restore Archived Historical Data | Actor-service + Authorization + Lifecycle | UC-SA-019 | BR-SA-020; BR-SA-025; BR-SA-029 | BW-SA-09 | Full |
| CFR-SA-016 | Permanently Purge Archived Data | Authorization + Lifecycle + Workflow progression | UC-SA-022; UC-SA-023 | BR-SA-021; BR-SA-022 | BW-SA-01; BW-SA-02; CW-SA-01 | Full |
| CFR-SA-017 | Maintain Audit Evidence and History | System-action + Compliance + Retention | UC-SA-009; UC-SA-010 | BR-SA-025; BR-SA-033 | N/A | Full |
| CFR-SA-018 | Audit Reporting and Administrative Monitoring | Information-access + Reporting | UC-SA-024; UC-SA-025; UC-SA-026 | BR-SA-025; BR-SA-026 | N/A | Full |
| CFR-SA-019 | Deliver Administrative Notifications | Notification + Timing + Channel policy | N/A | BR-SA-032 | N/A | Full |
| CFR-SA-020 | Protect Administrative Access Boundary | Authorization + Data-isolation constraint | UC-SA-014 | BR-SA-026; BR-SA-028; BR-SA-034 | N/A | Full |
| CFR-SA-021 | Secure Super Admin Authentication and Sessions | Security + Trigger + Session control | UC-SA-032; UC-SA-033; UC-SA-034 | BR-SA-024; BR-SA-025; BR-SA-027; BR-SA-031; BR-SA-032; BR-SA-033 | N/A | Full |
| CFR-SA-022 | Confirm Critical Operations | Security + Authorization | N/A | BR-SA-029 | N/A | Full |
| CFR-SA-023 | Configure Only Permitted System Parameters | Actor-service + Authorization + Constraint | UC-SA-027 | BR-SA-027; BR-SA-035 | N/A | Full |
