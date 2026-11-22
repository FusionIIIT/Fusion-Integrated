# Spec tests: vms

Student 1 (git author name): Krishna Rai
Student 2 (git author name): Ankita Jaiswal
Design commit (hash and subject): 235b425 test(vms): freeze spec test designs (FR, UC, BR, WF)
Baseline commit (hash and subject): 41db06f test(vms): add baseline spec tests and triage log (FR, UC, BR, WF)
Student 1's 10/10 commit the baseline ran on (hash): 01d5c78

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 20 | 14 | 6 | 0 | 69% | 89% |
| baseline | UC | 16 | 11 | 5 | 0 | 48% | 89% |
| baseline | BR | 14 | 12 | 2 | 0 | 49% | 91% |
| baseline | WF | 10 | 8 | 2 | 0 | 47% | 93% |
| Q2 | FR | 20 | 20 | 0 | 0 | 71% | 89% |
| Q2 | UC | 16 | 16 | 0 | 0 | 49% | 89% |
| Q2 | BR | 14 | 14 | 0 | 0 | 50% | 91% |
| Q2 | WF | 10 | 10 | 0 | 0 | 47% | 93% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| TC-FR-004 | VMS-CFR-005 / VMS-AFR-006 | FR | Test-generation / test-implementation problem | AttributeError: 'GateLog' has no attribute 'event_type' | Updated test assertion to inspect GateLog.action | No |
| TC-FR-006 | VMS-CFR-007 / VMS-AFR-009 | FR | Test-generation / test-implementation problem | AttributeError: 'BlacklistEntry' has no attribute 'status' | Updated test assertion to inspect BlacklistEntry.is_active | No |
| TC-FR-008 | VMS-CFR-010 / VMS-AFR-013 | FR | Test-generation / test-implementation problem | ImportError: get_approvals_for_host | Imported list_pending_approvals_for_host selector | No |
| TC-FR-012 | VMS-CFR-013 / VMS-AFR-020 | FR | Test-generation / test-implementation problem | Failed: DID NOT RAISE PassExpiredError | Used verify_qr_and_check_in service endpoint where expiry is enforced | No |
| TC-FR-013 | VMS-CFR-014 / VMS-AFR-024 | FR | Test-generation / test-implementation problem | Failed: DID NOT RAISE BlacklistMatchError | Used verify_qr_and_check_in service endpoint where blacklist check is enforced | No |
| TC-FR-014 | VMS-CFR-015 / VMS-AFR-021 | FR | Specification ambiguity | AssertionError: assert 'completed' == 'checked_out' | Agreed reading: visit lifecycle terminal state for check-out is 'completed' (VisitState.COMPLETED) | No |
| TC-UC-004 | VMS-UC-005 Main Flow | UC | Test-generation / test-implementation problem | ImportError: get_approvals_for_host | Imported list_pending_approvals_for_host selector | No |
| TC-UC-009 | VMS-UC-020 Exception Flow E1 | UC | Test-generation / test-implementation problem | Failed: DID NOT RAISE PassExpiredError | Used verify_qr_and_check_in service endpoint where expiry is enforced | No |
| TC-UC-010 | VMS-UC-021 Main Flow | UC | Specification ambiguity | AssertionError: assert 'completed' == 'checked_out' | Agreed reading: visit lifecycle terminal state for check-out is 'completed' (VisitState.COMPLETED) | No |
| TC-UC-015 | VMS-UC-027 Main Flow | UC | Test-generation / test-implementation problem | AttributeError: 'EmergencyMuster' has no attribute 'resolved_at' | Inspect resolved status and ended_at timestamp | No |
| TC-UC-016 | VMS-UC-036 Main Flow | UC | Specification ambiguity | AssertionError: assert 'completed' == 'checked_out' | Agreed reading: visit terminal state is 'completed' | No |
| TC-BR-003 | VMS-BR-004 Quorum Match | BR | Test-generation / test-implementation problem | AssertionError: assert False is True | Fixed test fixture name matching ("John Doe") | No |
| TC-BR-006 | VMS-BR-008 Pass Expiry | BR | Test-generation / test-implementation problem | TypeError: cannot unpack non-iterable bool object | check_overstay returns boolean | No |
| TC-WF-001 | BW-VMS-01 Full Lifecycle | WF | Specification ambiguity | AssertionError: assert 'completed' == 'checked_out' | Agreed reading: terminal checkout state is 'completed' | No |
| TC-WF-005 | BW-VMS-05 Early Termination | WF | Specification ambiguity | AssertionError: assert 'completed' == 'checked_out' | Agreed reading: terminal checkout state is 'completed' | No |
