---
owner: iam-lead
status: design
last-reviewed: 2026-08-03
---

# Permission Catalog

> **This file is the intended taxonomy, not the implemented one.** It was
> written before the code and covers modules that do not exist yet, so a code
> listed here may not be one any view guards on.
>
> For what is actually implemented and who actually holds it, read
> [permission-catalog.generated.md](permission-catalog.generated.md). That file
> is written by `make permissions` from each module's `registry.py` and verified
> in CI, so it cannot drift.

Naming rules and semantics: [rbac-model.md](rbac-model.md#permission-codes).
Format is `<module>.<resource>.<action>`, where the first segment must be an existing
`registry_module.code` and the action comes from a closed vocabulary.

**⚠️ marks `is_dangerous`** — those permissions force MFA on their holders, require step-up
re-authentication within 5 minutes, write an `audit_event` on every use (success or failure), and appear
in the weekly privileged-access report.

---

## `iam` — identity & access administration

| Code | Description | ⚠️ |
|---|---|---|
| `iam.user.view` | View user accounts and their roles | |
| `iam.user.create` | Create a user account | |
| `iam.user.update` | Edit profile fields on a user account | |
| `iam.user.manage` | Suspend, archive or restore an account | ⚠️ |
| `iam.credential.update` | Force a password reset for another user | ⚠️ |
| `iam.mfa.manage` | Reset or remove another user's MFA factors | ⚠️ |
| `iam.session.revoke` | Revoke another user's sessions | ⚠️ |
| `iam.role.view` | View roles and their permission sets | |
| `iam.role.create` | Create a role | ⚠️ |
| `iam.role.update` | Change a role's permissions or inheritance | ⚠️ |
| `iam.role.assign` | Grant or revoke a role for a user | ⚠️ |
| `iam.module.manage` | Grant or revoke a module for a role | ⚠️ |
| `iam.audit.view` | Read the audit log | |
| `iam.audit.export` | Export the audit log | ⚠️ |

## `dashboard`

| Code | Description | ⚠️ |
|---|---|---|
| `dashboard.summary.view` | View the personal dashboard | |

## `profile`

| Code | Description | ⚠️ |
|---|---|---|
| `profile.self.view` | View own profile | |
| `profile.self.update` | Edit own profile fields | |
| `profile.document.create` | Upload a personal document | |

## `academics` — read-only ACL over the ERP

No write permissions exist by design. The platform never writes academic data
([ADR-0007](../01-architecture/adr/0007-read-only-erp-access-via-acl.md)).

| Code | Description | ⚠️ |
|---|---|---|
| `academics.standing.view_self` | View own declared academic standing | |
| `academics.standing.view` | View any student's declared standing, within scope | |
| `academics.declaration.view` | View the declaration and ingest log | |
| `academics.declaration.import` | Trigger a manual re-ingest of a declaration | ⚠️ |

## `placement_cell`

### Companies & configuration

| Code | Description | ⚠️ |
|---|---|---|
| `placement_cell.company.view` | View companies and contacts | |
| `placement_cell.company.create` | Add a company | |
| `placement_cell.company.update` | Edit a company or its tier | |
| `placement_cell.company.manage` | Blacklist or restore a company | ⚠️ |
| `placement_cell.placement_year.view` | View placement years | |
| `placement_cell.placement_year.manage` | Open, close or configure a placement year | ⚠️ |
| `placement_cell.policy.update` | Change offer policy for a year | ⚠️ |
| `placement_cell.tier.manage` | Define company tiers and their ranks | |

### Postings

| Code | Description | ⚠️ |
|---|---|---|
| `placement_cell.job_posting.view` | View postings | |
| `placement_cell.job_posting.create` | Draft a posting | |
| `placement_cell.job_posting.update` | Edit a draft posting | |
| `placement_cell.job_posting.approve` | Approve a posting for publication | |
| `placement_cell.job_posting.publish` | Publish a posting, locking its eligibility rule | ⚠️ |
| `placement_cell.job_posting.delete` | Cancel a posting | ⚠️ |

### Registration & applications

| Code | Description | ⚠️ |
|---|---|---|
| `placement_cell.registration.view` | View student registrations | |
| `placement_cell.registration.create` | Register self for a placement year | |
| `placement_cell.registration.manage` | Debar or reinstate a student | ⚠️ |
| `placement_cell.application.view_self` | View own applications | |
| `placement_cell.application.create` | Apply to a posting | |
| `placement_cell.application.delete` | Withdraw own application | |
| `placement_cell.application.view` | View applications to a posting, within scope | |
| `placement_cell.application.review` | Move an application through review and shortlisting | |

### Rounds

| Code | Description | ⚠️ |
|---|---|---|
| `placement_cell.round.view` | View selection rounds and schedules | |
| `placement_cell.round.manage` | Create, schedule and edit rounds | |
| `placement_cell.round.update` | Record round outcomes | |

### Offers

| Code | Description | ⚠️ |
|---|---|---|
| `placement_cell.offer.view_self` | View own offers | |
| `placement_cell.offer.view` | View offers, within scope | |
| `placement_cell.offer.issue` | Issue an offer to a student | ⚠️ |
| `placement_cell.offer.update` | Extend an offer's response deadline | |
| `placement_cell.offer.revoke` | Revoke an issued or accepted offer | ⚠️ |
| `placement_cell.offer.approve` | Accept an offer (the student's own action) | |

### Records, reports, exports

| Code | Description | ⚠️ |
|---|---|---|
| `placement_cell.record.view` | View placement records | |
| `placement_cell.record.update` | Correct a placement record | ⚠️ |
| `placement_cell.statistics.view` | View placement statistics | |
| `placement_cell.report.export` | Export non-PII aggregate reports | |
| `placement_cell.export.pii` | Export student-identifying data | ⚠️ |

## `hr` *(Phase 6)*

| Code | Description | ⚠️ |
|---|---|---|
| `hr.employee.view` | View employee records, within scope | |
| `hr.employee.create` | Create an employee record | |
| `hr.employee.update` | Edit an employee record | |
| `hr.employment.manage` | Create or end an appointment | ⚠️ |
| `hr.export.pii` | Export employee-identifying data | ⚠️ |

## `leave` *(Phase 6)*

| Code | Description | ⚠️ |
|---|---|---|
| `leave.request.view_self` | View own leave requests and balance | |
| `leave.request.create` | Apply for leave | |
| `leave.request.delete` | Cancel own pending request | |
| `leave.request.view` | View leave requests, within scope | |
| `leave.request.approve` | Approve or reject a leave request | |
| `leave.balance.update` | Adjust a leave balance | ⚠️ |
| `leave.type.manage` | Configure leave types and entitlement rules | |

## `sysops` *(Phase 7 — absorbed from the console)*

| Code | Description | ⚠️ |
|---|---|---|
| `sysops.backup.view` | View backup history and schedules | |
| `sysops.backup.create` | Trigger a backup | |
| `sysops.backup.manage` | Create or edit backup schedules | |
| `sysops.backup.restore` | Restore a database from a backup | ⚠️ |
| `sysops.archive.view` | View archive records | |
| `sysops.archive.manage` | Archive students or faculty | ⚠️ |
| `sysops.batch.view` | View upcoming batch configuration | |
| `sysops.batch.manage` | Configure and onboard a batch | |
| `sysops.batch.import` | Bulk-import students | ⚠️ |
| `sysops.directory.view` | Browse the user directory | |

---

## Summary

| Module | Permissions | Dangerous |
|---|---|---|
| `iam` | 14 | 9 |
| `dashboard` | 1 | 0 |
| `profile` | 3 | 0 |
| `academics` | 4 | 1 |
| `placement_cell` | 36 | 11 |
| `hr` | 5 | 2 |
| `leave` | 7 | 1 |
| `sysops` | 10 | 3 |
| **Total** | **80** | **27** |

## Built-in role assignments

Which built-in roles hold which permissions is generated into the same file by the same command. Roles
themselves are documented in [rbac-model.md](rbac-model.md#built-in-roles).

| Role | Modules granted | Notable permissions |
|---|---|---|
| `student` | `dashboard`, `profile`, `placement_cell`, `academics` | the `*_self` set, `application.create`, `offer.approve`, `registration.create` |
| `faculty` | `dashboard`, `profile`, `leave` | `leave.request.create` |
| `staff` | `dashboard`, `profile`, `leave` | `leave.request.create` |
| `placement_viewer` | `placement_cell` | `job_posting.view`, `application.view`, `statistics.view` |
| `placement_coordinator` | inherits `placement_viewer` | `application.review`, `round.manage`, `round.update`, `job_posting.create` |
| `placement_officer` | inherits `placement_coordinator` | `job_posting.publish` ⚠️, `offer.issue` ⚠️, `offer.revoke` ⚠️, `export.pii` ⚠️, `policy.update` ⚠️ |
| `hr_officer` | `hr`, `leave` | `employee.*`, `employment.manage` ⚠️, `leave.request.approve` |
| `acadadmin` | `academics`, `dashboard` | `standing.view`, `declaration.view` |
| `dean_academic` | `academics`, `dashboard`, `placement_cell` | `standing.view`, `statistics.view` |
| `iam_admin` | `iam` | the whole `iam` set — every one audited |
| `sysops` | `sysops`, `iam` (view only) | `backup.restore` ⚠️, `archive.manage` ⚠️, `batch.import` ⚠️ |

Note `placement_officer` holds every dangerous placement permission, which is why any holder of that role
automatically gets `mfa_required = True`.
