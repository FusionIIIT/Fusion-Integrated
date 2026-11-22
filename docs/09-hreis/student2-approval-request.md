# HR-EIS Assignment 9 — pending Student 2 decisions

**Module:** `hreis` · **branch:** `module/hreis` on `keptbeetle/Fusion-Integrated`

**Status, 2026-11-22:** This is an unsigned request for authentic Student 2 decisions, not an approval, waiver, review verdict or production-readiness certificate. Student 1's post-R3 protected-file remediation is local until validated and published; use `git rev-parse HEAD` and the final verified change list to check the exact version being considered. The independent Stage 0/1 investigation is preliminary evidence, not the assignment's official Step 8.

## Decisions that need a real written response

- [ ] **Blueprint and timing:** Review `hreis-blueprint.md` against all six original documents at `D:\HR(EIS)\specifications`. Explicitly approve, reject or request changes. Acknowledge the documented deviation that implementation began before the required written approval; do not backdate any response.
- [ ] **Remaining shared implementation changes:** Approve or reject the exact `upstream/main...HEAD` diff for `fusion_auth/views.py`, `fusion_auth/tests/test_auth.py`, the fake IAM fixture extension in `conftest.py`, `modules/directory/contracts.py` and `modules/accesscontrol/management/commands/seed_modules.py`, unless these are first accepted through a separate authorized platform baseline. The active-role response must not be stale after a role switch.
- [ ] **Institutional rules:** Resolve the source's `Accountant` actor versus the provisional IAM `Accounts Admin` designation. Supply authoritative leave eligibility and quotas, appraisal windows, HOD/Registrar/Director route rules and retention parameters, or leave them explicitly unconfigured. The six specs supply no numerical leave quota.
- [ ] **External obligations:** Provide authoritative APIs, identity and status semantics for payroll/finance/real-time sync and file/email delivery, or record a clearly bounded incomplete/deferred disposition for `HR-CFR-013`, `HR-AFR-090`, `HR-AFR-091`, `HR-AFR-093`. Synthetic status recording is not a bank transfer or external-system integration.
- [ ] **Underspecified state:** Rule on `HR-AFR-059`'s LTC `Returned` audit obligation: the supplied active LTC use case and business-rule documents do not define a Returned transition. Do not invent that transition without a source-backed decision.
- [ ] **Final review and independent testing:** Obtain a fresh review of the final Student 1 commit using the original upstream nine-dimension review prompt and the guide's Step 7 rules. Begin official FR/UC/BR/WF spec-only test-design sessions only after the prerequisite review/decision process; Student 1 must never edit the reserved `modules/hreis/tests/spec/` and `docs/09-hreis/spec-tests/` paths.

## Shared-file change and resolution map

| File or group | Disposition |
| --- | --- |
| `.importlinter`, `config/settings/base.py`, `config/urls.py`, `config/celery.py`, `client/src/app/registry.ts` | Module registration/contract enforcement allowed by the guide |
| `client/e2e/accounts.ts` | Allowed new synthetic role-account entries only |
| `ops/docs/hreis_reference.py` | Required reference generator, allowed outside module |
| `docs/02-iam/permission-catalog.generated.md`, `openapi/fusion-integrated.v1.yaml`, `registry/permissions.json` | Generated manifests required by registration |
| `client/playwright.config.ts`, `client/e2e/global-setup.ts` | **Protected**; changes removed from module branch in post-R3 remediation. HR-EIS-only fixture seed and worker count now live in `client/e2e/hreis/run-isolated.sh` |
| `client/e2e/auth.spec.ts`, `client/src/auth/AuthProvider.tsx`, `client/src/auth/AuthProvider.test.tsx`, `client/src/auth/RequireAuth.test.tsx` | **Protected**; module-branch edits removed. HR-EIS's own API query hooks now scope reads by user ID and active role, with module-owned regression evidence. Platform-global cache clearing and login-throttle fixes are separate baseline concerns |
| `client/src/main.tsx`, `client/package.json`, `client/package-lock.json` | Frontend version upgrades removed; module uses upstream-pinned client versions |
| `docs/09-hreis/scripts/*.py` | HR-EIS-owned reference-support helpers moved from unapproved shared `ops/docs/hreis_*.py`; only the allowed `ops/docs/hreis_reference.py` remains there |
| `modules/directory/contracts.py` | Active-user projection retained, missing `get_users` docstring text restored; requires true approval/platform integration |
| `fusion_auth/views.py` and its regression test, `conftest.py` | Genuine shared active-role refresh/validation fix; needs acceptance or upstream baseline, not a fabricated waiver |
| `modules/accesscontrol/management/commands/seed_modules.py` | One-line registered-status logging correction; requires review/approval |

**Important:** A written approval cannot waive rubric-protected `§3.2` modifications if they remain in a submitted module branch. Check the actual final branch diff, not this description, before granting any approval.

## Evidence and response

Source specification documents are local to the original PC and must be shared separately. Student 1's quality report and the independent Stage 1 preflight evidence are supporting claims; an official reviewer must run the gates itself on the final commit. The preflight report is at `D:\fusion\HR-EIS-Student2-Results\stage-1-technical-resolution.md`.

The designated Student 2 should return an identifiable, dated **Approve / Request changes / Hold** response for each decision, with its exact branch commit hash and any exceptions. Preserve their original words without alteration. This document intentionally contains no impersonated approval, official review score or institutional PR link.
