Review findings on the Phase-1 modules/leave/domain/policy.py: check_applicant_overlap() always returns False and check_substitute_eligibility() always returns True (placeholders), calculate_consumed_days() ignores weekends and half days, EL is offered to faculty although BR-EL-005 limits it to non-faculty, and the VL-to-EL rate is inverted.

Rewrite modules/leave/domain/policy.py following the "domain/policy.py" section of DESIGN.md (read-only) and the business rules file (read-only). It must be pure Python: import only datetime, decimal and typing (no Django, DRF or Celery).

Define exactly:
- class PolicyError(Exception)
- CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")
- ENTITLEMENT: dict mapping each category to (days_per_year: Decimal, faculty_allowed: bool, staff_allowed: bool, carries_forward: bool) with the values in DESIGN.md
- CONTINUOUS = {"EL", "COL", "VL"}
- def entitlement(category: str, kind: str) -> Decimal | None
- def count_days(category: str, start: date, end: date, half_day: str = "none") -> Decimal
- def overlaps(a_start: date, a_end: date, a_half: str, b_start: date, b_end: date, b_half: str) -> bool
- def unit_head_is_final(category: str) -> bool

Raise PolicyError for an unknown category, end before start, or a half day that is not a single-day CL. Put a one-line comment with the BR-EL id where each rule is enforced. Write the whole file. Do not ask for more files.
