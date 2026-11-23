# MMS A9 design review and Student 2 approvals

**Date:** 2026-11-24 (Asia/Kolkata)  
**Formal design verdict:** **Rejected — content findings corrected; chronology and provider evidence remain open**

## Design review

Structural and traceability checks pass:

- FR has 112 unique cases, source IDs covering all 101 AFRs, and constituent-AFR coverage
  for all 22 CFRs. Its 19 blocked cases have null expected results, including the unresolved
  rebate-date change and institution-defined special-food decision period.
- UC has 128 unique cases covering all 31 use cases; 13 are blocked with null expected
  results.
- BR has 84 unique cases covering all 41 active rules; 13 are blocked with null expected
  results.
- WF has 24 unique cases referencing all 21 workflows (16 basis, 5 composite); 10 are
  blocked with null expected results.
- Each JSON file has the seven A9 Prompt A fields, unique test IDs, and a `source_id` that
  begins with its exact specification ID. Source and design hashes are recorded in
  `PROVENANCE.md` and match the current files.

The two content findings from the prior review are corrected in this revision:

1. **UC `TC-UC-073` now asserts Warden access.** It seeds Yes/No responses and checks that the
   Warden can open/search the summary, consistent with Problem Statement §3.3.9 and
   AFR-MMS-088.
2. **All 54 generic FR actions are now scenario-specific.** The FR cases name actors, inputs,
   conditions, and observable assertions. The unresolved rebate-date change (TC-FR-067) and
   institution-defined decision-period deadline (TC-FR-086) are now blocked with null expected
   results; no policy value was supplied.

The package remains rejected because required evidence and external policy rulings are still absent:

1. **Design-first chronology is not established.** The four JSON designs are now present in
   `docs/16-mms/spec-tests/` in the working tree, but are untracked. Existing Git objects show
   the A9 designs and MMS implementation together in baseline checkpoint
   `fb639b38aa147a9e1572e55e0f20f618c3200b13` (2026-11-24 01:53:30 +05:30), followed by an FR
   edit in `870f980daed25af7ba205507e47a4473412a6e38` (2026-11-24 02:01:54 +05:30). These do not
   establish an isolated design-first commit or a fresh source-only Prompt A session.
2. **Provider separation is unverified.** This review used OpenAI Codex, GPT-6. The repository
   contains no Student 1 tool/model/provider run record, so the different-provider requirement
   cannot be confirmed.
3. **External policy decisions remain open.** Special-food charge source/value and cancellation
   billing remain unspecified; the implementation keeps special-food approval blocked and does
   not invent cancellation billing treatment.

**ISS-MMS-014 is resolved as a specification interpretation.** Student 1 agrees that the active
Caretaker records Served/Cancelled updates because MMS-UC-021 names the Caretaker as Primary
Actor and assigns those actions in its main success scenario. The Problem Statement's actor
omission does not change that explicit use-case requirement. This interpretation is not an
institution policy ruling and does not resolve cancellation billing.

The A8 UC, BR, and WF case IDs and nonblocked expected results were preserved in A9-shaped
copies; historical A8 design files were not changed. The spec IDs, coverage totals, and hashes
were checked without database tests.

## Student 2 approvals

These are approvals I make on 2026-11-24. They are not backdated evidence of approval before
Student 1 wrote code. The quality report should link to this dated record.

### Blueprint

**Approved as the current blueprint** for the module-only architecture, directory-contract
boundary, registration plan, and documented no-default policy posture, subject to the design
corrections above. This approval does not establish that the required pre-code blueprint
approval occurred.

### Known gaps and decisions

| Item | Student 2 decision |
|---|---|
| ISS-MMS-012, Mess Admin menu visibility | Approve leaving unresolved and granting no menu access. |
| ISS-MMS-013, special-food decision period | Approve leaving unset; do not use an assumed 12-hour value. |
| ISS-MMS-014, Served/Cancelled actor | Student 2 approves, and Student 1 agrees with, the active Caretaker interpretation stated by MMS-UC-021. This is a specification reading, not institution policy; it does not resolve cancellation billing. |
| ISS-MMS-015, billing after Cancelled | Approve leaving unresolved; do not invent reversal or suppression. |
| ISS-MMS-019, vacation reminder cadence | Approve leaving unspecified; do not schedule a guessed cadence. |
| Rebate date modification | Approve leaving unavailable until the external policy supplies permitted changes. |
| Special-food charge source/value | Approve leaving unavailable; this approves no amount, fee source, or billing treatment. |

I do **not** approve any institution/instructor policy value or decision for these items.

### Shared-file changes

I approve the following reviewed MMS integrations outside the module folders:

| File | Approval and scope |
|---|---|
| `.importlinter` | Approve registering MMS and its layer/boundary contracts. |
| `client/src/app/registry.ts` | Approve the `/mms` module entry. |
| `config/celery.py` | Approve merging MMS-owned schedule and task routes. |
| `config/settings/base.py` | Approve the optional decision-hours setting: unset remains `None`; configured invalid/nonpositive values fail; no default is introduced. |
| `config/urls.py` | Approve mounting `/api/v1/mms/`. |
| `modules/directory/contracts.py` | Approve the additive active-student-ID contract used for MMS notification recipients. |
| `registry/permissions.json` | Approve the generated MMS grants; Mess Admin receives only role management. |
| `docs/02-iam/permission-catalog.generated.md` | Approve the generated MMS permission catalog entries. |
| `openapi/fusion-integrated.v1.yaml` | Approve the generated MMS API additions. Semantic comparison found all 55 prior paths unchanged and no prior schemas changed; 22 paths and 26 schemas were added. |

No Python or npm dependency-file changes are present in the current diff, so there is no new
dependency approval to grant. The dated approvals and quotes are now linked from the quality
report. They do not establish the required timing before implementation.

## Remaining prerequisites

- Preserve the corrected UC and FR content; complete a valid source-only A9 design session
  and canonical-path design-first evidence in a permitted future workflow. Existing artifacts
  cannot establish that chronology.
- Add Student 1's actual tool/model/provider to the run record and verify provider separation.
- The dated Student 2 approval record is linked from the quality report; this does not establish
  pre-implementation approval timing.
- For the implementation baseline, obtain Student 1’s clean committed baseline and the
  required 10/10 scorecard/hash; neither is established here.
- Obtain institution/instructor policy only if the team wants to test or implement the
  corresponding values: decision period, fulfillment authority if different, cancellation
  billing, reminder cadence, rebate-date rules, and special-food charge source/value.
- Run independent suites only after a valid committed design-first baseline is established.
