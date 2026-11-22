# Spec tests: vms
Student 1 (git author name): Yash Rahul Kondane
Student 2 (git author name): Vankayalapati Yaswanth
Design commit (hash and subject): eadb2ee test(vms): freeze specification-derived test designs for FR, UC, BR and WF
Baseline commit (hash and subject): 4b87c82 test(vms): implement executable spec tests and record baseline results
Student 1's 10/10 commit the baseline ran on (hash): f62fcac feat(vms): implement visitor management system module, API, and client UI

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 5 | 5 | 0 | 0 | 56.0% | 52.0% |
| baseline | UC | 4 | 4 | 0 | 0 | 55.0% | 50.0% |
| baseline | BR | 5 | 3 | 2 | 0 | 57.0% | 53.0% |
| baseline | WF | 2 | 1 | 1 | 0 | 55.0% | 51.0% |
| final | FR | 5 | 5 | 0 | 0 | 62.0% | 52.0% |
| final | UC | 4 | 4 | 0 | 0 | 60.0% | 50.0% |
| final | BR | 5 | 5 | 0 | 0 | 64.0% | 53.0% |
| final | WF | 2 | 2 | 0 | 0 | 61.0% | 51.0% |
| final | ALL (Expanded) | 296 | 296 | 0 | 0 | 97.0% | 90.0% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| BR-TEST-003 | VMS-BR-051 | BR | Confirmed implementation defect | Disqualifying blacklist check was bypassed when visitor phone number contained formatting whitespace or country prefixes | Fixed in commit 6b10e56: added normalized phone/ID lookups in check_is_blacklisted before request creation | No |
| BR-TEST-005 | VMS-BR-190 | BR | Specification ambiguity | Spec did not specify whether valid arrival window [valid_from, valid_to] is inclusive or exclusive on boundary limits | Agreed reading: window is inclusive [valid_from <= now <= valid_until] as per security access policy; enforced in validate_pass_gate_access | No |
| WF-TEST-002 | BW-VMS-01 | WF | Confirmed implementation defect | Double checkout attempt on already completed visit log raised unhandled exception rather than structured domain transition error | Fixed in commit 6b10e56: added validate_checkout_transition guard ensuring status must be strictly ON_SITE | No |
