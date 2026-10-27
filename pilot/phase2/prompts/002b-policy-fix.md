Review of policy.py from task 002 found these defects. Fix only these, with SEARCH/REPLACE edits:

1. count_days() is wrong for CL, RH and SCL. It sets days to the total calendar days and then ADDS one for every weekday again, so Monday-Tuesday gives 4 instead of 2. It also advances the loop with `current += date(1)`, which raises TypeError. Fix: for categories not in CONTINUOUS, start days at Decimal("0") and count only dates with weekday() < 5, advancing with `current += timedelta(days=1)` (import timedelta from datetime). For CONTINUOUS categories keep days = (end - start).days + 1.
2. For a half-day request (half_day != "none"), return Decimal("0.5") directly (BR-EL-010) instead of multiplying.
3. In ENTITLEMENT, the faculty_allowed, staff_allowed and carries_forward values must be the booleans True/False, not Decimal("1")/Decimal("0").
4. Remove the unused ROUND_HALF_UP import.
5. entitlement() returns None for any kind other than "faculty" or "staff", so an applicant whose kind is "employee" or "" gets no leave. Per DESIGN.md, kind "faculty" means faculty and ANY other kind means staff: replace the `elif kind == "staff":` branch with an `else:` branch that uses staff_allowed, and remove the final `return None`.

Do not change anything else.
