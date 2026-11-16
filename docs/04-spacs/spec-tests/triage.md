# Spec tests: spacs

Student 1 (git author name): Manvendra Singh  
Student 2 (git author name): Kasu Karunya Reddy  
Design commit (hash and subject): `02956eb` test(spacs): freeze specification test designs (FR, UC, BR, WF)  
Baseline commit (hash and subject): `6e5a19e` test(spacs): record spec tests baseline and triage log  
Student 1's 10/10 commit the baseline ran on (hash): `0251f41`  

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Baseline | FR | 47 | 46 | 1 | 0 | 57.42% | 47.22% |
| Baseline | UC | 11 | 11 | 0 | 0 | 58.00% | 43.89% |
| Baseline | BR | 20 | 20 | 0 | 0 | 24.94% | 33.33% |
| Baseline | WF | 8 | 8 | 0 | 0 | 51.53% | 28.33% |

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|:---|:---|:---|:---|:---|:---|:---:|
| `TEST-FR-026` | `AFR-SPACS-026` | `FR` | Confirmed implementation defect | `AssertionError: assert False where False = filter(recipient_user_id=25, event_type='sla_reminder').exists()` | DEF-SPACS-001: Pending Student 1 fix in `modules/spacs/domain/rules.py` to add `"sla_reminder"` to `SIGNIFICANT_EVENTS` | Yes |
