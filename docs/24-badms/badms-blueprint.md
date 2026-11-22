# BADMS Blueprint

**Status:** Draft implementation exists. The user reports that Student 2 has since
accepted the changes, but a dated written approval record is not included here. The
implementation remains subject to the unresolved platform/infrastructure decisions and
is not ready for deployment.
**Assignment:** BADMS · `24-BADMS` · prefix `BA` · module code `badms` · module-only.

## Phase 0 — specification and platform findings

### Specification inventory

- 19 CFRs and 66 active AFRs (`AFR-BA-001`–`043`, `045`–`049`, `051`–`068`).
- 23 use cases (`BA-UC-001`–`023`).
- 21 business rules (`BR-BA-001`–`021`).
- Seven basis workflows (`BW-BA-01`–`07`) and three composite workflows
  (`CW-BA-01`–`03`).
- The traceability workbook's UC/BR/workflow mapping columns are empty; its summary
  reports 0 fully covered and 66 partially/missing AFR mappings. This blueprint derives
  the initial placements below from the specifications, not those empty mappings.
- The synchronized problem statement explicitly excludes historical `FR-BA-044` and
  `FR-BA-050` from this version. They have no live AFR replacements and must not be
  cited as live requirements.
- The synchronized problem statement resolves the original global-policy role conflict:
  IT Security owns encryption/RBAC/security policy; Super Admin owns institution-wide
  backup schedules and defaults. It also excludes Research Supervisor, the HoD restoration
  authorization path, post-approval storage provisioning, automated infrastructure
  shortfall remediation, extra archival eligibility rules, and classification-specific
  retention durations.
- Actors include SysAdmin, student/faculty/staff users, departmental HoDs, IT Security
  Team, and Super Admin. Director of IT is a failure-escalation recipient, not a regular
  use-case actor. The originator of a special-archival request is offline and is not a
  BADMS actor. Scheduled execution and audit recording are system-triggered, not human
  actors.

### Platform constraints that shape this design

- BADMS is a modular-monolith module; `domain/` is pure Python, selectors own reads and
  scoping, services own writes/transactions, and API views are transport-only.
- All person references are integer `user_id` values. User/department facts come through
  the directory/IAM contract, not direct ERP queries or cross-module foreign keys.
- Authorization is IAM-owned and fails closed. BADMS may publish its permission/module
  manifest; it must not create parallel role, permission, or user-role tables.
- Out-of-scope records are filtered in selectors and return 404. Departmental scope is
  not encoded as a separate permission.
- Contracts are read-only and plural by signature. Cross-module writes require an agreed
  event/contract, not direct model imports.
- The module-only environment is selected, but no `fusion-dev.dump` fixture was found
  locally. The IAM repository exists; its role catalogue does not establish BADMS's
  exact designation strings.

## Phase 1 — bounded-context questions

### Boundary and dependencies

BADMS is a coherent context for backup scheduling/execution records, archival requests
and artifacts, restoration requests, storage-extension decisions, and operational audit
records. It depends on directory/IAM for the authenticated principal, department scope,
and user display data. Notification delivery, backup/recovery storage, encryption/key
management, storage-capacity facts, and database snapshot execution have no verified
contract or adapter in the available environment; these remain dependencies, not assumed
implementations.

### Identity, roles, and scope

The selected test-role mapping is `SysAdmin` → `SysAdmin`, `Super Admin` → `Super Admin`,
and `IT Security Team` → `IT Security Team`, provisioned only in the synthetic IAM
environment. Map a HoD to the existing department-specific designation (`HOD (CSE)`,
`HOD (ECE)`, `HOD (ME)`, `HOD (Design)`, `HOD (NS)`, or `HOD (Liberal Arts)`) according to
the requester's department. Synthetic role provisioning was approved by the user; use
test-fixture accounts only, not real institutional accounts. The production mapping must
be verified by the institution before deployment. `Director of IT` remains a notification
recipient, not a BADMS authorization role.

The requester sees their own requests and permitted status/history. A HoD sees and decides
only requests whose requester belongs to the HoD's department. SysAdmin and IT Security
visibility is limited to their explicitly authorized operational/security responsibilities.
Super Admin has the global schedule and special-archival responsibilities specified.
Selectors must enforce every row boundary and return 404 for out-of-scope object ids.

### Time and policy

