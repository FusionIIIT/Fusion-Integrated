# BADMS Blueprint

**Module:** Backup and Database Archive Management System (BADMS)
**Module code:** `badms`
**Branch:** `module/badms`
**Spec set:** `/home/sasank1236/Documents/Fusion/Assignment9_Specs_BADMS/24-BADMS`
**Spec versions:** Problem Statement v1.2 synchronized draft; Requirement Registry v1.1 final; Use Cases v1.2 final; Business Rules v1.1 final; Workflows v1.1 final; Traceability Matrix v1.1 final.
**Environment:** module-only.
**Approval status:** Student 2 approved on 2026-11-22. Exact record: “Yes i approve 22-11-2026 student - 2” (this Codex conversation). Approval covers this blueprint, the known E2E gap, adding `@playwright/test`, and the shared-file scope listed below.

## 1. Reading and scope decisions

The synchronized Problem Statement is the semantic baseline. Its resolved role boundaries govern where earlier source text overlapped: Super Admin owns institution-wide backup schedules and default backup policy; IT Security owns encryption, RBAC, and security policy. Special archival is an offline-triggered operation performed only by Super Admin within BADMS. Sensitive restoration requires SysAdmin approval; no HoD restoration-authorization path is included. Storage-extension handling ends at the recorded HoD decision and requester notification. Classification-specific retention durations, post-approval storage provisioning, infrastructure-shortfall remediation, and a Research Supervisor actor are out of scope.

The assigned work is a new domain module on `upstream/main`, not a continuation or copy of Assignment 8/6A implementation. The Assignment 8 test work is historical context only; it does not constitute Assignment 9 code, a Student 2 review, or a Student 2 test suite.

## 2. Architecture and integration shape

Follow `modules/placement` and the platform structure: Django models for persistence, pure Python domain rules/state transitions, selectors for reads, services for writes and transaction boundaries, thin DRF API adapters, Celery tasks for scheduled/long-running work, and explicit module contracts for any inter-module events. No cross-module foreign keys. BADMS rows use opaque local IDs and IAM principal/department identifiers as values. Authorization is server-side, fail-closed, and checks both role permission and owner/department scope. List endpoints use the platform cursor pagination and standard API error envelope.

Proposed module files: `modules/badms/{apps.py,contracts.py,events.py,models.py,permissions.py,registry.py,tasks.py}`, `domain/` (classification rules and transition tables), `selectors/`, `services/`, `api/` (serializers, views, permissions, urls), migrations, and unit/service/API tests. Client pages are a statically registered module under `client/src/modules/badms/` with route and navigation metadata matching server permissions. The module does not import another domain module's internals.

Cross-cutting implementation: existing platform IAM/RBAC and audit/outbox facilities are reused where they satisfy the contract. Database dumps and archive blobs use the BADMS-only Django `STORAGES["badms"]` alias so production S3 settings cannot redirect other modules' files. Production uses a durable private recovery object store with AES-256 server-side encryption and TLS restricted to AES-256-GCM, plus integrity checks and lifecycle controls. The storage provider's KMS owns key generation, storage, and rotation under IT Security policy; BADMS never handles raw key material. Local filesystem storage is development-only and must live outside the web root; Sensitive archive operations are disabled unless deployment settings attest that storage encryption and TLS are enabled. Retention duration comes from institute policy configuration; no duration is invented, and if policy is absent the retention operation fails closed.

## 3.1 Traceability and scope coverage

### Live CFRs and AFRs

All live consolidated requirements are in scope. The atomic registry has 66 live AFRs; historical `FR-BA-044` and `FR-BA-050` are excluded from this version and remain historical crosswalk entries only.

