# Task: align error message in modules/leave/services/applications.py (output the COMPLETE file)

In `modules/leave/services/applications.py`:
When `end_date < start_date`:
Raise ConflictError with exact message:
`raise ConflictError("end_date must be on or after start_date.", code="invalid_dates")`

Keep all other code in the file exactly as is. Output the COMPLETE file only.
Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