Scheduled backups use configured effective schedules. A failed-backup alert is due within
five minutes; three consecutive failures trigger escalation. Storage threshold monitoring
and classification-based retention are required, but their cadence and policy data are
not specified. No retention duration may be inferred; policy must be supplied before an
automated deletion/expiry action is designed.

## Phase 2 — proposed design

### 3.1 Traceability table

Each live specification id has its own row. The placement is a design proposal; unresolved
integrations and policies are identified in §3.8.

#### CFRs

| Id | Requirement | Layer / planned enforcement |
|---|---|---|
| CFR-BA-001 | Manual backup and outcome | service, backup adapter, audit |
| CFR-BA-002 | Scheduled backup, datasets, recovery storage, integrity | schedule task and service |
| CFR-BA-003 | Local schedule configuration and validation | domain policy, service, schedule API |
| CFR-BA-004 | Authorized backup status/history | scoped selector and API |
| CFR-BA-005 | Secure archival request intake | domain, upload validation, service |
| CFR-BA-006 | HoD decision and SysAdmin routing | transition table, scoped selector, service |
| CFR-BA-007 | Authoritative classification and security routing | domain, service |
| CFR-BA-008 | Sensitive archive AES-256 protection | encryption/storage adapter and service |
| CFR-BA-009 | Archival request tracking and notifications | selector, service/event dependency |
| CFR-BA-010 | Super Admin special archival | permission, service, audit |
| CFR-BA-011 | Restore request, approval, execution | transition table and restore adapter |
| CFR-BA-012 | Storage-extension request/decision | domain, scoped selector, service |
| CFR-BA-013 | Storage threshold monitoring | scheduled task and capacity contract |
| CFR-BA-014 | Global schedules/defaults and local precedence | schedule domain/service/task |
| CFR-BA-015 | Classification-based retention | policy and scheduled retention service |
| CFR-BA-016 | Five-minute failure alert and three-failure escalation | event/outbox task and notification dependency |
| CFR-BA-017 | Storage-extension notifications | service/event and notification dependency |
| CFR-BA-018 | Audit records and role-scoped operational reporting | audit service and scoped selectors |
| CFR-BA-019 | IAM/RBAC/security policy and role separation | IAM manifest boundary; conflict requires ruling |

#### AFRs