| CFR | Name | Live AFRs | Planned capability |
|---|---|---|---|
| CFR-BA-001 | Manual Backup Management | AFR-BA-001–005 | Authorized manual trigger, timestamp/artifacts, database-state dump, outcome and failure alert |
| CFR-BA-002 | Scheduled Automatic Backup Execution | AFR-BA-006–011 | Effective schedule, eligible datasets, reachable repository, transfer, integrity verification, timestamp/status |
| CFR-BA-003 | Local Backup Schedule Management | AFR-BA-012–016 | SysAdmin schedule view/create/update, validation, conflict handling, audit |
| CFR-BA-004 | Backup Status and History Visibility | AFR-BA-017–018 | Scope-authorized status/history views |
| CFR-BA-005 | Secure Archival Submission and Intake | AFR-BA-019–023, AFR-BA-029 | Metadata/file intake, Routine default, validation/quota, Submitted state, HoD routing |
| CFR-BA-006 | Secure Archival HoD Review and Routing | AFR-BA-024–027 | Department HoD decision, recorded outcome, approved request to SysAdmin |
| CFR-BA-007 | Authoritative Archival Classification and Policy Routing | AFR-BA-028, AFR-BA-030–031 | SysAdmin classification; Sensitive route to IT Security |
| CFR-BA-008 | Sensitive Data Encryption and Archive Creation | AFR-BA-032–034 | IT Security configuration; AES-256 at rest/in transit; recorded outcome |
| CFR-BA-009 | Secure Archival Tracking and Notifications | AFR-BA-035–036 | Requester status/history and submission/decision notices |
| CFR-BA-010 | Special Archival Operation | AFR-BA-037–039 | Super Admin-only offline-origin operation for Sensitive research data; outcome/audit |
| CFR-BA-011 | Data Restoration Management | AFR-BA-040–043 | User request/tracking; SysAdmin approval for Sensitive; standard and approved technical paths |
| CFR-BA-012 | Storage Extension Request and Decision | AFR-BA-045–049, AFR-BA-052 | Quota-full request, current usage/infrastructure validation, HoD decision and criteria |
| CFR-BA-013 | Storage Threshold Monitoring | AFR-BA-051 | Monitor and persist threshold/full-quota condition |
| CFR-BA-014 | Global Backup Schedules and Defaults | AFR-BA-053–055 | Super Admin global defaults; local schedule precedence |
| CFR-BA-015 | Retention by Data Classification | AFR-BA-056 | Enforce institute-defined classification policy without invented duration values |
| CFR-BA-016 | Backup Failure Notification and Escalation | AFR-BA-057–059 | SysAdmin failure alert within five minutes, third-consecutive escalation, status/completion notice |
| CFR-BA-017 | Storage-Extension Notifications | AFR-BA-060 | Requester submission and decision notices |
| CFR-BA-018 | Audit Logging and Operational Reporting | AFR-BA-061–065 | Audit identity/action/outcome/time; role-scoped audit, security, backup and departmental reports |
| CFR-BA-019 | RBAC, Security Policy, and Role Separation | AFR-BA-066–068 | IT Security RBAC/security policy authority and separation/department boundaries |

The source workbook's UC/BR/WF mapping columns are blank. The mapping below is therefore a proposed trace index from the synchronized requirements and use-case/workflow documents; Student 2 approved this interpretation on 2026-11-22. It does not change the source IDs or acceptance rules.

### Live use cases (all 23)

| Use case | Planned flow / component |
|---|---|
| BA-UC-001 Trigger Manual Backup | SysAdmin or Super Admin starts a run; outcome and timestamp recorded |
| BA-UC-002 Submit Secure Archival Request | User submits metadata/file; validate; default Routine; route to own HoD |
| BA-UC-003 Decide Secure Archival Request | Only own-department HoD approves/rejects |
| BA-UC-004 Classify Secure Archival Data | SysAdmin sets authoritative classification and routes by policy |
| BA-UC-005 Configure Sensitive-Data Encryption | IT Security configures encryption; encrypted archive is created |
| BA-UC-006 Execute Scheduled Automatic Backup | Scheduled service selects eligible data, backs up and verifies |
| BA-UC-007 Submit Storage-Extension Request | User submits when quota is full; validate usage/infrastructure; route HoD |
| BA-UC-008 Decide Storage-Extension Request | Own-department HoD records approve/reject using stated criteria |
| BA-UC-009 Configure Local Backup Schedule | SysAdmin manages valid local/dataset schedule |
| BA-UC-010 Perform Special Archival Operation | Super Admin performs the BADMS action for an offline request |
| BA-UC-011 Define Global Backup Schedules and Defaults | Super Admin manages global schedule/default policy |
| BA-UC-012 View Audit Logs and Activity History | SysAdmin views authorized history |
| BA-UC-013 Audit Data Activity and Review Security Reports | IT Security audits activity and sees security report data |
| BA-UC-014 View Backup History and Status | User/authorized administrator sees only permitted scope |
| BA-UC-015 Track Request Status | Request owner follows archival/storage/restoration request history |
| BA-UC-016 Request Data Restoration | User requests restore; Sensitive request enters approval path |
| BA-UC-017 Approve Sensitive Data Restoration | SysAdmin approves/rejects Sensitive restore before execution |
| BA-UC-018 Execute Data Restoration | SysAdmin performs standard non-Sensitive or approved Sensitive restore |
| BA-UC-019 Manage RBAC Permissions | Authorized IT Security member manages BADMS permissions |
| BA-UC-020 Define and Enforce Security Policies | IT Security defines/enforces security policies |
| BA-UC-021 View Department Data-Management Reports | HoD views only their department's operational reports |
| BA-UC-022 Monitor Storage Thresholds | System service monitors threshold/full quota |
| BA-UC-023 Record Audit Event | System/service records timestamp, actor, action and outcome |

