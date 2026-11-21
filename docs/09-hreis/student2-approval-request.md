# HR-EIS Assignment 9 — Student 2 approval record (pending)

**Module:** HR-EIS (`hreis`)
**Student 1 checkout:** `D:\fusion\Fusion-Integrated-A9-HREIS`, branch `module/hreis`
**Status:** **NOT APPROVED IN WRITING** as of 2026-11-21. Student 1 reports Student 2's verbal agreement; no signed or independently attributable written artifact has been supplied. Do not misrepresent this draft as approval.

## Decisions to confirm in writing

- [ ] Student 2 has reviewed and approves the source-to-build blueprint at `docs/09-hreis/hreis-blueprint.md` and its known documentation gaps (193 live IDs).
- [ ] Student 2 acknowledges the procedure deviation: Student 1 began implementation before the required written blueprint approval.
- [ ] Student 2 approves justified cross-cutting changes needed to mount HR-EIS within Fusion, listed below, and does not treat the initial verbal agreement as a final 10/10 review.
- [ ] Student 2 understands that the source problem statement **does not contain actual numerical institutional leave quotas, appraisal dates or a complete authority matrix**. The module refuses to assume them and requires explicit effective policy versions; any demo policies are disposable/synthetic.
- [ ] Student 2 understands that the finance endpoint uses a **provisional** mapping of the specifications' Accountant actor to the existing IAM `Accounts Admin` designation, still requiring an institutional authority decision before real deployment. It records *externally referenced* status with immutable audit evidence but executes no bank transfer; the email backend requires real provider settings and a configured recipient directory; secure claim-file upload/storage is not part of the current read-only shared file service.
- [ ] Student 2 will independently design, freeze and run its **own** FR/UC/BR/WF suites with a different AI provider after the approved Student 1 builder phase, not reuse Student 1's tests as the independent baseline.

## Non-HR-EIS shared files changed locally

These changes must be reviewed as a set. No Git commit or remote PR has been made.

| File | Purpose of change |
|---|---|
| `.importlinter` | Enforce HR-EIS package/layer boundaries |
| `ops/docs/hreis_reference.py` | Deterministically generate implementation reference from registry and workflow source |
| `client/e2e/accounts.ts` | Isolated test accounts for HR-EIS browser checks |
| `client/playwright.config.ts` | Serialize local Chromium E2E to avoid a shared IAM login-refresh race |
| `client/src/app/registry.ts` | Mount HR-EIS frontend routes |
| `config/celery.py` | Register HR-EIS notification task routing / optional polling |
| `config/settings/base.py` | Enable HR-EIS module app/settings |
| `config/urls.py` | Mount versioned HR-EIS API |
| `conftest.py` | Shared synthetic IAM/database testing fixtures |
| `fusion_auth/tests/test_auth.py` | Validate platform auth handling relevant to integration |
| `fusion_auth/views.py` | Integration auth changes (review for platform impact) |
| `modules/accesscontrol/management/commands/seed_modules.py` | Seed HR-EIS module as planned until readiness prerequisites pass |
| `docs/02-iam/permission-catalog.generated.md` | Regenerated permission catalog |
| `openapi/fusion-integrated.v1.yaml` | Regenerated API schema |
| `registry/permissions.json` | Regenerated HR-EIS role/action grants |

## What a future response must supply

An identifiable Student 2 acknowledgment stating which of the above items are **approved**, which are **not approved**, and any requested correction. Save the actual response alongside this record without modifying its meaning.

The official Student 1 fresh-committed-clone nine-dimension review remains **separate**. The independent uncommitted preflight in the quality report returned **NOT APPROVED**; do not cite it as a 10/10 scorecard.
