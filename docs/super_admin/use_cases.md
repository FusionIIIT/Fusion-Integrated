# 03_SA_Use_Case_Specifications_v1.1_FINAL

Use Case Specifications

Super Admin (SA) Module | v1.1 | FINAL SYNCHRONIZED

Artifact status

FINAL SYNCHRONIZED

Source baseline

SA v1.0 STUDENT BASELINE + resolved thread decisions

Synchronization rule

DIRECT_FINAL_v2 (2026-08-30)

Use cases are actor-triggered or event-triggered services. For event-triggered UCs the Primary Actor is “N.A. — Event-triggered”; time/external events are stated as triggers, and the system under specification is not modeled as its own UC actor. State-changing UCs are linked to workflows only where they participate in meaningful business-state progression.

UC-SA-001 - Create Basic User

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

User Repository; Notification Service

Goal / Description

Create a Student, Faculty, or Staff basic user account with valid institutional identity data and initial access.

Trigger

Super Admin selects Create User.

Preconditions

Super Admin is authenticated; required user data is available.

Main Success Scenario

1. Super Admin selects the basic user type.2. Super Admin enters the required personal and institutional data.3. System validates mandatory/type-specific data, Institute ID uniqueness, institute email, and duplicate identity.4. Super Admin submits the valid record.5. System creates the account and generates the internal user ID and initial credentials.6. System enables basic dashboard access.7. System records the operation and sends the welcome message.

Alternative Flows

A1. Super Admin cancels before submission: no account is created.A2. Correctable validation errors: system shows the errors and returns to data entry.

Exception Flows

E1. Duplicate Institute ID or duplicate identity: creation is rejected.E2. Notification failure after account creation: account remains created; delivery failure is logged for retry/attention.

Success Postcondition

Basic user exists with dashboard access; audit evidence and welcome notification are generated.

Failure / Minimal Guarantee

No invalid/duplicate account is created; submitted invalid data is not committed.

Related Business Rules

BR-SA-001; BR-SA-002; BR-SA-003; BR-SA-025; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Legacy sources SA-UC-001 and SA-UC-012 were overlapping; consolidated into this atomic actor-goal UC.

UC-SA-002 - View User Profile

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

User Repository

Goal / Description

View the user-profile information that the Super Admin is permitted to access.

Trigger

Super Admin opens a user record.

Preconditions

Super Admin is authenticated; target user exists.

Main Success Scenario

1. Super Admin searches/selects a user.2. System retrieves the permitted profile and lifecycle status/history summary.3. System displays the profile without module-specific operational content.

Alternative Flows

A1. User is archived: system may route to the archived-user view while preserving read-only restrictions.

Exception Flows

E1. User not found or access is not permitted: system shows an appropriate message.

Success Postcondition

Permitted profile information is displayed.

Failure / Minimal Guarantee

No unauthorized operational content is disclosed.

Related Business Rules

BR-SA-025; BR-SA-026; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-003 - Update User Profile

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

User Repository

Goal / Description

Update editable user-profile information while preserving immutable identity fields and audit history.

Trigger

Super Admin chooses Edit Profile.

Preconditions

Target user exists; Super Admin is authenticated.

Main Success Scenario

1. System displays editable profile fields and the non-editable Institute ID.2. Super Admin changes permitted information and enters the reason/context where required.3. System validates the changes.4. System saves the updated profile.5. System records timestamp, actor, changed fields, and reason/context.

Alternative Flows

A1. Super Admin cancels: no changes are saved.

Exception Flows

E1. Attempt to change Institute ID: rejected.E2. Invalid institute email/type-specific data: rejected with validation feedback.

Success Postcondition

Permitted profile fields are updated and audited.

Failure / Minimal Guarantee

Original profile remains unchanged if validation fails.

Related Business Rules

BR-SA-001; BR-SA-002; BR-SA-003; BR-SA-025; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-004 - Deactivate User

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

User Repository; Role Service; Notification Service

Goal / Description

Deactivate an active user account and trigger the role/access consequences defined by policy.

Trigger

Super Admin selects Deactivate User.

Preconditions

Target user is active; Super Admin is authenticated.

Main Success Scenario

1. Super Admin selects an active user and provides the required reason/context.2. System requests confirmation for the operation where designated critical.3. Super Admin confirms.4. System marks the account deactivated.5. System automatically inactivates/revokes assigned roles as required.6. System records the status change and sends the deactivation notice.

Alternative Flows

A1. Super Admin cancels confirmation: status remains active.

Exception Flows

E1. Target is not in a deactivatable state: operation is rejected.

Success Postcondition

User is deactivated; effective role access is removed as required; status history and notification are recorded.

Failure / Minimal Guarantee

No partial unauthorized status change remains.

Related Business Rules

BR-SA-015; BR-SA-025; BR-SA-029; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-005 - Reactivate User

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

User Repository; Notification Service

Goal / Description

Return a previously deactivated user account to active status when reactivation is policy-allowed.