### Business rules and workflow paths

Implement and test every live rule `BR-BA-001` through `BR-BA-021` as stated in the final BR document. Key constraints include manual backup role restriction; Routine default; own-department HoD review; authoritative classification; Sensitive-only encryption handling and Sensitive restore approval; local-over-global schedule precedence; valid repository reachability for scheduled runs; threshold/full-quota validation; no invented extension remediation; special archival Super Admin-only authority; only Super Admin global schedule authority; protected information scope; and IT Security-only RBAC/security-policy authority.

The state transition table in the workflow specification is authoritative. Implement these paths without adding implied states or steps:

- `BW-BA-01`: archival submission → HoD rejection.
- `BW-BA-02`: archival submission → HoD approval → SysAdmin non-Sensitive classification/policy applied.
- `BW-BA-03`: archival submission → HoD approval → SysAdmin Sensitive classification → IT Security encryption/archive.
- `BW-BA-04`: storage extension submission → HoD rejection.
- `BW-BA-05`: storage extension submission → HoD approval (terminal state for this version).
- `BW-BA-06`: non-Sensitive restoration request → standard technical restore path.
- `BW-BA-07`: Sensitive restoration request → SysAdmin rejection, or approval → technical restore.
- `CW-BA-01`, `CW-BA-02`, `CW-BA-03`: composite paths exactly as listed in their authoritative transition tables. Special archival, scheduled events, threshold monitoring and audit recording are not fabricated as multi-stage workflows.

### Exclusions and historical identifiers

Do not implement historical `FR-BA-044` or `FR-BA-050`; retain them only in the source crosswalk/history. Do not add Research Supervisor, a separate HoD restore approval, automatic infrastructure shortfall remediation, post-approval storage allocation, undefined secure-archival eligibility rules, or classification-specific retention periods.

## 3.2 Data model and invariants

Proposed aggregate records (exact field types and indexes to be set during implementation after inspecting the platform patterns):

- **BackupRun:** trigger kind (manual/scheduled), status, started/completed timestamps, initiating principal or system actor, dataset/repository references, outcome detail, integrity result, artifact locator/checksum metadata, and consecutive-failure sequence context. Artifacts remain in configured recovery storage; the DB stores metadata, not dumps.
- **BackupSchedule:** local/global scope, owner scope/dataset, cadence, time/time zone, classification filters, enabled state, validation status and audit timestamps. One effective schedule per dataset/time policy; valid local schedule wins over global, otherwise global applies.
- **ArchiveRequest:** requester principal and department snapshot, required file metadata, attachment/object reference, initial and authoritative classification separately, state, HoD/SysAdmin/IT Security decision actors/timestamps, and notification/audit references. Missing initial classification becomes Routine. State transitions are service-controlled and idempotency guarded.
- **StorageExtensionRequest:** requester/department, requested amount, justification, attachment, validated usage/infrastructure snapshot, HoD decision/outcome and timestamps; no allocation side effect after approval.
- **RestorationRequest:** requester, archive reference, classification, state, Sensitive approval actor/outcome, technical execution outcome and timestamps.
- **AuditEvent / NotificationOutbox:** use existing platform facilities where possible; otherwise module-local records conform to required fields and use transactional outbox delivery. Avoid duplicate incompatible platform abstractions.
- **Policy configuration:** classification treatment references existing approved institute policy/config; do not hard-code unknown retention durations or invent policy values.

