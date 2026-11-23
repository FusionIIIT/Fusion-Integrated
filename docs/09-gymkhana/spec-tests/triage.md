# Spec tests: gymkhana

Student 1 (git author name): Divyansh Agrawal
Student 2 (git author name): spidy-00-5
Design commit (hash and subject): fe2f927 (spec-tests: freeze all four design files (FR/UC/BR/WF))
Baseline commit (hash and subject): da21557 (Gymkhana: implement domain, models, services, api views, client routes, and test suite)
Student 1's 10/10 commit the baseline ran on (hash): da2155799fa97ea03cb9d9b1d11bdb437010e209

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 39 | 36 | 0 | 3 | 74 | 44 |
| baseline | UC | 25 | 22 | 0 | 3 | 69 | 35 |
| baseline | BR | 44 | 42 | 1 | 1 | 74 | 48 |
| baseline | WF | 16 | 15 | 1 | 0 | 61 | 25 |
| final | FR | 36 | 36 | 0 | 0 | 74 | 44 |
| final | UC | 22 | 22 | 0 | 0 | 69 | 35 |
| final | BR | 43 | 43 | 0 | 0 | 74 | 48 |
| final | WF | 16 | 16 | 0 | 0 | 61 | 25 |
| unconfirmed re-run | FR | 39 | 39 | 0 | 0 | 75 | 41 |
| unconfirmed re-run | UC | 25 | 25 | 0 | 0 | 75 | 40 |
| unconfirmed re-run | BR | 44 | 44 | 0 | 0 | 75 | 44 |
| unconfirmed re-run | WF | 16 | 16 | 0 | 0 | 67 | 23 |

The "unconfirmed re-run" rows are Student 1's run of the working tree after the changes marked "awaiting Student 2's confirmation" below. The "final" rows above it predate them.

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| FR-014 | CFR-GYM-003 / AFR-GYM-013 | FR | Confirmed implementation defect | Skipped at the baseline because nothing was queued. AFR-GYM-013: "After a session is successfully booked, the system shall notify the intended student recipients of the new session." | Announcements are now built, so the test was automated from the frozen case. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| FR-016 | CFR-GYM-003 / AFR-GYM-015 | FR | Confirmed implementation defect | Skipped at the baseline because nothing was queued. AFR-GYM-015: "After an event is successfully booked, the system shall notify the intended student recipients of the new event." | Announcements are now built, so the test was automated from the frozen case. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| FR-027 | CFR-GYM-005 / AFR-GYM-025 | FR | Confirmed implementation defect | Skipped at the baseline because nothing was queued. CFR-GYM-005: "notifying the target audience". | Announcements are now built, so the test was automated from the frozen case. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| UC-003 | UC-GYM-002 Main Flow | UC | Confirmed implementation defect | Skipped at the baseline because nothing was queued. Problem Statement 4.1 lists "Notifications for newly booked sessions and events." | Announcements are now built, so the test was automated from the frozen case. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| UC-005 | UC-GYM-003 Main Flow | UC | Confirmed implementation defect | Skipped at the baseline because nothing was queued. Problem Statement 4.1 lists "Notifications for newly booked sessions and events." | Announcements are now built, so the test was automated from the frozen case. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| UC-012 | UC-GYM-006 Main Flow | UC | Confirmed implementation defect | Skipped at the baseline because nothing was queued. Problem Statement 4.1 lists "Voting poll creation, target-group selection, notification, and student voting." | Announcements are now built, so the test was automated from the frozen case. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| BR-029 | BR-GYM-013 | BR | Confirmed implementation defect | Skipped at the baseline because nothing was queued. Problem Statement 4.1 lists "Voting poll creation, target-group selection, notification, and student voting." | Announcements are now built, so the test was automated from the frozen case. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| BR-032 | BR-GYM-014 — expired poll access denied | BR, WF | Confirmed implementation defect | BR-032 and WF-010 expect HTTP 400 for an expired poll; the implementation returned HTTP 409 Conflict. | Fixed in Student 1 commit by returning BadRequestError (HTTP 400) in modules/gymkhana/services/polls.py:cast_vote when voting on an expired poll. Both tests now pass. | No |
| WF-010 | BW-GYM-02 STT Transition 2 guard — expired poll | BR, WF | Confirmed implementation defect | WF-010 and BR-032 expect HTTP 400 for an expired poll; the implementation returned HTTP 409 Conflict. | Fixed in Student 1 commit by returning BadRequestError (HTTP 400) in modules/gymkhana/services/polls.py:cast_vote when voting on an expired poll. Both tests now pass. | No |
| BR-030 | BR-GYM-014 | BR | Test-generation / test-implementation problem | The frozen case says "Student belongs to batch=2024, branch=CSE", and the test never set them. | The fixture now sets both; the expected result is unchanged. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| BR-031 | BR-GYM-014 | BR | Test-generation / test-implementation problem | The frozen case says "Student belongs to batch=2023, branch=ECE", and the test never set them. | The fixture now sets both; the expected result is unchanged. Written by Student 1; awaiting Student 2's confirmation. | Yes |
| FR-015 | AFR-GYM-014 | FR | Specification ambiguity | AFR-GYM-014 lists a poster for an event; AFR-GYM-010 calls only the session's poster optional. The frozen case names a poster, and the test sends none and expects 201. | The code accepts an event with or without one. No reading is agreed yet. | Yes |