Trigger

Super Admin selects Reactivate User.

Preconditions

Target user is deactivated but not archived; reactivation is allowed by applicable policy.

Main Success Scenario

1. Super Admin selects the deactivated user.2. System validates reactivation eligibility and current profile data.3. Super Admin confirms reactivation.4. System marks the account active and records the status transition.5. System restores only the baseline access that is valid; previously expired/revoked additional roles are not silently recreated.

Alternative Flows

A1. Profile information requires update before reactivation: system requests correction first.

Exception Flows

E1. User is already archived or reactivation is outside policy: operation is rejected.

Success Postcondition

User account is active with valid baseline access and auditable status history.

Failure / Minimal Guarantee

Deactivated state is preserved on failure.

Related Business Rules

BR-SA-025; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-06; CW-SA-03

Notes / TODO

The original PS gives an illustrative reactivation period; the synchronized baseline treats it as policy-configurable.

UC-SA-006 - Bulk Create Users

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Batch Validation Service; User Repository; Notification Service

Goal / Description

Create multiple valid basic users from the approved CSV template.

Trigger

Super Admin selects Bulk Create and uploads a CSV file.

Preconditions

Super Admin is authenticated; file follows the published template; record count does not exceed the configured hard limit.

Main Success Scenario

1. Super Admin uploads the CSV.2. System validates file structure and record count.3. System validates each record against user-creation rules.4. System presents an error/preview summary.5. Super Admin confirms processing of the valid batch according to the supported all-or-valid-record policy.6. System creates valid accounts and sends required account notifications.7. System generates processing summary and detailed log and notifies the Super Admin.

Alternative Flows

A1. Record-level validation errors: invalid rows are identified before final processing.A2. Super Admin cancels after preview: no confirmed processing occurs.

Exception Flows

E1. Invalid template/file: rejected.E2. More than 1000 records: rejected or must be partitioned.E3. Processing service failure: committed rows and failed rows are reported accurately.

Success Postcondition

Bulk operation completes with traceable per-record results, summary, and notification.

Failure / Minimal Guarantee

No unvalidated record is silently created.

Related Business Rules

BR-SA-001; BR-SA-002; BR-SA-003; BR-SA-025; BR-SA-030; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Replaces the unsupported legacy CSV columns that assumed employee-only data and embedded role assignment.

UC-SA-007 - Bulk User Status Update

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Batch Processing Service; User Repository; Role Service; Notification Service

Goal / Description

Deactivate multiple users or apply another permitted bulk status update.

Trigger

Super Admin selects multiple users or uploads the supported status-update input and chooses a permitted bulk status operation.

Preconditions

Selected users exist; operation is permitted; count does not exceed 1000.

Main Success Scenario

1. Super Admin selects the target users and status operation.2. System validates record count and per-user eligibility.3. System shows preview and invalid targets.4. Super Admin confirms.5. System applies the permitted status updates and related role/access consequences.6. System produces summary/detailed log and notifies the Super Admin.

Alternative Flows

A1. Some targets are ineligible: system identifies them before execution.

Exception Flows

E1. Operation exceeds limit or is not a supported bulk status action: rejected.

Success Postcondition

Eligible status changes are completed and auditable; results are reported.

Failure / Minimal Guarantee

Ineligible users are not changed.

Related Business Rules

BR-SA-015; BR-SA-025; BR-SA-030; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Legacy SA-UC-019 allowed bulk role assignment and archival without PS support; synchronized scope is restricted to PS-listed bulk user operations.

UC-SA-008 - Assign Role

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Role Directory; Notification Service

Goal / Description

Assign an additional role to a basic user subject to role metadata, eligibility, dating, singularity, and conflict rules.

Trigger

Super Admin selects Assign Role for a target user or from role availability.

Preconditions

Target user exists and is eligible to hold roles; role definition is available for assignment.

Main Success Scenario

1. Super Admin selects target user and role.2. System displays role metadata and current availability.3. Super Admin enters start date, end date if time-bound, scope if applicable, and reason.4. System validates user-type eligibility, dates, singularity, and conflicts.5. Super Admin confirms the valid assignment.6. System records the assignment as active or scheduled according to start date.7. System updates role history/dashboard exposure and sends notifications.

Alternative Flows

A1. Future start date: assignment is recorded as scheduled and activates automatically later.A2. Permanent role: end date may be omitted.

Exception Flows

E1. Ineligible user, occupied singular role, invalid dates, or configured conflict: assignment is rejected with reason.

Success Postcondition

Role assignment is recorded in the correct lifecycle state, with audit/history and notification.

Failure / Minimal Guarantee

Existing assignments remain unchanged on rejection.

Related Business Rules

BR-SA-006; BR-SA-007; BR-SA-008; BR-SA-009; BR-SA-010; BR-SA-011; BR-SA-023; BR-SA-025; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-03; BW-SA-04; CW-SA-02

Notes / TODO

Legacy SA-UC-013 combined assignment and reassignment; it is split here.