| Id | Requirement | Layer / planned enforcement |
|---|---|---|
| AFR-BA-001 | Only SysAdmin/Super Admin trigger manual backup | IAM permission + service |
| AFR-BA-002 | Capture timestamp and required artifacts | backup service |
| AFR-BA-003 | Save current-state database dump with timestamp | backup adapter |
| AFR-BA-004 | Record and communicate Success/Failure | service and notification dependency |
| AFR-BA-005 | Failed state and SysAdmin alert | service, outbox/task |
| AFR-BA-006 | Scheduled backups run without user action | schedule task |
| AFR-BA-007 | Select eligible datasets | schedule/domain policy |
| AFR-BA-008 | Transfer datasets to recovery storage | storage adapter |
| AFR-BA-009 | Verify integrity and consistency | backup adapter/service |
| AFR-BA-010 | Log verified run timestamp/status | service/model |
| AFR-BA-011 | Require configured, reachable repository | schedule task/adapter |
| AFR-BA-012 | SysAdmin views schedules | permission and selector |
| AFR-BA-013 | Configure frequency, time, classification filters | service/domain validation |
| AFR-BA-014 | Reject invalid/conflicting schedules without applying | domain/service |
| AFR-BA-015 | Apply valid schedule | service and scheduler |
| AFR-BA-016 | Audit schedule changes | audit service |
| AFR-BA-017 | Keep backup status/history | backup-run model/service |
| AFR-BA-018 | Show authorized backup history/status | scoped selector |
| AFR-BA-019 | Authenticated user initiates archival request | permission and service |
| AFR-BA-020 | Capture required metadata and attachment | serializer/domain/upload service |
| AFR-BA-021 | Validate request/quota; no state change on failure | domain/service transaction |
| AFR-BA-022 | New valid archival request is Submitted | state transition |
| AFR-BA-023 | Route to requester's HoD | directory contract and service |
| AFR-BA-024 | HoD reviews details, attachments, policy context | scoped selector/API |
| AFR-BA-025 | HoD records approve/reject decision | permission and transition service |
| AFR-BA-026 | Only requester's HoD decides | selector scope and service guard |
| AFR-BA-027 | Approved request routes to SysAdmin | transition service/event |
| AFR-BA-028 | SysAdmin assigns authoritative classification | permission/domain/service |
| AFR-BA-029 | Initial classification defaults to Routine | domain validation |
| AFR-BA-030 | Apply security/retention by authoritative classification | policy service |
| AFR-BA-031 | Sensitive request routes to IT Security | transition service |
| AFR-BA-032 | IT Security configures Sensitive encryption | permission and encryption dependency |
| AFR-BA-033 | Create encrypted archive and record outcome | storage/encryption adapter |
| AFR-BA-034 | AES-256 at rest and in transit | adapter configuration and security tests |
| AFR-BA-035 | Requester tracks archival status/history | scoped selector |
| AFR-BA-036 | Submission and decision notifications | notification dependency |
| AFR-BA-037 | Super Admin performs offline-origin special archival | permission/service |
| AFR-BA-038 | Only Super Admin performs special archival | IAM permission and service |
| AFR-BA-039 | Record special-operation outcome and audit event | service/audit |
| AFR-BA-040 | User requests restoration | permission and service |
| AFR-BA-041 | Sensitive restore requires SysAdmin approval | state transition/service |
| AFR-BA-042 | Non-Sensitive restore uses standard procedure | restore adapter/service |
| AFR-BA-043 | User tracks restoration status | scoped selector |
| AFR-BA-045 | User may request storage extension at full quota | permission/service |
| AFR-BA-046 | Validate against current user storage usage | capacity contract/service |
| AFR-BA-047 | Route valid extension request to user's HoD | directory contract/service |
| AFR-BA-048 | HoD reviews request, attachments, capacity, policy, justification | scoped selector/API |
| AFR-BA-049 | HoD records approve/reject decision | permission/transition service |
| AFR-BA-051 | Monitor storage thresholds | scheduled task/capacity contract |
| AFR-BA-052 | Validate requested capacity against available infrastructure | capacity contract/domain |
| AFR-BA-053 | Super Admin configures global schedules/defaults | permission/service |
| AFR-BA-054 | Use global schedule when no valid local override exists | schedule selector/task |
| AFR-BA-055 | Valid dataset-local schedule overrides global | domain policy/service |
| AFR-BA-056 | Enforce institute retention by classification | policy/service/task |
| AFR-BA-057 | Alert SysAdmin within five minutes of failure | event/outbox/task |
| AFR-BA-058 | Escalate after three consecutive failures | failure counter/task |
| AFR-BA-059 | Send backup creation/completion/failure status | notification dependency |
| AFR-BA-060 | Notify requester on extension submission/decision | notification dependency |
| AFR-BA-061 | Audit actions/events with timestamp, actor, action, outcome | append-only audit service |
| AFR-BA-062 | SysAdmin views audit/activity history | permission and selector |
| AFR-BA-063 | IT Security reviews unauthorized access/security reports | permission and selector |
| AFR-BA-064 | HoD views own-department reports | scoped selector |
| AFR-BA-065 | Provide operational backup visibility | scoped selectors/report API |
| AFR-BA-066 | IT Security manages permissions through RBAC | IAM boundary; conflict requires ruling |
| AFR-BA-067 | IT Security defines/enforces security policies | policy service; ownership ruling required |
| AFR-BA-068 | Enforce role separation and HoD department scope | IAM permission + selector/service |

#### Business rules

| Id | Rule | Layer / planned enforcement |
|---|---|---|
| BR-BA-001 | Manual backup trigger authorization | IAM permission/service |
| BR-BA-002 | Only requester's HoD decides archival | selector/service |
| BR-BA-003 | IT Security alone configures Sensitive encryption | IAM permission/service |
| BR-BA-004 | SysAdmin assigns authoritative classification after HoD approval | transition/service |
| BR-BA-005 | SysAdmin approval precedes Sensitive restoration | transition/service |
| BR-BA-006 | Initial classification defaults to Routine | domain |
| BR-BA-007 | Sensitive data uses AES-256 in transit and at rest | storage/encryption adapter |
| BR-BA-008 | Retention follows institute policy by classification | policy/task |
| BR-BA-009 | Storage extension requires HoD decision | transition/service |
| BR-BA-010 | HoD actions/reports are department-scoped | selector |
| BR-BA-011 | Dataset-local schedule overrides global | schedule domain |
| BR-BA-012 | Validate schedule before application | domain/service |
| BR-BA-013 | Scheduled backup requires reachable repository | task/adapter |
| BR-BA-014 | Failure alert within five minutes | task/outbox |
| BR-BA-015 | Escalate three consecutive failures to Director of IT | task/outbox |
| BR-BA-016 | Extension request checks current usage | capacity contract/domain |
| BR-BA-017 | HoD considers capacity, department policy, justification | review service/API |
| BR-BA-018 | Offline special archival is performed only by Super Admin | permission/service |
| BR-BA-019 | Super Admin owns institution-wide schedule authority | permission/service |
| BR-BA-020 | Protected records visible only within authorized scope | selectors |
| BR-BA-021 | IT Security owns specified security/RBAC administration | IAM boundary; conflict requires ruling |

