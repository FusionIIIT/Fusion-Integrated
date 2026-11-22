# BADMS spec test triage

## Assignment and contributors

- Module: BADMS
- Assignment: 9
- Phase: Student 2
- Student 1: Git name `trupesha`; provider Google Gemini
- Student 2: Git name `sanebliss`; provider OpenAI Codex

## Frozen design and baseline

Frozen design commits: FR `e53669f`, UC `95634bd`, BR `8d16b8c`, WF `4808f33`.
Baseline commit: `cdd7f89`.

The baseline and repaired runs are separate snapshots. Repaired results do not replace or rewrite the frozen baseline.

| Suite | Baseline | Latest repaired |
|---|---:|---:|
| FR | 66 passed, 4 failed, 21 skipped | 69 passed, 1 failed, 21 skipped |
| UC | 20 passed, 0 failed, 3 skipped | 20 passed, 0 failed, 3 skipped |
| BR | 15 passed, 3 failed, 3 skipped | 17 passed, 1 failed, 3 skipped |
| WF | 3 passed, 7 failed, 0 skipped | 10 passed, 0 failed, 0 skipped |

The reported latest total is 116 passed, 2 failed, and 27 skipped.

## Remaining implementation compliance gaps

- `AFR-BA-014`: creating a schedule that conflicts with an active schedule currently returns `201` instead of the required `409`.
- `BR-BA-010`: an HOD requesting a report for another department currently receives `200` instead of the required `404`.

The assertions for both required responses remain in the tests.

## Repaired WF test defects

The restoration workflow tests had fake-IAM identity ordering defects: the process-global fake was set to the SysAdmin identity before user restoration requests, so those requests received `403`. The tests now install the user identity for the request and then install SysAdmin for administrative actions. The archival branch test also asserted stale ORM instances; it now refreshes them before checking persisted statuses. The requested workflow outcomes are exercised through the existing API transitions. WF subsequently passed 10/10.

## Skipped tests and NOT_AUTOMATED reasons

There are 27 skipped cases: FR 21, UC 3, BR 3, WF 0. The exact source cases and skip reasons are:

- FR (21): `CFR-BA-001` and `AFR-BA-005` — “manual backup has no failure-injection seam or observable failure path”; `AFR-BA-004` — “successful backup outcome communication is not recorded or exposed”; `AFR-BA-024` — “archival requests do not expose the required policy-review context”; `CFR-BA-008` and `AFR-BA-034` — “the implementation does not expose encryption-in-transit evidence”; `CFR-BA-009` and `AFR-BA-036` — “archival submission and decision notifications are not recorded or exposed”; `AFR-BA-035` — “archival history is not exposed to the requester”; `CFR-BA-012` and `AFR-BA-052` — “available storage-infrastructure capacity is not modeled or exposed”; `AFR-BA-048` — “storage-extension requests have no attachment, infrastructure, or policy-review fields”; `CFR-BA-014` and `AFR-BA-053` — “a global default backup-policy model is not implemented or exposed”; `CFR-BA-016` and `AFR-BA-059` — “backup creation-status and completion notifications are not recorded or exposed”; `CFR-BA-017` and `AFR-BA-060` — “storage-extension submission and decision notifications are not recorded or exposed”; `AFR-BA-067` — “security-policy enforcement is not implemented or exposed”; `CFR-BA-019` and `AFR-BA-066` — “IT Security RBAC permission management is not implemented or exposed.”
- UC (3): `BA-UC-011` — “global default backup-policy settings are not modeled or exposed”; `BA-UC-019` — “central IAM Administration Console is outside BADMS test control”; `BA-UC-020` — “security-policy enforcement is not implemented or exposed.”
- BR (3): `BR-BA-007` — “encryption in transit is not exposed by the BADMS API or model”; `BR-BA-017` — “infrastructure availability and departmental policy review are not modeled or exposed”; `BR-BA-021` — “central IAM RBAC administration is outside BADMS and no security-policy enforcement endpoint is exposed.”
- WF (0): no skipped cases.

## Verification note

Ruff and Python compilation passed. The earlier WF run was the pre-fix result (3 failed, 7 passed). The three test defects were repaired, and the subsequent terminal run verified 10/10 passing; the available repaired WF log records `10 passed in 3.45s`. Latest repaired totals are 116 passed, 2 failed, and 27 skipped. The baseline remains separately recorded above.