UC-SA-009 - Reassign Role

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Role Service; Task Routing Service; Notification Service

Goal / Description

Transfer an existing role assignment to a new user with effective-date handover.

Trigger

Super Admin selects Reassign on an existing role assignment.

Preconditions

Existing assignment exists; new holder satisfies role eligibility and conflict rules.

Main Success Scenario

1. Super Admin selects the existing assignment and proposed new holder.2. Super Admin enters effective date and reason; may choose emergency immediate reassignment.3. System validates eligibility, conflicts, singularity, and effective date.4. Super Admin confirms.5. On the effective date, system removes old holder role access and grants new holder access.6. System transfers pending role tasks/requests without showing operational content to the Super Admin.7. System preserves prior-holder read-only audit access for the configured period, records history, and notifies both users.

Alternative Flows

A1. Future-dated reassignment: handover is scheduled.A2. Emergency reassignment: effective date is immediate.

Exception Flows

E1. New holder is ineligible/conflicting: reassignment is rejected.

Success Postcondition

Role and pending-work ownership move to the new holder without overlapping singular-role authority; history is preserved.

Failure / Minimal Guarantee

Existing assignment remains in force if validation fails.

Related Business Rules

BR-SA-007; BR-SA-010; BR-SA-011; BR-SA-012; BR-SA-013; BR-SA-025; BR-SA-026; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-010 - Revoke Role

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Role Service; Task Routing Service; Notification Service

Goal / Description

Remove a role before its scheduled end date with controlled effective date, reason, and pending-task handling.

Trigger

Super Admin selects Revoke for an active/scheduled role assignment.

Preconditions

Role assignment exists and is revocable.

Main Success Scenario

1. Super Admin selects the role assignment.2. Super Admin chooses standard or emergency revocation, specifies effective date, mandatory reason, and pending-task disposition (transfer or close).3. System validates notice/effective-date rules.4. Super Admin confirms.5. On the effective date, system removes role access and performs the selected pending-task handling.6. System records the revocation and notifies the affected user and relevant module administrators.

Alternative Flows

A1. Future standard revocation: scheduled until effective date.A2. Emergency revocation: immediate and bypasses the standard notice period.

Exception Flows

E1. Standard revocation violates minimum notice: rejected or requires a compliant effective date.

Success Postcondition

Role becomes revoked at the effective time; pending work is handled, history is retained, and notifications are sent.

Failure / Minimal Guarantee

Role remains unchanged if the request is invalid.

Related Business Rules

BR-SA-014; BR-SA-015; BR-SA-023; BR-SA-025; BR-SA-026; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-011 - Extend Role Validity

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Role Service; Notification Service

Goal / Description

Extend the validity of a time-bound role before it expires.

Trigger

Super Admin acts on an expiry reminder or opens an active time-bound assignment.

Preconditions

Role is active and has an end date; new end date is later and otherwise valid.

Main Success Scenario

1. Super Admin opens the role assignment.2. System displays current validity and history.3. Super Admin enters new end date and reason.4. System validates the extension.5. Super Admin confirms.6. System updates the end date, records history, and notifies the affected user.

Alternative Flows

A1. Super Admin chooses no extension: role expires naturally under lifecycle rules.

Exception Flows

E1. Invalid new end date or conflict caused by extension: rejected.

Success Postcondition

Role remains active through the new valid end date; change is audited and user notified.

Failure / Minimal Guarantee

Original end date remains on failure.

Related Business Rules

BR-SA-007; BR-SA-011; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-05; CW-SA-02

Notes / TODO

N/A

UC-SA-012 - View Role Metadata and Availability

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Role Directory

Goal / Description

Inspect non-editable role definitions, availability, current assignment status, and role history.

Trigger

Super Admin opens Role Directory/Availability.

Preconditions

Super Admin is authenticated.

Main Success Scenario

1. System lists role definitions and metadata.2. Super Admin searches/filters roles including vacant roles.3. System shows availability status, current holder(s), scope, and past-holder history as permitted.

Alternative Flows

A1. Deprecated or temporarily unavailable role: system displays its status but does not offer normal assignment.

Exception Flows

E1. Role metadata service unavailable: system reports that the directory cannot be loaded.

Success Postcondition

Role metadata and availability are displayed read-only.

Failure / Minimal Guarantee

No role definition or permission set is modified.

Related Business Rules

BR-SA-025; BR-SA-026; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Retires legacy SA-UC-003/020 role-definition editing; PS permits viewing but states role metadata is not editable by Super Admin.

UC-SA-013 - Switch Active Role

UC Type

Actor-triggered

Primary Actor

Basic User

Supporting Actors / Systems

Role Service

Goal / Description

Select which one of the user's assigned roles is active for the current session.

Trigger

Logged-in user opens the role switcher.

Preconditions

User has more than one assigned role; selected role is currently active/valid.

Main Success Scenario

