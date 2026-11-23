# MMS A9 design review package provenance

This package is held outside `docs/16-mms/spec-tests/` and
`modules/mms/tests/spec/`, which are reserved Student 2 paths. It is available for review;
it is not the canonical handoff commit.

## Design sources and current SHA-256

| Design | Exact source files | SHA-256 at design preparation |
|---|---|---|
| FR | `docs/mms-specs/01_MMS_Problem_Statement_v1.0_SYNCHRONIZED.md` | `68193a4d1a4967d8f3069034452eaa4c2a4f9da315d33095b264237e753d9c1a` |
| FR | `docs/mms-specs/02_MMS_Requirements_Registry_CFR_AFR_v1.4_FINAL.md` | `e7cf9fc69dc7be844b397f0da8edf919e04963f0ff335da9d400e222b4e17c19` |
| UC | `docs/mms-specs/01_MMS_Problem_Statement_v1.0_SYNCHRONIZED.md` | `68193a4d1a4967d8f3069034452eaa4c2a4f9da315d33095b264237e753d9c1a` |
| UC | `docs/mms-specs/03_MMS_Use_Case_Specifications_v1.4_FINAL.md` | `41f1f1107f2999a4fe2442399bbe27fb979c1d3f2b2a6b0cc78dce56cbec72aa` |
| UC reuse | `a8_design/UC_DESIGN.json` | `5e02ffd20ca71fdf8728913b99b0d4e12de697e782649df3d60f0f502da473ea` |
| BR | `docs/mms-specs/01_MMS_Problem_Statement_v1.0_SYNCHRONIZED.md` | `68193a4d1a4967d8f3069034452eaa4c2a4f9da315d33095b264237e753d9c1a` |
| BR | `docs/mms-specs/04_MMS_Business_Rule_Specifications_v1.4_FINAL.md` | `3cf4336ae801946ae1103647a2fa655a3e51a255a876b970e1f349be60a68c94` |
| BR reuse | `a8_design/BR_DESIGN.json` | `0962930ac3f2436530ce189e09a40ba49976c08cf5e4e4cef222e6fbc9fd694a` |
| WF | `docs/mms-specs/01_MMS_Problem_Statement_v1.0_SYNCHRONIZED.md` | `68193a4d1a4967d8f3069034452eaa4c2a4f9da315d33095b264237e753d9c1a` |
| WF | `docs/mms-specs/05_MMS_Workflow_Specifications_v1.4_FINAL.md` | `b1eada54a933285c0d0712e810c833258153c5543b80441979aab501914e9538` |
| WF reuse | `a8_design/WF_DESIGN.json` | `a14689ca91542bfd220d004482c70df7958f4b7a9c5dfdabf02ce9534310faab` |

## A9 alignment checks

- The reused UC design declares 31 use cases; all 31 current spec IDs are represented by its
  128 cases. Its 14 blocked cases retain their unresolved reasons and have null expected
  results in the A9 copy.
- The reused BR design contains all 41 active rules; its 84 cases reference those rule IDs.
  Its 13 blocked cases retain their reasons and have null expected results in the A9 copy.
- The reused WF design identifies all 21 current workflows (16 basis, 5 composite) and has
  24 distinct cases. Its 10 blocked cases retain their reasons and have null expected results
  in the A9 copy.
- A8 source field names were normalized to the A9 Prompt A fields. Case IDs and nonblocked
  expected results were preserved. Each `source_id` begins with the exact source ID from its
  specification. Historical A8 design files were not changed.
- FR contains 112 cases for all 101 atomic AFRs, plus blocked cases for explicit unresolved
  CFR conditions. All 22 CFR roll-ups are covered by their constituent AFR cases. Blocked
  cases have null expected results; no numeric policy values, actor permissions, charge
  amounts, or unspecified outcomes were added.

## Current A9 design artifact SHA-256

| File | SHA-256 |
|---|---|
| `a9_design/FR_DESIGN.json` | `4bd3db76e8fc95ca8ff9f3cddb8ad15783bd2b2b2079d523ced5c892f7d3effe` |
| `a9_design/UC_DESIGN.json` | `2f54cecbc5758f1a85d1b74a6ff80ee19506021b962c9059603b2f2018909c0e` |
| `a9_design/BR_DESIGN.json` | `3b6ccaccddcd73f6d94170940db91ee834c7a7d79de7e5bf3fc5f6b828d3e351` |
| `a9_design/WF_DESIGN.json` | `f394a173e82792b26e273e0d7d7068595e004ea00ee7142bb3f21b1c4d19c788` |

## Path and chronology audit

- In the current checkout, `docs/16-mms/spec-tests/` contains `triage.md` only; the four A9
  design artifacts remain outside the prescribed canonical design path. Its recorded SHA-256
  is `52b98e33ab806e5d74406f02be8b30e9c673e1704e12b947b817e96fba7b8222`.
- Current `HEAD` is `5595be6628b4cdc6f8b47cf74bac267a2470f780`; the A9 design JSON files are
  untracked in this checkout. The visible Git object
  `fb639b38aa147a9e1572e55e0f20f618c3200b13`, dated 2026-11-24 01:53:30 +05:30, contains the
  four A9 designs in the same baseline checkpoint as MMS implementation. The later object
  `870f980daed25af7ba205507e47a4473412a6e38`, dated 2026-11-24 02:01:54 +05:30, changes the FR
  design. Neither is an isolated four-design commit preceding test generation.
- These existing artifacts do not prove a fresh source-only Prompt A session. No filesystem
  timestamps are used as chronology evidence. The required design-before-test gate remains
  unproven; no commit or timestamp has been fabricated.
- Student 2's current review session used OpenAI Codex, GPT-6. No Student 1 tool/model/provider
  record was found; provider separation cannot be verified.

## Evidence not asserted

No qualifying design-first commit, clean Student 1 baseline commit, 10/10 scorecard, or
pre-implementation approval timestamp is evidenced. The dated review and approvals in
`REVIEW_VERDICT.md` are current Student 2 decisions; they do not establish that approval
preceded implementation. Existing unresolved items include ISS-MMS-012/013/014/015/019,
rebate-date modification rules, special-food decision period, and special-food charge
source/value. No institution/instructor policy value or decision is supplied here. Student 1's
explicit ISS-MMS-014 agreement or disagreement is also not recorded.