#### Use cases

| Id | Use case | Layer / planned enforcement |
|---|---|---|
| BA-UC-001 | Trigger Manual Backup | API/service |
| BA-UC-002 | Submit Secure Archival Request | API/service |
| BA-UC-003 | Decide Secure Archival Request | API/service/selector |
| BA-UC-004 | Classify Secure Archival Data | API/service |
| BA-UC-005 | Configure Sensitive-Data Encryption | API/service/integration |
| BA-UC-006 | Execute Scheduled Automatic Backup | task/service |
| BA-UC-007 | Submit Storage-Extension Request | API/service |
| BA-UC-008 | Decide Storage-Extension Request | API/service/selector |
| BA-UC-009 | Configure Local Backup Schedule | API/service |
| BA-UC-010 | Perform Special Archival Operation | API/service |
| BA-UC-011 | Define Global Backup Schedules and Defaults | API/service |
| BA-UC-012 | View Audit Logs and Activity History | API/selector |
| BA-UC-013 | Audit Data Activity and Review Security Reports | API/selector |
| BA-UC-014 | View Backup History and Status | API/selector |
| BA-UC-015 | Track Request Status | API/selector |
| BA-UC-016 | Request Data Restoration | API/service |
| BA-UC-017 | Approve Sensitive Data Restoration | API/service |
| BA-UC-018 | Execute Data Restoration | service/task/adapter |
| BA-UC-019 | Manage RBAC Permissions | IAM boundary; conflict requires ruling |
| BA-UC-020 | Define and Enforce Security Policies | policy service; ownership ruling required |
| BA-UC-021 | View Department Data-Management Reports | API/selector |
| BA-UC-022 | Monitor Storage Thresholds | scheduled task |
| BA-UC-023 | Record Audit Event | audit service/event |

#### Workflows

| Id | Workflow | Layer / planned enforcement |
|---|---|---|
| BW-BA-01 | Secure Archival - HoD Rejection | archival state machine/service |
| BW-BA-02 | Secure Archival - Approved, Non-Sensitive Classification | archival state machine/service |
| BW-BA-03 | Secure Archival - Approved, Sensitive Encryption | archival state machine/integration |
| CW-BA-01 | Secure Archival Request Processing | composition of BW-BA-01/02/03 |
| BW-BA-04 | Storage Extension - Rejected | extension state machine/service |
| BW-BA-05 | Storage Extension - Approved | extension state machine/service |
| CW-BA-02 | Storage-Extension Request Processing | composition of BW-BA-04/05 |
| BW-BA-06 | Restoration - Non-Sensitive Standard Path | restoration state machine/adapter |
| BW-BA-07 | Restoration - Sensitive SysAdmin Approval | restoration state machine/adapter |
| CW-BA-03 | Data Restoration Processing | composition of BW-BA-06/07 |

### 3.2 Domain model

Proposed module-owned records, subject to §3.8:

- **BackupSchedule** — local or global scope, dataset selector, frequency/time, filters,
  enabled state, effective interval, and actor id. The database must enforce one effective
  schedule per dataset/scope and valid effective intervals; exact uniqueness depends on
  the approved dataset/repository identity.
- **BackupRun** — trigger type, schedule id where applicable, selected dataset identifiers,
  status, timestamps, artifact reference, size/checksum, and sanitized failure detail.
  Concurrent execution must be prevented by a named database constraint/lock strategy.
- **ArchivalRequest** — requester `user_id`, department identifier snapshot, required
  metadata, initial and authoritative classifications, status, decision actor ids/times,
  and artifact reference. Attachment bytes live in validated private storage, never a
  public path or model blob.
