# BADMS Quality Report

**Module:** Backup and Database Archive Management System (BADMS)
**Module code:** `badms`
**Branch:** `module/badms`
**Report status:** BADMS backend, client workflows, IAM integration, security-policy API, storage isolation, AES-256 TLS restrictions, policy tests, clean-install activation, generated teaching reference, and browser E2E are implemented. Final BADMS backend, client, and browser gates passed. The IAM migration drift check and all 162 IAM tests passed. Independent review/test phases and production cloud provisioning remain outstanding.
**Baseline:** `upstream/main` at `02b01fe` (clean Student 1 worktree before this report/blueprint).

## Approval record

| Item | Approver | Status | Evidence |
|---|---|---|---|
| BADMS blueprint and specification interpretation | Student 2 | Approved 2026-11-22 | “Yes i approve 22-11-2026 student - 2” — this Codex conversation |
| E2E gap, new Playwright dependency and shared/root/client changes | Student 2 | Approved 2026-11-22 | “Yes i approve 22-11-2026 student - 2” — this Codex conversation |

The required blueprint, E2E gap, dependency, and shared-file approvals are recorded above. Application and E2E implementation may now proceed.

The user explicitly authorized committing the current implementation snapshot on 2026-11-22. This authorization does not replace the independent review or Student 2 gates below; the commit is not represented as a review-approved final submission.

## Baseline checks

The clean `upstream/main` baseline was checked before drafting this blueprint. The recorded baseline run completed `make check` successfully, including system checks, migration drift check, Ruff, import-boundary checks, cross-module FK check, plural-contract checks, navigation/permission/schema checks, and pytest. This is baseline-only evidence; it does not verify BADMS implementation or the missing browser E2E target.

| Check | Baseline result | Final result |
|---|---|---|
| `make check` | Pass on `upstream/main` (`02b01fe`) | Pass: Django, migration drift, Ruff, import boundaries, schema, navigation/permission contracts, and full pytest suite |
| `make check-client` | Not run | Pass: TypeScript, 35 Vitest tests, and Vite production build (Vite reports the existing >500 kB main chunk warning) |
| `make e2e` | Target and Playwright E2E setup absent on baseline | Pass: 1 BADMS student smoke test (backup status to archive request list), run with Node 20.20.2 |
| BADMS module tests | Not applicable; module not implemented | Pass: 35 transition, approval-separation, scheduled-task, secure-storage, retention, security-policy, S3 transport, readiness, schedule-registration, and clean-install tests |
| Clean-install activation | Not run | Pass: pytest created a migrated database, `seed_modules` activated BADMS, a test IAM grant resolved, and the first authenticated backup-history request returned 200 |
| Teaching reference | Not present | Generated and verified: 19 CFRs / 66 live AFRs, 21 BRs, and 23 use cases linked to resolved implementation symbols |
| Scheduled task effects | Not run | Pass: due schedule dispatch, notification delivery, threshold update/audit, retention deletion/audit were each executed against the isolated test database |
| Celery beat merge | Not run | Pass: every BADMS beat entry is present in the merged application schedule |
| Production readiness command | Not present | Implemented and run in unconfigured production-like settings; it named 14 missing storage, retention, quota/capacity, and routing prerequisites |
| Independent Student 1 review rounds | None | Pending |
| Student 2 spec-driven review | Not started | Starts only after Student 1 reaches 10/10 |

## IAM integration and security-policy contract

The IAM service now persists `active_role` on each ERP session token. Its `/api/iam/v1/me` response scopes permissions and module grants to that selected role. `PATCH /api/iam/v1/me` accepts `last_selected_role` and refuses a role the user does not hold. The IAM permission catalogue is seeded from the v2 platform manifest; IT Security changes are stored as overrides on the existing IAM role-permission mapping and survive reseeding. The service records each successful grant/revoke in `IamSecurityAuditEvent` and exposes the latest 200 events to the BADMS security role.