Invariants: every record has an accountable actor/system event and timestamps; tenant/department ownership is immutable for authorization; users see only their allowed rows; HoD queries are constrained to the HoD's department in the database selector; users cannot self-approve; every transition checks current state and permission within the write transaction; retries cannot duplicate backup/notification effects; secrets and raw database dumps are never persisted in application tables/logs.

## 3.3 State transitions

States are limited to those named by the authoritative source transition tables. Initial submission state `Not Submitted` is a conceptual pre-record state. Archival transitions: `Submitted` → `Rejected` or `HoD Approved` → `Classified Non-Sensitive / Policy Applied` or `Classified Sensitive / Routed to IT Security` → `Sensitive Archive Encrypted`. Storage extension: `Submitted` → `Rejected` or `Approved`. Restore: `Restoration Requested / Standard Path` → `Restored`, or `Sensitive Restoration Pending Approval` → `Rejected` or `Approved for Restoration` → `Restored`. Backup runs record `Success`/`Failure` (scheduled verification is part of execution). No other states are inferred; validation errors leave request state unchanged.

Transitions are implemented as explicit domain functions with actor/guard inputs and exercised in domain and service tests. Side effects (notification, event, audit) are emitted only after a valid transition and committed through the platform outbox pattern.

## 3.4 Permissions and roles

The live permission codes and grants are defined by `modules/badms/registry.py` and generated into `registry/permissions.json`. Human capabilities include manual backup and status view, local/global schedule management, archive submission/review/classification/encryption/special archive, restoration request/approval/execution, storage-extension request/review, audit/security audit, department reports, and security-policy management. Scheduled backup, notification delivery, storage monitoring, and retention enforcement are system-only grants.

| Role | Assigned scope |
|---|---|
| Student/Faculty/Staff | Own archive, restore, and storage-extension requests; permitted backup status view |
| HoD | Own-department archive/storage decisions and department reports |
| SysAdmin | Manual backup, local schedules, authoritative classification, restore approval/execution, audit history |
| Super Admin | Manual backup, global schedules, special archival |
| IT Security Team | Sensitive encryption, security audit, BADMS security policy; IAM permission API administration |
| Director of IT | Receives escalation after three consecutive backup failures |
| System/service actors | Scheduled backup, threshold monitoring, retention enforcement, and notification delivery |

These are separate capabilities: no blanket administrator bypass, no cross-role escalation, no HoD cross-department query, and no permission for IT Security to alter global backup policy. The exact codes and grant matrix are visible in the generated manifest; they do not imply role assignment.

## 3.5 API surface and contracts

Proposed base path: `/app/api/platform/v1/badms`. Use snake_case JSON, plural collections, no trailing slashes, opaque IDs, cursor pagination, standard error envelopes, and explicit POST subresources for state-changing actions. All paths require the corresponding permission plus owner/department scope check.

| Resource/action | Method and path | Contract intent |
|---|---|---|
| Backup runs | `GET /backup_runs`; `GET /backup_runs/{id}` | Scoped status/history |
| Manual run | `POST /backup_runs` | SysAdmin/Super Admin trigger; returns run receipt |
| Schedules | `GET/POST /schedules`; `GET/PATCH /schedules/{id}` | Authorized local schedule management; validate before apply |
| Global policy | `GET/PUT /global_backup_policy` | Super Admin global defaults/schedule; local override precedence |
| Archive requests | `GET/POST /archive_requests`; `GET /archive_requests/{id}` | Create and track, with visibility scope |
| Archive decision | `POST /archive_requests/{id}/decision` | HoD approve/reject; only own department |
| Classification | `POST /archive_requests/{id}/classification` | SysAdmin authoritative classification |
| Sensitive encryption | `POST /archive_requests/{id}/encryption` | IT Security configuration and archive outcome |
| Special archive | `POST /special_archives` | Super Admin records offline-origin operation |
| Restoration | `GET/POST /restoration_requests`; `GET /restoration_requests/{id}` | Request and track |
| Sensitive restore decision | `POST /restoration_requests/{id}/decision` | SysAdmin approval/rejection |
| Restore execution | `POST /restoration_requests/{id}/execution` | SysAdmin technical execution under correct path |
| Storage extension | `GET/POST /storage_extension_requests`; `GET /storage_extension_requests/{id}` | User request and own status |
| Storage decision | `POST /storage_extension_requests/{id}/decision` | HoD decision with recorded criteria inputs |
| Reports/audit | `GET /audit_events`, `/reports/department`, `/reports/security` | Filtered, role-scoped visibility only |
| Security policy | `GET/PUT /security_policies` | BADMS stores institute-supplied retention days for every classification; encryption requirements are fixed at AES-256 at rest and in transit and cannot be weakened through this API |
| Permission administration | IAM `GET/PATCH /api/iam/v1/security/permissions`; audit `GET /api/iam/v1/security/audit` | IAM updates the existing designation-to-permission mapping after checking active role `IT Security Team` and its `badms.security.audit` permission. Changes are append-audited. The IAM manifest catalogue is authoritative; runtime overrides survive reseeding. |

