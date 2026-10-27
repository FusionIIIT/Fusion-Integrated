# Task: rewrite modules/leave/domain/rules.py so that every test in modules/leave/tests/test_rules.py passes

The test file (read-only context) is the exact contract. Rewrite rules.py as ONE complete file. It is pure Python:
import only `datetime`, `decimal`, `typing`/`collections.abc`. NEVER import Django, DRF or Celery (an import-linter contract forbids it).
Use `Decimal` everywhere (never float). Keep module-level docstring short. Max line length 100.

## Required public API (exact names)
- `class RuleViolation(ValueError)`
- `CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")`
- `get_annual_entitlement(category_code: str, is_faculty: bool = False) -> Decimal`
  CL 8, RH 2, SCL 15, COL 20 (everyone); EL 30 non-faculty / 0 faculty; VL 60 faculty / 0 non-faculty. Unknown -> RuleViolation.
- `calculate_leave_days(category_code, start_date, end_date, half_day=None, holidays=frozenset()) -> Decimal`
  1. unknown category -> RuleViolation; end_date < start_date -> RuleViolation.
  2. half_day not in (None, "first", "second") -> RuleViolation.
  3. If half_day is given: category must be "CL" and start_date == end_date, else RuleViolation. The date must be a chargeable
     day (not Saturday/Sunday, not in holidays) else RuleViolation. Result Decimal("0.5").
  4. EL, COL, VL: every calendar day in the inclusive range counts (weekends and holidays included, BR-EL-011).
  5. CL, SCL, RH: count only days that are not Saturday/Sunday (`date.weekday() >= 5`) and not in `holidays`.
  6. If the total is 0 -> RuleViolation("no chargeable days").
- `check_overlap(existing, new_start, new_end, new_half=None) -> bool`
  `existing` = iterable of `(start_date, end_date, half)` tuples, half is None/"first"/"second".
  For each existing leave: if the date ranges do not share a date (existing_start > new_end or existing_end < new_start) skip it.
  Otherwise it overlaps, EXCEPT when new_half and existing half are both set, are different, and both ranges are the same single date
  (new_start == new_end == existing_start == existing_end). Return True on the first overlap, else False.
- `convert_vl_to_el(vl_days: Decimal) -> Decimal`: negative -> RuleViolation; else `vl_days / Decimal(2)`.
- `has_sufficient_balance(balance: Decimal, requested_days: Decimal) -> bool`: any negative argument -> RuleViolation; else `balance >= requested_days`.
- `carry_forward_amount(category_code: str, balance: Decimal) -> Decimal`: unknown -> RuleViolation; CL/RH/SCL/VL -> Decimal("0");
  EL/COL -> balance.
Remove the old `check_half_day_exception` function (its job is now inside check_overlap).
Every function gets a one-line docstring naming its BR-EL id. Use small helper `_require_category(code)`.

## Output rules
Output the COMPLETE file modules/leave/domain/rules.py only. No explanations, no placeholders, no TODOs.