The IAM permission-management endpoint requires the active designation `IT Security Team`, the existing `badms.security.audit` permission, and the BADMS module grant. This uses the current manifest without changing the shared access-control module, as requested. The role-management UI is deferred; the API is available for direct integration. Session caches in Fusion-Integrated may delay permission changes by up to `IAM_SESSION_CACHE_SECONDS` (60 seconds by default).

Transport configuration restricts the shared Nginx endpoint to AES-256-GCM cipher suites for TLS 1.2 and TLS 1.3. This directive requires NGINX 1.19.4+ and TLS 1.3-capable OpenSSL; NGINX is not installed in this WSL environment, so deployment `nginx -t` and a live handshake check remain required before reload. The BADMS S3 client independently restricts outbound connections to TLS 1.2 AES-256-GCM and keeps certificate validation enabled. Automated unit checks validate its SSL context.

IAM verification: `manage.py makemigrations --check --dry-run` reported no changes, and `manage.py test iam.tests` passed 162 tests. The ordinary test bootstrap tries to migrate an ERP-only table into a fresh default test database; the run used temporary isolated settings that mirrored the unused default alias to the isolated system database. No ERP database was migrated or modified.

BADMS `GET/PUT /api/v1/badms/security_policies` exposes fixed AES-256 at-rest and in-transit requirements and stores institute-provided positive retention-day values for all classifications. Encryption choices cannot be weakened through the API. Retention values are still unconfigured until the institute supplies them; no durations are assumed. Every policy update is recorded in BADMS audit history.

## E2E baseline gap

The Assignment 9 guide requires `make e2e` on the final commit and a clean reviewer copy to run it. The baseline had no Make target, browser tests, or Playwright dependency. Student 2 approved adding those on 2026-11-22; the browser smoke test passes with Node 20.20.2. The host's default Node 18.19.1 cannot run Playwright.

## Student 1 review rounds

| Round | Spec | Arch | Code | Security | Tests | E2E | Frontend | Ops | Hygiene | Open findings |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| None | — | — | — | — | — | — | — | — | — | No fresh independent review has run |

## Adversarial pass

Submitters are excluded from HoD decision, SysAdmin classification, Sensitive archive handling, Sensitive restoration approval, and restoration execution. Pending self-submissions are omitted from department approval lists. Services lock pending rows and query only the expected state, preventing duplicate transitions. Requested storage bytes must be positive and cannot exceed configured capacity; missing quota/capacity settings refuse submission. Archive dates remain historical metadata because the synchronized spec defines no permitted date window. Required department/security notification contacts are named by the readiness check; current deployment contacts are not configured.

## Storage and encryption decisions

Per the user's instruction to choose a concrete production option, BADMS configures Amazon S3 with SSE-KMS, an institute-owned AWS KMS key, TLS 1.2 AES-256-GCM, and private bucket settings. An AWS workload role should supply credentials. Enable S3 versioning and lifecycle rules using institute retention requirements. BADMS never handles key material. Sensitive archive operations fail closed unless the deployment confirms S3, private storage, AES-256, and TLS. Local storage is development-only. AWS documents SSE-KMS and TLS requirements for KMS-protected objects [here](https://docs.aws.amazon.com/AmazonS3/latest/userguide/specifying-kms-encryption.html).

## Outstanding work

1. Run a Student 2 independent spec-only review for FR/UC/BR/WF test design, execution, and triage; no pair-authored acceptance suite is being represented as that independent evidence.
2. Complete fresh Student 1 review rounds until the latest committed version receives 10/10 in all nine dimensions. No independent Student 1 score is claimed. The user authorized an implementation snapshot commit, but that does not satisfy this review gate.
3. Hand the 10/10 commit to Student 2 for their different-provider final review. Student 2's tests and results are not represented by this report yet.
4. Provision the production S3 bucket, customer-managed KMS key, workload IAM role, bucket policy, versioning, institute retention lifecycle rules, and deployment attestations before production use. No cloud resources have been created.
5. Configure an institute-approved retention duration for every classification. The settings endpoint validates shape and positive integers, but does not decide institutional values.
6. The separate IAM API has no BADMS role-management UI, which the user deferred. Direct API administration is currently supported.
