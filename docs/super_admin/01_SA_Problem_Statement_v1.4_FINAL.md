# 01_SA_Problem_Statement_v1.4_FINAL

Problem Statement — Final Synchronized Baseline

Super Admin (SA) Module | v1.4 | FINAL SYNCHRONIZED

Artifact status

FINAL SYNCHRONIZED

Source baseline

SA v1.0 STUDENT BASELINE + resolved thread decisions

Synchronization rule

DIRECT_FINAL_v2 (2026-08-30)

1. Purpose and Context

The Super Admin Module is the administrative control plane for Fusion ERP at IIITDM Jabalpur. It manages basic-user lifecycle, additional-role assignment and lifecycle, archival control, audit/monitoring, and a limited set of system-wide administrative parameters. The module carries the highest in-application administrative privilege and is deployed separately for security and integrity.

The module is not an operational-module superuser. Its authority is intentionally limited to identity, role-control, audit/activity metadata, archive-management functions, and approved system-wide parameters; it must not expose academic, financial, medical/complaint, request/approval, document, submission, or other module-specific operational content.

2. Actors and External Roles

2.1 Super Admin

Creates and maintains Student, Faculty, and Staff basic-user accounts.

Assigns, reassigns, revokes, and extends additional roles.

Controls user and historical-data archival within policy.

Views audit/activity metadata, reports, dashboards, role availability, and archive metadata permitted by the module.

Configures only the limited system-wide parameters explicitly allocated to this module.

Cannot assign or modify their own Super Admin status.

2.2 Basic User (Student / Faculty / Staff)

Receives credentials and lifecycle/role notifications.

Views assigned roles and can switch the active role when multiple valid roles exist.

Accesses modules only through permissions of the active role.

Cannot directly request additional-role assignment under the accepted baseline.

2.3 IT Head

Participates only where explicitly required by policy: permanent purge of archived data requires dual authorization by a Super Admin and the IT Head.

2.4 IT Team (outside module boundary)

Assignment of the Super Admin role itself is performed outside this module through direct database operation by the IT team. No in-module use case is defined for assigning Super Admin status.

3. Functional Scope

3.1 User Management

Create Student, Faculty, and Staff basic-user accounts from required personal/institutional data; validate Institute ID uniqueness, institute email, user-type-required data, and duplicates.

Generate internal user ID, initial credentials, baseline dashboard access, and a welcome message with first-login guidance.

View permitted user profiles; update editable information while keeping Institute ID immutable; deactivate and reactivate accounts; preserve complete profile/status history.

Perform PS-supported bulk operations: CSV batch user creation, bulk deactivation, and permitted bulk status updates. Validate before processing, report invalid records, generate completion summaries/detailed logs, and notify the Super Admin.

3.2 Role Management

View non-editable role definitions and metadata including eligibility, singularity, validity, permissions, compatibility, module/department association, and availability/current/past holders.

Assign an additional role by specifying role, target user, start date, end date where required, scope where applicable, and reason. Validate user-type eligibility, singularity, and configured conflicts.

Support multiple simultaneous roles, future activation, automatic expiry, user dashboard role switching, assignment history, and assignment notifications.

Reassign a role to a new holder with an effective date and reason. On the effective date, remove old access, grant new access, transfer pending role tasks/requests through system services, notify both users, preserve history, and retain previous-holder read-only access to their own prior actions for the policy-defined audit period.

Revoke a role before its end date with effective date, mandatory reason, and pending-task disposition (transfer or close); support standard, emergency, and automatic revocation.

Track time-bound roles, send expiry reminders at the configured lead time, and allow validity extension with a new end date and reason.

3.3 User and Data Archival

Archive only eligible deactivated users after the policy-defined deactivation interval and after pending-transaction constraints are satisfied. Capture archival date, reason, and permitted retention option.

On user archival, disable all system access/credentials, revoke roles, move retained data to the archive, preserve required profile/role/module-participation/audit information subject to policy, and list the user under Archived Users.

Archive eligible historical data by category/date range only after retention/completion/dependency checks, authenticated confirmation, and backup. Generate an archival summary.

Provide read-only search/retrieval of permitted archived records and metadata; generate archive reports, export search results, and export authorized archive packages for external storage.

Restore archived users only during the configured reversible period when required authorization exists. Once this period expires, the archived user account becomes permanently non-restorable. Restore historical data when the required approval exists.

Permit permanent purge only after retention expiry and only through dual authorization by Super Admin and IT Head.

3.4 Audit, Monitoring, and Reporting

Maintain comprehensive logs of user, role, authentication, archival, and permitted configuration actions with timestamp, actor, action, target, IP address, result, and available context/reason.

