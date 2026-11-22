# HR-EIS Assignment 9 — Student 2 written decisions received

**Module:** `hreis` · **branch:** `module/hreis` on `keptbeetle/Fusion-Integrated`

**Status, 2026-11-22:** Student 2's dated written reply and returned Excel decision register for commit `12e1ddfe964873dbcd2080f4a74b0a41b5b82d94` have been supplied: **Approve D01 and D03–D07; Approve with limitations D08–D18; Acknowledge D02 and D19–D22. Overall: "Approve specified items only."** The exact dated decision language for all 22 IDs is in section 30 of `hreis-quality-report.md`; preserve the source email and Excel outside Git. This post-implementation reply is not a backdated pre-code approval, formal Step 7 10/10 verdict or permission to begin official Step 8.

## Original questions and recorded decisions (the real response is now documented)

- [x] **Blueprint and timing (D01 approved with bounded scope; D02 acknowledged):** Review `hreis-blueprint.md` against all six original documents at `D:\HR(EIS)\specifications`. Explicitly approve, reject or request changes. Acknowledge the documented deviation that implementation began before the required written approval; do not backdate any response.
- [x] **Five retained non-protected shared implementation changes (D03–D07 approved):** Approve or reject the exact `upstream/main...HEAD` diff for `fusion_auth/views.py`, `fusion_auth/tests/test_auth.py`, the fake IAM fixture extension in `conftest.py`, `modules/directory/contracts.py` and `modules/accesscontrol/management/commands/seed_modules.py`, unless these are first accepted through a separate authorized platform baseline. The active-role response must not be stale after a role switch.
- [x] **Institutional rules (D08–D11 approved with limitations; production authority still absent):** Resolve the source's `Accountant` actor versus the provisional IAM `Accounts Admin` designation. Supply authoritative leave eligibility and quotas, appraisal windows, HOD/Registrar/Director route rules and retention parameters, or leave them explicitly unconfigured. The six specs supply no numerical leave quota.
- [x] **External obligations (D12–D15 and D17–D18 bounded gaps accepted for module-only scope):** Provide authoritative APIs, identity and status semantics for payroll/finance/real-time sync and file/email delivery, or record a clearly bounded incomplete/deferred disposition for `HR-CFR-013`, `HR-AFR-090`, `HR-AFR-091`, `HR-AFR-093`. Synthetic status recording is not a bank transfer or external-system integration.
- [x] **Underspecified state (D16 limitation accepted; source owner still needed for production):** Rule on `HR-AFR-059`'s LTC `Returned` audit obligation: the supplied active LTC use case and business-rule documents do not define a Returned transition. Do not invent that transition without a source-backed decision.
- [ ] **Formal Step 7 and Step 8 still outstanding (D22 acknowledgment is not completion):** Obtain a fresh review of the final Student 1 commit using the original upstream nine-dimension review prompt and the guide's Step 7 rules. Begin official FR/UC/BR/WF spec-only test-design sessions only after the prerequisite review/decision process; Student 1 must never edit the reserved `modules/hreis/tests/spec/` and `docs/09-hreis/spec-tests/` paths.

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
| `modules/directory/contracts.py` | Active-user projection retained, restored `get_users` docstring; **approved in D06** for module-only scope; separate upstream integration still recommended |
| `fusion_auth/views.py` and its regression test, `conftest.py` | Genuine shared active-role refresh/validation fix; **D03–D05 approved in writing** for module-only scope; upstream integration remains a recommended platform action |
| `modules/accesscontrol/management/commands/seed_modules.py` | One-line registered-status logging correction; **approved in D07** |

**Important:** A written approval cannot waive rubric-protected `§3.2` modifications if they remain in a submitted module branch. Check the actual final branch diff, not this description, before granting any approval.

## Evidence received; original transport proof to archive

Student 2's reply, as shown in user-supplied Gmail screenshots, confirms that the six original specifications and listed review documents were considered. The attached completed workbook specifies each D01–D22 decision; Student 1 has transcribed exact decision text into `hreis-quality-report.md` §30 and into an external evidence note at `D:\HR(EIS)\lab 9\evidence\student2-approvals\`. Preserve the actual received Gmail `.eml` with headers and the untouched returned workbook to strengthen provenance. The preflight evidence remains review support, not a formal Step 7 scorecard.

**Received disposition:** Student 2's dated message for commit `12e1ddfe964873dbcd2080f4a74b0a41b5b82d94` says **"Approve specified items only"**; the workbook records 6 Approve, 11 Approve with limitations and 5 Acknowledged. This is not a backdated initial signoff, a formal 10/10 verdict or an institutional production approval. The original email and workbook have not been altered by this source documentation.
