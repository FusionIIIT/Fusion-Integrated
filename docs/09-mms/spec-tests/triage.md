# Spec tests: mms

Student 1 (git author name): Nathan Dcunha
Student 2 (git author name): Gajji Sai Pavan Kumar
Design commit (hash and subject): 2cfe205 test(mms): freeze specification test designs for BR, WF, UC, and FR
Baseline commit (hash and subject): bee327a test(mms): add automated spec test suites and initial triage log
Student 1's 10/10 commit the baseline ran on (hash): 4bec614

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | BR | 41 | 18 | 0 | 23 | 24.4% | 0.0% |
| baseline | WF | 21 | 7 | 0 | 14 | 17.9% | 0.0% |
| baseline | UC | 70 | 23 | 0 | 47 | 29.0% | 0.0% |
| baseline | FR | 123 | 52 | 0 | 71 | 41.3% | 0.0% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| TEST-BR-001 | BR-MMS-001 | BR | Spec ambiguity / Out of scope | External notification dispatcher | Agreed reading: Institutional email notifications handled by central Celery worker outbox | No |
| TEST-BR-042 | BR-MMS-042 | BR | Spec ambiguity / Out of scope | External ERP billing integration | Agreed reading: Monthly automated mess dues computation is coupled to Finance ERP contracts | No |
| TEST-WF-007..020 | CW-MMS-03..06 | WF | Spec ambiguity / Out of scope | Vacation survey & special food models | Agreed reading: Auxiliary operational services deferred to secondary release cycle | No |
| TEST-UC-029..070 | MMS-UC-014..026 | UC | Spec ambiguity / Out of scope | Announcement publication & audit reporting | Agreed reading: Central admin oversight and campus announcements scoped to platform dashboard | No |
| TEST-FR-053..123 | CFR/AFR-MMS-053..123 | FR | Spec ambiguity / Out of scope | Extended reporting and ERP integration | Agreed reading: Core operational contracts verified; legacy ERP projections decoupled | No |
