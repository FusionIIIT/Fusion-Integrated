# HR-EIS Assignment 9 — Student 2 approval record (pending)

**Module:** HR-EIS (`hreis`)
**Student 1 checkout:** `D:\fusion\Fusion-Integrated-A9-HREIS`, branch `module/hreis`
**Status:** **READY TO REQUEST REVIEW; NOT APPROVED IN WRITING** as of 2026-11-22. Student 1 reports Student 2's verbal agreement; no independently attributable written approval has been supplied. This form is a request for decisions, not evidence of acceptance.

## Decisions to confirm in writing

- [ ] Student 2 has reviewed and approves the source-to-build blueprint at `docs/09-hreis/hreis-blueprint.md` and its known documentation gaps (193 live IDs).
- [ ] Student 2 acknowledges the procedure deviation: Student 1 began implementation before the required written blueprint approval.
- [ ] Student 2 approves justified cross-cutting changes needed to mount HR-EIS within Fusion, listed below, and does not treat the initial verbal agreement as a final 10/10 review.
- [ ] Student 2 understands that the source problem statement **does not contain actual numerical institutional leave quotas, appraisal dates or a complete authority matrix**. The module refuses to assume them and requires explicit effective policy versions; any demo policies are disposable/synthetic.
- [ ] Student 2 understands that the finance endpoint uses a **provisional** mapping of the specifications' Accountant actor to the existing IAM `Accounts Admin` designation, still requiring an institutional authority decision before real deployment. It records *externally referenced* status with immutable audit evidence but executes no bank transfer; the email backend requires real provider settings and a configured recipient directory; secure claim-file upload/storage is not part of the current read-only shared file service.
- [ ] Student 2 will independently design, freeze and run its **own** FR/UC/BR/WF suites with a different AI provider after the approved Student 1 builder phase, not reuse Student 1's tests as the independent baseline.

## Non-HR-EIS shared files changed locally

These changes are committed on the fork's `module/hreis` branch and require review. There is **no institutional pull request**. The module review rubric explicitly prohibits certain protected harness/auth-file changes **even if Student 2 approves them**; those must instead be resolved through an accepted platform baseline before a formal nine-dimension 10/10 review. Written agreement is not a waiver.

| File | Purpose of change |
|---|---|
| `.importlinter` | Enforce HR-EIS package/layer boundaries |
| `ops/docs/hreis_reference.py` | Deterministically generate implementation reference from registry and workflow source |
| `client/e2e/accounts.ts` | Isolated test accounts for HR-EIS browser checks |
| `client/playwright.config.ts` | **Protected by rubric:** serialized Chromium E2E to avoid a shared IAM role-refresh race; requires platform-baseline resolution |\n| `client/e2e/global-setup.ts`, `client/e2e/auth.spec.ts` | **Protected by rubric:** synthetic HR fixture installation and login-rate-limit test behavior; requires platform-baseline resolution |\n| `client/src/auth/AuthProvider.tsx` and auth tests | **Protected by rubric:** clear role-scoped query caches on IAM role switch; requires platform-baseline resolution |\n| `client/src/main.tsx`, `client/package.json`, `client/package-lock.json` | Shared router entry and frontend dependency upgrades; separately review any platform-wide compatibility impact |\n| `modules/directory/contracts.py` | Surface active-user status through the existing directory contract, used to reject inactive appraisal reviewers |\n| `ops/docs/hreis_browser_walkthrough.py`, `ops/docs/hreis_client_types.py`, `ops/docs/hreis_traceability.py` | Additional HR-EIS teaching/verification helpers outside the exact allowed reference-script path; approval/disposition needed |
| `client/src/app/registry.ts` | Mount HR-EIS frontend routes |
| `config/celery.py` | Register HR-EIS notification task routing / optional polling |
| `config/settings/base.py` | Enable HR-EIS module app/settings |
| `config/urls.py` | Mount versioned HR-EIS API |
| `fusion_auth/tests/test_auth.py` | Validate platform auth handling relevant to integration |
| `fusion_auth/views.py` | Refresh the principal after IAM role change so the API response reflects current role; shared platform change, not module-only |
| `modules/accesscontrol/management/commands/seed_modules.py` | Seed HR-EIS module as planned until readiness prerequisites pass |
| `docs/02-iam/permission-catalog.generated.md` | Regenerated permission catalog |
| `openapi/fusion-integrated.v1.yaml` | Regenerated API schema |
| `registry/permissions.json` | Regenerated HR-EIS role/action grants |

## What a future response must supply

An identifiable Student 2 acknowledgment stating which of the above items are **approved**, which are **not approved**, and any requested correction. Save the actual response alongside this record without modifying its meaning.

The latest committed-clone technical review round R3 is recorded in the quality report and the local evidence bundle. It was **NOT APPROVED** due to missing signed decisions and protected shared-file differences, and must not be represented as a formal 10/10 result. Student 2's own independent model, spec-test suites and written response remain required.
