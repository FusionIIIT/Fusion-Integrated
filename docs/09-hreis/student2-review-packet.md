# HR-EIS Assignment 9 — Student 2 review and testing packet

**Purpose:** Share Student 1's implementation for Student 2's **written decisions, independent specification tests and review**. This is not a certificate of institutional acceptance, a completed independent nine-dimension 10/10, or a request to merge to production.

**Repository:** https://github.com/keptbeetle/Fusion-Integrated/tree/module/hreis
**Branch:** `module/hreis` (use `git rev-parse HEAD` and record the exact hash when reviewing)
**Source specifications:** the six supplied files under `D:\HR(EIS)\specifications`; share those original files separately with Student 2 if they cannot access that folder.
**Reserved Student 2 paths:** `modules/hreis/tests/spec/`, `docs/09-hreis/spec-tests/` (Student 1 must not edit these).

## What is implemented and can be exercised

HR employee service records and verified leave credit ledger; leave applications and approval chains; LTC/CPDA advance and reimbursement, HR verification and authorized financial *status recording*; annual appraisal reviewer assignment, review and immutable archival; effective-dated explicit policy versions; configured dashboard notifications, pending-action reminders, immutable audit history and redacted compliance reads. Access is limited by the active IAM role and the matching module/action grant. There are no institutional policy defaults.

All 21 live HR-EIS use cases have synthetic Chromium browser journeys, and each of the 12 role designations has a walkthrough. Security tests include ten denied deep links and permission/module grant refusal for every API operation. The test suite also guards the HR-EIS API against unsupported and malformed list query parameters. The R2 policy/reviewer/reminder defects have backend regression tests.

The module **does not** execute a bank transfer, claim that an external payroll or finance API exchanged any data, upload actual documents to an authorized storage provider, assert official SMTP delivery, or infer an undocumented institutional leave quota or authority matrix.

## Where to start reviewing

1. `hreis-blueprint.md` — traced implementation decisions and open institutional choices.
2. `hreis-traceability-status.md` and generated `hreis-reference.md` — 193 live source IDs, 188 directly cited in Student 1 tests, and five uncited external/undefined obligations.
3. `hreis-quality-report.md` and `review-remediation.md` — verified technical gates, old findings and their current disposition.
4. `browser-coverage.md`, `browser-walkthrough.md`, and `student1-handoff.md` — test mapping, walkthrough evidence and runnable environment instructions.
5. `student2-approval-request.md` — **unsigned** decision checklist; it is not proof of approval.
6. `docs/08-delivery/online-ai-assignment-guide.md` and `module-review-prompt.md` from **upstream/main** — governing independent-review rules.

## Reproduce the Student 1 technical tests

With the repository's Linux/WSL virtual environment, Node, PostgreSQL, Redis and *synthetic* IAM configured, run:

```bash
make check
make check-client
.venv/bin/pytest modules/hreis --ignore=modules/hreis/tests/spec --cov=modules/hreis --cov-branch --cov-report=term-missing --cov-fail-under=90
.venv/bin/pytest modules/hreis --ignore=modules/hreis/tests/spec --cov=modules/hreis/domain --cov-branch --cov-report=term-missing --cov-fail-under=95
```

For full browser E2E, follow `browser-coverage.md`; `client/e2e/hreis/run-isolated.sh` requires a clearly opted-in **synthetic** IAM service, starts the test stack on 8002/5173, uses a disposable DB and revokes the temporary credential. **Never** run this synthetic fixture against a real institutional IAM or production database.

Developer/operator secrets belong in the local environment, not in this branch. Original detailed R3 review logs and R2 closure evidence are held outside Git under `D:\HR(EIS)\lab 9\evidence`.

## Decisions that must be returned in writing before formal acceptance

- **Blueprint:** approve or identify exact disagreements with `hreis-blueprint.md`, the source interpretation and 193 live IDs. Acknowledge Student 1's earlier procedural deviation if appropriate; do not backdate any signature.
- **Protected platform changes:** review `client/playwright.config.ts`, `client/e2e/global-setup.ts`, `client/e2e/auth.spec.ts`, `client/src/auth/`, `client/src/main.tsx`, `client/package*.json` and `fusion_auth/views.py`. The review rubric forbids some of these modifications on a module submission even if approved: decide the **platform-baseline integration route** rather than treating a signoff as a waiver.
- **Additional shared contract changes:** directory's `is_active` projection, the access-control seed status, and HR-EIS helper scripts under `ops/docs/` outside the one allowed reference script. Identify which require a permitted platform change.
- **External integrations:** state the authoritative payroll and finance provider/endpoints/status semantics, document storage API, official email settings, data sync triggers and reconciliation guarantees, or explicitly document which requirements remain pending.
- **Routing policies:** decide the true Accountant versus current IAM `Accounts Admin` mapping, HOD/Registrar/Director routing, leave quota/eligibility, appraisal submission windows and evidence retention according to actual institutional policy rather than synthetic fixtures.
- **Unresolved source language:** `HR-AFR-059` calls for retaining audit history of **returned** LTC requests, but the given active LTC workflow does not define a Returned transition; provide a sourced ruling rather than inventing one. The other open integration/source IDs are `HR-CFR-013` and `HR-AFR-090/091/092/093`; `HR-AFR-092` has a partial real directory-contract regression, not complete interoperability certification.

## Student 2's independent work

**Required sequence:** Student 2 can review the blueprint, approve or challenge the pending decisions and prepare the testing environment immediately. The assignment's official Step 8 independent spec-test phase must begin **only after** Student 1's branch has passed a fresh nine-dimension 10/10 review, including resolution of the non-waivable protected-file baseline issue. This packet requests approval and prepares the testing handoff; it does not skip that prerequisite.

Use the **different AI-provider model** required by the assignment. Extract FR/UC/BR/WF test designs independently from the original source specs, freeze the four `*_DESIGN.json` files and triage records under `docs/09-hreis/spec-tests/`, then implement those tests only under `modules/hreis/tests/spec/`. Run their suites against the same pinned commit. Return any failed test id, command, observed/expected effect, and the specification sentence. Student 1 will fix implementation code; Student 2 owns frozen spec tests.

A formal reviewer then scores all nine dimensions on a fresh, committed checkout. The module cannot be declared **10/10 in all nine dimensions** while the protected-file baseline or mandatory written approvals remain unresolved. No PR to the institution's `main` branch is authorized by this packet.

## What should be sent

Send Student 2 the exact branch/commit link, the six original source documents, this packet, `student2-approval-request.md`, and (if they need reproducible review) the sanitized local evidence/checklist. Ask for a dated identifiable **approve / reject / needs changes** response to each decision. Preserve the authentic response in the project; never write one on their behalf.

**Current handoff status:** Student 1's implementation is suitable for Student 2 to **inspect and respond to**. It is **not** claimed to have received Student 2's written approval, completed Student 2 testing, or qualified for institutional merge.