Keep Super Admin audit logs immutable and permanently retained. Preserve role-assignment history after role expiry.

Allow read-only audit-log inspection and configurable audit reports with tabular/graphical presentation and PDF/Excel export.

Display the PS-defined dashboard metrics: user counts/status, role counts and upcoming expiry, recent user/role actions, archive volume/operations, system-health indicators, active/logged-in users, role holders, and failed-login statistics where monitoring data is available.

3.5 Notifications

Basic users receive applicable account-creation, role assignment/reassignment/revocation/expiry, deactivation, and archival notifications.

Super Admin receives bulk-operation completion, role-expiry, failed user-creation, security-alert, and archival-completion notifications.

Relevant module administrators receive role assignment/reassignment/revocation notifications for roles in their module.

Email and in-system notification are supported. SMS is an optional channel for critical security alerts. Role assignment/revocation notifications to affected users must be delivered within one hour of the effective operation.

3.6 Security and Access Control

Enforce strong-password policy and mandatory two-factor authentication for Super Admin login; optional IP-whitelist enforcement may be enabled by configuration.

Allow only one active Super Admin session; enforce the configured inactivity timeout and maintain session logs.

Log failed login attempts and alert after five consecutive failures.

Require confirmation with authentication for operations designated critical.

Prevent a Super Admin from self-assigning or changing their own Super Admin status.

Enforce the data-isolation boundary defined in Section 1 even when system services transfer/archive operational records.

3.7 Limited System Configuration

The Super Admin may configure password policy, session timeout, archival retention periods within institutional policy limits, notification preferences, and bulk-operation limits. The Super Admin may not modify module-specific configurations, academic calendars/schedules, financial rules/policies, or operational module workflows. A bulk operation is limited to 1000 records.

4. Governing Business Policies

Policy Area

Accepted Baseline

Identity

Institute ID is unique and immutable; only valid institute email addresses are accepted; user-type-required data must be present.

Role lifecycle

Multiple roles are allowed; singular roles have one active holder; start date is mandatory; time-bound roles require end date; future activation and expiry are automatic; compatibility/conflict checks are mandatory.

Reassignment/revocation

Reassignment transfers pending role work. Emergency reassignment/revocation may be immediate. Standard revocation requires at least one day notice.

Archival

Only eligible inactive/deactivated users may be archived; historical data requires policy/dependency eligibility and backup; archived data remains read-only and retained according to institutional/module policy. An archived user may be restored only during the configured reversible period with required authorization; after that period expires, the account is permanently non-restorable.

Purge

Permanent purge occurs only after retention expiry and requires Super Admin + IT Head authorization.

Notification

Affected users receive role assignment/revocation notification within one hour. Failed-login alert threshold is five consecutive failures.

Audit

All Super Admin actions are auditable; audit logs cannot be altered/deleted and are retained permanently.

Security

2FA is mandatory; critical operations require authenticated confirmation; bulk operations are limited to 1000 records; password rotation follows the configured interval.

5. Configurable / Non-Frozen Policy Parameters

Values presented in the source PS as examples ("e.g.") are not treated as fixed requirements. They are policy/configuration parameters until separately approved. This includes the deactivation-to-archive interval, reversible-archive window, role-expiry reminder lead time, previous-holder audit-access period, archive retention duration, session inactivity timeout, user-activity-log retention, and password-rotation interval.

Resolved policy decision (ISS-SA-004): an archived user may be restored only during the configured reversible period with required authorization. Once the period expires, the archived user account is permanently non-restorable; any restoration attempt must be rejected.

6. Explicit Exclusions

Creating/modifying system role definitions or permission sets from the Super Admin module.

Defining department hierarchy or assigning HoD as an organizational-structure administration function.

Generic emergency temporary user access with Director/CTO approval.

Direct user requests for additional-role assignment.

Operational module configuration, academic scheduling, financial policy, and operational workflow editing.

Assignment of Super Admin status itself (external IT-team procedure).

7. Acceptance Boundary

This v1.4 final synchronized Problem Statement is the authoritative functional-context baseline for the accompanying Requirement Registry (CFR/AFR), UC, BR, WF, and RTM artifacts. The prior v1.0 STUDENT BASELINE package remains unchanged as historical continuity evidence. All previously identified domain issues remain closed; ISS-SA-004 continues to require archived user accounts to become permanently non-restorable after the configured reversible period expires.

8. Direct-Final Continuity Note

DIRECT_FINAL_v2 changes the representation and synchronization formalism, not the accepted Super Admin domain policy. The CFR/AFR registry, event-triggered UC classification, revised workflow set, and final RTM are specified in the accompanying artifacts. No new unsupported Super Admin authority is introduced.