1. System displays the user's currently valid assigned roles.2. User selects a role.3. System validates that the role remains active for the user.4. System updates the session active-role context and refreshes dashboard/module options.

Alternative Flows

A1. User selects the already-active role: no material change is required.

Exception Flows

E1. Selected role has expired/revoked since display: switch is denied and role list is refreshed.

Success Postcondition

Session active-role context is updated to a valid assigned role.

Failure / Minimal Guarantee

Existing active-role context remains if the switch fails.

Related Business Rules

BR-SA-006; BR-SA-034

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Legacy SA-UC-015 retained semantically.

UC-SA-014 - Access Module by Active Role

UC Type

Actor-triggered

Primary Actor

Basic User

Supporting Actors / Systems

Module Access Service

Goal / Description

Open only modules/resources permitted by the active role.

Trigger

User selects a module link.

Preconditions

User is authenticated and has an active role context.

Main Success Scenario

1. User selects a module/resource.2. System evaluates the active role's permission mapping.3. If permitted, system opens the module in the authorized role context and logs access metadata.4. If not permitted, access is denied.

Alternative Flows

A1. User may switch role and retry if another assigned role provides the required permission.

Exception Flows

E1. Role becomes inactive during access check: deny access and refresh role context.

Success Postcondition

Authorized module access is granted only within active-role permissions.

Failure / Minimal Guarantee

Unauthorized module content is not disclosed.

Related Business Rules

BR-SA-026; BR-SA-034

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Legacy SA-UC-016 retained semantically.

UC-SA-015 - Archive User

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

User Repository; Role Service; Archive Repository; Notification Service

Goal / Description

Move an eligible deactivated user and allowed retained data into the archive.

Trigger

Super Admin selects Archive User.

Preconditions

Target user is deactivated; minimum deactivation interval has elapsed; no unresolved pending transaction blocks archival.

Main Success Scenario

1. Super Admin selects the user(s), archival date, reason, and allowed retention option.2. System validates archival eligibility and dependencies without exposing unauthorized operational content.3. Super Admin confirms the critical operation with authentication.4. System revokes remaining role/access state, disables credentials, and moves the permitted retained record set to the archive.5. System lists the user under Archived Users, writes audit evidence, and sends the archival notice.

Alternative Flows

A1. Multiple individually selected eligible users may be processed when the archive interface supports that selection.

Exception Flows

E1. User is active, deactivation interval has not elapsed, or pending transaction exists: archival is rejected.E2. Archive storage failure: original data remains protected and failure is logged.

Success Postcondition

User is archived with access disabled and retained information preserved according to policy.

Failure / Minimal Guarantee

No ineligible user is archived; no unauthorized data is exposed to the Super Admin.

Related Business Rules

BR-SA-004; BR-SA-019; BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-07; BW-SA-08; CW-SA-03

Notes / TODO

Legacy SA-UC-014 was split because user archival and historical-data archival have materially different conditions.

UC-SA-016 - Archive Historical Data

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Archive Service; Backup Service; Module Metadata Services

Goal / Description

Archive eligible historical system data by category/date range without giving the Super Admin operational-content access.

Trigger

Super Admin selects Historical Data Archival.

Preconditions

Selected category is archive-enabled and retention/dependency metadata is available.

Main Success Scenario

1. Super Admin selects data category and date range.2. System produces an allowed summary and dependency/eligibility assessment.3. Super Admin reviews the summary and confirms with authentication.4. System creates the required backup.5. System moves eligible data to the archive database.6. System generates the archival summary and records the operation.

Alternative Flows

A1. Some records are ineligible: system excludes/identifies them according to archive policy and presents the impact before confirmation.

Exception Flows

E1. Pending actions/dependencies block all selected data: archival does not proceed.E2. Backup failure: archival is aborted.

Success Postcondition

Eligible historical data is archived with backup and summary report; audit evidence is preserved.

Failure / Minimal Guarantee

Active data and audit logs that are not eligible remain unchanged.

Related Business Rules

BR-SA-017; BR-SA-018; BR-SA-019; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-09

Notes / TODO

N/A

UC-SA-017 - Search and View Archived Records

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Archive Query Service

Goal / Description

Locate and view permitted archived users/records in read-only form.

Trigger

Super Admin opens Archive Management/Search.

Preconditions

Archive query service is available; Super Admin is authenticated.

Main Success Scenario

1. Super Admin enters one or more supported criteria.2. System searches archived records.3. System returns permitted metadata/results with filters.4. Super Admin opens a selected archived record in read-only mode.

Alternative Flows

A1. No matches: empty result set is shown.

Exception Flows

E1. Query requests restricted operational content: system does not expose it.

Success Postcondition

Matching permitted archive records are displayed read-only.

Failure / Minimal Guarantee

Archive content remains unmodified and restricted content undisclosed.

Related Business Rules

BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-018 - Restore Archived User

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Archive Service; User Repository

Goal / Description

Restore an archived user only within the policy-defined reversible period when required authorization exists.

Trigger