Request/response fields will use source-defined data only. Validation error responses leave persisted request state unchanged. Refusal status follows `docs/01-architecture/api-conventions.md`. Binary file uploads use the established platform upload/storage boundary; no base64 blobs in JSON. OpenAPI must be regenerated with the repository's `make schema` gate.

## 3.6 Events and integration

Use existing transactional outbox/Celery conventions. Proposed versioned events: `badms.backup.completed`, `badms.backup.failed`, `badms.archive.submitted`, `badms.archive.decided`, `badms.archive.classified`, `badms.archive.encrypted`, `badms.restore.requested`, `badms.restore.decided`, `badms.restore.completed`, `badms.storage_extension.submitted`, `badms.storage_extension.decided`, and `badms.audit.recorded`. Payloads carry identifiers and minimum required metadata, never file contents, database dumps, credentials, or encryption keys. Events are emitted only after transaction commit, are idempotent, and consumers do not import BADMS internals. If the platform already supplies equivalent notification/audit contracts, reuse them rather than introduce duplicate topics. No cross-module FK or direct dependency on IAM private tables.

## 3.7 Frontend and navigation

A shell-compatible BADMS route set is registered statically and mirrored by server registry/nav entries. The current client provides overview, archive-request, and operations pages. Navigation is server-filtered by each capability. The security-policy API is implemented, but its UI and an IAM permission-management UI/proxy are deferred by the user; administrators use the IAM API directly. Every implemented page handles loading, empty, error, unauthorized, and success states. Do not expose another user's request via route IDs or UI filtering alone. Standalone module UI works in the integrated client; no legacy portal dependence.

## 3.8 Operations, quality and delivery

Scheduled backups and threshold checks are Celery tasks with bounded retries, idempotency keys, structured logs, request/correlation IDs, and audit/outbox writes. The five-minute failure alert target and third-consecutive escalation are explicit acceptance criteria. Health/readiness must not reveal credentials or storage internals. Retention follows institute policy configuration; retention schedules must not guess undefined durations. File/dump storage access uses least-privilege service identities and private buckets/volumes. Migrations are forward-only, tested against the isolated project database, with no production dump data in fixtures.

Required gates before review: `make check`, `make check-client`, `make e2e`, OpenAPI/permission generation and consistency checks. Add domain, service, API authorization/scope, transition, task/idempotency, client component/route tests, and end-to-end browser tests. The quality report records actual commands/results after the latest code change and each review round, without naming tools.

### E2E gap and approved implementation scope

Repository inspection found no `make e2e` target, no `client/e2e` tree, and no Playwright dependency in the current upstream baseline. Student 2 approved adding pinned `@playwright/test`, a root `make e2e` target, Playwright configuration/scripts, and `client/e2e/badms/` specs on 2026-11-22. The E2E target should use an isolated backend and Vite frontend, wait for readiness, run Playwright in headless Chromium, and tear down only its own processes. It should cover route/nav permission behavior, user-owned requests, same-department decisions and cross-department denial, administrator actions, and sensitive restoration approval/encryption. It must refuse to run if conflicting development servers are active. Exact fixtures/auth seeding and role UI flows must be verified against the existing platform before implementation.

