# Spec tests: oap

Student 1 (git author name): Nirvan Jain
Student 2 (git author name): Rounak Agarwal
Design commit (hash and subject): 179f020c60b23c057260537c608fc0f6037e72ba Freeze spec test designs (FR, UC, BR, WF)
Baseline commit (hash and subject): cd2c584742a78f6ea49a18d1844bfe1009149479 Add spec test suites (FR, UC, BR, WF), baseline results, and triage log
Student 1's 10/10 commit the baseline ran on (hash): 0044813b501239464b9f75eebef87e2d0c166d7c

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 63 | 60 | 0 | 3 | 85.33% | 48.18% |
| baseline | UC | 60 | 60 | 0 | 0 | 86.94% | 53.64% |
| baseline | BR | 34 | 34 | 0 | 0 | 83.09% | 45.45% |
| baseline | WF | 13 | 13 | 0 | 0 | 80.14% | 37.27% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with spec sentence) |
|---------|-----------|------------|----------|----------|------------------------------------------------------------------------------|
| TEST-FR-033, TEST-FR-034, TEST-FR-035 | CFR-OAP-009, AFR-OAP-023, AFR-OAP-024, AFR-OAP-025 | FR | Confirmed implementation defect | IAM module does not define roles/designations for Department, Academic Section, or Student Section verifiers (recorded as architectural Gap G2 in module blueprint). Tests skipped pending IAM designation provisioning or fallback mapping. | Skipped under Gap G2; to be addressed in Step 9 triage resolution. |