Super Admin selects Restore on an archived user.

Preconditions

User is within the configured reversible period; required authorization has been obtained/recorded. The reversible period has not expired.

Main Success Scenario

1. Super Admin selects the archived user.2. System checks reversible-window eligibility and authorization evidence.3. System shows the permitted restoration impact.4. Super Admin confirms with authentication.5. System restores the user record to the active user store and records the lifecycle transition.6. System restores only access that remains valid under current role/account policy.

Alternative Flows

A1. Restored account may require profile/status review before normal use.

Exception Flows

E1. Required authorization is absent: reject.E2. Reversible period has elapsed: reject restoration; the account remains permanently archived and non-restorable.

Success Postcondition

Eligible user is restored with auditable lifecycle transition.

Failure / Minimal Guarantee

Archived state remains on failure. If the reversible period has elapsed, the account remains permanently archived and cannot be restored.

Related Business Rules

BR-SA-005; BR-SA-020; BR-SA-025; BR-SA-029; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-07; CW-SA-03

Notes / TODO

Post-window restoration is prohibited; policy resolved by ISS-SA-004.

UC-SA-019 - Restore Archived Historical Data

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Archive Service

Goal / Description

Restore archived historical data to the active system when the required approval exists.

Trigger

Super Admin selects Restore Data on an archived data set.

Preconditions

Target archived data is restorable under policy and required approval is available.

Main Success Scenario

1. Super Admin selects the archived data set.2. System validates retention/restoration rules and approval evidence.3. System shows dependency/impact summary.4. Super Admin confirms with authentication.5. System restores the data to the active store in a controlled manner and records the operation.

Alternative Flows

A1. Restore may be limited to an approved subset when policy permits.

Exception Flows

E1. Approval missing or dependencies prevent restoration: operation is rejected.

Success Postcondition

Approved archived data is restored and auditable.

Failure / Minimal Guarantee

Archived data remains unchanged if restoration fails.

Related Business Rules

BR-SA-020; BR-SA-025; BR-SA-029; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-09

Notes / TODO

The approving authority is not identified in the PS; approval is therefore a precondition rather than a modeled actor workflow.

UC-SA-020 - Generate and Export Archive Report

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Archive Query Service; Report Service

Goal / Description

Generate reports from permitted archived data and export archive search/report results.

Trigger

Super Admin selects Report/Export from Archive Management.

Preconditions

Permitted archive result set or report parameters are available.

Main Success Scenario

1. Super Admin chooses report/search criteria.2. System generates a permitted read-only report.3. Super Admin may export search/report results to CSV or PDF.4. System records the export/report action.

Alternative Flows

A1. Large result set: system applies supported batching/pagination.

Exception Flows

E1. Requested fields violate data-isolation policy: restricted fields are excluded/denied.

Success Postcondition

Report/export is produced without altering archived records.

Failure / Minimal Guarantee

Archive remains unchanged and restricted content is not disclosed.

Related Business Rules

BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-021 - Export Archived Data for External Storage

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Archive Service; Export Service

Goal / Description

Create an authorized export package of archived data for external storage.

Trigger

Super Admin selects Export Archived Data.

Preconditions

Target archive data is exportable under retention/access policy.

Main Success Scenario

1. Super Admin selects the archive set and export destination/package options allowed by policy.2. System validates access and export eligibility.3. Super Admin confirms if designated critical.4. System generates the export package and records the operation.

Alternative Flows

A1. Export is metadata-only where operational content is not permitted to the Super Admin.

Exception Flows

E1. Policy/access validation fails: export is rejected.

Success Postcondition

Authorized export package is produced and audited.

Failure / Minimal Guarantee

No unauthorized content is exported through the Super Admin interface.

Related Business Rules

BR-SA-019; BR-SA-020; BR-SA-025; BR-SA-026; BR-SA-029; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-022 - Request Permanent Data Purge

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Archive Service

Goal / Description

Request permanent purge of retention-expired archived data, initiating required dual authorization.

Trigger

Super Admin selects Permanently Purge on eligible archived data.

Preconditions

Target data is archived; applicable retention period has elapsed.

Main Success Scenario

1. Super Admin selects the archived data set.2. System validates retention expiry and purge eligibility.3. System shows the destructive-action impact.4. Super Admin confirms with authentication and submits the purge request.5. System records the Super Admin authorization and places the request in Pending IT Head Authorization state.

Alternative Flows

A1. Super Admin cancels before submission: no request is created.

Exception Flows

E1. Retention period has not elapsed: request is rejected.

Success Postcondition

A purge request exists pending IT Head decision; data remains archived.

Failure / Minimal Guarantee

No data is purged without the second authorization.

Related Business Rules

BR-SA-021; BR-SA-022; BR-SA-025; BR-SA-029; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-01; BW-SA-02; CW-SA-01

Notes / TODO

N/A

UC-SA-023 - Authorize Permanent Data Purge

UC Type

Actor-triggered

Primary Actor

