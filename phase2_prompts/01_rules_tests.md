# Task: write pytest unit tests for modules/leave/domain/rules.py (tests ONLY, file: modules/leave/tests/test_rules.py)

You are writing tests for the NEW rules API below. The implementation is written in the next step, so write the tests against
this exact API. The rules module is pure Python (no Django, no database). Use plain `pytest` functions and `pytest.raises`.
Import with: `from modules.leave.domain import rules` and use `from datetime import date` and `from decimal import Decimal`.

## API under test (exact names, signatures, behaviour)
- `rules.RuleViolation` : exception class (subclass of ValueError).
- `rules.CATEGORIES` : tuple `("CL", "RH", "SCL", "EL", "COL", "VL")`.
- `rules.get_annual_entitlement(category_code, is_faculty=False) -> Decimal`
  - CL=8, RH=2, SCL=15, COL=20 for everyone (BR-EL-002/003/004/009).
  - EL = 30 for non-faculty, 0 for faculty (BR-EL-005).
  - VL = 60 for faculty, 0 for non-faculty (BR-EL-006).
  - unknown code (e.g. "XX") raises `RuleViolation`.
- `rules.calculate_leave_days(category_code, start_date, end_date, half_day=None, holidays=frozenset()) -> Decimal`
  - `half_day` is None, "first" or "second".
  - end_date before start_date raises RuleViolation. Unknown category raises RuleViolation.
  - BR-EL-010: half_day is only allowed for CL and only when start_date == end_date; result is Decimal("0.5").
    Half day for any other category, or on a multi-day range, raises RuleViolation. Any half_day value other than None/"first"/"second" raises RuleViolation.
  - BR-EL-011: for EL, COL, VL every calendar day in the inclusive range counts, including weekends and holidays.
  - BR-EL-011: for CL, SCL, RH, Saturdays, Sundays and dates in `holidays` do NOT count.
  - If the result would be 0 days (for example a CL on a Sunday) raise RuleViolation.
- `rules.check_overlap(existing, new_start, new_end, new_half=None) -> bool`
  - `existing` is an iterable of tuples `(start_date, end_date, half)` where half is None (full days) or "first"/"second".
  - Returns True if the new request overlaps any existing one (BR-EL-012).
  - Date ranges overlap when they share at least one calendar date (ends are inclusive).
  - EXCEPTION: if the new request and the existing one are both half days, both on the same single date, and in DIFFERENT halves ("first" vs "second"), they do NOT overlap.
  - Same half on the same date overlaps. A half day on a date inside an existing multi-day leave overlaps. A half day vs a full day on the same date overlaps.
- `rules.convert_vl_to_el(vl_days) -> Decimal` : 2 VL = 1 EL, fractions kept (BR-EL-007). Decimal("5") -> Decimal("2.5"). Negative input raises RuleViolation.
- `rules.has_sufficient_balance(balance, requested_days) -> bool` : True when `balance >= requested_days`. Negative inputs raise RuleViolation.
- `rules.carry_forward_amount(category_code, balance) -> Decimal` (year end):
  - CL, RH, SCL lapse -> Decimal("0") (BR-EL-002/003/004). EL and COL carry forward the whole balance (BR-EL-005/009).
  - VL never carries forward as VL -> Decimal("0") (BR-EL-007).
  - unknown category raises RuleViolation.

## Tests required (at least these; name them clearly)
Entitlements for all 6 categories incl. faculty vs non-faculty EL/VL, unknown category.
Day counting: EL over a weekend (Fri 2026-10-23 to Mon 2026-10-26 = Decimal("4")); the same range for CL = Decimal("2");
CL single weekday = 1; CL half day = 0.5; half day on multi-day range raises; half day on EL raises; bad half value raises;
end before start raises; CL on Sunday 2026-10-25 raises; a holiday inside a CL range is not counted.
Overlap: disjoint dates false; touching end/start date true; first-half vs second-half same date false;
first vs first true; half day inside a multi-day leave true; half day vs full day same date true; empty list false.
VL->EL: 5 -> 2.5, 1 -> 0.5, 0 -> 0, negative raises. Balance: equal true, less false, negative raises.
Carry forward: CL/RH/SCL/VL -> 0, EL/COL -> full balance, unknown raises.

## Output rules
Output the COMPLETE file modules/leave/tests/test_rules.py only. No explanations, no placeholders, no TODOs, no commented-out code.
Use Decimal values (e.g. `Decimal("0.5")`), never floats. Do not edit any other file.