- **RestoreRequest** — requester `user_id`, archive identifier, reason, sensitivity,
  status, approval actor/time, and execution outcome.
- **StorageExtensionRequest** — requester `user_id`, department identifier snapshot,
  justification/attachment references, capacity requested, decision actor/time, and
  terminal decision. Capacity units and source are unresolved.
- **StorageObservation** — observed usage/capacity and observation time, only if a verified
  capacity source is selected.
- **SecurityPolicyVersion** — immutable/effective-dated policy reference only if BADMS
  owns policy configuration after the RBAC ownership conflict is resolved.
- **AuditRecord** — append-only event id, event time, actor `user_id` or system actor,
  action, target type/id, outcome, and non-sensitive context. Audit storage ownership and
  retention remain to be confirmed.

No auth/role tables, ERP shadow tables, cross-module foreign keys, or credentials are
introduced. Cross-module identities remain integer ids; department facts are resolved
through directory contracts.

### 3.3 State machines

Declarative transitions proposed; exact labels and failure/retry behavior must be confirmed
before implementation.

| Aggregate | From | Event / actor | To |
|---|---|---|---|
| BackupRun | queued | execute / system | running |
| BackupRun | running | verified / system | succeeded |
| BackupRun | running | execution_failed / system | failed |
| ArchivalRequest | draft | submit / requester | submitted |
| ArchivalRequest | submitted | reject / requester's HoD | rejected |
| ArchivalRequest | submitted | approve / requester's HoD | approved |
| ArchivalRequest | approved | classify_non_sensitive / SysAdmin | classified |
| ArchivalRequest | approved | classify_sensitive / SysAdmin | security_review |
| ArchivalRequest | security_review | encryption_configured / IT Security | ready_to_archive |
| ArchivalRequest | classified or ready_to_archive | archive_succeeded / system | archived |
| ArchivalRequest | classified or ready_to_archive | archive_failed / system | failed |
| RestoreRequest | submitted, non-sensitive | execute / SysAdmin | restoring |
| RestoreRequest | submitted, sensitive | approve / SysAdmin | approved |
| RestoreRequest | approved, sensitive | execute / SysAdmin | restoring |
| RestoreRequest | restoring | execution_succeeded / system | restored |
| RestoreRequest | restoring | execution_failed / system | failed |
| StorageExtensionRequest | submitted | approve / requester's HoD | approved |
| StorageExtensionRequest | submitted | reject / requester's HoD | rejected |

The special archival operation is an audited Super Admin operation originating from an
offline request; the approved record shape and whether it is an ArchivalRequest transition
or a separate operation record are unresolved.

### 3.4 Permissions

Permission codes must use `badms.<singular_resource>.<closed_verb>` and be enforced both
server-side and in server-driven navigation. Initial permission candidates:

- `badms.backup.view`, `badms.backup.create`, `badms.backup.restore`
- `badms.schedule.view`, `badms.schedule.create`, `badms.schedule.update`
- `badms.archive.view`, `badms.archive.create`, `badms.archive.review`,
  `badms.archive.approve`, `badms.archive.assign`
- `badms.encryption.manage`
- `badms.restore.view`, `badms.restore.create`, `badms.restore.approve`,
  `badms.restore.restore`
- `badms.storage_extension.view`, `badms.storage_extension.create`,
  `badms.storage_extension.review`, `badms.storage_extension.approve`
- `badms.audit_event.view`, `badms.report.view`, `badms.security_policy.manage`

Candidate system permissions for scheduled behavior are `badms.backup.create`,
`badms.audit_event.create`, and `badms.storage_observation.create`; confirm the permission
catalogue and actual task needs before publishing. Candidate scope permissions are the
request, report, and audit `view` permissions, narrowed by selectors to requester,
department, or explicitly authorized operational scope.

The implementation contains provisional `ROLE_GRANTS` for the selected test-role
strings above and department-specific HoD designations. These grants are assumptions
for this draft, not an approved production mapping; do not assign them to real accounts.

### 3.5 Endpoints and navigation

Proposed route families under `/api/v1/badms/`; exact response contracts and permissions
depend on §3.4 resolution:

| Method / path | Purpose |
|---|---|
| `GET/POST /backups/` | List scoped runs / request manual backup |
| `GET /backups/{id}/` | Read a scoped run |
| `GET/POST /schedules/` | List/configure local schedules |
| `GET/POST /global-schedules/` | Read/configure global schedules |
| `GET/POST /archives/` | List/create archival requests |
| `GET /archives/{id}/` | Read scoped request details |
| `POST /archives/{id}/decision/` | HoD decision |
| `POST /archives/{id}/classification/` | SysAdmin authoritative classification |
| `POST /archives/{id}/encryption/` | IT Security configuration outcome |
| `POST /archives/{id}/special-operation/` | Super Admin special archival operation |
| `GET/POST /restores/` | List/create restoration requests |
| `POST /restores/{id}/approval/` | SysAdmin Sensitive restoration approval |
| `POST /restores/{id}/execute/` | Execute approved/non-sensitive restore |
| `GET/POST /storage-extensions/` | List/create storage-extension requests |
| `POST /storage-extensions/{id}/decision/` | HoD decision |
| `GET /audit/` | Role-scoped audit/activity records |
| `GET /reports/` | Authorized operational reports |
| `GET /security-policies/` | Read permitted policy state |
| `POST /security-policies/` | Configure policy only if BADMS ownership is approved |

Detail views should use drawers/modals from the list route rather than standalone routes
unless the navigation parity check allows otherwise. Every client route must match one
server-filtered nav item and have a `RequirePermission` guard. The module-only sidebar
handoff entry is: `id=badms`, `label=Backup and Data Management`, icon to be selected from
the existing icon catalogue, `to=/badms`, `section=Operations`. Final label/icon/route
must be approved before handoff.

### 3.6 Contracts

Required read-only dependency proposals:

- Directory: batched `get_users(user_ids)` and a supported department/HoD lookup for
  requester department membership and scope.
- IAM: authenticated principal and effective permission checks only; BADMS does not read
  IAM tables or manage user-role assignments directly.
- Capacity/repository facts: no existing contract was verified. Add or identify an owned
  provider before implementing quota, reachability, and infrastructure checks.
- Notification delivery and audit persistence: identify existing event/contract owners;
  do not call another module's models or invent an endpoint.

No BADMS public contract is currently justified by the spec; add one only when a consumer
and plural read signature are identified.

### 3.7 Scheduled work

| Work | Cadence/trigger | Consequence if absent |
|---|---|---|
| Execute due automatic backups | Effective schedule | Missing backup snapshots |
| Retry/record failed delivery and notify SysAdmin | Alert deadline ≤5 minutes | Failure remains unnoticed |
| Escalate consecutive failures | On third consecutive failure | Director of IT is not notified |
| Monitor storage thresholds | Unspecified; needs approval | Quota/full-threshold changes are missed |
| Apply retention by classification | Unspecified; requires effective policy | Data is retained/deleted incorrectly |

Celery beat/worker availability, idempotency, locking, outbox delivery, and operational
alerts are deployment prerequisites once cadence and integrations are approved.

### 3.8 Open questions and blockers

1. **RBAC ownership conflict — proposed resolution:** `AFR-BA-066`, `AFR-BA-067`,
   `BR-BA-021`,
   `BA-UC-019`, and `BA-UC-020` assign permission/security-policy administration to IT
   Security. Platform architecture says IAM owns roles, permissions, grants, and module
   navigation; a module may only publish its permission manifest. The user answered
   "yes" to the IAM-owned interpretation: IAM remains the role, permission, and grant
   system of record; IT Security administers through IAM's approved administration path;
   BADMS publishes and consumes its manifest. BADMS may own effective-dated module
   data-protection policy, but not a parallel RBAC system. Record the approver's dated
   ruling and obtain Student 2 approval of this interpretation before implementing.
2. **Designation mapping — proposed for synthetic tests:** use the exact test strings
   `SysAdmin`, `Super Admin`, and `IT Security Team`; map HoDs by department to the
   existing `HOD (...)` designations listed in Phase 1. The user approved synthetic test
   role provisioning. The fixture file was not found, so test accounts must be created by
   the test setup; do not modify persistent ERP roles until the fixture/account workflow
   is available. Production role mappings still require institutional verification.
