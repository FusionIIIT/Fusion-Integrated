# Super Admin module

This first implementation slice keeps institute identities and role definitions
in Fusion System Administrator (IAM). Fusion Integrated exposes authenticated,
permission-gated UI/API routes and proxies only documented IAM requests using the
current operator's session token.

## Implemented in this branch

- Read-only Student, Faculty, and Staff directory with IAM-supported filters.
- Read role metadata and a user's assigned roles.
- Proxy faculty/staff account creation, CSV import, role replacement, and password
  reset to IAM. IAM remains the authority for validation and persistence.
- Prevent a Super Admin from changing their own Super Admin assignment.
- Register module and endpoint permissions in the integrated permission manifest.

## Spec coverage still required

This is not the complete Assignment 7 feature set. The available IAM API contract
does not expose the policy-aware operations needed here, so the following use
cases remain unimplemented or only partially supported: student single-account
creation and profile updates (`UC-SA-001`, `UC-SA-003`); deactivation/reactivation
and bulk status changes (`UC-SA-004`–`UC-SA-007`); date-aware role assignment,
handover, revocation, extension, activation, expiry and reminders (`UC-SA-008`–
`UC-SA-011`, `UC-SA-028`–`UC-SA-030`); archive/restore, historical-data archive,
reports, permanent purge and dual authorization (`UC-SA-015`–`UC-SA-023`,
`UC-SA-031`); audit/report/dashboard, permitted configuration, authentication
controls and security alerts (`UC-SA-024`–`UC-SA-027`, `UC-SA-032`–`UC-SA-034`).

The current IAM role-replacement endpoint does not enforce the business-rule
preconditions for timed roles, user-type compatibility/conflict checking, or the
required pending handover. The archive service likewise does not document the
reversible-window, backup, historical-data or dual-authorization policy. Those
flows must not be presented as complete until the IAM contract is extended or a
spec-approved owner for their durable state and enforcement is established.

Super Admin status itself remains assigned by the external IT process in the
problem statement. This module does not create role definitions or grant itself
Super Admin access.