| Required Student 2 approval | Scope | Status |
|---|---|---|
| Blueprint and reading of spec | This document, including source-to-feature trace and exclusions | Approved 2026-11-22 |
| Known baseline E2E gap | Missing `make e2e`, E2E folder and browser test runner on current main | Approved 2026-11-22 |
| New dependency | `@playwright/test` and its lockfile changes | Approved 2026-11-22 |
| Out-of-module/shared changes | Root `Makefile`, `client/package.json`/lockfile, Playwright config/scripts, shared E2E harness if needed; module-specific tests under `client/e2e/badms/` | Approved 2026-11-22 |

Student 2's dated written approval is recorded in §6 and `badms-quality-report.md`. Any shared-file change beyond the listed scope requires separate approval before editing.

## 4. Test and acceptance plan

1. Domain tests cover every transition, permission guard, classification routing rule, local/global schedule precedence, failure count/time conditions, and validation no-state-change behavior.
2. Service/API tests cover each UC success flow and explicit alternative/exception, role and department isolation, persistence/audit/outbox atomicity, duplicate/retry behavior, and refusal response conventions.
3. Task tests cover scheduled execution eligibility/reachability, integrity result, alert timing behavior, three consecutive failure escalation, storage threshold monitoring and actor-less system execution.
4. Client tests cover route registration, server-filtered navigation, role pages, form validation, request status rendering, and error/empty states.
5. Playwright E2E coverage follows the approved scope above; no E2E framework or test case is added until approval.
6. Run all repository gates and actual browser role walkthroughs; save output and record exact commit in the quality report.
7. Student 1 review rounds use fresh reviewer sessions and clean clones. Fix every finding and reach 10/10 in all nine dimensions before handing the commit to Student 2. Student 2 then independently creates spec-only FR/UC/BR/WF designs, freezes and commits them before seeing code, runs and triages tests, and performs the separate-provider review.

## 5. Open questions / approval blockers

1. Student 2 approved the blueprint, the known E2E gap, `@playwright/test`, and the listed shared/root/client E2E scope on 2026-11-22.
2. Chosen implementation: production storage is a private Amazon S3 bucket using SSE-KMS with an institute-owned customer-managed AWS KMS key. The BADMS S3 client requires HTTPS and TLS 1.2 AES-256-GCM; the workload role supplies credentials without static application keys. Enable S3 versioning and institute-defined lifecycle rules. IT Security owns KMS key lifecycle and access review; BADMS never handles key material. Local storage is development-only. AWS documents SSE-KMS and TLS requirements for KMS-protected S3 objects [here](https://docs.aws.amazon.com/AmazonS3/latest/userguide/specifying-kms-encryption.html). These are explicit deployment requirements, not claims that infrastructure is already provisioned.
3. IAM had no active-role update endpoint, returned permissions for the union of all held roles, and had no ERP-user permission-administration API. The approved IAM integration now persists the selected role, scopes the `/me` permission and module payload to that role, and administers the existing permission-mapping model from its manifest catalogue. Permission changes are written to IAM security audit records. The BADMS role-management UI is deferred; administrators use the IAM API directly.
4. To respect the user's instruction not to change the shared access-control module, IAM permission administration is restricted to the exact `IT Security Team` active designation and requires its existing `badms.security.audit` grant. No new shared permission-manifest checker behavior was added. The IAM session cache can delay propagation of a change by up to the configured `IAM_SESSION_CACHE_SECONDS` (60 seconds by default).
5. Security-policy fields are derived from explicit requirements only: fixed AES-256 at-rest/in-transit requirements and positive retention-day values for each classification. The API does not permit changing encryption algorithms. Institute administrators must supply actual retention durations; none are selected by this implementation. Missing retention policy still blocks classification.
6. During implementation, verify notification and audit/outbox contracts. If a required interface is missing or conflicts with the spec, stop and report rather than inventing a shared platform contract.

## 6. Approval record

| Approver | Date/time | Exact approval or decision | Where recorded |
|---|---|---|---|
| Student 2 | 2026-11-22 | “Yes i approve 22-11-2026 student - 2” — approval of blueprint, E2E gap, Playwright dependency, and shared-file scope | This Codex conversation |
