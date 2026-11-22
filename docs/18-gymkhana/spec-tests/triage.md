# Spec tests: gymkhana

Student 1 (git author name): Deepak Kumar
Student 2 (git author name): Sujeet Das
Design commit (hash and subject): `f9c6cf5` test(gymkhana): freeze specification-derived test designs
Baseline commit (hash and subject): `a17cf30` feat(gymkhana): implement gymkhana module and verify review gates
Student 1's 10/10 commit the baseline ran on (hash): `a17cf30edc85059fc91632489294cf6e6dece811`

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | fr | 26 | 26 | 0 | 0 | 96.1% | 94.2% |
| baseline | uc | 43 | 43 | 0 | 0 | 97.4% | 95.8% |
| baseline | br | 26 | 26 | 0 | 0 | 96.8% | 95.1% |
| baseline | wf | 37 | 37 | 0 | 0 | 98.2% | 96.9% |
| Q1 (final) | all | 132 | 132 | 0 | 0 | 98.2% | 96.9% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| GYM-016 | AFR-GYM-021 | fr | Test-generation / test-implementation problem | Helper `_club` assigned default coordinator ID 2001 to both clubs, making other_head test with coordinator of target club. | Updated test to assign distinct coordinator ID 2003 to other_club. All assertions pass. | No |
| GYM-026 | AFR-GYM-034 | fr | Test-generation / test-implementation problem | Consecutive `_client(stub_iam)` calls overwrote active stub session to non-councillor user before retrieval. | Scoped client session activations appropriately. All assertions pass. | No |
| GYM-015 | BR-GYM-012 | br | Test-generation / test-implementation problem | Assertion `not VotingPoll.objects.exists()` was evaluated after valid poll was created by subsequent POST call. | Placed assertion immediately following rejection of invalid payload. All assertions pass. | No |
| TC-005 | UC-GYM-001 Exception Flow | uc | Specification ambiguity | No public interface or failure injection for physical storage failure without mocking DB. | Agreed reading: Physical disk failure is infrastructure, not functional requirement. Covered by DB constraints. | No |
| TC-008 | UC-GYM-011 Exception Flow | uc | Specification ambiguity | Internal DB update failure on club confirmation. | Agreed reading: Covered by transaction rollbacks; no separate functional failure flow specified. | No |
| TC-015 | UC-GYM-002 Exception Flow | uc | Specification ambiguity | Synchronous notification failure on session booking. | Agreed reading: NotificationOutbox decouples dispatch from transaction; asynchronous delivery tested in test_schedule.py. | No |
| TC-028 | UC-GYM-005 Alternative Flow | uc | Specification ambiguity | Bulk membership approval interaction. | Agreed reading: Spec defines singular approval endpoint `POST /api/v1/gymkhana/clubs/{id}/memberships/{app_id}/approve`. | No |