3. **Storage and encryption — selected proposal:** PostgreSQL `pg_dump`/`pg_restore` for
   database snapshots/restores; a private Amazon S3 bucket for backup/archive artifacts and
   attachments; AES-256-GCM envelope encryption for Sensitive payloads, with AWS KMS
   managing data keys; TLS 1.3 with an AES-256-GCM cipher suite for network transfers.
   Platform Operations owns the bucket, KMS key, and lifecycle configuration; BADMS owns
   internal `SnapshotProvider` and `ArchiveStorage` adapters using the S3 API and KMS
   `GenerateDataKey`/decrypt contract. Require private bucket policy, blocked public
   access, workload identity rather than static credentials, key-version metadata per
   artifact, and a tested recovery procedure. KMS key rotation and retained-key access
   must be verified with Operations before deployment. This is a proposed stack selected
   under the user's direction, not evidence that the services already exist.
   Do not reuse the IAM optional Fernet/AES-128 behavior as AES-256 evidence. Approve any
   new SDK/crypto dependencies through the assignment's dependency gate.
4. **Dataset/repository scope:** identify databases/datasets in scope, repository identity,
   reachability checks, local/global schedule granularity, timezone, supported frequencies,
   conflict semantics, and retry/locking behavior.
5. **Capacity source:** identify quota owner, measurement units, threshold definition,
   requested extension amount, infrastructure capacity source, refresh cadence, and what
   the system does when capacity is insufficient. The spec excludes automated remediation
   but requires detection and decision context.
6. **Retention:** provide the institute-approved effective-dated classification policy,
   retention durations, archive/delete behavior, legal hold behavior, and whether policy
   changes apply retroactively. No automated purge can be designed from the current spec.
7. **Notifications/audit:** identify notification channels, recipients and retry policy;
   confirm audit storage owner, immutable-write mechanism, event fields, visibility, and
   retention. Director of IT escalation requires a resolvable recipient.
8. **Operational semantics:** confirm archive/restore allowed file types and limits,
   Sensitive-restore execution authority, failure/retry transitions, and how an offline
   special-archival request is recorded and verified.
9. **Reporting scope:** define which operational reports are required and which roles may
   see institution-wide versus department/requester-scoped aggregates.
10. **Disposition of open items:** resolve each item above or record the approver's
    explicit acceptance as an implementation exception. Do not silently defer a question
    that implementation depends on.
11. **Approval record:** after the rulings and dispositions above, obtain written
    instructor/platform-owner decisions where required and written Student 2 approval of
    the updated blueprint. The user reported the IAM interpretation and approved
    synthetic test-role provisioning, and delegated the infrastructure proposal to
    Student 1; these reports do not replace Student 2's review or the remaining
    implementation-dependent dispositions.

**Gate:** The user's later implementation request permits draft code work, but does not
clear this assignment gate. Do not mark the blueprint approved, deploy the module, or
claim requirement completion until the RBAC/architecture ruling, role mappings, required
integrations, remaining-item dispositions, and written review approvals are recorded.

### Review record

- **2026-11-22, 22:38 IST — Student 2 decision relayed by the user:** "Decision: Do not
  approve." Student 2 found the blueprint well-structured but blocked on the rulings and
  integrations in §3.8, requested those and all implementation-dependent open items be
  resolved or explicitly accepted, and confirmed no implementation/testing was performed.
  This is a rejection, not an approval record.
- **2026-11-22, 22:42 IST — user-reported follow-up:** the user answered "yes" to IAM
  remaining the RBAC owner, approved synthetic role provisioning, requested that Student 1
  choose designation labels and the storage stack, and reported that dispositions for the
  other open items have not been received. The proposals in §3.8 record that direction;
  Student 2 approval and remaining dispositions are still outstanding.
- **Date not independently recorded — user implementation direction:** proceed with
  application-code work using explicit best-effort assumptions because time is limited.
  This direction does not reverse Student 2's rejection or constitute instructor,
  platform-owner, or Student 2 approval.
- **Implementation progress:** draft BADMS models, APIs, UI, IAM permission manifest,
  PostgreSQL snapshot runner, S3/KMS encrypted storage, workflow tasks, notifications,
  and capacity monitoring are present in the repository. Local checks cover Django
  system checks, BADMS pytest cases, SQLite migration application, migration drift,
  permission-manifest consistency, Python lint/import boundaries, and client typecheck,
  tests, and production build. Live PostgreSQL, AWS S3/KMS, email delivery, and Celery
  infrastructure are not configured here, so their runtime integrations remain
  unverified. These checks do not clear any outstanding approval or deployment gate.
- **2026-11-22, 23:50 IST — user-reported Student 2 acceptance:** the user reports that
  Student 2 accepted the changes. No written review artifact or instructor/platform-owner
  ruling was added to the repository in this session.
