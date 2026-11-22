# Spec tests: psm

**Student 1 (Builder):** J Yasaswin (24BCS096)  
**Student 2 (Auditor / Spec Tester):** MV Siva Poojith (24BCS157)  
**Design commit:** `363a81d` test(psm): freeze specification-based test designs for FR, UC, BR, and WF  
**Student 1's 10/10 commit the baseline ran on:** `04b11ad` docs(psm): add quality report for Purchase and Stores Management  

---

## Results

| Run | Strategy | Cases | Passed | Failed | Skipped | Line % | Branch % |
|---|---|---|---|---|---|---|---|
| baseline | FR | 92 | 85 | 7 | 0 | 88.4% | 82.1% |
| baseline | UC | 64 | 59 | 5 | 0 | 89.2% | 83.5% |
| baseline | BR | 54 | 48 | 6 | 0 | 91.0% | 86.4% |
| baseline | WF | 42 | 39 | 3 | 0 | 92.5% | 88.0% |
| Q1 (final) | FR | 92 | 92 | 0 | 0 | 94.6% | 90.2% |
| Q1 (final) | UC | 64 | 64 | 0 | 0 | 95.1% | 91.0% |
| Q1 (final) | BR | 54 | 54 | 0 | 0 | 96.3% | 92.8% |
| Q1 (final) | WF | 42 | 42 | 0 | 0 | 96.8% | 93.4% |

---

## Failures and skips

| Test id | Source id | Strategies | Category | Evidence | Outcome (fixing commit, covering test, or agreed reading with the spec sentence) | Open? |
|---|---|---|---|---|---|---|
| TC-FR-003, TC-FR-022 | AFR-PSM-003, AFR-PSM-022 | FR, UC, BR | Confirmed implementation defect | DEF-PSM-001: Duplicate indent detection | Fixed by Student 1 in indent service duplicate validation; verified passing in Q1 | No |
| TC-FR-014, TC-FR-031 | AFR-PSM-014, AFR-PSM-031 | FR, UC, BR, WF | Confirmed implementation defect | DEF-PSM-002: Stock reservation over-allocation | Fixed by Student 1 via reservation check `qty <= available` and DB constraint `psm_stock_reserved_lte_on_hand` | No |
| TC-BR-012, TC-WF-010 | BR-PSM-010, BW-PSM-03 | BR, WF | Confirmed implementation defect | DEF-PSM-003: High-value approval routing exact threshold boundary | Fixed by Student 1 in threshold policy (`>= 250000.00` requires Director approval) | No |
| TC-FR-058, TC-WF-022 | AFR-PSM-058, BW-PSM-06 | FR, UC, BR, WF | Confirmed implementation defect | DEF-PSM-004: Discrepancy report payment hold state freeze | Fixed by Student 1 in GRN service auto-raising `OPEN_HOLD_PAYMENT` discrepancy on goods rejection | No |
| TC-FR-045, TC-BR-018 | AFR-PSM-045, BR-PSM-012 | FR, BR | Confirmed implementation defect | DEF-PSM-005: Unverified vendor PO issuance gate | Fixed by Student 1 in PO service via `validate_vendor_verified_for_po()` | No |
