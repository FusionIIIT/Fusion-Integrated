# Spec tests: spacs

Student 1 (git author name): Sunkara Nandan
Student 2 (git author name): Pulkit Sharma
Design commit (hash and subject): d988c76 Spec: freeze FR, UC, BR, WF test designs for spacs
Baseline commit (hash and subject): e736e94 Tests: add automated spec test suites and triage log for spacs
Student 1's 10/10 commit the baseline ran on (hash): 4c268d4 SPACS: implement scholarships and awards module with full architectural documentation

## Results
| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|-----|----------|-------|--------|--------|---------|--------|----------|
| baseline | FR | 54 | 40 | 14 | 0 | 47.45% | 40.79% |
| baseline | UC | 42 | 32 | 10 | 0 | 47.45% | 40.00% |
| baseline | BR | 38 | 24 | 14 | 0 | 40.01% | 31.05% |
| baseline | WF | 24 | 17 | 7 | 0 | 38.16% | 30.00% |
| final (Q1) | FR | 54 | 54 | 0 | 0 | 78.40% | 68.25% |
| final (Q1) | UC | 42 | 42 | 0 | 0 | 77.15% | 67.50% |
| final (Q1) | BR | 38 | 38 | 0 | 0 | 75.80% | 65.40% |
| final (Q1) | WF | 24 | 24 | 0 | 0 | 74.20% | 64.10% |

## Failures and skips
| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---------|-----------|------------|----------|----------|-----------------------------------------------------------------------------------|-------|
| TC-FR-053 | CFR-SPACS-001 | FR, UC, BR | Confirmed implementation defect | Multiple active drafts permitted concurrently for same scheme/cycle | Fixed in applications.py: enforce cycle-level uniqueness check before draft creation | No |
| TC-UC-003 | UC-SPACS-003 | UC, BR | Confirmed implementation defect | Stale eligibility snapshot retained upon correction resubmission | Fixed in applications.py: re-evaluate snapshot on modify_application resubmit | No |
| TC-BR-003 | BR-SPACS-003 | BR | Confirmed implementation defect | Reusing previously rejected document resets status without check | Fixed in documents.py: reject reuse if prior status was rejected | No |
| TC-WF-BRANCH-06 | CFR-SPACS-015 | WF | Confirmed implementation defect | Missing escalation notification to Convener on scrutiny concern | Fixed in tasks.py & notifications.py: dispatch escalation outbox record | No |
| TC-FR-015 | AFR-SPACS-004 | FR, UC | Confirmed implementation defect | Missing audit trail record on draft fact updates | Fixed in applications.py: record SpacsAuditLog entry on facts modification | No |
| TC-FR-011 | AFR-SPACS-009 | FR, BR | Confirmed implementation defect | Document expiry date validation bypassed during upload | Fixed in documents.py: validate expiry_date >= current_date | No |
| TC-FR-008 | AFR-SPACS-003 | FR, BR | Confirmed implementation defect | Application permitted against deprecated or draft policy | Fixed in applications.py: require policy status == published | No |
| TC-FR-018 | AFR-SPACS-018 | FR, UC, BR | Confirmed implementation defect | Missing mandatory reason validation on correction request | Fixed in applications.py: require non-empty remarks for request_correction | No |
| TC-BR-010 | BR-SPACS-010 | BR, WF | Confirmed implementation defect | Unbounded correction iterations allowed beyond threshold | Fixed in state_machine.py: enforce MAX_CORRECTIONS <= 2 | No |
| TC-FR-012 | BR-SPACS-001 | FR, UC, BR | Confirmed implementation defect | CPI boundary comparison strictly greater than instead of >= | Fixed in eligibility.py: evaluate cpi >= min_cpi inclusively | No |
| TC-FR-013 | BR-SPACS-001 | FR, BR | Confirmed implementation defect | Parental income ceiling boundary evaluated exclusively | Fixed in eligibility.py: evaluate income <= max_income inclusively | No |
| TC-FR-023 | BR-SPACS-006 | FR, WF | Confirmed implementation defect | Assistant permitted direct application terminal decisions | Fixed in applications.py: restrict approved/rejected actions to spacs_convener | No |
| TC-FR-028 | AFR-SPACS-028 | FR, BR, WF | Confirmed implementation defect | Renewal application accepted after published deadline | Fixed in renewal.py: check submission_date <= renewal_window_end | No |
| TC-FR-032 | AFR-SPACS-032 | FR, UC, BR | Confirmed implementation defect | Committee evaluation score allowed outside [0, 100] | Fixed in awards.py: validate 0.0 <= score <= 100.0 | No |
| TC-FR-030 | BR-SPACS-013 | FR, UC, BR | Confirmed implementation defect | Un-empaneled faculty recording evaluation scores | Fixed in awards.py: verify evaluator user is active CommitteeMember | No |
| TC-FR-035 | AFR-SPACS-035 | FR, BR, WF | Confirmed implementation defect | Publication of award results without approval reference | Fixed in awards.py: require non-empty approval_reference before publish | No |
| TC-FR-046 | AFR-SPACS-042 | FR, BR | Confirmed implementation defect | Disciplinary clearance gate not verified prior to approval | Fixed in awards.py: query disciplinary status before award sanction | No |
| TC-FR-037 | AFR-SPACS-037 | FR, UC | Confirmed implementation defect | SLA overdue verification escalation reminder missing | Fixed in tasks.py: trigger SpacsNotification for scrutiny breach | No |
| TC-WF-BRANCH-05 | BW-SPACS-05 | WF | Confirmed implementation defect | Withdrawal of awarded scholarship fails to release slot | Fixed in awards.py: release AwardAllocation slot on applicant withdrawal | No |
| TC-WF-BRANCH-09 | BW-SPACS-09 | WF | Confirmed implementation defect | Split committee vote deadlock unhandled | Fixed in awards.py: route tie vote to Convener casting vote state | No |
| TC-UC-010 | AFR-SPACS-002 | UC | Confirmed implementation defect | Inactive scheme catalogue entry permitted in draft creation | Fixed in applications.py: verify scheme.is_active is True | No |
| TC-UC-026 | CFR-SPACS-013 | UC | Confirmed implementation defect | Bulk clearance check partial atomicity failure | Fixed in awards.py: wrap bulk clearance evaluation in atomic transaction | No |
