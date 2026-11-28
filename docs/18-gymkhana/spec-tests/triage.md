# Spec tests: gymkhana

Student 1 (git author name): revankumarz
Student 2 (git author name): Saroj Aman
Design commit (hash and subject): f7b9608 Freeze spec test designs (FR, UC, BR, WF), written from the spec only
Baseline commit (hash and subject): the commit that adds this file, "Spec tests (FR, UC, BR, WF) and triage with baseline results"
Student 1's commit the baseline ran on (hash): 6d303c1 (not a 10/10 commit: review rounds 1-3 ended "not yet"; stopped for the deadline)

## Design notes
- WF: Prompt A ran four times in fresh sessions and every attempt failed the source_id check (1 empty; 2 and 4 cited Problem Statement sections; 3 wrote WF-GYM-0x for the spec's BW-GYM-0x). Attempt 3 was frozen unchanged because of the deadline and limited quota. Its WF-GYM-0x ids mean BW-GYM-0x.

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 34 | 34 | 0 | 0 | 79.8 | 45.9 |
| baseline | UC | 30 | 28 | 1 | 1 | 78.9 | 44.2 |
| baseline | BR | 46 | 42 | 3 | 1 | 77.8 | 45.5 |
| baseline | WF | 27 | 24 | 3 | 0 | 77.1 | 43.0 |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|
| TC-UC-GYM-009-EXC | UC-GYM-009 Exception Flows | UC | Unresolved | negative-amount budget request: expected 422, got 400 (api-conventions: 422 = validation) | open: does the 400 come from the negative amount (code) or a field the test omits (test)? |
| GYM-024 | budget path | WF | Unresolved | expected 422, got 400 | open: same question as TC-UC-GYM-009-EXC |
| GYM-025 | budget path | WF | Unresolved | expected 422, got 400 | open: same question as TC-UC-GYM-009-EXC |
| BR-GYM-007-02 | BR-GYM-007 condition-false | BR | Unresolved | apply to an open club: refused with 404, test expects 422 (api-conventions: 404 when outside visibility) | open: likely test-implementation (status) |
| BR-GYM-010-03 | BR-GYM-010 condition-false | BR | Unresolved | non-head action: refused with 404, test expects 403 (api-conventions: never 403 when existence must not leak) | open: likely test-implementation (status) |
| BR-GYM-014-03 | BR-GYM-014 condition-false | BR | Unresolved | setup creates an already-expired poll; creation is refused 422 expiry_in_past, so the vote step never runs | open: likely test-implementation (setup) |
| GYM-014 | BW-GYM-02 transition 2 | WF | Unresolved | vote answers 201; the test reads "id" but the API returns "choice_id" | open: likely test-implementation |
| UC storage-failure case (skipped) | UC exception flow | UC | Unresolved | NOT_AUTOMATED: no way to cause a real storage outage without mocking | open |
| BR inactive-poll case (skipped) | BR-GYM-014 | BR | Unresolved | NOT_AUTOMATED: the module has no inactive-poll state | open: possibly spec ambiguity (active = unexpired) |

A rebase gives every commit a new hash. After one, update every hash in this file.