IT Head

Supporting Actors / Systems

Archive Service

Goal / Description

Approve or reject a pending permanent-purge request as the second required authorizer.

Trigger

IT Head opens a pending purge authorization request.

Preconditions

A valid purge request exists with recorded Super Admin authorization; IT Head is authenticated and authorized for this decision.

Main Success Scenario

1. IT Head reviews the purge request metadata and impact summary permitted by policy.2. IT Head chooses Approve or Reject and records the decision.3. If approved, system records second authorization and executes the permanent purge.4. If rejected, system closes/rejects the request and leaves data archived.5. System records the decision and resulting state.

Alternative Flows

A1. IT Head requests no decision and exits: request remains pending.

Exception Flows

E1. Request is no longer eligible or has already been decided: decision is rejected.

Success Postcondition

Approved request results in permanent purge; rejected request leaves data archived; decision is auditable.

Failure / Minimal Guarantee

Archived data is never purged on an invalid/incomplete authorization path.

Related Business Rules

BR-SA-021; BR-SA-022; BR-SA-025; BR-SA-026; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-01; BW-SA-02; CW-SA-01

Notes / TODO

N/A

UC-SA-024 - View Audit Log

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Audit Log Service

Goal / Description

Inspect immutable audit and activity-log entries with filters.

Trigger

Super Admin selects Audit Log.

Preconditions

Super Admin is authenticated.

Main Success Scenario

1. System loads audit-log entries accessible to the Super Admin.2. Super Admin applies supported filters/search criteria.3. System displays matching immutable entries and details.

Alternative Flows

A1. No matching entries: empty result set is shown.

Exception Flows

E1. Log service unavailable: system reports the failure without altering logs.

Success Postcondition

Audit evidence is displayed read-only.

Failure / Minimal Guarantee

No audit record is modified or deleted.

Related Business Rules

BR-SA-025; BR-SA-026; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Legacy SA-UC-005 retained semantically; export belongs to report UC.

UC-SA-025 - Generate Audit Report

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Report Service; Audit Log Service

Goal / Description

Analyze permitted audit/activity information and produce configurable reports.

Trigger

Super Admin selects Audit Reports.

Preconditions

Audit/report data sources are available.

Main Success Scenario

1. Super Admin selects report type, date range, filters, and parameters.2. System generates tabular and/or graphical results.3. Super Admin sorts/filters the displayed report.4. Super Admin may export the report to PDF or Excel.5. System records report/export activity.

Alternative Flows

A1. No data for parameters: report is generated with no-result indication.

Exception Flows

E1. Requested report would expose prohibited operational content: restricted data is excluded/denied.

Success Postcondition

Requested permitted report is displayed/exported and audited.

Failure / Minimal Guarantee

Audit source remains immutable.

Related Business Rules

BR-SA-025; BR-SA-026; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-026 - View Super Admin Dashboard

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Monitoring/Analytics Services

Goal / Description

View the dashboard metrics and near-real-time administrative/security indicators defined for the module.

Trigger

Super Admin opens the module dashboard.

Preconditions

Super Admin is authenticated; required metric sources are available.

Main Success Scenario

1. System aggregates user, role, expiry, recent operation, archive-volume, system-health, active-session, failed-login, and archive-operation metrics.2. System displays the dashboard.3. Super Admin may navigate from a metric to the corresponding permitted detail view where available.

Alternative Flows

A1. A metric source is unavailable: system marks that metric unavailable/stale without fabricating a value.

Exception Flows

E1. Dashboard service failure: system reports the failure.

Success Postcondition

Available dashboard metrics are displayed without operational-content leakage.

Failure / Minimal Guarantee

No restricted content is disclosed.

Related Business Rules

BR-SA-025; BR-SA-026; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

N/A

UC-SA-027 - Configure Permitted System Parameters

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Configuration Service

Goal / Description

Change only the limited system-wide parameters allocated to Super Admin control.

Trigger

Super Admin selects System Configuration.

Preconditions

Super Admin is authenticated; selected parameter is within the permitted configuration set.

Main Success Scenario

1. System displays permitted parameters: password policy, session timeout, archival retention periods within policy limits, notification preferences, and bulk-operation limits.2. Super Admin edits a permitted value.3. System validates policy bounds.4. For a critical change, system requests authenticated confirmation.5. System saves the valid change and records it in the audit log.

Alternative Flows

A1. Super Admin cancels: no configuration change is made.

Exception Flows

E1. Attempt to modify module-specific configuration, academic calendar/schedule, financial policy, or operational workflow: denied.E2. Value violates policy bounds: rejected.

Success Postcondition

Only permitted configuration is changed and audited.

Failure / Minimal Guarantee

Forbidden configuration remains unchanged.

Related Business Rules

BR-SA-025; BR-SA-027; BR-SA-029; BR-SA-030; BR-SA-031; BR-SA-033; BR-SA-035

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Legacy role/permission editing is not part of this configuration UC.

