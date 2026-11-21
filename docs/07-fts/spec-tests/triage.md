# Spec tests: fts

Student 1 (git author name): cosypix
Student 2 (git author name): Daggula Amulya
Design commit (hash and subject): a7d1c4f feat(fts): add Prompt A spec test designs for FR, UC, BR, and WF strategies
Baseline commit (hash and subject): 639cc57 feat(fts): implement spec tests and establish baseline triage for Q1
Student 1's 10/10 commit the baseline ran on (hash): feb8bff

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 88 | 77 | 1 | 10 | 77.5% | 68.4% |
| baseline | UC | 40 | 37 | 2 | 1 | 78.0% | 71.0% |
| baseline | BR | 46 | 40 | 2 | 4 | 76.9% | 67.1% |
| baseline | WF | 23 | 23 | 0 | 0 | 50.6% | 52.6% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| FR-055 | AFR-FTS-043 non-owner-archival-blocked | FR, UC, BR | Confirmed implementation defect | `can_archive_file` in `modules/fts/domain/workflow.py:174` checks `user_id not in {creator_id, current_holder_id}`, permitting non-owner current holders to archive the file, contradicting AFR-FTS-003 and BR-FTS-012 which restrict archival strictly to the file owner/creator. | Pending Student 1 implementation fix in modules/fts/domain/workflow.py and services/archival.py in Phase 4 (Convergence) | Yes |
| UC-029 | FTS-UC-007 Exception Flow 1 | FR, UC, BR | Confirmed implementation defect | Same underlying defect as FR-055 (DEF-001): non-owner recipient attempting archive is permitted rather than denied. | Pending Student 1 implementation fix in modules/fts/domain/workflow.py and services/archival.py in Phase 4 (Convergence) | Yes |
| BR-037 | BR-FTS-012 non-owner-archival-prohibited | FR, UC, BR | Confirmed implementation defect | Same underlying defect as FR-055 (DEF-001): non-owner recipient attempting archive is permitted rather than denied. | Pending Student 1 implementation fix in modules/fts/domain/workflow.py and services/archival.py in Phase 4 (Convergence) | Yes |
| UC-014 | FTS-UC-003 Exception Flow 2 | UC, BR | Confirmed implementation defect | `forward_file` in `modules/fts/services/movements.py:22` does not validate whether `receiver_id` exists as an active employee identifier or is non-empty, permitting forwards to invalid or non-existent recipients without validation refusal. | Pending Student 1 implementation fix in modules/fts/services/movements.py to validate recipient identifier in Phase 4 (Convergence) | Yes |
| BR-020 | BR-FTS-007 recipient-invalid-prohibited | UC, BR | Confirmed implementation defect | Same underlying defect as UC-014 (DEF-002): forward to non-existent or invalid recipient succeeds instead of refusing with validation error. | Pending Student 1 implementation fix in modules/fts/services/movements.py to validate recipient identifier in Phase 4 (Convergence) | Yes |
| FR-008 | AFR-FTS-006 sysadmin-role-administration | FR | Specification ambiguity | Central IAM role administration interface is external to FTS module scope. | Pending pair agreement / integration verification in Phase 4 | Yes |
| FR-009 | AFR-FTS-007 sysadmin-usage-monitoring | FR | Specification ambiguity | System admin usage monitoring statistics interface is not implemented in FTS backend. | Pending pair agreement / interface implementation in Phase 4 | Yes |
| FR-010 | AFR-FTS-008 sysadmin-audit-oversight | FR | Specification ambiguity | System admin audit oversight view across all module files is not implemented in FTS backend. | Pending pair agreement / interface implementation in Phase 4 | Yes |
| UC-034 | FTS-UC-009 Main Flow | UC | Specification ambiguity | Central IAM role assignment interface is external to FTS module scope. | Pending pair agreement / integration verification in Phase 4 | Yes |
| FR-075 | CFR-FTS-011 notification-event-generation | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| FR-076 | AFR-FTS-061 notification-file-received | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| FR-077 | AFR-FTS-062 notification-file-forwarded | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| FR-078 | AFR-FTS-063 notification-file-returned | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| FR-079 | AFR-FTS-064 notification-file-archived | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| FR-080 | AFR-FTS-065 notification-role-assigned | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| FR-081 | AFR-FTS-066 notification-delivery-handshake | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| BR-040 | BR-FTS-013 notify-file-received-and-forwarded | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| BR-041 | BR-FTS-013 notify-file-returned | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| BR-042 | BR-FTS-013 notify-file-archived | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
| BR-043 | BR-FTS-013 notify-role-reassigned | FR, BR | Environment / setup problem | Central notification dispatcher interface is not yet available in FTS, decoupled per blueprint Step 3.8 (h). | Decoupled per blueprint Step 3.8 (h); pending central notification integration in Phase 4 | Yes |
