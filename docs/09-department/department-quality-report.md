# Department Module Quality Report (Post-Q1 Corrections)

- **Module Name:** Department (DEPT)
- **Module Code:** `department`
- **Docs Folder:** `docs/09-department/`
- **Builder (Student 1):** 24BCS026 (Claude 3.7 Sonnet)
- **Reviewer (Student 2):** 24BCS126 (Gemini 3.8 Flash)
- **Status:** **All 5 Baseline Defects Resolved**

## Q1 Findings Resolution
1. **TEST-BR-004:** Added `relevant_announcements()` selector with multi-attribute audience filtering.
2. **TEST-BR-005:** Added `edit()` / `update()` in `services.announcements` guarded by `_require_hod()`.
3. **TEST-BR-015:** Added status check in `StockRequest.clean()` ensuring unapproved requests cannot be set to `ISSUED`.
4. **TEST-BR-028:** Added inventory check in `StockRequest.clean()` raising `ValidationError` when requested quantity exceeds inventory.
5. **TEST-BR-030:** Added automated decrement of `item.quantity` in `StockRequest.save()` on status transition to `ISSUED`.

Ready for Student 2 Round Q2 verification.