UC-SA-028 - Activate Scheduled Role Assignment

UC Type

Event-triggered

Primary Actor

N.A. — Event-triggered

Supporting Actors / Systems

N.A.

Goal / Description

Activate a valid future-dated role assignment automatically when its start date is reached.

Trigger

Configured role-assignment start date/time is reached.

Preconditions

A valid role assignment exists in Scheduled state; it has not been superseded by reassignment/revocation and the associated user remains eligible and active.

Main Success Scenario

1. The start-date event occurs.2. System verifies that the scheduled assignment is still valid and not superseded.3. System changes the assignment status to Active and enables the role permissions for the user.4. System exposes the active role in the user role context and records the lifecycle transition in audit/history.

Alternative Flows

A1. Assignment was superseded before the start date: no activation occurs; existing superseding state is preserved.

Exception Flows

E1. Associated user is no longer eligible/active at activation time: system does not activate the assignment and records the failed transition for administrative attention.

Success Postcondition

Scheduled role becomes active at its start date with effective access and preserved history.

Failure / Minimal Guarantee

No invalid or superseded scheduled assignment is activated.

Related Business Rules

BR-SA-009; BR-SA-015; BR-SA-025; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-04; CW-SA-02

Notes / TODO

Introduced by DIRECT_FINAL_v2 to represent a meaningful time-event system service explicitly; System is not modeled as the UC actor.

UC-SA-029 - Expire Time-Bound Role

UC Type

Event-triggered

Primary Actor

N.A. — Event-triggered

Supporting Actors / Systems

Basic User (affected user / notification recipient)

Goal / Description

Expire and inactivate a time-bound role automatically when its effective end date is reached.

Trigger

Effective role end date/time is reached.

Preconditions

Role assignment is active (including an extended assignment) and has not been superseded by reassignment or revocation.

Main Success Scenario

1. The end-date event occurs.2. System verifies that the assignment is still active and the end date is current.3. System changes the role assignment to Expired/Inactive and removes effective role access.4. System preserves role-assignment history.5. System notifies the affected user of role expiry and records the transition.

Alternative Flows

A1. The role was validly extended before the original end date: system uses the revised end date and does not expire at the superseded date.

Exception Flows

E1. Lifecycle update fails: role state is not silently changed; failure is logged for recovery/attention.

Success Postcondition

Time-bound role is inactive after its applicable end date; history and expiry notification are preserved.

Failure / Minimal Guarantee

No premature expiry occurs and prior history remains intact.

Related Business Rules

BR-SA-009; BR-SA-015; BR-SA-016; BR-SA-025; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-03; BW-SA-04; BW-SA-05; CW-SA-02

Notes / TODO

Introduced by DIRECT_FINAL_v2 to make automatic expiry a first-class event-triggered service.

UC-SA-030 - Send Role-Expiry Reminder

UC Type

Event-triggered

Primary Actor

N.A. — Event-triggered

Supporting Actors / Systems

Super Admin; Basic User (affected user)

Goal / Description

Notify the Super Admin and affected user when a time-bound role approaches expiration at the configured reminder lead time.

Trigger

Configured reminder lead-time point is reached for an active time-bound role.

Preconditions

Role has a valid end date and remains active; reminder configuration is available.

Main Success Scenario

1. Reminder event is reached.2. System verifies that the role is still active and approaching its current end date.3. System sends the expiry reminder to the Super Admin and affected user through supported configured channels.4. System records notification outcome.

Alternative Flows

A1. End date was extended before reminder dispatch: system evaluates the current end date and suppresses an obsolete reminder.

Exception Flows

E1. A delivery channel fails: role state is unchanged; failure is logged for retry/attention according to notification service behavior.

Success Postcondition

Required recipients receive or have a traceable delivery attempt for the configured expiry reminder.

Failure / Minimal Guarantee

No role lifecycle state is changed by reminder failure.

Related Business Rules

BR-SA-016; BR-SA-032

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Non-state-changing event-triggered UC; therefore intentionally not an STT workflow step.

UC-SA-031 - Finalize Archived User as Permanently Non-Restorable

UC Type

Event-triggered

Primary Actor

N.A. — Event-triggered

Supporting Actors / Systems

N.A.

Goal / Description

Apply the accepted archival policy when an archived user reaches the end of the configured reversible period.

Trigger

Configured reversible archival period expires for an archived user.

Preconditions

User account is archived and remains within the reversible lifecycle until this event; no valid restoration completed before expiry.

Main Success Scenario

1. Reversible-period expiry event occurs.2. System verifies that the user remains archived and has not been restored.3. System marks the archival lifecycle as permanent/non-restorable.4. System preserves the archived account and required retained information.5. System records the lifecycle transition.

Alternative Flows

A1. User was validly restored before expiry: no permanent-archive transition occurs.

Exception Flows

E1. Lifecycle update cannot be committed: current archived state is preserved and failure is logged for recovery; restoration must not be enabled merely because the update failed.

Success Postcondition

