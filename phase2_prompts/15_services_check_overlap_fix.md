# Task: fix check_overlap call in modules/leave/services/applications.py (output the COMPLETE file)

In `modules/leave/services/applications.py`, `rules.check_overlap` has the signature:
`rules.check_overlap(existing: Iterable[Tuple[date, date, Optional[str]]], new_start: date, new_end: date, new_half: Optional[str] = None) -> bool`

Replace the overlap check block in `apply` with:
```python
    # Overlap check
    qs = LeaveApplication.objects.filter(user_id=user_id).exclude(
        status__in=sm.TERMINAL
    )
    existing_leaves = [
        (
            existing.start_date,
            existing.end_date,
            existing.half_day if existing.half_day in ("first", "second") else None,
        )
        for existing in qs
    ]
    if rules.check_overlap(existing_leaves, start_date, end_date, half_day_val):
        raise ConflictError(
            "Application overlaps with an existing active leave.",
            code="leave_overlap"
        )
```

Keep all other code in the file completely intact. Output the COMPLETE file only.
Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
