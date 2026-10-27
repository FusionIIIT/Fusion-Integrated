# Task: fix half_day conversion in modules/leave/services/applications.py (output the COMPLETE file)

In `modules/leave/services/applications.py`:
1. `rules.calculate_leave_days` expects `half_day` to be `None` or `"first"` or `"second"` (an empty string `""` raises RuleViolation).
   Before calling `rules.calculate_leave_days`, convert `half_day`:
   ```python
   half_day_val = half_day if half_day in ("first", "second") else None
   days = rules.calculate_leave_days(
       category_code, start_date, end_date, half_day=half_day_val,
       holidays=frozenset(holidays) if holidays else frozenset()
   )
   ```
2. When calling `rules.check_overlap`:
   ```python
   existing_half = existing.half_day if existing.half_day in ("first", "second") else None
   if rules.check_overlap(
       (existing.start_date, existing.end_date, existing_half),
       (start_date, end_date, half_day_val)
   ):
       raise ConflictError(
           "Application overlaps with an existing active leave.",
           code="leave_overlap"
       )
   ```
3. In `apply`, pass `half_day=half_day or ""` when creating `LeaveApplication` (database stores "" for full day).
4. In `transition`, when restoring balance on cancellation, do:
   ```python
   if bal is not None and app.balance_deducted > Decimal("0.0"):
       bal.balance_days += app.balance_deducted
       bal.save(update_fields=["balance_days", "updated_at"])
   app.balance_deducted = Decimal("0.0")
   ```

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs. Max line length 100.