Archived account is permanently non-restorable after expiry of the reversible period.

Failure / Minimal Guarantee

Archived account is not incorrectly restored or made accessible.

Related Business Rules

BR-SA-005; BR-SA-019; BR-SA-025; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

BW-SA-08; CW-SA-03

Notes / TODO

Implements the thread-resolved ISS-SA-004 policy as an explicit time-event lifecycle service.

UC-SA-032 - Process Failed-Login Threshold Alert

UC Type

Event-triggered

Primary Actor

N.A. — Event-triggered

Supporting Actors / Systems

Super Admin (security-alert recipient)

Goal / Description

Log failed Super Admin authentication attempts and trigger the required security alert when five consecutive failures are observed.

Trigger

A failed Super Admin authentication event is received; alert behavior applies when the consecutive-failure count reaches five.

Preconditions

Authentication monitoring and notification channels are available.

Main Success Scenario

1. Failed-authentication event occurs.2. System writes the failed-login audit event.3. System evaluates the consecutive-failure count.4. When the count reaches five, system creates a security alert.5. System dispatches the alert through configured critical-security channels, with SMS used only when that optional channel is enabled.

Alternative Flows

A1. Consecutive-failure count is below five: attempt is logged but no threshold alert is dispatched.

Exception Flows

E1. Notification delivery fails: failed-login evidence and alert state remain recorded; delivery failure is logged.

Success Postcondition

Every failed attempt is logged, and the fifth consecutive failure triggers a traceable security alert.

Failure / Minimal Guarantee

Authentication failures are not silently discarded; no unsupported access is granted.

Related Business Rules

BR-SA-024; BR-SA-025; BR-SA-027; BR-SA-032; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Event-triggered monitoring UC; no workflow is created because the service does not participate in a broader business-state progression.

UC-SA-033 - Authenticate Super Admin and Establish Session

UC Type

Actor-triggered

Primary Actor

Super Admin

Supporting Actors / Systems

Two-Factor Authentication Service; authentication/session infrastructure

Goal / Description

Authenticate a Super Admin and establish at most one valid administrative session under the configured security controls.

Trigger

Super Admin opens the dedicated Super Admin login and submits authentication credentials.

Preconditions

Super Admin account exists and is eligible to authenticate; authentication services are available.

Main Success Scenario

1. Super Admin submits identity credentials.2. System validates the configured strong-password policy and applies the optional IP-whitelist check when enabled.3. System requires successful two-factor authentication.4. System verifies that establishing the session would not violate the single-active-session rule.5. If the configured password-rotation interval requires a password change, the Super Admin completes the required change before session establishment.6. System establishes the administrative session and records the session/login audit evidence.

Alternative Flows

A1. Password rotation is due: system requires a compliant password change before completing authentication.A2. Optional IP whitelist is disabled: no whitelist rejection is applied.

Exception Flows

E1. Credential, IP-whitelist, or 2FA validation fails: no session is established and the failed authentication event is processed by UC-SA-032.E2. Another active Super Admin session would cause a second concurrent session: the new session is not established.

Success Postcondition

Exactly one valid Super Admin session is established under configured authentication controls and session logging is preserved.

Failure / Minimal Guarantee

No unauthorized or second concurrent Super Admin session is created; failed authentication evidence is retained.

Related Business Rules

BR-SA-024; BR-SA-025; BR-SA-027; BR-SA-031; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Added in DIRECT_FINAL_v2 because the PS contains explicit Super Admin authentication/session obligations that were previously represented only as rules.

UC-SA-034 - Terminate Inactive Super Admin Session

UC Type

Event-triggered

Primary Actor

N.A. — Event-triggered

Supporting Actors / Systems

Super Admin (affected session user)

Goal / Description

Terminate an active Super Admin session automatically when the configured inactivity timeout is reached.

Trigger

Configured inactivity duration elapses for the active Super Admin session.

Preconditions

A Super Admin session is active and has remained inactive for the configured timeout duration.

Main Success Scenario

1. Inactivity-timeout event occurs.2. System verifies that the session has not become active again and the current configured timeout is satisfied.3. System terminates the session.4. System records the session termination in the session/audit log.5. Any later administrative action requires a new successful authentication.

Alternative Flows

A1. Valid activity occurs before timeout evaluation completes: session remains active and the inactivity timer is evaluated from the new activity point.

Exception Flows

E1. Session-termination infrastructure fails: system must not silently treat the session as valid beyond policy; failure is recorded for security recovery/attention.

Success Postcondition

Inactive Super Admin session is terminated at the configured timeout and the termination is auditable.

Failure / Minimal Guarantee

No additional administrative access is granted because of timeout-processing failure.

Related Business Rules

BR-SA-025; BR-SA-027; BR-SA-033

Related CFRs / AFRs

Related Workflow(s)

N/A

Notes / TODO

Event-triggered session-control service. It is not a workflow step because it is an isolated session-state transition rather than part of a broader business workflow.