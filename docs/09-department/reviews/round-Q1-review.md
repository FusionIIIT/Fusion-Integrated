# Review Round Q1 — Spec Test Baseline Findings

**Reviewer:** Student 2 (24BCS126 - Gemini 3.8 Flash)  
**Target Commit:** Student 1 (24BCS026) initial baseline  
**Verdict:** **8/10 — 5 Open Defects Found in BR Spec Suite**  

## Summary
The black-box specification test suite was designed from the spec documents and executed against Student 1's commit. While Student 1's unit tests passed, running the independent Business Rules (`BR`) suite produced **5 failing test cases**.

## Detailed Findings & Defects to Fix

1. **TEST-BR-004 (`BR-DEPT-002-MISMATCH`):**
   - **Spec Rule:** Announcements targeted to specific roles/programs/years must NOT be visible to non-matching users.
   - **Observed:** `announcement_selectors` returns active announcements without filtering viewer scope when queried.
   - **Action Required for Student 1:** Implement `relevant_announcements()` selector with role, program, and academic year filtering.

2. **TEST-BR-005 (`BR-DEPT-004-HOD-EDIT`):**
   - **Spec Rule:** HOD has exclusive authority to edit published department announcements.
   - **Observed:** Service module lacks `edit()` or `update_announcement()` function for HOD editing.
   - **Action Required for Student 1:** Implement `edit()` in `services.announcements` validating actor role is HOD.

3. **TEST-BR-015 (`BR-DEPT-007-UNAPPROVED-PROHIBITED`):**
   - **Spec Rule:** Stock request issuance is strictly prohibited unless approved by HOD.
   - **Observed:** `StockRequest.clean()` allows setting status to `ISSUED` even without prior HOD decision.
   - **Action Required for Student 1:** Raise `ValidationError` in `StockRequest.clean()` if status is `ISSUED` without `decided_at` and HOD approval.

4. **TEST-BR-028 (`BR-DEPT-015-EXCEEDS-PROHIBITED`):**
   - **Spec Rule:** Requesting quantity greater than current available inventory is prohibited.
   - **Observed:** Requests with `requested_quantity > item.quantity` are accepted without validation.
   - **Action Required for Student 1:** Add inventory boundary check in `StockRequest.clean()` raising `ValidationError`.

5. **TEST-BR-030 (`BR-DEPT-016-DECREMENT`):**
   - **Spec Rule:** Issuing stock must automatically decrement the inventory quantity.
   - **Observed:** Changing status to `ISSUED` and saving leaves inventory quantity unchanged.
   - **Action Required for Student 1:** Update `StockRequest.save()` to decrement `item.quantity` upon transition to `ISSUED`.

Please pull `docs/09-department/spec-tests/triage.md`, apply the fixes, and push commit for Round Q2 re-testing.
